import { User, Bot, AlertCircle } from 'lucide-react'
import { MetadataBadges } from './MetadataBadges'
import { SourcePanel } from './SourcePanel'

export function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 mb-6 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-1 ${isUser ? 'bg-slate-200 text-slate-600' : 'bg-blue-600 text-white shadow-sm'}`}>
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <Bot className="w-4 h-4" />
        )}
      </div>

      <div className={`max-w-[78%] sm:max-w-[72%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl px-4 py-3 ${isUser ? 'bg-blue-600 text-white rounded-tr-sm shadow-sm' : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm'}`}>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
            {message.streaming && <span className="inline-block w-0.5 h-4 bg-current ml-0.5 animate-pulse rounded-sm align-middle opacity-60" />}
          </p>
          {message.error && (
            <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-slate-200">
              <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
              <p className="text-xs text-red-500">Backend connection failed</p>
            </div>
          )}
        </div>
        {!isUser && (
          <>
            <MetadataBadges latency_ms={message.latency_ms} reranked={message.reranked} hyde={message.hyde} />
            <SourcePanel sources={message.sources} />
          </>
        )}
      </div>
    </div>
  )
}

