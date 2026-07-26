import threading
import time
from typing import Any, Dict, Optional

_lock = threading.Lock()

# session_id -> {"inputs": {...}, "analysis": {...}, "updated_at": float}
_soil_context_store: Dict[str, Dict[str, Any]] = {}

# Soil context older than this is considered stale and ignored by the
# chatbot, so an old session tab left open overnight doesn't quietly
# reuse yesterday's soil values.
_MAX_CONTEXT_AGE_SECONDS = 6 * 60 * 60  # 6 hours


def set_soil_context(session_id: str, inputs: Dict[str, Any], analysis: Dict[str, Any]) -> None:
    """
    Store the latest Soil Health Analyzer inputs + computed analysis for
    a single session. Overwrites any previous value for that session only.
    """
    if not session_id:
        return
    with _lock:
        _soil_context_store[session_id] = {
            "inputs": inputs,
            "analysis": analysis,
            "updated_at": time.time(),
        }


def get_soil_context(session_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Retrieve the latest soil context for a session, or None if this
    session has no recent analysis on record.
    """
    if not session_id:
        return None
    with _lock:
        entry = _soil_context_store.get(session_id)

    if not entry:
        return None
    if time.time() - entry["updated_at"] > _MAX_CONTEXT_AGE_SECONDS:
        return None
    return entry


def clear_soil_context(session_id: str) -> None:
    """Remove stored soil context for a session (e.g. on explicit reset)."""
    with _lock:
        _soil_context_store.pop(session_id, None)
