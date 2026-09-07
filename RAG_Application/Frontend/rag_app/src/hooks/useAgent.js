import { useCallback, useRef, useState } from 'react'
import { streamAgent } from '../api/agent'

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
            ? { ...m, thoughts: [...(m.thoughts || []), event.text] }
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
                  { tool: event.tool, args: event.args, result: null, status: 'running' },
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
          return { ...m, toolCalls }
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
          thoughts: [],
          toolCalls: [],
          latency_ms: null,
          budgetHit: false,
        },
      ],
    }))

    abortRef.current = new AbortController()
    try {
      for await (const event of streamAgent(
        { ...payload, session_id: sessionId },
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
