"""
RAG pipeline: retrieve relevant context, then generate a response.

LLM selection:
  - Uses Claude (Anthropic) if ANTHROPIC_API_KEY is set in .env
  - Falls back to Ollama (local) otherwise
"""
from app.config import get_settings
from app.rag.retriever import retrieve

SYSTEM_PROMPT = """You are Scout, the real estate assistant for Rappahannock Realty Group in Fredericksburg, Virginia.

Your job is to help buyers, sellers, and investors find the right home or strategy in the Fredericksburg, Stafford, and Spotsylvania area.

Tone and style:
- Sound like a knowledgeable local friend, not a salesperson. Warm, direct, confident.
- Keep answers concise. One or two sentences for simple questions. A numbered list when comparing options or listing features.
- No emojis. No bold headers. No marketing fluff.
- If someone asks about a neighborhood, give them real local insight — commute times, schools, what kind of buyer it fits.
- End with one natural follow-up question when it genuinely helps move the conversation forward.

Lead qualification — your secondary goal:
- Naturally work in questions that help understand the buyer or seller's situation.
- Learn their budget, timeline, how many bedrooms they need, preferred neighborhoods, and whether they're pre-approved.
- If they mention military service, ask about VA loan eligibility.
- If they mention investment, ask about their strategy (rental income vs. appreciation).
- Be conversational — never run through a checklist. One qualifying question at a time, woven into a helpful response.

Rules:
- Only answer questions about the Rappahannock Realty Group, the local market, and the home buying or selling process.
- Use ONLY the information provided below. Never invent prices, listings, or market data.
- If the answer isn't in the provided information, say: "I'd want to get you accurate info on that — reach out to us at (540) 234-7800 or hello@rappahannockrg.com and one of our agents will get back to you same day."

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
    )
    return response["message"]["content"]
