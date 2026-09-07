import { Brain, Wrench, CheckCircle2, Loader2, AlertTriangle } from 'lucide-react'
import MetricFooter from './MetricFooter'

export default function AgentStream({ panel }) {
  const { events = [], tokens = '', toolCalls = [], metrics, streaming, error, budgetHit, budgetReason } = panel

  return (
    <div className="flex flex-col h-full">
      <div className="text-sm font-semibold text-emerald-700 mb-2 flex items-center gap-1.5">
        🤖 AGENT
        {streaming && <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-500" />}
      </div>

      <div className="flex-1 space-y-1.5 overflow-y-auto text-xs">
        {/* Tool calls */}
        {toolCalls.map((tc, i) => (
          <div key={i} className="flex items-start gap-1.5 bg-amber-50 border border-amber-100 rounded px-2 py-1">
            <Wrench className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="min-w-0">
              <span className="font-medium text-amber-700">{tc.tool}</span>
              {tc.status === 'running' ? (
                <Loader2 className="inline ml-1 w-3 h-3 text-amber-400 animate-spin" />
              ) : (
                <CheckCircle2 className="inline ml-1 w-3 h-3 text-emerald-500" />
              )}
              {tc.result && (
                <div className="text-slate-500 truncate">
                  → {typeof tc.result === 'object' ? JSON.stringify(tc.result).slice(0, 60) : String(tc.result).slice(0, 60)}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Thoughts */}
        {events.filter(e => e.type === 'thought').map((e, i) => (
          <div key={i} className="flex items-start gap-1.5 text-slate-500">
            <Brain className="w-3 h-3 text-violet-400 flex-shrink-0 mt-0.5" />
            <span className="line-clamp-2">{e.text.replace(/^Thought:\s*/,'').slice(0, 120)}</span>
          </div>
        ))}

        {/* Final answer */}
        {tokens && (
          <div className="mt-2 text-slate-700 leading-relaxed whitespace-pre-wrap">
            {tokens}
            {streaming && <span className="inline-block w-1 h-3.5 bg-slate-400 animate-pulse ml-0.5" />}
          </div>
        )}

        {budgetHit && (
          <div className="flex items-center gap-1.5 text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Budget hit: {budgetReason}</span>
          </div>
        )}

        {error && (
          <div className="text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5">{error}</div>
        )}
      </div>

      <MetricFooter metrics={metrics} mode="agent" />
    </div>
  )
}
