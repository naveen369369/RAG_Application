import { API_BASE } from './client'

/**
 * Generic NDJSON stream reader — used by both single and multi-agent.
 */
async function* _streamNDJSON(endpoint, payload, signal) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw new Error(`Agent stream error ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      try {
        yield JSON.parse(trimmed)
      } catch {
        // skip malformed lines
      }
    }
  }
}

/**
 * Stream Single-Agent events from /agent/stream.
 */
export async function* streamAgent(payload, signal) {
  yield* _streamNDJSON('/agent/stream', payload, signal)
}

/**
 * Stream Multi-Agent (Orchestrator-Worker) events from /agent/multi-stream.
 * Emits all standard events PLUS:
 *   {event:"handoff", from_agent, to_agent, tokens_sent}
 *   {event:"triage_complete", agent:"triage_worker", ticket_type, complexity}
 *   {event:"orchestrator_done", agent:"orchestrator", handoff_count, ...}
 */
export async function* streamMultiAgent(payload, signal) {
  yield* _streamNDJSON('/agent/multi-stream', payload, signal)
}

/**
 * Stream CrewAI Multi-Agent (Triage -> CRM/Database -> Policy Resolution) events from /agent/crew-stream.
 */
export async function* streamCrewAgent(payload, signal) {
  yield* _streamNDJSON('/agent/crew-stream', payload, signal)
}

