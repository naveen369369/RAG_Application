"""
intent_guard.py
===============
Lightweight intent classifier that short-circuits the RAG pipeline for:
  - Greetings / chit-chat  ("hi", "hello", "how are you", ...)
  - Completely off-topic questions (coding, maths, general knowledge, news, ...)

Detection is two-tier:
  1. Fast regex check  — catches obvious greetings with zero latency
  2. LLM classifier    — for borderline cases that slip past regex

Returns:
    is_off_topic: bool
    intent:       "greeting" | "off_topic" | "support"
    reply:        pre-written polite response (empty string if support)
"""
from __future__ import annotations

import os
import re
from typing import Tuple

# ---------------------------------------------------------------------------
# Tier-1: Regex patterns (zero-cost, instant)
# ---------------------------------------------------------------------------

_GREETING_PATTERNS = re.compile(
    r"^\s*("
    r"hi|hello|hey|hiya|howdy|greetings|good\s*(morning|afternoon|evening|day)|"
    r"what'?s\s*up|sup|yo|hola|namaste|salut|"
    r"how\s+are\s+you|how\s+r\s+u|how\s+do\s+you\s+do|"
    r"are\s+you\s+there|anyone\s+there|"
    r"thanks?(\s+you)?(\s+so\s+much)?|thx|ty|cheers|"
    r"bye(\s+bye)?|goodbye|see\s+you(\s+later)?|"
    r"good\s*(bye|night|luck)|take\s+care"
    r")(\s+(there|everyone|all|guys|team|friend))?[!?.,]*\s*$",
    re.IGNORECASE,
)

_OFF_TOPIC_PATTERNS = re.compile(
    r"\b("
    r"write\s+(me\s+)?(a\s+)?(code|program|script|poem|essay|story|joke)|"
    r"who\s+is\s+the\s+president|"
    r"what\s+is\s+the\s+capital\s+of|"
    r"weather\s+(in|today|forecast)|"
    r"stock\s+price|"
    r"latest\s+news|"
    r"solve\s+(this\s+)?equation|"
    r"calculate\s+\d|"
    r"translate\s+.{1,40}\s+to\s+\w+|"
    r"recipe\s+for|"
    r"sports\s+score|"
    r"movie\s+review|"
    r"who\s+won\s+the"
    r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Canned responses
# ---------------------------------------------------------------------------

_GREETING_REPLY = (
    "Hello! 👋 I'm your support assistant. "
    "I can help you with questions about our products, shipping, returns, "
    "billing, and account support. What can I help you with today?"
)

_OFF_TOPIC_REPLY = (
    "I'm sorry, I can only help with questions related to our products, "
    "policies, shipping, billing, and account support. "
    "Is there something specific about your order or account I can assist you with?"
)


# ---------------------------------------------------------------------------
# Tier-2: LLM classifier (only called when regex doesn't match)
# ---------------------------------------------------------------------------

_LLM_CLASSIFIER_PROMPT = """\
You are an intent classifier for a customer support system.
Classify the user's message into one of three categories:
  - greeting   : the message is a greeting, farewell, or social chit-chat with no support question
  - off_topic  : the message is completely unrelated to product support (e.g. general knowledge, coding, math, news, weather, personal advice)
  - support    : the message is a genuine customer support question (shipping, returns, billing, account, products, policies, etc.)

Reply with ONLY one word: greeting, off_topic, or support.

Message: {question}
Category:"""


def _llm_classify(question: str) -> str:
    """Call the LLM to classify intent. Returns 'greeting', 'off_topic', or 'support'."""
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage

        model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile").removeprefix("groq/")
        llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY", ""),
            temperature=0.0,
            max_tokens=5,        # We only need one word back
        )
        prompt = _LLM_CLASSIFIER_PROMPT.format(question=question.strip())
        response = llm.invoke([HumanMessage(content=prompt)])
        label = (response.content or "support").strip().lower().split()[0]
        if label in ("greeting", "off_topic", "support"):
            return label
        return "support"
    except Exception:
        # On any failure, let the pipeline proceed normally
        return "support"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_intent(question: str, use_llm_fallback: bool = True) -> Tuple[bool, str, str]:
    """
    Classify a user question.

    Returns:
        (is_off_topic, intent, reply)
        - is_off_topic: True  → short-circuit the pipeline with `reply`
                        False → proceed with normal RAG pipeline
        - intent: "greeting" | "off_topic" | "support"
        - reply:  pre-written response if off-topic, else ""
    """
    q = question.strip()

    # Tier-1: instant regex check
    if _GREETING_PATTERNS.match(q):
        return True, "greeting", _GREETING_REPLY

    if _OFF_TOPIC_PATTERNS.search(q):
        return True, "off_topic", _OFF_TOPIC_REPLY

    # Tier-2: LLM classifier for borderline cases
    if use_llm_fallback and len(q) > 3:
        intent = _llm_classify(q)
        if intent == "greeting":
            return True, "greeting", _GREETING_REPLY
        if intent == "off_topic":
            return True, "off_topic", _OFF_TOPIC_REPLY

    return False, "support", ""
