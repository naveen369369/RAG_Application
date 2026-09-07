import { API_BASE } from './client'

/**
 * Stream workflow step events from /workflow/stream.
 * Yields parsed event objects:
 *   {event:"step_start",step} {event:"step_done",step,result}
 *   {event:"token",t} {event:"done",latency_ms,total_tokens,cost_usd}
 *   {event:"error",detail}
 */
export async function* streamWorkflow(payload, signal) {
  const res = await fetch(`${API_BASE}/workflow/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw new Error(`Workflow stream error ${res.status}`)

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
