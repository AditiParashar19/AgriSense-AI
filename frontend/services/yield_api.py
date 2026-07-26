"""
yield_api.py
------------
Thin HTTP client wrapper around the backend Yield Prediction API.
"""

import os
import requests
from typing import Dict, Any

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 30


def predict_yield(area: str, item: str, year: int, rainfall: float,
                   pesticides: float, temperature: float) -> Dict[str, Any]:
    """
    Call the backend yield prediction endpoint and return the parsed
    JSON response. Raises requests.RequestException on network errors.
    """
    payload = {
        "area": area,
        "item": item,
        "year": year,
        "rainfall": rainfall,
        "pesticides": pesticides,
        "temperature": temperature,
    }
    response = requests.post(f"{BACKEND_URL}/api/yield/predict", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_yield_history(limit: int = 50) -> Dict[str, Any]:
    """Fetch recent yield prediction history from the backend."""
    response = requests.get(
        f"{BACKEND_URL}/api/yield/history", params={"limit": limit}, timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()
