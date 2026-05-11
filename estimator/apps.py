from django.apps import apps

def predict_ajax(request):
    model = apps.get_app_config('estimator').model
    if model:
        # Use the model for prediction
        prediction = model.predict(input_data)
    else:
        # Fallback logic if model not loaded
        prediction = calculate_fallback_cost(input_data)
