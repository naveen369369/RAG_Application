# Verdict

> **Sunk-cost bias**: Do not keep multi-agent simply because it was built. Evaluate on measured results only.

## Measured Numbers

- Pass rate     : Single = **100%** | Multi = **100%** (delta = +0.0 pp)
- p50 Latency   : Single = **5754 ms** | Multi = **10125 ms** (delta = +4371 ms)
- Token overhead: **1.6x** context re-send multiplier
- Cost/ticket   : Single = **115.47 muUSD** | Multi = **194.52 muUSD** (+68.5%)

## Decision: **KEEP**

Quality and structured triage routing justify orchestrator overhead on complex multi-step tickets.