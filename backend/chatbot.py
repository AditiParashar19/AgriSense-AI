"""
chatbot.py
----------
FastAPI router for the AI Agriculture Chatbot (RAG-powered).

Pipeline for each question:
    1. Retrieve relevant chunks from the local FAISS knowledge base (rag.py).
    2. If that context is too thin, optionally fall back to a Google web
       search (web_search.py) - only when configured, never required.
    3. Pull recent conversation turns for this session (conversation memory).
    4. Pull the farmer's latest Soil Health Analyzer values for this
       session, if any (context awareness - session-scoped, never shared
       across users, see session_store.py).
    5. Ask Gemini to answer strictly from that combined context, in a
       structured format, citing sources, and refusing to answer
       non-agriculture questions or invent facts.
    6. Persist the exchange to chat_history (used for memory + Dashboard).

Every external call (Gemini, web search) is wrapped so a failure returns
a friendly in-chat message instead of crashing the request.
"""

import os
import uuid
from typing import List, Optional

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database import get_chat_history, insert_chat_message
from rag import format_context, list_sources, retrieve_relevant_chunks
from session_store import get_soil_context
from web_search import format_web_context, web_search

load_dotenv()

router = APIRouter(prefix="/api/chatbot", tags=["AI Chatbot"])

GEMINI_MODEL_NAME = "gemini-2.5-flash"

# Below this many characters of retrieved context, we treat the local
# knowledge base as "too thin" and try the web search fallback (if configured)
# before giving up and saying we don't have enough information.
MIN_CONTEXT_CHARS = 120

# How many previous turns (question+answer pairs) to include as memory.
MEMORY_TURNS = 4

NO_INFO_MESSAGE = "I don't have enough information to answer that."

SYSTEM_PROMPT = """You are AgriBot, a professional AI agriculture advisor for the \
AgriSense-AI platform, assisting farmers.

STRICT RULES:
- Only answer questions related to agriculture: soil health, fertilizers, crop \
selection, irrigation, plant diseases, pest management, yields, and farming practices.
- If the question is NOT agriculture-related, politely decline and say you can only \
help with agriculture topics.
- Base your answer strictly on the CONTEXT provided below. NEVER invent facts, \
figures, or recommendations that are not supported by the CONTEXT.
- If the CONTEXT does not contain enough information to answer confidently, reply \
with exactly: "{no_info_message}" (nothing else).
- If KNOWN SOIL DATA is provided below, use those values automatically when the \
farmer's question depends on soil conditions (e.g. fertilizer choice, crop choice) - \
do NOT ask the farmer to re-enter values you already have.
- If PREVIOUS CONVERSATION is provided, use it to understand follow-up questions \
(e.g. "recommend crops" after they mentioned their pH earlier).

RESPONSE FORMAT (use these headings, skip "Example" if not applicable):
**Overview**
**Explanation**
**Best Practices**
**Common Mistakes**
**Example** (only if a concrete example helps)
**Summary**

At the very end, add a line starting with "Source:" listing the document name(s) \
or "Web Search" you actually used. If you used no context (i.e. you gave the \
no-information reply), omit the Source line.

KNOWN SOIL DATA (from this farmer's Soil Health Analyzer, may be empty):
{soil_context}

PREVIOUS CONVERSATION (most recent turns in this session, may be empty):
{conversation_history}

CONTEXT (retrieved knowledge base / web content):
{context}

FARMER'S QUESTION:
{question}

Answer now, following the RESPONSE FORMAT and STRICT RULES above.
"""


def _get_gemini_model():
    """Configure and return the Gemini generative model client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Please add it to your .env file "
            "before using the chatbot."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL_NAME)


def _build_soil_context_block(session_id: str) -> str:
    """
    Build a short, readable block describing this session's most recent
    Soil Health Analyzer values, or an empty string if none exist.
    Strictly session-scoped - see session_store.py.
    """
    entry = get_soil_context(session_id)
    if not entry:
        return "(none provided yet)"

    inputs = entry.get("inputs", {})
    analysis = entry.get("analysis", {})
    lines = [
        f"- Nitrogen: {inputs.get('nitrogen')} kg/ha",
        f"- Phosphorus: {inputs.get('phosphorus')} kg/ha",
        f"- Potassium: {inputs.get('potassium')} kg/ha",
        f"- pH: {inputs.get('ph')}",
        f"- Organic Carbon: {inputs.get('organic_carbon')}%",
        f"- Electrical Conductivity: {inputs.get('ec')} dS/m",
        f"- Soil Health Score: {analysis.get('health_score')}/100 ({analysis.get('health_rating')})",
    ]
    return "\n".join(lines)


def _build_conversation_history_block(session_id: str) -> str:
    """Build a short transcript of the last few turns in this session for memory."""
    previous = get_chat_history(session_id=session_id, limit=MEMORY_TURNS)
    if not previous:
        return "(no previous messages)"

    lines = []
    for turn in previous:
        lines.append(f"Farmer: {turn['question']}")
        lines.append(f"AgriBot: {turn['answer']}")
    return "\n".join(lines)


class ChatInput(BaseModel):
    """Request schema for chatbot messages."""
    question: str = Field(..., min_length=1, description="Farmer's question")
    session_id: Optional[str] = Field(None, description="Chat session identifier")


class ChatOutput(BaseModel):
    """Response schema for chatbot messages."""
    answer: str
    session_id: str
    sources: List[str] = Field(default_factory=list)


@router.post("/chat", response_model=ChatOutput)
def chat(payload: ChatInput):
    """
    Answer a farmer's agriculture question using RAG (FAISS retrieval),
    an optional web search fallback, conversation memory, and Soil
    Health Analyzer context - all scoped to this session_id.
    """
    session_id = payload.session_id or uuid.uuid4().hex
    sources: List[str] = []

    try:
        # 1. Local knowledge base retrieval (always tried first).
        try:
            relevant_chunks = retrieve_relevant_chunks(payload.question, k=5)
            context = format_context(relevant_chunks)
            sources.extend(list_sources(relevant_chunks))
        except RuntimeError:
            # No knowledge base files present at all.
            relevant_chunks, context = [], ""

        # 2. Web search fallback, only if local context is too thin.
        if len(context.strip()) < MIN_CONTEXT_CHARS:
            web_results = web_search(payload.question)
            if web_results:
                web_context = format_web_context(web_results)
                context = f"{context}\n\n{web_context}".strip() if context else web_context
                sources.append("Web Search")

        # 3. Conversation memory + soil context (both session-scoped).
        conversation_block = _build_conversation_history_block(session_id)
        soil_block = _build_soil_context_block(session_id)

        if not context.strip():
            answer = NO_INFO_MESSAGE
        else:
            try:
                model = _get_gemini_model()
                prompt = SYSTEM_PROMPT.format(
                    no_info_message=NO_INFO_MESSAGE,
                    soil_context=soil_block,
                    conversation_history=conversation_block,
                    context=context,
                    question=payload.question,
                )
                response = model.generate_content(prompt)
                answer = (response.text or "").strip() or NO_INFO_MESSAGE
            except RuntimeError:
                # Missing GOOGLE_API_KEY - surface as a clean 503, handled below.
                raise
            except Exception:
                # Any Gemini-side failure (quota, network, etc.) - friendly,
                # non-crashing response rather than a 500 error page.
                answer = (
                    "⚠️ I'm having trouble reaching the AI model right now. "
                    "Please try again in a moment."
                )

        insert_chat_message(session_id=session_id, question=payload.question, answer=answer)

        return ChatOutput(answer=answer, session_id=session_id, sources=sources)

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot failed to respond: {str(e)}")


@router.get("/history")
def chat_history(session_id: Optional[str] = None, limit: int = 50):
    """Return chat history, optionally filtered to a single session."""
    try:
        return {"history": get_chat_history(session_id=session_id, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")


@router.post("/rebuild-index")
def rebuild_index():
    """
    Force an immediate rebuild of the FAISS knowledge base index from
    whatever .pdf/.txt files are currently in backend/data/. Useful
    after adding new knowledge base files without restarting the server
    (though a restart or the next chat request will also auto-detect
    changes and rebuild automatically).
    """
    try:
        from rag import build_vectorstore, _current_source_files
        build_vectorstore(force_rebuild=True)
        files = [os.path.basename(p) for p in _current_source_files()]
        return {"status": "ok", "message": "Knowledge base index rebuilt.", "files_indexed": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild index: {str(e)}")