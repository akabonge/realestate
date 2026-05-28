"""
Persistent lead storage backed by a local JSON file.
Thread-safe via a module-level lock; suitable for a single-process demo server.
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.models import Lead

_lock = threading.Lock()


def _path() -> Path:
    return Path(get_settings().leads_file)


def _load() -> list[dict]:
    p = _path()
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(leads: list[dict]) -> None:
    _path().parent.mkdir(parents=True, exist_ok=True)
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)


def upsert_lead(lead: Lead) -> None:
    with _lock:
        leads = _load()
        for i, existing in enumerate(leads):
            if existing.get("session_id") == lead.session_id:
                leads[i] = lead.model_dump()
                _save(leads)
                return
        leads.append(lead.model_dump())
        _save(leads)


def get_lead(session_id: str) -> Optional[Lead]:
    with _lock:
        for raw in _load():
            if raw.get("session_id") == session_id:
                return Lead(**raw)
    return None


def get_all_leads() -> list[Lead]:
    with _lock:
        return [Lead(**r) for r in _load()]


def new_lead(session_id: str) -> Lead:
    return Lead(
        session_id=session_id,
        captured_at=datetime.now(timezone.utc).isoformat(),
    )
