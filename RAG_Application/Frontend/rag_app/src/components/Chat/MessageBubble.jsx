import { useState } from 'react'
import {
  User,
  Bot,
  AlertCircle,
  AlertTriangle,
  Copy,
  Check,
} from 'lucide-react'
import { MetadataBadges } from './MetadataBadges'
import { SourcePanel } from './SourcePanel'
import ReActTrace from './ReActTrace'
import MarkdownRenderer from './MarkdownRenderer'
import RetrievalModal from './RetrievalModal'

export function MessageBubble({ message }) {
  const [copied, setCopied] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalInitialTab, setModalInitialTab] = useState('chunks')

  const isUser = message.role === 'user'
  const isAgent = !isUser && message.agentMode
  const hasContent = Boolean(message.content && message.content.trim())
  const isStreaming = Boolean(message.streaming)
  const isLoading = isStreaming && !hasContent

  // Extract resolved sources from normal RAG sources or Agent rag_retrieval chunks
  const resolvedSources =
    Array.isArray(message.sources) && message.sources.length > 0
      ? message.sources
      : message.toolCalls?.find((tc) => tc.tool === 'rag_retrieval' && tc.result?.chunks)
        ?.result?.chunks || []

  const handleCopy = () => {
    if (!message.content) return
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Active tool being run
  const runningTool = message.toolCalls?.find((tc) => tc.status === 'running')

  return (
    <div className={`flex gap-3.5 mb-6 group ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 shadow-xs transition-transform ${isUser
            ? 'bg-slate-200 text-slate-600'
            : isAgent
              ? 'bg-violet-600 text-white shadow-violet-200'
              : 'bg-blue-600 text-white shadow-blue-200'
          }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className={`max-w-[85%] sm:max-w-[80%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Agent thoughts trace if present */}
        {isAgent && message.thoughts && message.thoughts.length > 0 && (
          <div className="w-full mb-1">
            <ReActTrace thoughts={message.thoughts} />
          </div>
        )}

        {/* Message Bubble Container */}
        <div
          className={`rounded-2xl px-4 py-3.5 sm:px-5 sm:py-4 transition-all ${isUser
              ? 'bg-blue-600 text-white rounded-tr-xs shadow-xs'
              : 'bg-white border border-slate-200/90 text-slate-800 rounded-tl-xs shadow-xs hover:border-slate-300'
            }`}
        >
          {/* User message */}
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap selection:bg-blue-800">
              {message.content}
            </p>
          ) : (
            /* Assistant message */
            <div>
              {/* Animated Message Loader (ChatGPT style) when waiting for response */}
              {isLoading && (
                <div className="flex items-center gap-3 py-1.5 px-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-600 dot-pulse-1" />
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-600 dot-pulse-2" />
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-600 dot-pulse-3" />
                  </div>
                  <span className="text-xs font-medium text-slate-500 animate-pulse">
                    {runningTool
                      ? `Executing ${runningTool.tool}…`
                      : isAgent
                        ? 'Agent is thinking & searching documents…'
                        : 'Searching knowledge base & generating answer…'}
                  </span>
                </div>
              )}

              {/* Formatted Markdown Content */}
              {hasContent && (
                <div className="relative">
                  <MarkdownRenderer content={message.content} />
                  {isStreaming && (
                    <span
                      className="inline-block w-1.5 h-4 bg-blue-600 ml-1 animate-pulse align-middle rounded-xs"
                      title="Generating response..."
                    />
                  )}
                </div>
              )}

              {/* Budget Hit Alert */}
              {message.budgetHit && (
                <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-amber-200 text-amber-700">
                  <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                  <p className="text-xs">Budget limit reached: {message.budgetReason}</p>
                </div>
              )}

              {/* Error Alert */}
              {message.error && (
                <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-red-200 text-red-600">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                  <p className="text-xs">{message.error || 'Failed to generate response'}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Assistant Footer Actions & Badges */}
        {!isUser && (
          <div className="flex flex-wrap items-center gap-2 mt-1.5 px-1">
            {/* Metadata badges (latency, rerank, tool call details) */}
            <MetadataBadges
              latency_ms={message.latency_ms}
              reranked={message.reranked}
              hyde={message.hyde}
              tool_calls_made={message.tool_calls_made}
              toolCalls={message.toolCalls}
              onOpenToolsModal={() => {
                setModalInitialTab('tools')
                setModalOpen(true)
              }}
              agent={isAgent}
            />

            {/* Single clean source citations button (opens rich popup window) */}
            <SourcePanel
              sources={resolvedSources}
              onOpenModal={() => {
                setModalInitialTab('chunks')
                setModalOpen(true)
              }}
            />

            {/* Copy Response Button */}
            {hasContent && (
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-700 hover:bg-slate-100 px-2 py-1 rounded-md transition-colors"
                title="Copy response to clipboard"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-600" />
                    <span className="text-emerald-600">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Popup Window Modal for Chunks & Tools */}
      <RetrievalModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        message={{ ...message, sources: resolvedSources }}
        initialTab={modalInitialTab}
      />
    </div>
  )
}

export default MessageBubble

