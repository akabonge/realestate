"""
AI Lead Extractor — the extraordinary feature.

After each conversation turn, this module:
1. Reads the full conversation history
2. Asks the LLM to extract structured lead data (name, email, budget, timeline, etc.)
3. Scores the lead 1-10 with written reasoning
4. Persists the result to the lead store

This runs as a background task — it never blocks the chat response.
"""
import json
import re
from app.config import get_settings
from app.models import Lead
from app.lead_store import upsert_lead, get_lead, new_lead

EXTRACTION_PROMPT = """You are a real estate lead analyst. Read this conversation between a buyer/seller and Scout (a real estate assistant), then extract all available lead information and score the lead.

Conversation:
{conversation}

Return a JSON object with these fields (use null for anything not mentioned):
{{
  "name": null,
  "email": null,
  "phone": null,
  "budget_min": null,
  "budget_max": null,
  "bedrooms": null,
  "neighborhoods": [],
  "home_type": null,
  "timeline": null,
  "motivation": null,
  "is_pre_approved": null,
  "is_military": null,
  "is_investor": null,
  "conversation_summary": "one sentence summary of what the lead is looking for",
  "score": 0,
  "score_reasoning": "explanation of the score"
}}

Lead scoring criteria (1-10):
- 9-10: Has budget, timeline under 3 months, pre-approved or VA eligible, knows target neighborhoods — ready to move now
- 7-8: Has budget and general timeline, actively looking, specific preferences stated
- 5-6: Actively engaged, asking detailed questions, budget range implied or stated, timeline 3-6 months
- 3-4: Browsing, exploring the market, no specific timeline or budget yet
- 1-2: Very early stage, vague questions, no qualifying information shared

Return ONLY valid JSON. No explanation, no markdown fences."""


def extract_and_score(session_id: str, history: list[dict]) -> Lead:
    """
    Runs lead extraction in the background. Returns the updated Lead object.
    history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    """
    settings = get_settings()

    conversation_text = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}" for msg in history
    )

    raw_json = _call_llm_for_extraction(conversation_text, settings)
    extracted = _parse_extraction(raw_json)

    existing = get_lead(session_id) or new_lead(session_id)

    # Merge: only overwrite None fields with newly extracted values
    for field, value in extracted.items():
        if value is not None and value != [] and value != "":
            setattr(existing, field, value)

    # Score always updates to the latest assessment
    if extracted.get("score"):
        existing.score = extracted["score"]
    if extracted.get("score_reasoning"):
        existing.score_reasoning = extracted["score_reasoning"]
    if extracted.get("conversation_summary"):
        existing.conversation_summary = extracted["conversation_summary"]

    upsert_lead(existing)
    return existing


def _call_llm_for_extraction(conversation: str, settings) -> str:
    prompt = EXTRACTION_PROMPT.format(conversation=conversation)

    if settings.anthropic_api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    import ollama
    response = ollama.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]


def _parse_extraction(raw: str) -> dict:
    try:
        # Strip markdown fences if model wraps despite instruction
        cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return {}
