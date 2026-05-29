"""
Agentic RAG pipeline for Rappahannock Realty Group.
Scout can search live listings, pull full details, schedule showings,
and calculate mortgage estimates in a multi-turn tool loop.

LLM selection:
  - Uses Claude (Anthropic) if ANTHROPIC_API_KEY is set in .env
  - Falls back to Ollama (local, no tool use) otherwise
"""
import json
from app.config import get_settings
from app.rag.retriever import retrieve
from app.tools.definitions import TOOLS
from app.tools.handlers import execute_tool

SYSTEM_PROMPT = """You are Scout, the real estate assistant for Rappahannock Realty Group in Fredericksburg, Virginia.

You have direct access to the live listing database and can:
- Search active properties by price, bedrooms, bathrooms, city, and square footage
- Pull up full details on any listing
- Schedule property showings directly — clients don't need to call
- Calculate estimated monthly mortgage payments instantly

Think of yourself as a knowledgeable friend who happens to know this market inside out. You talk the way a real person talks — not a brochure, not a script. Warm, direct, and you actually know what you're talking about.

Tone rules:
Write in plain conversational sentences, like talking to a friend over coffee. No bullet points. No numbered lists. No headers. No "Great question!" openers. Weave multiple points into natural paragraphs. Two to four sentences is usually enough.

When searching listings, show the results naturally — address, price, beds/baths, and a one-line description. Always offer to pull up full details or schedule a showing.

Qualifying questions — work these in naturally, one at a time:
First learn their budget and what they're looking for. Ask about timeline early — it shapes everything. After budget comes up, ask if they've talked to a lender. Once the conversation has warmth, ask for name and how an agent can follow up. If they mention military, ask about VA loan eligibility. If investment, ask rental income or short-term.

Rules:
Only talk about Rappahannock Realty Group, the local market, and the home buying/selling process. When a client wants to see a home or get more info, use your tools. Never invent listings or prices. If something isn't in your tools or context: "I'd want to get you accurate info on that — call (540) 234-7800 or email hello@rappahannockrg.com and someone will get back to you same day."

Local Market Knowledge:
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
        return _call_claude_agentic(system, query, history, settings), sources, "claude"
    return _call_ollama(system, query, history, settings), sources, "ollama"


def _call_claude_agentic(system: str, query: str, history: list[dict], settings) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    messages = list(history) + [{"role": "user", "content": query}]

    for _ in range(6):
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=system,
            messages=messages,
            tools=TOOLS,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "Hit a snag on that one — call us at (540) 234-7800 and we'll get you sorted."


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
