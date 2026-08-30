import { Zap, Sparkles, Clock } from 'lucide-react'

export function MetadataBadges({ latency_ms = 0, reranked = false, hyde = false }) {
  if (!latency_ms && !reranked && !hyde) return null

  const latLabel = latency_ms < 1000 ? `${Math.round(latency_ms)} ms` : `${(latency_ms / 1000).toFixed(2)} s`
  const latCls = latency_ms < 1000 ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : latency_ms < 3000 ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-red-50 border-red-200 text-red-600'

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
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

