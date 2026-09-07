import { CheckCircle2, Circle, Loader2 } from 'lucide-react'
import MetricFooter from './MetricFooter'

const STEP_LABELS = {
  guard_classify:  '🛡️ Intent check',
  guard_respond:   '💬 Guard response',
  route_namespace: 'Route namespace',
  rag_retrieval:   'Retrieve documents',
  generate:        'Generate answer',
}

export default function WorkflowStream({ panel }) {
  const { steps = [], tokens = '', metrics, streaming, error } = panel

  return (
    <div className="flex flex-col h-full">
      <div className="text-sm font-semibold text-blue-700 mb-2 flex items-center gap-1.5">
        ⚡ WORKFLOW
        {streaming && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />}
      </div>

      <div className="flex-1 space-y-1.5 overflow-y-auto">
        {/* Step progress */}
        <div className="space-y-1">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              {s.status === 'done' ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
              ) : s.status === 'running' ? (
                <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin flex-shrink-0" />
              ) : (
                <Circle className="w-3.5 h-3.5 text-slate-300 flex-shrink-0" />
              )}
              <span className={s.status === 'done' ? 'text-slate-700' : 'text-slate-400'}>
                {STEP_LABELS[s.step] || s.step}
              </span>
              {s.status === 'done' && s.result && (
                <span className="text-slate-400 truncate">
                  → {typeof s.result === 'object'
                    ? Object.values(s.result)[0]?.toString().slice(0, 30)
                    : String(s.result).slice(0, 30)}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Final answer */}
        {tokens && (
          <div className="mt-2 text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
            {tokens}
            {streaming && <span className="inline-block w-1 h-3.5 bg-slate-400 animate-pulse ml-0.5" />}
          </div>
        )}

        {error && (
          <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1.5">{error}</div>
        )}
      </div>

      <MetricFooter metrics={metrics} mode="workflow" />
    </div>
  )
}
