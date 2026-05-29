from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.models import ChatRequest, ChatResponse, LeadListResponse
from app.rag.pipeline import generate_response
from app.rag.lead_extractor import extract_and_score
from app.lead_store import get_all_leads, get_lead, new_lead, upsert_lead
from app.config import get_settings
from app.rag.embedder import get_collection
from app.guardrails import check_input, check_output


class ContactUpdate(BaseModel):
    session_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

router = APIRouter()

# In-memory session store: session_id -> list of message dicts
_sessions: dict[str, list[dict]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    guard = check_input(req.message, req.session_id)
    if not guard.allowed:
        return ChatResponse(
            response=guard.reason,
            sources=[],
            session_id=req.session_id,
            provider="guardrail",
            lead_captured=False,
        )

    settings = get_settings()
    history = _sessions.get(req.session_id, [])

    response_text, sources, provider = generate_response(guard.cleaned_input, history)
    _, response_text = check_output(response_text)

    history = history + [
        {"role": "user", "content": guard.cleaned_input},
        {"role": "assistant", "content": response_text},
    ]
    # Keep only the most recent N messages
    if len(history) > settings.max_history_messages * 2:
        history = history[-(settings.max_history_messages * 2):]
    _sessions[req.session_id] = history

    # Run lead extraction asynchronously — never blocks the response
    background_tasks.add_task(extract_and_score, req.session_id, history)

    return ChatResponse(
        response=response_text,
        sources=sources,
        session_id=req.session_id,
        provider=provider,
        lead_captured=True,
    )


@router.get("/health")
async def health():
    settings = get_settings()
    try:
        collection = get_collection()
        doc_count = collection.count()
    except Exception:
        doc_count = 0

    return {
        "status": "ok",
        "provider": "claude" if settings.anthropic_api_key else "ollama",
        "model": settings.anthropic_model if settings.anthropic_api_key else settings.ollama_model,
        "documents_indexed": doc_count,
        "active_sessions": len(_sessions),
    }


@router.get("/leads", response_model=LeadListResponse)
async def list_leads():
    leads = get_all_leads()
    return LeadListResponse(total=len(leads), leads=leads)


@router.post("/leads/contact")
async def save_contact(data: ContactUpdate):
    lead = get_lead(data.session_id) or new_lead(data.session_id)
    if data.name:  lead.name  = data.name.strip()
    if data.email: lead.email = data.email.strip()
    if data.phone: lead.phone = data.phone.strip()
    upsert_lead(lead)
    return {"ok": True, "session_id": data.session_id}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    removed = _sessions.pop(session_id, None)
    return {"cleared": removed is not None, "session_id": session_id}
