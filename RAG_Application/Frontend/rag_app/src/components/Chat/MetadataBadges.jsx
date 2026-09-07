import { Zap, Sparkles, Clock, Wrench } from 'lucide-react'

export function MetadataBadges({ latency_ms = 0, reranked = false, hyde = false, tool_calls_made, agent = false }) {
  if (!latency_ms && !reranked && !hyde && !tool_calls_made) return null

  const latLabel = latency_ms < 1000 ? `${Math.round(latency_ms)} ms` : `${(latency_ms / 1000).toFixed(2)} s`
  const latCls = latency_ms < 1000 ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : latency_ms < 3000 ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-red-50 border-red-200 text-red-600'

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {agent && tool_calls_made > 0 && (
        <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-amber-50 border border-amber-200 text-amber-700 font-medium">
          <Wrench className="w-3 h-3 text-amber-600" /> {tool_calls_made} tool{tool_calls_made !== 1 ? 's' : ''}
        </span>
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

