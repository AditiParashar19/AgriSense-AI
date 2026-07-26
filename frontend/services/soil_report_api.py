"""
soil_report_api.py
-------------------
Thin HTTP client wrapper around the backend Soil Health Analyzer API.
No file upload / OCR - this sends manually entered soil values.
"""

import os
from typing import Any, Dict

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 30


def analyze_soil(session_id: str, nitrogen: float, phosphorus: float, potassium: float,
                  ph: float, organic_carbon: float, ec: float) -> Dict[str, Any]:
    """
    Send manually entered soil values to the backend Soil Health Analyzer
    and return the parsed JSON response (nutrient status, health score,
    fertilizer recommendations, improvement tips, suitable crops, warnings).
    """
    payload = {
        "session_id": session_id,
        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium,
        "ph": ph,
        "organic_carbon": organic_carbon,
        "ec": ec,
    }
    response = requests.post(f"{BACKEND_URL}/api/soil-report/analyze", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def download_soil_report_pdf(session_id: str) -> bytes:
    """
    Download the PDF version of this session's most recent Soil Health
    Analyzer result. Raises requests.HTTPError (404) if no analysis has
    been run yet in this session.
    """
    response = requests.get(
        f"{BACKEND_URL}/api/soil-report/pdf", params={"session_id": session_id}, timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.content


def get_soil_report_history(limit: int = 50) -> Dict[str, Any]:
    """Fetch recent soil report analysis history from the backend."""
    response = requests.get(
        f"{BACKEND_URL}/api/soil-report/history", params={"limit": limit}, timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()
