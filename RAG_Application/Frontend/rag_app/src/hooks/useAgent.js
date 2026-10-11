import { useCallback, useRef, useState } from 'react'
import { streamAgent, streamMultiAgent, streamCrewAgent } from '../api/agent'


function getOrCreateSessionId() {
  let id = sessionStorage.getItem('rag_session_id')
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem('rag_session_id', id)
  }
  return id
}

function applyAgentEvent(state, event) {
  const { messages } = state
  const last = messages[messages.length - 1]

  switch (event.event) {
    case 'thought':
      return {
        ...state,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? { ...m, thoughts: [...(m.thoughts || []), { text: event.text, agent: event.agent || 'agent' }] }
            : m
        ),
      }
    case 'handoff':
      return {
        ...state,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? {
                ...m,
                handoffs: [
                  ...(m.handoffs || []),
                  {
                    from: event.from_agent,
                    to: event.to_agent,
                    tokens: event.tokens_sent,
                    purpose: event.purpose,
                  },
                ],
              }
            : m
        ),
      }
    case 'triage_complete':
      return {
        ...state,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? {
                ...m,
                triage: {
                  ticket_type: event.ticket_type,
                  complexity: event.complexity,
                  summary: event.summary,
                  needs_order_lookup: event.needs_order_lookup,
                  needs_customer_lookup: event.needs_customer_lookup,
                  needs_policy_lookup: event.needs_policy_lookup,
                },
              }
            : m
        ),
      }
    case 'tool_start':
      return {
        ...state,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? {
                ...m,
                toolCalls: [
                  ...(m.toolCalls || []),
                  { tool: event.tool, args: event.args, result: null, status: 'running', agent: event.agent },
                ],
              }
            : m
        ),
      }
    case 'tool_result':
      return {
        ...state,
        messages: messages.map((m, i) => {
          if (i !== messages.length - 1 || m.role !== 'assistant') return m
          const toolCalls = (m.toolCalls || []).map((tc) =>
            tc.tool === event.tool && tc.status === 'running'
              ? { ...tc, result: event.result, status: 'done' }
              : tc
          )
          const sources = (event.tool === 'rag_retrieval' && event.result?.chunks)
            ? event.result.chunks
            : (m.sources || [])
          return { ...m, toolCalls, sources }
        }),
      }
    case 'token':
      return {
        ...state,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? { ...m, content: (m.content || '') + event.t }
            : m
        ),
      }
    case 'done':
      return {
        ...state,
        streaming: false,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? {
                ...m,
                streaming: false,
                latency_ms: event.latency_ms,
                tool_calls_made: event.tool_calls_made,
                budget: event.budget,
                orchestrator_latency_ms: event.orchestrator_latency_ms,
              }
            : m
        ),
      }
    case 'orchestrator_done':
      return {
        ...state,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? {
                ...m,
                orchestratorDone: {
                  latency_ms: event.latency_ms,
                  handoff_count: event.handoff_count,
                  triage_tokens: event.triage_tokens,
                  policy_tokens: event.policy_tokens,
                  ticket_type: event.ticket_type,
                },
              }
            : m
        ),
      }
    case 'budget_hit':
      return {
        ...state,
        streaming: false,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? { ...m, streaming: false, budgetHit: true, budgetReason: event.reason }
            : m
        ),
      }
    case 'error':
      return {
        ...state,
        streaming: false,
        messages: messages.map((m, i) =>
          i === messages.length - 1 && m.role === 'assistant'
            ? { ...m, streaming: false, error: event.detail }
            : m
        ),
      }
    default:
      return state
  }
}

export function useAgent() {
  const [state, setState] = useState({ messages: [], streaming: false })
  const abortRef = useRef(null)

  const sendMessage = useCallback(async (payload) => {
    const sessionId = getOrCreateSessionId()
    const arch = payload._architecture || 'single'
    const isMulti = arch === 'multi' || arch === 'crew'
    let streamFn = streamAgent
    if (arch === 'multi') streamFn = streamMultiAgent
    else if (arch === 'crew') streamFn = streamCrewAgent

    setState((prev) => ({
      ...prev,
      streaming: true,
      messages: [
        ...prev.messages,
        { role: 'user', content: payload.question },
        {
          role: 'assistant',
          content: '',
          streaming: true,
          agentMode: true,
          isMultiAgent: isMulti,
          thoughts: [],
          toolCalls: [],
          handoffs: [],
          triage: null,
          latency_ms: null,
          budgetHit: false,
        },
      ],
    }))

    abortRef.current = new AbortController()
    // Remove internal key before sending to backend
    const { _architecture, ...backendPayload } = payload
    try {
      for await (const event of streamFn(
        { ...backendPayload, session_id: sessionId },
        abortRef.current.signal
      )) {
        setState((prev) => ({
          ...applyAgentEvent(prev, event),
          streaming: event.event !== 'done' && event.event !== 'budget_hit' && event.event !== 'error',
        }))
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setState((prev) => ({
          ...prev,
          streaming: false,
          messages: prev.messages.map((m, i) =>
            i === prev.messages.length - 1 && m.role === 'assistant'
              ? { ...m, streaming: false, error: err.message }
              : m
          ),
        }))
      }
    }
  }, [])

  const clearMessages = useCallback(() => {
    abortRef.current?.abort()
    setState({ messages: [], streaming: false })
  }, [])

  return {
    messages: state.messages,
    streaming: state.streaming,
    sendMessage,
    clearMessages,
  }
}

