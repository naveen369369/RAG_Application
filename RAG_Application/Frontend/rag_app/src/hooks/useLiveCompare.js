import { useCallback, useState } from 'react'
import { streamAgent } from '../api/agent'
import { streamWorkflow } from '../api/workflow_stream'

const emptyPanel = () => ({
  events: [],
  tokens: '',
  steps: [],
  toolCalls: [],
  metrics: null,
  streaming: false,
  error: null,
  budgetHit: false,
  budgetReason: '',
})

export function useLiveCompare() {
  const [agentPanel, setAgentPanel] = useState(emptyPanel())
  const [workflowPanel, setWorkflowPanel] = useState(emptyPanel())
  const [comparing, setComparing] = useState(false)

  const compare = useCallback(async (payload) => {
    setAgentPanel({ ...emptyPanel(), streaming: true })
    setWorkflowPanel({ ...emptyPanel(), streaming: true })
    setComparing(true)

    // Fire both streams concurrently — no await between them
    const agentDone = (async () => {
      try {
        for await (const event of streamAgent(payload)) {
          setAgentPanel((prev) => applyAgentPanelEvent(prev, event))
        }
      } catch (err) {
        setAgentPanel((prev) => ({ ...prev, streaming: false, error: err.message }))
      }
    })()

    const workflowDone = (async () => {
      try {
        for await (const event of streamWorkflow(payload)) {
          setWorkflowPanel((prev) => applyWorkflowPanelEvent(prev, event))
        }
      } catch (err) {
        setWorkflowPanel((prev) => ({ ...prev, streaming: false, error: err.message }))
      }
    })()

    await Promise.allSettled([agentDone, workflowDone])
    setComparing(false)
  }, [])

  const reset = useCallback(() => {
    setAgentPanel(emptyPanel())
    setWorkflowPanel(emptyPanel())
    setComparing(false)
  }, [])

  return { agentPanel, workflowPanel, comparing, compare, reset }
}

function applyAgentPanelEvent(prev, event) {
  switch (event.event) {
    case 'thought':
      return { ...prev, events: [...prev.events, { type: 'thought', text: event.text }] }
    case 'tool_start':
      return {
        ...prev,
        toolCalls: [...prev.toolCalls, { tool: event.tool, args: event.args, status: 'running' }],
        events: [...prev.events, { type: 'tool_start', tool: event.tool, args: event.args }],
      }
    case 'tool_result':
      return {
        ...prev,
        toolCalls: prev.toolCalls.map((tc) =>
          tc.tool === event.tool && tc.status === 'running'
            ? { ...tc, result: event.result, status: 'done' }
            : tc
        ),
        events: [...prev.events, { type: 'tool_result', tool: event.tool, result: event.result }],
      }
    case 'token':
      return { ...prev, tokens: prev.tokens + event.t }
    case 'done':
      return {
        ...prev,
        streaming: false,
        metrics: {
          latency_ms: event.latency_ms,
          tool_calls_made: event.tool_calls_made,
          budget: event.budget,
        },
      }
    case 'budget_hit':
      return { ...prev, streaming: false, budgetHit: true, budgetReason: event.reason }
    case 'error':
      return { ...prev, streaming: false, error: event.detail }
    default:
      return prev
  }
}

function applyWorkflowPanelEvent(prev, event) {
  switch (event.event) {
    case 'step_start':
      return { ...prev, steps: [...prev.steps, { step: event.step, status: 'running' }] }
    case 'step_done':
      return {
        ...prev,
        steps: prev.steps.map((s) =>
          s.step === event.step && s.status === 'running'
            ? { ...s, status: 'done', result: event.result }
            : s
        ),
      }
    case 'token':
      return { ...prev, tokens: prev.tokens + event.t }
    case 'done':
      return {
        ...prev,
        streaming: false,
        metrics: {
          latency_ms: event.latency_ms,
          total_tokens: event.total_tokens,
          cost_usd: event.cost_usd,
        },
      }
    case 'error':
      return { ...prev, streaming: false, error: event.detail }
    default:
      return prev
  }
}
