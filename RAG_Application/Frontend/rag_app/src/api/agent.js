import { API_BASE } from './client'

/**
 * Stream agent events from /agent/stream.
 * Yields parsed event objects:
 *   {event:"start"} {event:"thought",text} {event:"tool_start",tool,args}
 *   {event:"tool_result",tool,result} {event:"token",t}
 *   {event:"done",latency_ms,tool_calls_made,budget}
 *   {event:"budget_hit",reason,partial_answer} {event:"error",detail}
 */
export async function* streamAgent(payload, signal) {
  const res = await fetch(`${API_BASE}/agent/stream`, {
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
    buffer = lines.pop() // keep partial line
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
