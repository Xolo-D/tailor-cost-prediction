"""
ML Predictor for Tailor Cost Estimation System
University of Zululand – Group 7
Handles loading the trained Random Forest model and making predictions.
"""

import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# Price-per-metre reference (from dataset median values)
FABRIC_PRICE_MAP = {
    'Cotton': 90,
    'Denim': 114,
    'Leather': 275,
    'Linen': 140,
    'Nylon': 70,
    'Polyester': 68,
    'Silk': 173,
    'Wool': 217,
}

GARMENTS = [
    'Blouse', 'Coat', 'Dress', 'Hoodie', 'Jacket',
    'Jersey', 'Shirt', 'Shorts', 'Skirt', 'Suit',
    'Tracksuit', 'Trousers',
]

FABRICS = ['Cotton', 'Denim', 'Leather', 'Linen', 'Nylon', 'Polyester', 'Silk', 'Wool']

# Garment complexity multipliers (derived from dataset analysis)
GARMENT_COMPLEXITY = {
    'Blouse': 1.0, 'Shorts': 1.0, 'Shirt': 1.1, 'Skirt': 1.15,
    'Trousers': 1.2, 'Dress': 1.35, 'Hoodie': 1.4, 'Jersey': 1.3,
    'Jacket': 1.5, 'Tracksuit': 1.6, 'Suit': 1.8, 'Coat': 1.9,
}


class TailorPredictor:
    """Wraps the sklearn pipeline. Falls back to fresh RF if version mismatch."""

    _instance = None
    _model = None
    _dataset = None
    _model_source = 'unknown'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, model_path=None, dataset_path=None):
        """Load or retrain model. Call once at app startup."""
        base_dir = Path(settings.BASE_DIR)
        
        # Set default paths if not provided
        if model_path is None:
            model_path = base_dir / 'estimator' / 'ml' / 'fine_tuned_random_forest_regressor.joblib'
        if dataset_path is None:
            dataset_path = base_dir / 'estimator' / 'ml' / 'group_7_dataset.csv'
        
        # Try to load dataset
        try:
            if os.path.exists(dataset_path):
                self._dataset = pd.read_csv(dataset_path)
                logger.info(f"Dataset loaded: {len(self._dataset)} rows")
            else:
                logger.warning(f"Dataset not found at {dataset_path}")
        except Exception as e:
            logger.warning(f"Could not load dataset: {e}")
        
        # Try loading the saved joblib first
        try:
            import joblib
            if os.path.exists(model_path):
                self._model = joblib.load(model_path)
                self._model_source = 'saved_joblib'
                logger.info(f"✅ Loaded saved model from {model_path}")
                return self
            else:
                logger.warning(f"Model file not found at {model_path}")
        except Exception as e:
            logger.warning(f"Could not load saved model ({e})")
        
        # If model doesn't exist, try to retrain from dataset
        if self._dataset is not None:
            try:
                self._retrain(model_path)
                self._model_source = 'retrained'
                logger.info("✅ Model retrained successfully")
                return self
            except Exception as e:
                logger.warning(f"Could not retrain model: {e}")
        
        # Final fallback - use calculation only
        self._model = None
        self._model_source = 'fallback'
        logger.info("⚠️ Using fallback calculation mode (no ML model)")
        
        return self

    def _retrain(self, save_path=None):
        """Train a Random Forest pipeline on the dataset"""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.pipeline import Pipeline
        from sklearn.compose import ColumnTransformer
        from sklearn.preprocessing import OneHotEncoder
        import joblib
        
        df = self._dataset
        
        # Features: Garment, Fabric_Type, Fabric_m, Price_per_m
        X = df[['Garment', 'Fabric_Type', 'Fabric_m', 'Price_per_m']]
        y = df['Total_Cost_ZAR']
        
        cat_features = ['Garment', 'Fabric_Type']
        num_features = ['Fabric_m', 'Price_per_m']
        
        preprocessor = ColumnTransformer([
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_features),
            ('num', 'passthrough', num_features),
        ])
        
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('regressor', RandomForestRegressor(
                n_estimators=200,
                max_depth=12,
                min_samples_split=4,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )),
        ])
        
        pipeline.fit(X, y)
        self._model = pipeline
        logger.info(f"Model retrained. R² on full data: {pipeline.score(X, y):.4f}")
        
        if save_path:
            retrain_path = str(save_path).replace('.joblib', '_retrained.joblib')
            joblib.dump(pipeline, retrain_path)
            logger.info(f"Retrained model saved to {retrain_path}")

    def predict(self, garment: str, fabric_type: str, fabric_m: float):
        """Run prediction and return total cost"""
        
        price_per_m = FABRIC_PRICE_MAP.get(fabric_type, 100)
        material_cost = fabric_m * price_per_m
        
        # Try ML prediction if model exists and dataset exists
        if self._model is not None and self._dataset is not None:
            try:
                input_df = pd.DataFrame([{
                    'Garment': garment,
                    'Fabric_Type': fabric_type,
                    'Fabric_m': fabric_m,
                    'Price_per_m': price_per_m,
                }])
                total_cost = float(self._model.predict(input_df)[0])
                logger.info(f"ML prediction: {total_cost}")
                return max(total_cost, material_cost)
            except Exception as e:
                logger.warning(f"Model predict failed ({e}), using formula fallback")
        
        # Fallback formula calculation
        multiplier = GARMENT_COMPLEXITY.get(garment, 1.3)
        labour_base = 80 + (fabric_m * 20)
        total_cost = material_cost * multiplier + labour_base
        total_cost = total_cost * 1.08  # Add 8% overhead
        
        logger.info(f"Fallback prediction: {total_cost}")
        return round(total_cost, 2)

    def predict_full(self, garment: str, fabric_type: str, fabric_m: float) -> dict:
        """Run prediction and return full estimation breakdown"""
        
        total_cost = self.predict(garment, fabric_type, fabric_m)
        price_per_m = FABRIC_PRICE_MAP.get(fabric_type, 100)
        material_cost = round(fabric_m * price_per_m, 2)
        labour_cost = round(total_cost * 0.32, 2)
        overhead_cost = round(total_cost * 0.08, 2)
        
        return {
            'total_cost': total_cost,
            'material_cost': material_cost,
            'labour_cost': labour_cost,
            'overhead_cost': overhead_cost,
            'price_per_m': price_per_m,
            'fabric_m': fabric_m,
            'garment': garment,
            'fabric_type': fabric_type,
            'model_source': self._model_source,
        }

    @property
    def is_loaded(self):
        return self._model is not None or self._model_source == 'fallback'


# Singleton instance
predictor = TailorPredictor()
