import { Zap, Sparkles, Clock, Wrench, ExternalLink } from 'lucide-react'
import { getToolMeta } from './ToolCallBubble'

export function MetadataBadges({
  latency_ms = 0,
  reranked = false,
  hyde = false,
  tool_calls_made,
  toolCalls = [],
  onOpenToolsModal,
  agent = false,
}) {
  const hasTools = agent && (tool_calls_made > 0 || toolCalls.length > 0)
  if (!latency_ms && !reranked && !hyde && !hasTools) return null

  const latLabel = latency_ms < 1000 ? `${Math.round(latency_ms)} ms` : `${(latency_ms / 1000).toFixed(2)} s`
  const latCls = latency_ms < 1000 ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : latency_ms < 3000 ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-red-50 border-red-200 text-red-600'

  const count = toolCalls.length > 0 ? toolCalls.length : (tool_calls_made || 0)
  const toolNames = toolCalls.map(t => t.tool).filter(Boolean)

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2">
      {hasTools && (
        <button
          type="button"
          onClick={onOpenToolsModal}
          className="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-md bg-amber-50 hover:bg-amber-100 border border-amber-200 hover:border-amber-300 text-amber-800 font-medium transition-all shadow-2xs group cursor-pointer"
          title="Click to view tool execution details, arguments, and outputs"
        >
          <Wrench className="w-3 h-3 text-amber-600 group-hover:rotate-12 transition-transform" />
          <span>
            {toolNames.length > 0
              ? `${count} tool${count !== 1 ? 's' : ''}: ${toolNames.join(', ')}`
              : `${count} tool${count !== 1 ? 's' : ''} called`}
          </span>
          <span className="text-[10px] text-amber-600 font-bold bg-amber-100/80 px-1 py-0.2 rounded flex items-center gap-0.5 ml-0.5 group-hover:bg-amber-200/90 transition-colors">
            <span>View</span>
            <ExternalLink className="w-2.5 h-2.5 opacity-80 group-hover:opacity-100" />
          </span>
        </button>
      )}
      {reranked && (
        <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-violet-50 border border-violet-200 text-violet-700 font-medium">
          <Zap className="w-3 h-3 text-violet-600" /> Reranked
        </span>
      )}
      {hyde && (
        <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-blue-50 border border-blue-200 text-blue-700 font-medium">
          <Sparkles className="w-3 h-3 text-blue-600" /> HyDE
        </span>
      )}
      {latency_ms > 0 && (
        <span className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md border font-medium ${latCls}`}>
          <Clock className="w-3 h-3" /> {latLabel}
        </span>
      )}
    </div>
  )
}


