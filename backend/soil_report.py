
"""
soil_report.py
---------------
FastAPI router for the Soil Health Analyzer.

This REPLACES the previous OCR-based Soil Report Analysis. There is no
file upload and no OCR anywhere in this module - the farmer manually
enters six soil test values, and this module returns:

    1. Nutrient status (Low / Medium / High / Optimal / Acidic / Neutral / Alkaline)
    2. An overall Soil Health Score (0-100) with a transparent, rule-based formula
    3. Fertilizer recommendations for any deficient nutrient
    4. Personalized soil improvement tips
    5. Suitable crops (Highly Suitable / Moderately Suitable / Not Recommended)
    6. Warnings for any concerning readings
    7. A downloadable PDF version of the full report

IMPORTANT - PER-SESSION DATA ONLY:
    Each analysis is scoped to the caller's `session_id`. Results are
    stored in `session_store` (in-memory, per-session) so the chatbot
    can be context-aware for THAT farmer only - never shared or averaged
    across sessions. The permanent audit trail in SQLite is also tagged
    with session_id (see database.py) purely for the Dashboard's recent-
    activity view, not for cross-session context.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from database import insert_soil_report, get_soil_reports
from pdf_report import generate_soil_report_pdf
from session_store import set_soil_context, get_soil_context

router = APIRouter(prefix="/api/soil-report", tags=["Soil Health Analyzer"])


# ---------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------

class SoilInput(BaseModel):
    """Manually entered soil test values."""
    session_id: str = Field(..., min_length=1, description="Browser session identifier")
    nitrogen: float = Field(..., ge=0, le=1000, description="Nitrogen (N) in kg/ha")
    phosphorus: float = Field(..., ge=0, le=500, description="Phosphorus (P) in kg/ha")
    potassium: float = Field(..., ge=0, le=1000, description="Potassium (K) in kg/ha")
    ph: float = Field(..., ge=0, le=14, description="Soil pH")
    organic_carbon: float = Field(..., ge=0, le=10, description="Organic Carbon (%)")
    ec: float = Field(..., ge=0, le=20, description="Electrical Conductivity (dS/m)")


class NutrientStatusEntry(BaseModel):
    value: float
    status: str


class FertilizerRecommendation(BaseModel):
    nutrient: str
    status: str
    recommended: List[str]
    reason: str
    application: str


class SuitableCrops(BaseModel):
    highly_suitable: List[str]
    moderately_suitable: List[str]
    not_recommended: List[str]


class SoilAnalysisOutput(BaseModel):
    """Full Soil Health Analyzer result."""
    inputs: dict
    nutrient_status: dict
    health_score: float
    health_rating: str
    fertilizer_recommendations: List[FertilizerRecommendation]
    improvement_tips: List[str]
    suitable_crops: SuitableCrops
    warnings: List[str]


# ---------------------------------------------------------------------
# Nutrient classification thresholds
# (Standard agronomic ranges - documented inline for transparency.)
# ---------------------------------------------------------------------

def _classify_nitrogen(n: float) -> str:
    if n < 280:
        return "Low"
    if n <= 560:
        return "Medium"
    return "High"


def _classify_phosphorus(p: float) -> str:
    if p < 10:
        return "Low"
    if p <= 25:
        return "Medium"
    return "High"


def _classify_potassium(k: float) -> str:
    if k < 110:
        return "Low"
    if k <= 280:
        return "Medium"
    return "High"


def _classify_ph(ph: float) -> str:
    if ph < 5.5:
        return "Acidic"
    if ph <= 7.5:
        return "Neutral"
    return "Alkaline"


def _classify_organic_carbon(oc: float) -> str:
    if oc < 0.4:
        return "Low"
    if oc <= 0.75:
        return "Optimal"
    return "High"


def _classify_ec(ec: float) -> str:
    if ec < 1.0:
        return "Optimal"
    if ec <= 4.0:
        return "Medium"
    return "High"


def _build_nutrient_status(payload: SoilInput) -> dict:
    return {
        "nitrogen": {"value": payload.nitrogen, "status": _classify_nitrogen(payload.nitrogen)},
        "phosphorus": {"value": payload.phosphorus, "status": _classify_phosphorus(payload.phosphorus)},
        "potassium": {"value": payload.potassium, "status": _classify_potassium(payload.potassium)},
        "ph": {"value": payload.ph, "status": _classify_ph(payload.ph)},
        "organic_carbon": {"value": payload.organic_carbon, "status": _classify_organic_carbon(payload.organic_carbon)},
        "ec": {"value": payload.ec, "status": _classify_ec(payload.ec)},
    }


# ---------------------------------------------------------------------
# Soil Health Score (transparent, rule-based - max points per parameter
# are documented so the scoring logic is auditable, not a black box)
# ---------------------------------------------------------------------

def _compute_health_score(status: dict) -> float:
    score = 0.0

    # Nitrogen: up to 20 points - full for Medium, partial otherwise.
    score += {"Low": 8, "Medium": 20, "High": 14}[status["nitrogen"]["status"]]

    # Phosphorus: up to 15 points.
    score += {"Low": 6, "Medium": 15, "High": 11}[status["phosphorus"]["status"]]

    # Potassium: up to 15 points.
    score += {"Low": 6, "Medium": 15, "High": 11}[status["potassium"]["status"]]

    # pH: up to 20 points - full for Neutral, partial for Acidic/Alkaline.
    score += {"Acidic": 10, "Neutral": 20, "Alkaline": 10}[status["ph"]["status"]]

    # Organic Carbon: up to 20 points.
    score += {"Low": 8, "Optimal": 20, "High": 16}[status["organic_carbon"]["status"]]

    # Electrical Conductivity: up to 10 points - penalize high salinity most.
    score += {"Optimal": 10, "Medium": 6, "High": 2}[status["ec"]["status"]]

    return round(min(score, 100.0), 1)


def _health_rating(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Moderate"
    return "Poor"


# ---------------------------------------------------------------------
# Fertilizer recommendations
# ---------------------------------------------------------------------

def _fertilizer_recommendations(status: dict) -> List[dict]:
    recs = []

    if status["nitrogen"]["status"] == "Low":
        recs.append({
            "nutrient": "Nitrogen", "status": "Low",
            "recommended": ["Urea", "Ammonium Sulphate"],
            "reason": "Nitrogen deficiency detected.",
            "application": "Split application: half at sowing, remainder as top dressing during vegetative growth.",
        })
    if status["phosphorus"]["status"] == "Low":
        recs.append({
            "nutrient": "Phosphorus", "status": "Low",
            "recommended": ["DAP", "SSP"],
            "reason": "Phosphorus deficiency detected - can limit root development and flowering.",
            "application": "Apply full dose as basal fertilizer at the time of sowing/transplanting.",
        })
    if status["potassium"]["status"] == "Low":
        recs.append({
            "nutrient": "Potassium", "status": "Low",
            "recommended": ["MOP (Muriate of Potash)"],
            "reason": "Potassium deficiency detected - can reduce fruit/grain quality and disease resistance.",
            "application": "Apply full dose as basal fertilizer; supplement before flowering for fruiting crops.",
        })
    if status["nitrogen"]["status"] == "High":
        recs.append({
            "nutrient": "Nitrogen", "status": "High",
            "recommended": ["No additional nitrogen fertilizer"],
            "reason": "Nitrogen levels are already high; more nitrogen risks excess vegetative growth and pest attraction.",
            "application": "Skip nitrogen fertilizer this season; retest before the next crop cycle.",
        })

    return recs


# ---------------------------------------------------------------------
# Soil improvement tips
# ---------------------------------------------------------------------

def _improvement_tips(status: dict) -> List[str]:
    tips = []

    if status["organic_carbon"]["status"] == "Low":
        tips += ["Increase organic matter", "Use compost", "Apply farmyard manure"]

    tips.append("Practice crop rotation")

    if status["nitrogen"]["status"] in ("Low", "Medium"):
        tips.append("Grow legumes to naturally fix nitrogen in the soil")

    if status["ec"]["status"] in ("Medium", "High"):
        tips += ["Avoid over-irrigation", "Improve field drainage to reduce salt buildup"]

    tips.append("Maintain consistent soil moisture")

    if status["nitrogen"]["status"] == "High":
        tips.append("Avoid excessive nitrogen fertilizer this season")

    if status["phosphorus"]["status"] == "Low" or status["potassium"]["status"] == "Low":
        tips.append("Apply micronutrients (zinc, boron) if deficiency symptoms appear")

    if status["ph"]["status"] == "Acidic":
        tips.append("Apply agricultural lime to raise soil pH toward neutral")
    if status["ph"]["status"] == "Alkaline":
        tips.append("Apply gypsum or elemental sulfur to lower soil pH toward neutral")

    # De-duplicate while preserving order.
    seen = set()
    unique_tips = []
    for t in tips:
        if t not in seen:
            seen.add(t)
            unique_tips.append(t)
    return unique_tips


# ---------------------------------------------------------------------
# Suitable crops
# ---------------------------------------------------------------------

def _suitable_crops(status: dict) -> dict:
    highly_suitable, moderately_suitable, not_recommended = set(), set(), set()

    ph_status = status["ph"]["status"]
    ec_status = status["ec"]["status"]

    if ph_status == "Neutral":
        highly_suitable.update(["Wheat", "Rice", "Maize", "Sugarcane"])
        moderately_suitable.update(["Mustard", "Potato"])
    elif ph_status == "Acidic":
        highly_suitable.update(["Tea", "Potato"])
        moderately_suitable.update(["Maize", "Rice"])
        not_recommended.update(["Cotton", "Sugarcane"])
    else:  # Alkaline
        highly_suitable.update(["Barley", "Cotton", "Sugar Beet"])
        moderately_suitable.update(["Wheat", "Mustard"])
        not_recommended.update(["Potato", "Tea"])

    if ec_status == "High":
        not_recommended.update(["Potato", "Rice"])
        moderately_suitable.update(["Barley", "Cotton"])
        highly_suitable -= {"Potato", "Rice"}

    if status["nitrogen"]["status"] == "Low" and status["organic_carbon"]["status"] == "Low":
        not_recommended.add("Sugarcane")
        highly_suitable.discard("Sugarcane")

    # Keep crops from appearing in more than one bucket, favoring the
    # more cautious classification (not_recommended > moderate > high).
    moderately_suitable -= not_recommended
    highly_suitable -= not_recommended
    highly_suitable -= moderately_suitable

    if not highly_suitable and not moderately_suitable:
        moderately_suitable.update(["Wheat", "Maize"])

    return {
        "highly_suitable": sorted(highly_suitable),
        "moderately_suitable": sorted(moderately_suitable),
        "not_recommended": sorted(not_recommended),
    }


# ---------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------

def _warnings(status: dict) -> List[str]:
    warnings = []
    if status["nitrogen"]["status"] == "Low":
        warnings.append("Low Nitrogen detected.")
    if status["phosphorus"]["status"] == "Low":
        warnings.append("Low Phosphorus detected.")
    if status["potassium"]["status"] == "Low":
        warnings.append("Low Potassium detected.")
    if status["ph"]["status"] == "Acidic":
        warnings.append("Soil is acidic.")
    if status["ph"]["status"] == "Alkaline":
        warnings.append("Soil is alkaline.")
    if status["ec"]["status"] == "High":
        warnings.append("High salinity detected.")
    if status["organic_carbon"]["status"] == "Low":
        warnings.append("Low organic carbon.")
    return warnings


# ---------------------------------------------------------------------
# Core analysis (shared by /analyze and /pdf)
# ---------------------------------------------------------------------

def _run_analysis(payload: SoilInput) -> dict:
    status = _build_nutrient_status(payload)
    score = _compute_health_score(status)

    return {
        "inputs": payload.model_dump(exclude={"session_id"}),
        "nutrient_status": status,
        "health_score": score,
        "health_rating": _health_rating(score),
        "fertilizer_recommendations": _fertilizer_recommendations(status),
        "improvement_tips": _improvement_tips(status),
        "suitable_crops": _suitable_crops(status),
        "warnings": _warnings(status),
    }


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------

@router.post("/analyze", response_model=SoilAnalysisOutput)
def analyze_soil(payload: SoilInput):
    """
    Analyze manually entered soil values and return nutrient status,
    health score, fertilizer recommendations, improvement tips,
    suitable crops, and warnings. Also stores the result:
      - in session_store, scoped to THIS session only, so the chatbot
        can answer context-aware questions for this farmer.
      - in SQLite (soil_reports), tagged with session_id, for the
        Dashboard's recent-activity view.
    """
    try:
        analysis = _run_analysis(payload)

        set_soil_context(payload.session_id, payload.model_dump(exclude={"session_id"}), analysis)

        insert_soil_report(
            filename="Manual Entry (Soil Health Analyzer)",
            session_id=payload.session_id,
            nitrogen=payload.nitrogen,
            phosphorus=payload.phosphorus,
            potassium=payload.potassium,
            ph=payload.ph,
            organic_carbon=payload.organic_carbon,
            ec=payload.ec,
            health_score=analysis["health_score"],
            summary=f"{analysis['health_rating']} soil health ({analysis['health_score']}/100).",
            suggested_crops=", ".join(analysis["suitable_crops"]["highly_suitable"]) or "None",
            suggested_fertilizers=", ".join(
                r["nutrient"] for r in analysis["fertilizer_recommendations"]
            ) or "None required",
            soil_improvements=", ".join(analysis["improvement_tips"]),
        )

        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Soil analysis failed: {str(e)}")


@router.get("/pdf")
def download_soil_report_pdf(session_id: str):
    """
    Regenerate and download the most recent Soil Health Analyzer result
    for this session as a PDF. Requires /analyze to have been called
    first in this session.
    """
    context = get_soil_context(session_id)
    if not context:
        raise HTTPException(
            status_code=404,
            detail="No soil analysis found for this session. Please run the Soil Health Analyzer first.",
        )

    try:
        pdf_bytes = generate_soil_report_pdf(context["inputs"], context["analysis"])
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=soil_health_report.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")


@router.get("/history")
def soil_report_history(limit: int = 50):
    """Return the most recent soil analyses (across all sessions, for the Dashboard)."""
    try:
        return {"history": get_soil_reports(limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch soil report history: {str(e)}")
