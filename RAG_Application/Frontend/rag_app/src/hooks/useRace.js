import { useCallback, useRef, useState } from 'react'
import { streamRace } from '../api/race'

const TICKET_IDS = ['T01','T02','T03','T04','T05','T06','T07','T08','T09','T10']

function initialTicketRows() {
  return TICKET_IDS.reduce((acc, id) => {
    acc[id] = { agent: null, workflow: null }
    return acc
  }, {})
}

export function useRace() {
  const [racing, setRacing] = useState(false)
  const [ticketRows, setTicketRows] = useState(initialTicketRows())
  const [summary, setSummary] = useState(null)
  const [verdict, setVerdict] = useState('')
  const abortRef = useRef(null)

  const runRace = useCallback(async () => {
    setRacing(true)
    setTicketRows(initialTicketRows())
    setSummary(null)
    setVerdict('')

    abortRef.current = new AbortController()
    try {
      for await (const event of streamRace(abortRef.current.signal)) {
        if (event.event === 'ticket_done') {
          setTicketRows((prev) => ({
            ...prev,
            [event.ticket_id]: {
              ...prev[event.ticket_id],
              [event.mode]: {
                passed: event.passed,
                latency_ms: event.latency_ms,
                total_tokens: event.total_tokens,
                cost_usd: event.cost_usd,
                budget_hit: event.budget_hit,
              },
            },
          }))
        } else if (event.event === 'race_complete') {
          setSummary(event.summary)
          setVerdict(event.verdict)
          setRacing(false)
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') console.error('Race error:', err)
      setRacing(false)
    }
  }, [])

  const stopRace = useCallback(() => {
    abortRef.current?.abort()
    setRacing(false)
  }, [])

  return { racing, ticketRows, summary, verdict, runRace, stopRace }
}
