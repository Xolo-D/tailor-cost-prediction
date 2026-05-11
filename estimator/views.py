"""
Views for Tailor Cost Prediction System
University of Zululand – Group 7
"""

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.conf import settings

from .forms import LoginForm, RegisterForm, ProfileForm, EstimateForm
from .models import TailorProfile, EstimateHistory
from .ml.predictor import predictor, FABRIC_PRICE_MAP, GARMENTS, FABRICS

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap model on first use
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_model_loaded():
    if not predictor.is_loaded:
        try:
            predictor.load(
                model_path=str(settings.ML_MODEL_PATH),
                dataset_path=str(settings.ML_DATASET_PATH),
            )
        except Exception as e:
            logger.error("Failed to load ML model: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def login_view(request):
    """Login page — uses email as username."""
    if request.user.is_authenticated:
        return redirect('estimator')

    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        email    = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Allow login by email: resolve username from email
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            username = email

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            return redirect('estimator')
        else:
            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'estimator/login.html', {'form': form})


def register_view(request):
    """Registration / Sign Up page."""
    if request.user.is_authenticated:
        return redirect('estimator')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Account created! Welcome, {user.first_name}!')
        return redirect('estimator')
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{error}')

    return render(request, 'estimator/register.html', {'form': form})


def logout_view(request):
    """Log the user out and redirect to login."""
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('login')


# ─────────────────────────────────────────────────────────────────────────────
# CORE ESTIMATOR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def estimator_view(request):
    """Main estimator page with form and result panels."""
    _ensure_model_loaded()

    form        = EstimateForm()
    result      = None
    recent      = EstimateHistory.objects.filter(user=request.user)[:6]
    profile     = _get_or_create_profile(request.user)

    if request.method == 'POST':
        form = EstimateForm(request.POST)
        if form.is_valid():
            garment     = form.cleaned_data['garment']
            fabric_type = form.cleaned_data['fabric_type']
            fabric_m    = form.cleaned_data['fabric_m']

            try:
                result = predictor.predict(garment, fabric_type, fabric_m)

                # Save to history
                EstimateHistory.objects.create(
                    user          = request.user,
                    garment       = garment,
                    fabric_type   = fabric_type,
                    fabric_m      = fabric_m,
                    price_per_m   = result['price_per_m'],
                    material_cost = result['material_cost'],
                    labour_cost   = result['labour_cost'],
                    overhead_cost = result['overhead_cost'],
                    total_cost    = result['total_cost'],
                )
                # Refresh recent list
                recent = EstimateHistory.objects.filter(user=request.user)[:6]

            except Exception as e:
                logger.error("Prediction error: %s", e)
                messages.error(request, 'Prediction failed. Please try again.')

    return render(request, 'estimator/estimator.html', {
        'form':        form,
        'result':      result,
        'recent':      recent,
        'profile':     profile,
        'fabric_prices': FABRIC_PRICE_MAP,
    })


@login_required
@require_POST
def predict_ajax(request):
    """AJAX endpoint for live predictions from the estimator form."""
    _ensure_model_loaded()

    try:
        body        = json.loads(request.body)
        garment     = body.get('garment', '').strip()
        fabric_type = body.get('fabric_type', '').strip()
        fabric_m    = float(body.get('fabric_m', 0))

        if not garment or not fabric_type or fabric_m <= 0:
            return JsonResponse({'error': 'Invalid input'}, status=400)

        if garment not in GARMENTS:
            return JsonResponse({'error': f'Unknown garment: {garment}'}, status=400)
        if fabric_type not in FABRICS:
            return JsonResponse({'error': f'Unknown fabric: {fabric_type}'}, status=400)

        result = predictor.predict(garment, fabric_type, fabric_m)

        # Save to history
        EstimateHistory.objects.create(
            user          = request.user,
            garment       = garment,
            fabric_type   = fabric_type,
            fabric_m      = fabric_m,
            price_per_m   = result['price_per_m'],
            material_cost = result['material_cost'],
            labour_cost   = result['labour_cost'],
            overhead_cost = result['overhead_cost'],
            total_cost    = result['total_cost'],
        )

        return JsonResponse({'success': True, **result})

    except (ValueError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error("AJAX predict error: %s", e)
        return JsonResponse({'error': 'Server error during prediction'}, status=500)


@login_required
@require_POST
def chat_predict(request):
    """
    Natural language chat endpoint.
    Parses messages like 'silk dress 3m' or 'denim jacket 2.5 meters'.
    """
    _ensure_model_loaded()

    try:
        body    = json.loads(request.body)
        message = body.get('message', '').strip().lower()

        garment     = None
        fabric_type = None
        fabric_m    = None

        # Detect garment
        for g in GARMENTS:
            if g.lower() in message:
                garment = g
                break

        # Detect fabric
        for f in FABRICS:
            if f.lower() in message:
                fabric_type = f
                break

        # Detect meters (e.g. "3m", "2.5m", "3 meters", "2.5 metres")
        import re
        m_match = re.search(r'(\d+\.?\d*)\s*m(?:eters?|etres?)?', message)
        if m_match:
            fabric_m = float(m_match.group(1))

        if not all([garment, fabric_type, fabric_m]):
            missing = []
            if not garment:     missing.append('garment type')
            if not fabric_type: missing.append('fabric type')
            if not fabric_m:    missing.append('fabric meters')
            return JsonResponse({
                'success': False,
                'reply': f"I couldn't find the {', '.join(missing)}. "
                         f"Try: \"silk dress 3m\" or \"denim jacket 2.5 meters\".",
            })

        result = predictor.predict(garment, fabric_type, fabric_m)

        EstimateHistory.objects.create(
            user          = request.user,
            garment       = garment,
            fabric_type   = fabric_type,
            fabric_m      = fabric_m,
            price_per_m   = result['price_per_m'],
            material_cost = result['material_cost'],
            labour_cost   = result['labour_cost'],
            overhead_cost = result['overhead_cost'],
            total_cost    = result['total_cost'],
        )

        reply = (
            f"Estimated a {fabric_type} {garment} using {fabric_m}m of fabric — "
            f"Total Cost: R{result['total_cost']:,.2f} | "
            f"Material: R{result['material_cost']:,.2f} | "
            f"Labour: R{result['labour_cost']:,.2f}."
        )

        return JsonResponse({'success': True, 'reply': reply, **result})

    except Exception as e:
        logger.error("Chat predict error: %s", e)
        return JsonResponse({'success': False, 'reply': 'Sorry, an error occurred.'}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def history_view(request):
    """Paginated estimate history for the logged-in tailor."""
    estimates = EstimateHistory.objects.filter(user=request.user)
    profile   = _get_or_create_profile(request.user)

    # Optional filter
    garment_filter = request.GET.get('garment', '')
    fabric_filter  = request.GET.get('fabric', '')
    if garment_filter:
        estimates = estimates.filter(garment=garment_filter)
    if fabric_filter:
        estimates = estimates.filter(fabric_type=fabric_filter)

    from django.core.paginator import Paginator
    paginator = Paginator(estimates, 15)
    page_num  = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page_num)

    # Summary stats
    all_ests  = EstimateHistory.objects.filter(user=request.user)
    total_est = all_ests.count()
    avg_cost  = round(sum(e.total_cost for e in all_ests) / total_est, 2) if total_est else 0
    max_cost  = max((e.total_cost for e in all_ests), default=0)

    return render(request, 'estimator/history.html', {
        'page_obj':       page_obj,
        'profile':        profile,
        'garment_filter': garment_filter,
        'fabric_filter':  fabric_filter,
        'garments':       GARMENTS,
        'fabrics':        FABRICS,
        'total_est':      total_est,
        'avg_cost':       avg_cost,
        'max_cost':       max_cost,
    })


@login_required
def delete_estimate(request, pk):
    """Delete a single estimate from history."""
    estimate = get_object_or_404(EstimateHistory, pk=pk, user=request.user)
    estimate.delete()
    messages.success(request, 'Estimate removed from history.')
    return redirect('history')


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    """Tailor profile page — view and edit."""
    profile = _get_or_create_profile(request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    estimates   = EstimateHistory.objects.filter(user=request.user)
    total_est   = estimates.count()
    total_spend = round(sum(e.total_cost for e in estimates), 2)

    return render(request, 'estimator/profile.html', {
        'form':        form,
        'profile':     profile,
        'total_est':   total_est,
        'total_spend': total_spend,
    })


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_profile(user):
    profile, _ = TailorProfile.objects.get_or_create(user=user)
    if not profile.avatar_initials:
        profile.save()   # triggers auto avatar generation
    return profile
