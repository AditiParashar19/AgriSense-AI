import importlib

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import crop
import soil_report
import chatbot
from database import get_dashboard_summary

# 'yield' is a reserved Python keyword, so backend/yield.py cannot be
# imported with a normal "import yield" statement. importlib bypasses
# the language grammar restriction safely.
yield_module = importlib.import_module("yield")

app = FastAPI(
    title="AgriSenseAI API",
    description="AI-powered Precision Agriculture platform for farmers.",
    version="1.0.0",
)

# Allow the Streamlit frontend (and local development tools) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all feature routers.
app.include_router(crop.router)
app.include_router(yield_module.router)
app.include_router(soil_report.router)
app.include_router(chatbot.router)


@app.get("/", tags=["Health"])
def read_root():
    """Simple health-check endpoint."""
    return {
        "status": "ok",
        "service": "AgriSenseAI API",
        "message": "Welcome to the AgriSenseAI Precision Agriculture API.",
    }


@app.get("/api/dashboard/summary", tags=["Dashboard"])
def dashboard_summary():
    """
    Return aggregate statistics and recent activity across all features,
    used to populate the Streamlit dashboard page.
    """
    try:
        return get_dashboard_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard summary: {str(e)}")
