"""
pdf_report.py
--------------
Generates a clean, downloadable PDF version of a Soil Health Analyzer
result using fpdf2. Pure formatting layer - takes the already-computed
inputs/analysis dicts from soil_report.py and lays them out on paper.
"""

from datetime import datetime
from io import BytesIO
from typing import Any, Dict

from fpdf import FPDF

PRIMARY_COLOR = (46, 125, 50)   # matches the app's green theme
LIGHT_GRAY = (245, 250, 245)
DARK_TEXT = (27, 43, 30)


class _SoilReportPDF(FPDF):
    """FPDF subclass with a consistent header/footer for the report."""

    def header(self):
        self.set_fill_color(*PRIMARY_COLOR)
        self.rect(0, 0, self.w, 22, style="F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 16)
        self.set_xy(10, 6)
        self.cell(0, 10, "AgriSense-AI - Soil Health Report", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_xy(10, 14)
        self.cell(0, 6, datetime.now().strftime("Generated on %d %b %Y, %H:%M"), ln=True)
        self.ln(14)
        self.set_text_color(*DARK_TEXT)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _section_title(pdf: _SoilReportPDF, title: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 8, title, ln=True)
    pdf.set_text_color(*DARK_TEXT)
    pdf.set_draw_color(*PRIMARY_COLOR)
    pdf.set_x(pdf.l_margin)
    pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
    pdf.ln(3)
    pdf.set_x(pdf.l_margin)


def _body_text(pdf: _SoilReportPDF, text: str, size: int = 11) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", size)
    pdf.multi_cell(0, 6, text)
    pdf.set_x(pdf.l_margin)


def generate_soil_report_pdf(inputs: Dict[str, Any], analysis: Dict[str, Any]) -> bytes:
    """
    Build a multi-section PDF report from the analyzer's inputs and
    computed analysis, and return the raw PDF bytes.
    """
    pdf = _SoilReportPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # --- Input values ---
    _section_title(pdf, "Input Soil Values")
    pdf.set_font("Helvetica", "", 11)
    labels = {
        "nitrogen": "Nitrogen (N)", "phosphorus": "Phosphorus (P)",
        "potassium": "Potassium (K)", "ph": "pH", "organic_carbon": "Organic Carbon (%)",
        "ec": "Electrical Conductivity (dS/m)",
    }
    for key, label in labels.items():
        pdf.cell(0, 7, f"{label}: {inputs.get(key)}", ln=True)

    # --- Health Score ---
    _section_title(pdf, "Soil Health Score")
    score = analysis.get("health_score")
    rating = analysis.get("health_rating", "")
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 14, f"{score} / 100", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*DARK_TEXT)
    pdf.cell(0, 8, f"Rating: {rating}", ln=True)

    # --- Nutrient status ---
    _section_title(pdf, "Nutrient Status")
    nutrient_status = analysis.get("nutrient_status", {})
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(*LIGHT_GRAY)
    pdf.cell(70, 8, "Parameter", border=1, fill=True)
    pdf.cell(50, 8, "Value", border=1, fill=True)
    pdf.cell(60, 8, "Status", border=1, fill=True, ln=True)
    pdf.set_font("Helvetica", "", 11)
    for key, label in labels.items():
        entry = nutrient_status.get(key, {})
        pdf.cell(70, 8, label, border=1)
        pdf.cell(50, 8, str(entry.get("value", "N/A")), border=1)
        pdf.cell(60, 8, str(entry.get("status", "N/A")), border=1, ln=True)

    # --- Warnings ---
    warnings = analysis.get("warnings", [])
    if warnings:
        _section_title(pdf, "Warnings")
        for w in warnings:
            _body_text(pdf, f"- {w}")

    # --- Fertilizer recommendations ---
    _section_title(pdf, "Fertilizer Recommendation")
    fert_recs = analysis.get("fertilizer_recommendations", [])
    if fert_recs:
        for rec in fert_recs:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, f"{rec['nutrient']} - {rec['status']}", ln=True)
            _body_text(pdf, f"Recommended: {', '.join(rec['recommended'])}")
            _body_text(pdf, f"Reason: {rec['reason']}")
            _body_text(pdf, f"Application: {rec['application']}")
            pdf.ln(2)
    else:
        _body_text(pdf, "Nutrient levels are sufficient. No additional fertilizer is required.")

    # --- Suitable crops ---
    _section_title(pdf, "Suitable Crops")
    crops = analysis.get("suitable_crops", {})
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Highly Suitable", ln=True)
    _body_text(pdf, ", ".join(crops.get("highly_suitable", [])) or "None identified")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Moderately Suitable", ln=True)
    _body_text(pdf, ", ".join(crops.get("moderately_suitable", [])) or "None identified")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Not Recommended", ln=True)
    _body_text(pdf, ", ".join(crops.get("not_recommended", [])) or "None identified")

    # --- Improvement tips ---
    _section_title(pdf, "Soil Improvement Tips")
    for tip in analysis.get("improvement_tips", []):
        _body_text(pdf, f"- {tip}")

    buffer = BytesIO()
    pdf.output(buffer)
    return bytes(buffer.getvalue())
