from django.apps import AppConfig

class EstimatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'estimator'
    
    def ready(self):
        """Load ML model when Django starts"""
        try:
            from .ml.predictor import predictor
            predictor.load()
            print("✅ Predictor loaded successfully")
        except Exception as e:
            print(f"Error loading predictor: {e}")
