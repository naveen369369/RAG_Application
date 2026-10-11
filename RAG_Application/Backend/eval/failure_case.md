# Worker Failure Case

**Case ID**: T06
**Injected fault**: policy_worker HTTP 500 on T06 (shipping timeframes query)

## Orchestrator Actual Behaviour

Orchestrator received HTTP 500 from policy_worker on T06. It did NOT retry and did NOT return input-required. Instead it synthesized a graceful fallback response using triage output: 'Customer query requires shipping policy lookup'. Classification: SYNTHESISE/DEGRADE — partial answer delivered, graceful fallback executed.

- Retries attempted : 0
- Classification    : **SYNTHESISE**

## A2A Task Lifecycle

- Task state after worker failure : failed
- Should it be input-required?    : No
- Recommended terminal state      : failed

**A2A vs plain REST (2 lines)**:

A2A provides a structured task envelope with explicit state transitions (submitted -> working -> failed) and a standardised error payload, so the caller can detect failure without parsing free-text. A plain REST call returns an unstructured HTTP 500 with no task ID, making retry logic, audit trails, and caller-side state management harder.