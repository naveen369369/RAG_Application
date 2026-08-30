import { useState, useCallback } from 'react'
import { streamChat } from '../api/chat'

export function useChat() {
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)

  const sendMessage = useCallback(async (payload) => {
    setMessages(prev => [
      ...prev,
      { role: 'user', content: payload.question },
      { role: 'assistant', content: '', streaming: true },
    ])
    setStreaming(true)

    let fullContent = ''
    try {
      for await (const chunk of streamChat(payload)) {
        if (chunk.t) {
          fullContent += chunk.t
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], content: fullContent }
            return next
          })
        } else if (chunk.done) {
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = {
              role: 'assistant',
              content: fullContent,
              streaming: false,
              latency_ms: chunk.latency_ms ?? 0,
              reranked: chunk.reranked ?? false,
              hyde: chunk.hyde ?? false,
              sources: chunk.sources ?? [],
            }
            return next
          })
        }
      }
    } catch {
      setMessages(prev => {
        const next = [...prev]
        next[next.length - 1] = {
          role: 'assistant',
          content: 'Error: Could not connect to the backend. Make sure `uvicorn main:app --port 8000` is running.',
          streaming: false,
          error: true,
        }
        return next
      })
    } finally {
      setStreaming(false)
    }
  }, [])

  const clearMessages = useCallback(() => setMessages([]), [])

  return { messages, streaming, sendMessage, clearMessages }
}
