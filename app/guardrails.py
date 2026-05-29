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
  - Rate abuse: bot or script floods the endpoint
  - Output poisoning: LLM returns empty/garbage/oversized content
  - Session spoofing: attacker passes arbitrary session IDs

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
_INJECTION_PATTERNS = [
    # Classic instruction override
    r"ignore\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|directives?|rules?|context)",
    r"disregard\s+(all|your|previous|prior|everything|the\s+above)",
    r"forget\s+(everything|all|your\s+instructions|what\s+you\s+were\s+told|your\s+training)",
    r"override\s+(your\s+)?(instructions?|programming|training|guidelines?|safety)",
    r"from\s+now\s+on\s+(you\s+)?(are|will|must|should|have\s+to)",
    # Persona hijacking
    r"you\s+are\s+now\s+(a|an|DAN|GPT|ChatGPT|an?\s+AI\s+without)",
    r"(new|updated|changed|different|revised)\s+(system\s+)?(prompt|instructions?|rules?|persona)",
    r"(act|behave|respond|pretend|roleplay)\s+as\s+(if\s+)?(you\s+are|a|an)",
    r"pretend\s+you\s+(are|were|have\s+no)",
    r"(simulate|emulate|impersonate|mimic)\s+(being\s+)?(a|an)\s+\w",
    r"\bDAN\b|\bDANmode\b",
    r"jailbreak|jail\s*break",
    # Safety bypass
    r"(bypass|disable|remove|turn\s+off)\s+(your\s+)?(safety|filter|restriction|guardrail|limit)",
    r"as\s+(a|an)\s+(language\s+model|llm|gpt|ai\s+model)\s+(without|that\s+(has\s+)?no)",
    r"you\s+(can|should|must)\s+(help|assist|answer)\s+(me\s+)?(with\s+)?(anything|everything|all\s+topics?)",
    # System prompt extraction
    r"system\s*prompt\s*:",
    r"<\s*system\s*>|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]",
    r"print\s+(your\s+)?(system\s+prompt|instructions|prompt)",
    r"repeat\s+(your\s+)?(system|instructions|prompt)\s+(after|back|to)\s+me",
    r"tell\s+me\s+(what|about)\s+(your\s+)?(system\s+prompt|instructions?|rules?|configuration)",
    r"what\s+(are|were)\s+(your|the)\s+(original\s+)?(instructions?|rules?|guidelines?|constraints?)",
    # Code/script injection
    r"(execute|run|eval|exec)\s*[\(\{<]",
    r"<\s*script|javascript\s*:|data\s*:\s*text",
    # Credential fishing
    r"\b(password|passwd|api.?key|secret.?key|access.?token|bearer.?token)\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

# ── Session ID validation ─────────────────────────────────────────────────────
_SESSION_ID_RE = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')

# ── Rate limiting — session-based ─────────────────────────────────────────────
_session_rate_store: dict[str, list[float]] = {}
_session_rate_lock = threading.Lock()
SESSION_RATE_LIMIT = 25
SESSION_RATE_WINDOW = 300

# ── Rate limiting — IP-based ──────────────────────────────────────────────────
_ip_rate_store: dict[str, list[float]] = {}
_ip_rate_lock = threading.Lock()
IP_RATE_LIMIT = 120
IP_RATE_WINDOW = 3600

# ── Input / output constraints ────────────────────────────────────────────────
MAX_INPUT_LENGTH = 600
MIN_INPUT_LENGTH = 1
MAX_OUTPUT_LENGTH = 2000


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""
    cleaned_input: str = ""


def check_input(text: str, session_id: str, ip: str = "") -> GuardrailResult:
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
            reason=f"Your message is a bit long. Please keep it under {MAX_INPUT_LENGTH} characters.",
        )

    if not _SESSION_ID_RE.match(session_id):
        return GuardrailResult(allowed=False, reason="Invalid session. Please refresh and try again.")

    for pattern in _COMPILED:
        if pattern.search(text):
            return GuardrailResult(
                allowed=False,
                reason="I'm only here to help with questions about real estate in the Fredericksburg area. What can I help you with?",
            )

    if ip and not _within_ip_rate_limit(ip):
        return GuardrailResult(
            allowed=False,
            reason="Too many requests from your network. Please wait a few minutes and try again.",
        )

    if not _within_session_rate_limit(session_id):
        return GuardrailResult(
            allowed=False,
            reason="You've sent quite a few messages. Give it a moment and try again.",
        )

    return GuardrailResult(allowed=True, cleaned_input=text)


def check_output(response: str) -> tuple[bool, str]:
    """
    Validate LLM output before returning to the user.
    Returns (is_valid, response_or_fallback_message).
    """
    if not response or not response.strip():
        return False, "I didn't quite catch that. Could you try asking again?"

    response = response.strip()

    if len(response) < 4:
        return False, "Something went wrong on my end. Please try again."

    if len(response) > MAX_OUTPUT_LENGTH:
        response = response[:MAX_OUTPUT_LENGTH].rsplit(" ", 1)[0] + "..."

    return True, response


def _within_session_rate_limit(session_id: str) -> bool:
    now = time.time()
    with _session_rate_lock:
        timestamps = [t for t in _session_rate_store.get(session_id, [])
                      if now - t < SESSION_RATE_WINDOW]
        if len(timestamps) >= SESSION_RATE_LIMIT:
            _session_rate_store[session_id] = timestamps
            return False
        timestamps.append(now)
        _session_rate_store[session_id] = timestamps
        return True


def _within_ip_rate_limit(ip: str) -> bool:
    now = time.time()
    with _ip_rate_lock:
        timestamps = [t for t in _ip_rate_store.get(ip, [])
                      if now - t < IP_RATE_WINDOW]
        if len(timestamps) >= IP_RATE_LIMIT:
            _ip_rate_store[ip] = timestamps
            return False
        timestamps.append(now)
        _ip_rate_store[ip] = timestamps
        return True
