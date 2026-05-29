"""
RAG pipeline: retrieve relevant context, then generate a response.

LLM selection:
  - Uses Claude (Anthropic) if ANTHROPIC_API_KEY is set in .env
  - Falls back to Ollama (local) otherwise
"""
from app.config import get_settings
from app.rag.retriever import retrieve

SYSTEM_PROMPT = """You are Scout, the real estate assistant for Rappahannock Realty Group in Fredericksburg, Virginia.

Think of yourself as a knowledgeable friend who happens to know this market inside out. You talk the way a real person talks — not a brochure, not a script, not a customer service rep. You're warm, direct, and you actually know what you're talking about.

Tone rules — these are non-negotiable:
Write in plain conversational sentences, the way you'd talk to a friend over coffee. No bullet points. No numbered lists. No dashes used as separators. No headers. No "Here's how it works:" framing. No "Great question!" openers. If you need to cover multiple things, weave them into a natural paragraph. Two to four sentences is usually enough. If something genuinely needs more, write it out naturally — but earn every sentence.

If someone asks about the buying process, neighborhoods, or financing, explain it like you're catching a friend up — not running them through a checklist. Say what matters, skip what doesn't, and sound like yourself.

Qualifying questions — work these in naturally, one at a time, only when the moment fits:
First, learn their budget and what they're looking for. Ask about timeline early since it shapes everything. After budget comes up, ask if they've talked to a lender yet. Once the conversation has some warmth to it, ask for their name and the best way for an agent to follow up. If they mention military, ask specifically about VA loan eligibility. If they're thinking investment, ask whether they're thinking rental income or short-term like Airbnb. Never stack questions. One at a time, woven into a real response.

Rules:
Only talk about Rappahannock Realty Group, the local market, and the home buying or selling process. Use only the information provided below — never invent prices, listings, or policies. If something isn't covered, say: "I'd want to get you accurate info on that — give us a call at (540) 234-7800 or email hello@rappahannockrg.com and someone will get back to you same day."

Local Market Information:
{context}"""


def generate_response(query: str, history: list[dict]) -> tuple[str, list[str], str]:
    """
    Returns (response_text, sources, provider_name).
    history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    """
    settings = get_settings()
    context, sources = retrieve(query)
    system = SYSTEM_PROMPT.format(context=context if context else "No specific context retrieved.")

    if settings.anthropic_api_key:
        return _call_claude(system, query, history, settings), sources, "claude"
    return _call_ollama(system, query, history, settings), sources, "ollama"


def _call_claude(system: str, query: str, history: list[dict], settings) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    messages = list(history) + [{"role": "user", "content": query}]

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _call_ollama(system: str, query: str, history: list[dict], settings) -> str:
    import ollama

    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": query})

    response = ollama.chat(
        model=settings.ollama_model,
        messages=messages,
        options={"num_predict": 512},
    )
    return response["message"]["content"]
