"""
ML Predictor for Tailor Cost Estimation System
University of Zululand – Group 7
"""

import logging
import pandas as pd
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# Price-per-metre reference
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

GARMENT_COMPLEXITY = {
    'Blouse': 1.0, 'Shorts': 1.0, 'Shirt': 1.1, 'Skirt': 1.15,
    'Trousers': 1.2, 'Dress': 1.35, 'Hoodie': 1.4, 'Jersey': 1.3,
    'Jacket': 1.5, 'Tracksuit': 1.6, 'Suit': 1.8, 'Coat': 1.9,
}


class TailorPredictor:
    _instance = None
    _model = None
    _model_source = 'fallback'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, model_path=None, dataset_path=None):
        """Load predictor - uses fallback calculation"""
        logger.info("Predictor loaded using fallback calculation")
        self._model_source = 'fallback'
        return self

    def predict(self, garment: str, fabric_type: str, fabric_m: float):
        """Calculate cost prediction"""
        
        price_per_m = FABRIC_PRICE_MAP.get(fabric_type, 100)
        material_cost = fabric_m * price_per_m
        multiplier = GARMENT_COMPLEXITY.get(garment, 1.3)
        labour_base = 80 + (fabric_m * 20)
        total_cost = (material_cost * multiplier) + labour_base
        total_cost = total_cost * 1.08  # Add 8% overhead
        
        return round(total_cost, 2)

    @property
    def is_loaded(self):
        return True


predictor = TailorPredictor()
