from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.models import ChatRequest, ChatResponse, LeadListResponse
from app.rag.pipeline import generate_response
from app.rag.lead_extractor import extract_and_score
from app.lead_store import get_all_leads
from app.config import get_settings
from app.rag.embedder import get_collection

router = APIRouter()

# In-memory session store: session_id -> list of message dicts
_sessions: dict[str, list[dict]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    settings = get_settings()
    history = _sessions.get(req.session_id, [])

    response_text, sources, provider = generate_response(req.message, history)

    history = history + [
        {"role": "user", "content": req.message},
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


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    removed = _sessions.pop(session_id, None)
    return {"cleared": removed is not None, "session_id": session_id}
