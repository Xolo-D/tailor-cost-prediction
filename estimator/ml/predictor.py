"""
ML Predictor for Tailor Cost Estimation System
University of Zululand – Group 7

Handles loading the trained Random Forest model and making predictions.
Falls back to retraining from dataset if the joblib version is incompatible.
"""

import os
import logging
import numpy as np
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Price-per-metre reference (from dataset median values) ──────────────────
FABRIC_PRICE_MAP = {
    'Cotton':    90,
    'Denim':     114,
    'Leather':   275,
    'Linen':     140,
    'Nylon':     70,
    'Polyester': 68,
    'Silk':      173,
    'Wool':      217,
}

GARMENTS = [
    'Blouse', 'Coat', 'Dress', 'Hoodie', 'Jacket',
    'Jersey', 'Shirt', 'Shorts', 'Skirt', 'Suit',
    'Tracksuit', 'Trousers',
]

FABRICS = ['Cotton', 'Denim', 'Leather', 'Linen', 'Nylon', 'Polyester', 'Silk', 'Wool']

# Garment complexity multipliers (derived from dataset analysis)
GARMENT_COMPLEXITY = {
    'Blouse':    1.0,
    'Shorts':    1.0,
    'Shirt':     1.1,
    'Skirt':     1.15,
    'Trousers':  1.2,
    'Dress':     1.35,
    'Hoodie':    1.4,
    'Jersey':    1.3,
    'Jacket':    1.5,
    'Tracksuit': 1.6,
    'Suit':      1.8,
    'Coat':      1.9,
}


class TailorPredictor:
    """Wraps the sklearn pipeline. Falls back to a fresh RF if version mismatch."""

    _instance = None
    _model = None
    _dataset: pd.DataFrame = None
    _model_source = 'unknown'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, model_path: str, dataset_path: str):
        """Load or retrain model. Call once at app startup."""
        self._dataset = pd.read_csv(dataset_path)
        logger.info("Dataset loaded: %d rows", len(self._dataset))

        # Try loading the saved joblib first
        try:
            import joblib
            self._model = joblib.load(model_path)
            self._model_source = 'saved_joblib'
            logger.info("Loaded saved model from %s", model_path)
        except Exception as e:
            logger.warning("Could not load saved model (%s). Retraining from dataset…", e)
            self._model = self._retrain(dataset_path, model_path)
            self._model_source = 'retrained'

        return self

    def _retrain(self, dataset_path: str, save_path: str = None):
        """Train a Random Forest pipeline on the dataset and optionally save it."""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.pipeline import Pipeline
        from sklearn.compose import ColumnTransformer
        from sklearn.preprocessing import OneHotEncoder
        import joblib

        df = pd.read_csv(dataset_path)

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
        logger.info("Model retrained. R² on full data: %.4f", pipeline.score(X, y))

        if save_path:
            retrain_path = str(save_path).replace('.joblib', '_retrained.joblib')
            joblib.dump(pipeline, retrain_path)
            logger.info("Retrained model saved to %s", retrain_path)

        return pipeline

    def predict(self, garment: str, fabric_type: str, fabric_m: float) -> dict:
        """
        Run prediction and return full estimation breakdown.

        Returns:
            {
              total_cost, material_cost, price_per_m,
              labour_cost, overhead_cost,
              fabric_m, garment, fabric_type,
              comparables: [ {garment, fabric_type, fabric_m, total_cost, material_cost}, … ]
            }
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call TailorPredictor().load() first.")

        price_per_m = FABRIC_PRICE_MAP.get(fabric_type, 100)
        material_cost = round(fabric_m * price_per_m, 2)

        # Build input dataframe matching training schema
        input_df = pd.DataFrame([{
            'Garment':     garment,
            'Fabric_Type': fabric_type,
            'Fabric_m':    fabric_m,
            'Price_per_m': price_per_m,
        }])

        try:
            total_cost = float(self._model.predict(input_df)[0])
        except Exception as e:
            # Fallback formula if pipeline predict fails
            logger.warning("Model predict failed (%s), using formula fallback", e)
            multiplier = GARMENT_COMPLEXITY.get(garment, 1.3)
            labour_base = 80 + (fabric_m * 20)
            total_cost = material_cost * multiplier + labour_base

        total_cost = round(max(total_cost, material_cost), 2)
        labour_cost = round(max(total_cost - material_cost - (total_cost * 0.08), 0), 2)
        overhead_cost = round(total_cost * 0.08, 2)

        comparables = self._get_comparables(garment, fabric_type, fabric_m, total_cost)

        return {
            'total_cost':    total_cost,
            'material_cost': material_cost,
            'price_per_m':   price_per_m,
            'labour_cost':   labour_cost,
            'overhead_cost': overhead_cost,
            'fabric_m':      fabric_m,
            'garment':       garment,
            'fabric_type':   fabric_type,
            'comparables':   comparables,
            'model_source':  self._model_source,
        }

    def _get_comparables(self, garment, fabric_type, fabric_m, predicted_cost, n=4):
        """Find nearest comparable garments from the dataset."""
        if self._dataset is None:
            return []

        df = self._dataset.copy()

        # Prefer same garment or same fabric; sort by fabric_m proximity
        same_garment = df[df['Garment'] == garment].copy()
        same_fabric  = df[df['Fabric_Type'] == fabric_type].copy()
        pool = pd.concat([same_garment, same_fabric]).drop_duplicates()

        if pool.empty:
            pool = df.copy()

        pool['_dist'] = abs(pool['Fabric_m'] - fabric_m)
        pool = pool.sort_values('_dist').head(n)

        return [
            {
                'garment':       row['Garment'],
                'fabric_type':   row['Fabric_Type'],
                'fabric_m':      row['Fabric_m'],
                'total_cost':    round(row['Total_Cost_ZAR'], 2),
                'material_cost': round(row['Material_Cost_ZAR'], 2),
            }
            for _, row in pool.iterrows()
        ]

    @property
    def is_loaded(self):
        return self._model is not None


# Singleton instance
predictor = TailorPredictor()
