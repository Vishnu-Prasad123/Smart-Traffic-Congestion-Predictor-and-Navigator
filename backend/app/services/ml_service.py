"""
backend/app/services/ml_service.py
-----------------------------------
Loads the trained Random Forest pipeline and provides prediction functionality.
"""
import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger(__name__)

_pipeline = None
_is_demo_mode = False


def _get_settings():
    from app.core.config import settings
    return settings


def load_model() -> bool:
    """Load the model pipeline from disk. Returns True if successful."""
    global _pipeline, _is_demo_mode
    settings = _get_settings()

    if not settings.MODEL_PATH.exists():
        logger.warning(f"Model not found at {settings.MODEL_PATH}. Running in demo mode.")
        _is_demo_mode = True
        return False

    try:
        _pipeline = joblib.load(settings.MODEL_PATH)
        logger.info("Model loaded successfully.")
        _is_demo_mode = False
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        _is_demo_mode = True
        return False


def is_model_loaded() -> bool:
    return _pipeline is not None


def is_demo_mode() -> bool:
    return _is_demo_mode


def normalize_weather(val: str) -> str:
    """Normalize weather labels across Kaggle dataset, demo data, and user input."""
    v = str(val).strip().capitalize()
    if v in ["Rain", "Rainy"]:
        return "Rain"
    if v in ["Overcast", "Cloudy"]:
        return "Overcast"
    if v in ["Fog", "Foggy"]:
        return "Fog"
    if v in ["Windy"]:
        return "Windy"
    if v in ["Clear"]:
        return "Clear"
    return "Unknown"


def predict_batch(features_list: list) -> list:
    """
    Predict congestion levels for a batch of feature dictionaries in a single vectorized pass.
    """
    if not features_list:
        return []

    if _pipeline is None:
        return [_demo_predict(f) for f in features_list]

    try:
        rows = []
        for f in features_list:
            raw_weather = f.get("weather_conditions", "Clear")
            rows.append({
                "Traffic Volume": f.get("traffic_volume", 2000),
                "Average Speed (km/h)": f.get("average_speed", 30),
                "Travel Time Index": f.get("travel_time_index", 1.5),
                "Road Capacity Utilization (%)": f.get("road_capacity_utilization", 60),
                "Incident Reports": f.get("incident_reports", 0),
                "DayOfWeek": f.get("day_of_week", 0),
                "Month": f.get("month", 1),
                "Weather Conditions": normalize_weather(raw_weather),
                "Roadwork and Construction Activity": f.get("roadwork_activity", "No"),
            })
        df = pd.DataFrame(rows)

        predictions = _pipeline.predict(df)
        probas = _pipeline.predict_proba(df)
        classes = list(_pipeline.classes_)

        results = []
        for pred, proba in zip(predictions, probas):
            proba_dict = {cls: float(p) for cls, p in zip(classes, proba)}
            for missing in ["LOW", "MEDIUM", "HIGH"]:
                proba_dict.setdefault(missing, 0.0)

            confidence = float(max(proba))
            results.append({
                "congestion_level": str(pred),
                "probabilities": {
                    "LOW": round(proba_dict.get("LOW", 0.0), 4),
                    "MEDIUM": round(proba_dict.get("MEDIUM", 0.0), 4),
                    "HIGH": round(proba_dict.get("HIGH", 0.0), 4),
                },
                "confidence": round(confidence, 4),
                "is_demo_mode": False,
            })
        return results
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        return [_demo_predict(f) for f in features_list]


def predict(features: dict) -> dict:
    """
    Predict congestion level from a single features dictionary.
    """
    res = predict_batch([features])
    return res[0] if res else _demo_predict(features)



def _demo_predict(features: dict) -> dict:
    """Rule-based demo prediction when model is not available."""
    vol = features.get("traffic_volume", 2000)
    speed = features.get("average_speed", 30)
    cap = features.get("road_capacity_utilization", 60)

    score = 0.4 * (vol / 8000) + 0.3 * (1 - speed / 80) + 0.3 * (cap / 100)

    if score < 0.35:
        level = "LOW"
        proba = {"LOW": 0.75, "MEDIUM": 0.20, "HIGH": 0.05}
    elif score < 0.65:
        level = "MEDIUM"
        proba = {"LOW": 0.20, "MEDIUM": 0.65, "HIGH": 0.15}
    else:
        level = "HIGH"
        proba = {"LOW": 0.05, "MEDIUM": 0.20, "HIGH": 0.75}

    return {
        "congestion_level": level,
        "probabilities": proba,
        "confidence": proba[level],
        "is_demo_mode": True,
        "warning": "Model not trained yet. Using rule-based demo prediction.",
    }


def get_metrics() -> Optional[dict]:
    """Load and return saved model evaluation metrics."""
    settings = _get_settings()
    if not settings.METRICS_PATH.exists():
        return None
    with open(settings.METRICS_PATH) as f:
        return json.load(f)


def get_feature_importance() -> Optional[dict]:
    """Load and return feature importances."""
    settings = _get_settings()
    if not settings.FEATURE_IMPORTANCE_PATH.exists():
        return None
    with open(settings.FEATURE_IMPORTANCE_PATH) as f:
        return json.load(f)
