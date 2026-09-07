import { Wrench, CheckCircle2, Loader2 } from 'lucide-react'

export default function ToolCallBubble({ toolCalls = [] }) {
  if (!toolCalls.length) return null
  return (
    <div className="mt-2 space-y-1.5">
      {toolCalls.map((tc, i) => (
        <div
          key={i}
          className="flex items-start gap-2 text-xs rounded-lg bg-amber-50 border border-amber-200 px-3 py-2"
        >
          <Wrench className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-amber-700">{tc.tool}</span>
              {tc.status === 'running' ? (
                <Loader2 className="w-3 h-3 text-amber-400 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
              )}
            </div>
            {tc.args && Object.keys(tc.args).length > 0 && (
              <div className="text-amber-600 truncate mt-0.5">
                {Object.entries(tc.args)
                  .map(([k, v]) => `${k}: ${String(v).slice(0, 40)}`)
                  .join(', ')}
              </div>
            )}
            {tc.status === 'done' && tc.result && (
              <div className="text-slate-500 truncate mt-0.5">
                → {typeof tc.result === 'object'
                  ? JSON.stringify(tc.result).slice(0, 80)
                  : String(tc.result).slice(0, 80)}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
