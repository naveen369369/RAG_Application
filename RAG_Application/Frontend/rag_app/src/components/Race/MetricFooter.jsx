import { Clock, Hash, DollarSign } from 'lucide-react'

export default function MetricFooter({ metrics, mode }) {
  if (!metrics) return null
  const color = mode === 'agent' ? 'text-emerald-700' : 'text-blue-700'
  return (
    <div className={`flex items-center gap-3 text-xs ${color} border-t pt-2 mt-2`}>
      <span className="flex items-center gap-1">
        <Clock className="w-3 h-3" />
        {metrics.latency_ms}ms
      </span>
      <span className="flex items-center gap-1">
        <Hash className="w-3 h-3" />
        {metrics.total_tokens ?? metrics.budget?.tokens_used ?? '—'} tok
      </span>
      {metrics.cost_usd != null && (
        <span className="flex items-center gap-1">
          <DollarSign className="w-3 h-3" />
          ${metrics.cost_usd.toFixed(5)}
        </span>
      )}
    </div>
  )
}
