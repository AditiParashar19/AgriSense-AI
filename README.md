<div align="center">

# 🌿 AgriSense-AI

**An AI-Powered Precision Agriculture Platform**

Crop Recommendation · Yield Prediction · Soil Health Analyzer · Grounded AI Chatbot

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-F7931E?logo=scikitlearn&logoColor=white)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/RAG-LangChain%20%2B%20FAISS-1C3C3C)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#️-tech-stack)
- [Screenshots](#-screenshots)
- [Project Structure](#-project-structure)
- [Setup](#️-setup)
- [Running the App](#️-running-the-app)
- [Database](#️-database)
- [Session Isolation](#-session-isolation)
- [API Endpoints](#-api-endpoints)

---

## 🔎 Overview

**AgriSense-AI** combines classical Machine Learning with Retrieval-Augmented Generation (RAG) to
give farmers a single platform for crop selection, yield forecasting, soil diagnostics, and
trustworthy AI-powered guidance — without hallucinated advice.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌱 **Crop Recommendation** | Suggests the best crop to grow based on soil nutrients (N, P, K) and climate (temperature, humidity, pH, rainfall) using a Random Forest Classifier. |
| 🌾 **Crop Yield Prediction** | Predicts expected crop yield based on area, crop item, year, rainfall, pesticide use, and temperature using a Random Forest Regressor. |
| 🧪 **Soil Health Analyzer** | Manually enter N, P, K, pH, Organic Carbon, and EC values. Get an instant nutrient status breakdown, a transparent 0-100 Soil Health Score, fertilizer recommendations, improvement tips, suitable-crop suggestions, warnings, and a downloadable PDF report. |
| 🤖 **AI Agriculture Chatbot** | A RAG-powered chatbot (LangChain + FAISS + local HuggingFace embeddings + Gemini 2.5 Flash) that answers questions grounded in your own `.pdf`/`.txt` knowledge base, with conversation memory, session-based context-awareness, source citations, and an optional Google Search fallback. |
| 📊 **Dashboard** | View aggregate stats and recent activity across all features in one place. |

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Streamlit
- **Machine Learning:** scikit-learn (Random Forest Classifier + Regressor)
- **PDF Reports:** fpdf2
- **RAG:** LangChain, FAISS, local HuggingFace sentence embeddings (`all-MiniLM-L6-v2`), Gemini 2.5 Flash
- **Optional Web Search:** Google Custom Search API
- **Database:** SQLite

---

## 📁 Project Structure

```
AgriSenseAI/
│
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── crop.py               # Crop recommendation router
│   ├── yield.py               # Yield prediction router
│   ├── soil_report.py         # Soil Health Analyer
│   ├── chatbot.py              # RAG chatbot router
│   ├── rag.py                   # FAISS vector store + retrieval 
│   ├── database.py               # SQLite schema + CRUD helpers
│   ├── session_store.py           # Per-session (in-memory) soil context for the chatbot
│   ├── pdf_report.py               # Soil Health Analyzer PDF report generation
│   ├── web_search.py                # Optional Google Search fallback for the chatbot
│   ├── models/                       
│   └── data/                          
│       └── faiss_index/                
│
├── frontend/
│   ├── app.py                  # Streamlit entry point 
│   ├── components/
│   │   └── sidebar.py            # Sidebar navigation
│   ├── frontend_pages/
│   │   ├── home.py
│   │   ├── crop.py
│   │   ├── yield.py
│   │   ├── soil_report.py          # Manual Soil Health Analyzer UI
│   │   ├── chatbot.py                # Chatbot UI 
│   │   └── dashboard.py
│   ├── services/                      # API client wrappers
│   │   ├── crop_api.py
│   │   ├── yield_api.py
│   │   ├── chatbot_api.py
│   │   └── soil_report_api.py       
│   └── assets/
│       └── style.css                  
│
├── dataset/                    
├── notebooks/                  
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/AditiParahsar19/AgriSense-AI.git
cd AgriSense-AI
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your trained ML models


```
backend/models/random_forest.pkl              # Crop Recommendation classifier greater than 25MB so not uploaded
backend/models/label_encoder.pkl              # Crop label encoder
backend/models/random_forest_regressor.pkl    # Yield Prediction regressor
backend/models/area_encoder.pkl               # Yield "Area" label encoder
backend/models/item_encoder.pkl               # Yield "Item" (crop) label encoder
```
---

## ▶️ Running the App

**Terminal 1 — Backend (FastAPI):**
```bash
cd backend
uvicorn main:app --reload --port 8000
```
API docs: `http://localhost:8000/docs`

**Terminal 2 — Frontend (Streamlit):**
```bash
cd frontend
streamlit run app.py
```
App: `http://localhost:8501`

---

## 🗄️ Database

SQLite, zero-config, auto-created at `backend/data/soilsense.db` on first run:

- `crop_predictions`
- `yield_predictions`
- `soil_reports` — includes `session_id`, `health_score`
- `chat_history`

---

## 🔒 Session Isolation

Every browser session gets a unique `session_id` (generated in `frontend/app.py`), shared between
the Soil Health Analyzer and the Chatbot. Soil values are stored in-memory
(`backend/session_store.py`) keyed strictly by `session_id` — never shared, averaged, or leaked
across sessions. This lets the chatbot answer "what fertilizer should I use?" using a farmer's own
data automatically and safely, even in a multi-user deployment.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/crop/predict` | Predict best crop |
| `GET` | `/api/crop/history` | Recent crop predictions |
| `POST` | `/api/yield/predict` | Predict crop yield |
| `GET` | `/api/yield/history` | Recent yield predictions |
| `POST` | `/api/soil-report/analyze` | Run the Soil Health Analyzer |
| `GET` | `/api/soil-report/pdf?session_id=...` | Download the PDF report |
| `GET` | `/api/soil-report/history` | Recent soil analyses |
| `POST` | `/api/chatbot/chat` | Ask the AI chatbot |
| `GET` | `/api/chatbot/history` | Chat history |
| `POST` | `/api/chatbot/rebuild-index` | Force a knowledge base rebuild |
| `GET` | `/api/dashboard/summary` | Aggregate stats for the dashboard |
