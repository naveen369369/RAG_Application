import { Scale } from 'lucide-react'

export default function VerdictCard({ verdict, summary }) {
  if (!verdict) return null

  const agentBetter = summary?.agent?.pass_rate > summary?.workflow?.pass_rate
  const workflowCheaper = summary?.workflow?.cost_per_ticket_usd < summary?.agent?.cost_per_ticket_usd

  // Highlight the key sentence about dependency tickets
  const parts = verdict.split(/(T06, T07, T08|missing-order escalation class)/g)

  return (
    <div className="mt-3 rounded-lg border border-violet-200 bg-violet-50 p-3">
      <div className="flex items-center gap-2 mb-2">
        <Scale className="w-4 h-4 text-violet-600" />
        <span className="text-sm font-semibold text-violet-700">Verdict</span>
        {agentBetter ? (
          <span className="ml-auto text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">Agent wins on pass rate</span>
        ) : (
          <span className="ml-auto text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Workflow wins overall</span>
        )}
      </div>
      <p className="text-xs text-slate-700 leading-relaxed">
        {parts.map((part, i) =>
          part === 'T06, T07, T08' || part === 'missing-order escalation class'
            ? <strong key={i} className="text-amber-700">{part}</strong>
            : <span key={i}>{part}</span>
        )}
      </p>
      <div className="mt-2 flex gap-2 flex-wrap">
        {summary?.agent && (
          <span className="text-xs bg-emerald-50 border border-emerald-200 text-emerald-700 px-2 py-0.5 rounded">
            Agent: {summary.agent.pass_rate}% pass
          </span>
        )}
        {summary?.workflow && (
          <span className="text-xs bg-blue-50 border border-blue-200 text-blue-700 px-2 py-0.5 rounded">
            Workflow: {summary.workflow.pass_rate}% pass
          </span>
        )}
        {workflowCheaper && (
          <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
            Workflow {((1 - summary.workflow.cost_per_ticket_usd / summary.agent.cost_per_ticket_usd) * 100).toFixed(0)}% cheaper/ticket
          </span>
        )}
      </div>
    </div>
  )
}
