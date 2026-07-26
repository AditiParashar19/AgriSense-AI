"""
crop_api.py
-----------
Thin HTTP client wrapper around the backend Crop Recommendation API.
"""

import os
import requests
from typing import Dict, Any

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 30


def predict_crop(nitrogen: float, phosphorus: float, potassium: float,
                  temperature: float, humidity: float, ph: float,
                  rainfall: float) -> Dict[str, Any]:
    """
    Call the backend crop prediction endpoint and return the parsed
    JSON response. Raises requests.RequestException on network errors.
    """
    payload = {
        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium,
        "temperature": temperature,
        "humidity": humidity,
        "ph": ph,
        "rainfall": rainfall,
    }
    response = requests.post(f"{BACKEND_URL}/api/crop/predict", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_crop_history(limit: int = 50) -> Dict[str, Any]:
    """Fetch recent crop prediction history from the backend."""
    response = requests.get(
        f"{BACKEND_URL}/api/crop/history", params={"limit": limit}, timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()
