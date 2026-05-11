from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from .forms import RegisterForm, LoginForm, ProfileUpdateForm, EstimateForm
from .models import TailorProfile, EstimateHistory
from .ml.predictor import predictor

logger = logging.getLogger(__name__)

# Create your views here.

def login_view(request):
    if request.user.is_authenticated:
        return redirect('estimator')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            
            try:
                from django.contrib.auth.models import User
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                
                if user is not None:
                    login(request, user)
                    return redirect('estimator')
                else:
                    messages.error(request, 'Invalid password')
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email')
    else:
        form = LoginForm()
    
    return render(request, 'estimator/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('estimator')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Create TailorProfile
                TailorProfile.objects.create(
                    user=user,
                    institution=form.cleaned_data.get('institution', ''),
                    phone=form.cleaned_data.get('phone', ''),
                    address=form.cleaned_data.get('address', '')
                )
                
                login(request, user)
                messages.success(request, 'Registration successful!')
                return redirect('estimator')
            except IntegrityError:
                messages.error(request, 'Email already exists')
            except Exception as e:
                messages.error(request, f'Registration error: {str(e)}')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = RegisterForm()
    
    return render(request, 'estimator/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def estimator_view(request):
    form = EstimateForm()
    
    # Get user's profile
    try:
        profile = TailorProfile.objects.get(user=request.user)
    except TailorProfile.DoesNotExist:
        profile = TailorProfile.objects.create(user=request.user)
    
    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'estimator/estimator.html', context)

@login_required
@csrf_exempt
def predict_ajax(request):
    if request.method == 'POST':
        try:
            # Get data from POST request
            garment = request.POST.get('garment')
            fabric_type = request.POST.get('fabric_type')
            fabric_m = float(request.POST.get('fabric_m', 0))
            
            logger.info(f"Prediction request: {garment}, {fabric_type}, {fabric_m}")
            
            if not garment or not fabric_type or fabric_m <= 0:
                return JsonResponse({
                    'success': False, 
                    'error': 'Please provide valid garment, fabric type, and meters'
                })
            
            # Ensure predictor is loaded
            predictor.load()
            
            # Get prediction
            total_cost = predictor.predict(garment, fabric_type, fabric_m)
            
            # Calculate breakdown
            fabric_prices = {
                'Cotton': 90, 'Denim': 114, 'Leather': 275,
                'Linen': 140, 'Nylon': 70, 'Polyester': 68,
                'Silk': 173, 'Wool': 217,
            }
            
            price_per_m = fabric_prices.get(fabric_type, 100)
            material_cost = fabric_m * price_per_m
            labour_cost = total_cost * 0.32
            overhead_cost = total_cost * 0.08
            
            # Verify total matches
            calculated_total = material_cost + labour_cost + overhead_cost
            if abs(calculated_total - total_cost) > 1:
                total_cost = calculated_total
            
            # Save to history
            EstimateHistory.objects.create(
                user=request.user,
                garment=garment,
                fabric_type=fabric_type,
                fabric_m=fabric_m,
                material_cost=round(material_cost, 2),
                labour_cost=round(labour_cost, 2),
                overhead_cost=round(overhead_cost, 2),
                total_cost=round(total_cost, 2)
            )
            
            response_data = {
                'success': True,
                'total_cost': round(total_cost, 2),
                'material_cost': round(material_cost, 2),
                'labour_cost': round(labour_cost, 2),
                'overhead': round(overhead_cost, 2),
                'price_per_m': price_per_m,
                'fabric_m': fabric_m,
                'garment': garment,
                'fabric_type': fabric_type,
            }
            
            logger.info(f"Prediction response: {response_data}")
            return JsonResponse(response_data)
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback_str = traceback.format_exc()
            logger.error(f"Prediction error: {error_msg}")
            logger.error(traceback_str)
            return JsonResponse({
                'success': False, 
                'error': error_msg
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def history_view(request):
    estimates = EstimateHistory.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(estimates, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estimator/history.html', {'page_obj': page_obj})

@login_required
def delete_estimate(request, estimate_id):
    estimate = get_object_or_404(EstimateHistory, id=estimate_id, user=request.user)
    estimate.delete()
    messages.success(request, 'Estimate deleted successfully')
    return redirect('history')

@login_required
def profile_view(request):
    profile, created = TailorProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            
            # Update user details
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.save()
            
            messages.success(request, 'Profile updated successfully')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'estimator/profile.html', context)

# Temporary admin creation view
def create_admin_view(request):
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@test.com', 'admin1234')
        return HttpResponse("Admin created! Username: admin, Password: admin1234")
    return HttpResponse("Admin already exists")

# Health check endpoint for Render
def health_check(request):
    return JsonResponse({'status': 'healthy'})
