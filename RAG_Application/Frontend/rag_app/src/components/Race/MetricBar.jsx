/**
 * Horizontal bar comparison: agent vs workflow for a single metric.
 */
export default function MetricBar({ label, agentVal, workflowVal, format = (v) => v, lowerIsBetter = false }) {
  if (agentVal == null || workflowVal == null) return null
  const max = Math.max(agentVal, workflowVal) || 1
  const agentPct = (agentVal / max) * 100
  const workflowPct = (workflowVal / max) * 100
  const agentWins = lowerIsBetter ? agentVal <= workflowVal : agentVal >= workflowVal

  return (
    <div className="space-y-0.5">
      <div className="text-xs font-medium text-slate-600">{label}</div>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 w-16">Agent</span>
          <div className="flex-1 bg-slate-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${agentWins ? 'bg-emerald-500' : 'bg-slate-400'}`}
              style={{ width: `${agentPct}%` }}
            />
          </div>
          <span className="text-xs font-medium w-20 text-right">{format(agentVal)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 w-16">Workflow</span>
          <div className="flex-1 bg-slate-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${!agentWins ? 'bg-blue-500' : 'bg-slate-400'}`}
              style={{ width: `${workflowPct}%` }}
            />
          </div>
          <span className="text-xs font-medium w-20 text-right">{format(workflowVal)}</span>
        </div>
      </div>
    </div>
  )
}
