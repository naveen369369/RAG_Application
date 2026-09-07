import { User, Bot, AlertCircle, AlertTriangle } from 'lucide-react'
import { MetadataBadges } from './MetadataBadges'
import { SourcePanel } from './SourcePanel'
import ToolCallBubble from './ToolCallBubble'
import ReActTrace from './ReActTrace'

export function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isAgent = !isUser && message.agentMode

  return (
    <div className={`flex gap-3 mb-6 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-1 ${
        isUser ? 'bg-slate-200 text-slate-600'
        : isAgent ? 'bg-violet-600 text-white shadow-sm'
        : 'bg-blue-600 text-white shadow-sm'
      }`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className={`max-w-[78%] sm:max-w-[72%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Agent-specific: tool calls + ReAct trace shown above the bubble */}
        {isAgent && (
          <div className="w-full mb-2">
            <ToolCallBubble toolCalls={message.toolCalls} />
            <ReActTrace thoughts={message.thoughts} />
          </div>
        )}

        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-sm shadow-sm'
            : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm'
        }`}>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
            {message.streaming && <span className="inline-block w-0.5 h-4 bg-current ml-0.5 animate-pulse rounded-sm align-middle opacity-60" />}
          </p>

          {message.budgetHit && (
            <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-amber-200">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
              <p className="text-xs text-amber-600">Budget hit: {message.budgetReason}</p>
            </div>
          )}

          {message.error && (
            <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-slate-200">
              <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
              <p className="text-xs text-red-500">{message.error || 'Backend connection failed'}</p>
            </div>
          )}
        </div>

        {!isUser && (
          <>
            <MetadataBadges
              latency_ms={message.latency_ms}
              reranked={message.reranked}
              hyde={message.hyde}
              tool_calls_made={message.tool_calls_made}
              agent={isAgent}
            />
            <SourcePanel sources={message.sources} />
          </>
        )}
      </div>
    </div>
  )
}

