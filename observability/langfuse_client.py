"""
Langfuse Observability Client
==============================
Singleton wrapper around the Langfuse v2 Python SDK.

If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set (or are placeholder
values), every function silently returns a no-op object so the application
runs normally without any tracing.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

_langfuse = None
_enabled = False


def _init():
    global _langfuse, _enabled
    pub = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sec = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not pub or not sec or pub.startswith("your_") or sec.startswith("your_"):
        logger.info("Langfuse not configured — set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY to enable.")
        return

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(public_key=pub, secret_key=sec, host=host)
        _enabled = True
        logger.info(f"Langfuse initialized — traces → {host}")
    except ImportError:
        logger.warning("langfuse not installed — run: pip install langfuse==2.60.10")
    except Exception as exc:
        logger.warning(f"Langfuse init failed: {exc}")


_init()


# ---------------------------------------------------------------------------
# No-op stubs — returned when Langfuse is disabled
# ---------------------------------------------------------------------------

class _NoOpObj:
    def span(self, **kw): return _NoOpObj()
    def generation(self, **kw): return _NoOpObj()
    def score(self, **kw): return self
    def update(self, **kw): return self
    def end(self, **kw): return self


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_enabled() -> bool:
    return _enabled


def create_trace(**kwargs):
    """Create a Langfuse trace (or no-op if disabled)."""
    if not _enabled or _langfuse is None:
        return _NoOpObj()
    try:
        return _langfuse.trace(**kwargs)
    except Exception as exc:
        logger.debug(f"create_trace failed: {exc}")
        return _NoOpObj()


def flush_langfuse():
    """Flush all pending events to Langfuse."""
    if _enabled and _langfuse is not None:
        try:
            _langfuse.flush()
        except Exception as exc:
            logger.debug(f"flush failed: {exc}")
