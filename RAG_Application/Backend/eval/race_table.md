# Race Table: Single Agent vs Multi-Agent

Real live evaluation on the 10 customer support tickets. Judged on live retrieval & LLM generation.

| Case | SA Pass | MA Pass | SA Lat (ms) | MA Lat (ms) | SA Tokens | MA Tokens | SA Cost (muUSD) | MA Cost (muUSD) |
|------|---------|---------|-------------|-------------|-----------|-----------|-----------------|-----------------|
| T01 | PASS | PASS | 9217 | 102846 | 435 | 717 | 160.50 | 240.30 |
| T02 | PASS | PASS | 8216 | 9701 | 366 | 536 | 115.80 | 186.00 |
| T03 | PASS | PASS | 5701 | 9940 | 366 | 536 | 115.80 | 186.00 |
| T04 | PASS | PASS | 5398 | 74483 | 362 | 795 | 114.60 | 263.70 |
| T05 | PASS | PASS | 6256 | 10125 | 357 | 527 | 113.10 | 183.30 |
| T06 | PASS | PASS | 5960 | 10645 | 333 | 503 | 105.90 | 176.10 |
| T07 | PASS | PASS | 4754 | 10424 | 338 | 508 | 107.40 | 177.60 |
| T08 | PASS | PASS | 5754 | 10568 | 338 | 508 | 107.40 | 177.60 |
| T09 | PASS | PASS | 5416 | 9937 | 338 | 508 | 107.40 | 177.60 |
| T10 | PASS | PASS | 8694 | 9965 | 336 | 506 | 106.80 | 177.00 |

## Summary

| Metric | Single Agent | Multi-Agent |
|--------|-------------|-------------|
| Pass Rate | 100% | 100% |
| p50 Latency | 5754 ms | 10125 ms |
| p99 Latency | 9217 ms | 102846 ms |
| Total Tokens | 3569 | 5644 |
| Cost/ticket | 115.47 muUSD | 194.52 muUSD |
