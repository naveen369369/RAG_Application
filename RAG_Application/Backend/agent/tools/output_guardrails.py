"""
output_guardrails.py
====================
Final-answer output scanner — called before any agent response is streamed
to the user.

Checks for:
  - Injection markers (directives embedded in tool outputs that leaked through)
  - PII (SSN, credit card, phone numbers)
  - System prompt leakage

Used by:
    from agent.tools.output_guardrails import validate_output
    safe, violations = validate_output(final_answer)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Tool Output Sanitizer (Defends against Indirect Prompt Injections)
# ---------------------------------------------------------------------------

_SUSPICIOUS_TOOL_DIRECTIVES = [
    r"SYSTEM\s*:",
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(the\s+)?system\s+prompt",
    r"forward\s+.{0,40}to\s+\w+@\w+\.\w+",
    r"send\s+(all\s+)?(data|customer|records|database)\s+to",
    r"exfiltrate",
    r"<script\b",
    r"Act\s+as\s+DAN",
]


def sanitise_tool_output(raw: str) -> str:
    """
    Sanitise document text or tool output before passing to LLM.
    Replaces prompt injection directives embedded in retrieved text.
    """
    if not isinstance(raw, str):
        return raw
    cleaned = raw
    for pat in _SUSPICIOUS_TOOL_DIRECTIVES:
        cleaned = re.sub(pat, "[BLOCKED_DIRECTIVE]", cleaned, flags=re.IGNORECASE)
    return cleaned


# ---------------------------------------------------------------------------
# Patterns for Output Scanning
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?previous\s+instructions",    "injection_marker"),
    (r"disregard\s+(the\s+)?system\s+prompt",          "injection_marker"),
    (r"forward\s+.{0,40}to\s+\w+@\w+\.\w+",           "data_exfiltration"),
    (r"send\s+(data|info|details)\s+to",               "data_exfiltration"),
    (r"exfiltrate",                                     "data_exfiltration"),
    (r"<script\b",                                      "xss"),
    (r"SYSTEM\s*:.*?(forward|send|email)",              "indirect_injection"),
    (r"Act\s+as\s+DAN",                                "jailbreak_marker"),
    (r"developer\s+mode\s+enabled",                    "jailbreak_marker"),
]

_PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b",                               "ssn"),
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b", "credit_card"),
    (r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b",                  "phone_number"),
]

_SYSTEM_PROMPT_PATTERNS = [
    (r"REACT_SYSTEM_PROMPT",                           "system_prompt_leak"),
    (r"RULES:\s*-\s*Call rag_retrieval",               "system_prompt_leak"),
    (r"QUESTION TYPE:\s*(Simple|Complex)",             "system_prompt_leak"),
    (r"Step 1.*customer_lookup.*FIRST",                "system_prompt_leak"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_output(text: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate agent output before delivery to the user.

    Args:
        text: The final answer string from the agent.

    Returns:
        (is_safe: bool, violations: list)
        Each violation: {'type': str, 'category': str, 'match': str}
    """
    violations: List[Dict[str, Any]] = []

    for pattern, vtype in _INJECTION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            violations.append({
                "type": vtype,
                "category": "injection",
                "match": m.group(0)[:100],
            })

    for pattern, vtype in _PII_PATTERNS:
        m = re.search(pattern, text)
        if m:
            violations.append({
                "type": vtype,
                "category": "pii",
                "match": m.group(0)[:100],
            })

    for pattern, vtype in _SYSTEM_PROMPT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            violations.append({
                "type": vtype,
                "category": "leakage",
                "match": m.group(0)[:100],
            })

    return len(violations) == 0, violations


SAFE_REFUSAL = (
    "I'm sorry, I encountered an issue processing your request. "
    "Please contact our support team directly for assistance."
)


def guard_output(text: str) -> str:
    """
    High-level guard: validate output and return the original if safe,
    or a safe refusal if violations are found.

    Use this as the final step before streaming/returning the answer.
    """
    is_safe, violations = validate_output(text)
    if is_safe:
        return text
    import logging
    logging.getLogger(__name__).warning(
        "Output guardrail blocked response. Violations: %s",
        [v["type"] for v in violations],
    )
    return SAFE_REFUSAL
