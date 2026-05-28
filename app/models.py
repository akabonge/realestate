from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    sources: list[str]
    session_id: str
    provider: str
    lead_captured: bool = False


class Lead(BaseModel):
    session_id: str
    captured_at: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    bedrooms: Optional[int] = None
    neighborhoods: list[str] = []
    home_type: Optional[str] = None
    timeline: Optional[str] = None
    motivation: Optional[str] = None
    is_pre_approved: Optional[bool] = None
    is_military: Optional[bool] = None
    is_investor: Optional[bool] = None
    score: int = 0
    score_reasoning: str = ""
    conversation_summary: str = ""


class LeadListResponse(BaseModel):
    total: int
    leads: list[Lead]
