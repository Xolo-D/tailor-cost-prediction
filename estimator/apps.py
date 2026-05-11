from .ml.predictor import predictor

@login_required
def predict_ajax(request):
    if request.method == 'POST':
        try:
            garment = request.POST.get('garment')
            fabric_type = request.POST.get('fabric_type')
            fabric_m = float(request.POST.get('fabric_m'))
            
            # Ensure model is loaded
            predictor.load()
            
            # Get prediction
            result = predictor.predict_full(garment, fabric_type, fabric_m)
            
            # Save to history
            EstimateHistory.objects.create(
                user=request.user,
                garment=garment,
                fabric_type=fabric_type,
                fabric_m=fabric_m,
                material_cost=result['material_cost'],
                labour_cost=result['labour_cost'],
                overhead_cost=result['overhead_cost'],
                total_cost=result['total_cost']
            )
            
            return JsonResponse({
                'success': True,
                'total_cost': result['total_cost'],
                'material_cost': result['material_cost'],
                'labour_cost': result['labour_cost'],
                'overhead': result['overhead_cost'],
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
