"""
AI Input/Output Guardrails
==========================
Defends against prompt injection, abuse, and runaway costs.
Every message passes through check_input() before hitting the LLM,
and every LLM response passes through check_output() before returning
to the client.

Threat model:
  - Prompt injection: attacker tries to override system instructions
  - Token abuse: very long messages waste API budget
  - Off-topic hijacking: attacker tries to use the chatbot for unrelated tasks
  - Rate abuse: bot floods the endpoint with requests
  - Output poisoning: LLM returns empty/garbage under load

What this does NOT cover (handle at infrastructure level):
  - Network-level DDoS (use Cloudflare / Railway's built-in protection)
  - Authentication (these are intentionally public demo endpoints)
  - HTTPS (handled by Railway's reverse proxy)
"""

import re
import time
import threading
from dataclasses import dataclass

# ── Prompt injection patterns ─────────────────────────────────────────────────
# These patterns match known jailbreak and injection techniques.
# Not exhaustive — determined attackers always find new vectors —
# but covers the most common automated and manual attempts.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|directives?|rules?|context)",
    r"you\s+are\s+now\s+(a|an|DAN|GPT|ChatGPT|an?\s+AI\s+without)",
    r"(new|updated|changed|different|revised)\s+(system\s+)?(prompt|instructions?|rules?|persona)",
    r"disregard\s+(all|your|previous|prior|everything|the\s+above)",
    r"forget\s+(everything|all|your\s+instructions|what\s+you\s+were\s+told|your\s+training)",
    r"(act|behave|respond|pretend|roleplay)\s+as\s+(if\s+)?(you\s+are|a|an)",
    r"pretend\s+you\s+(are|were|have\s+no)",
    r"\bDAN\b|\bDANmode\b",
    r"jailbreak|jail\s*break",
    r"from\s+now\s+on\s+(you\s+)?(are|will|must|should|have\s+to)",
    r"override\s+(your\s+)?(instructions?|programming|training|guidelines?|safety)",
    r"(bypass|disable|remove|turn\s+off)\s+(your\s+)?(safety|filter|restriction|guardrail|limit)",
    r"system\s*prompt\s*:",
    r"<\s*system\s*>|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]",  # token injection
    r"print\s+(your\s+)?(system\s+prompt|instructions|prompt)",
    r"repeat\s+(your\s+)?(system|instructions|prompt)\s+(after|back|to)\s+me",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

# ── Rate limiting ─────────────────────────────────────────────────────────────
_rate_store: dict[str, list[float]] = {}
_rate_lock = threading.Lock()

RATE_LIMIT_MESSAGES = 25        # max messages per session in the window
RATE_LIMIT_WINDOW_SEC = 300     # 5-minute rolling window

# ── Input constraints ─────────────────────────────────────────────────────────
MAX_INPUT_LENGTH = 600
MIN_INPUT_LENGTH = 1


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""
    cleaned_input: str = ""


def check_input(text: str, session_id: str) -> GuardrailResult:
    """
    Run all input guardrails. Call this before sending anything to the LLM.
    Returns GuardrailResult — if allowed=False, return reason directly to client.
    """
    text = text.strip()

    if len(text) < MIN_INPUT_LENGTH:
        return GuardrailResult(allowed=False, reason="Please type a message.")

    if len(text) > MAX_INPUT_LENGTH:
        return GuardrailResult(
            allowed=False,
            reason=f"Your message is a bit long — please keep it under {MAX_INPUT_LENGTH} characters.",
        )

    for pattern in _COMPILED:
        if pattern.search(text):
            return GuardrailResult(
                allowed=False,
                reason="I'm only here to help with questions about real estate in the Fredericksburg area. What can I help you with?",
            )

    if not _within_rate_limit(session_id):
        return GuardrailResult(
            allowed=False,
            reason="You've sent quite a few messages — give it a moment and try again.",
        )

    return GuardrailResult(allowed=True, cleaned_input=text)


def check_output(response: str) -> tuple[bool, str]:
    """
    Validate LLM output before returning to the user.
    Returns (is_valid, response_or_fallback_message).
    """
    if not response or not response.strip():
        return False, "I didn't quite catch that — could you try asking again?"

    if len(response.strip()) < 4:
        return False, "Something went wrong on my end. Please try again."

    return True, response.strip()


def _within_rate_limit(session_id: str) -> bool:
    now = time.time()
    with _rate_lock:
        timestamps = [t for t in _rate_store.get(session_id, [])
                      if now - t < RATE_LIMIT_WINDOW_SEC]
        if len(timestamps) >= RATE_LIMIT_MESSAGES:
            _rate_store[session_id] = timestamps
            return False
        timestamps.append(now)
        _rate_store[session_id] = timestamps
        return True
