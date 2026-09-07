import { API_BASE } from './client'

/**
 * Stream the 10-ticket race from /race.
 * Yields parsed event objects:
 *   {event:"ticket_start",ticket_id,mode}
 *   {event:"ticket_done",ticket_id,mode,passed,latency_ms,total_tokens,cost_usd}
 *   {event:"budget_hit",ticket_id,mode,reason}
 *   {event:"race_complete",summary:{agent:{...},workflow:{...}},verdict}
 */
export async function* streamRace(signal) {
  const res = await fetch(`${API_BASE}/race`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
    signal,
  })
  if (!res.ok) throw new Error(`Race error ${res.status}`)

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
