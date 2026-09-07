import MetricBar from './MetricBar'

const TICKET_IDS = ['T01','T02','T03','T04','T05','T06','T07','T08','T09','T10']
const DEP_TICKETS = new Set(['T06','T07','T08'])

function Cell({ val, passed }) {
  if (val == null) return <td className="px-2 py-1.5 text-center text-slate-300 text-xs">—</td>
  return (
    <td className={`px-2 py-1.5 text-center text-xs ${passed ? 'bg-emerald-50' : 'bg-red-50'}`}>
      {passed ? '✓' : '✗'}
    </td>
  )
}

function NumCell({ val, unit = '', win }) {
  if (val == null) return <td className="px-2 py-1.5 text-center text-slate-300 text-xs">—</td>
  return (
    <td className={`px-2 py-1.5 text-center text-xs font-mono ${win ? 'text-emerald-700 font-semibold' : 'text-slate-600'}`}>
      {val}{unit}
    </td>
  )
}

export default function RaceTable({ ticketRows, summary }) {
  return (
    <div className="space-y-4">
      {/* Summary bars */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-lg">
          <MetricBar
            label="Pass rate (%)"
            agentVal={summary.agent?.pass_rate}
            workflowVal={summary.workflow?.pass_rate}
            format={(v) => `${v}%`}
          />
          <MetricBar
            label="P50 latency (ms)"
            agentVal={summary.agent?.p50_latency_ms}
            workflowVal={summary.workflow?.p50_latency_ms}
            format={(v) => `${v}ms`}
            lowerIsBetter
          />
          <MetricBar
            label="Total tokens"
            agentVal={summary.agent?.total_tokens}
            workflowVal={summary.workflow?.total_tokens}
            lowerIsBetter
          />
          <MetricBar
            label="Cost/ticket"
            agentVal={summary.agent?.cost_per_ticket_usd}
            workflowVal={summary.workflow?.cost_per_ticket_usd}
            format={(v) => `$${v.toFixed(5)}`}
            lowerIsBetter
          />
        </div>
      )}

      {/* Per-ticket table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100">
              <th className="px-2 py-1.5 text-left text-slate-600">Ticket</th>
              <th className="px-2 py-1.5 text-center text-emerald-700 bg-emerald-50" colSpan={4}>🤖 Agent</th>
              <th className="px-2 py-1.5 text-center text-blue-700 bg-blue-50" colSpan={4}>⚡ Workflow</th>
            </tr>
            <tr className="bg-slate-50 text-slate-500">
              <th className="px-2 py-1.5" />
              <th className="px-2 py-1.5">Pass</th>
              <th className="px-2 py-1.5">Latency</th>
              <th className="px-2 py-1.5">Tokens</th>
              <th className="px-2 py-1.5">Cost</th>
              <th className="px-2 py-1.5">Pass</th>
              <th className="px-2 py-1.5">Latency</th>
              <th className="px-2 py-1.5">Tokens</th>
              <th className="px-2 py-1.5">Cost</th>
            </tr>
          </thead>
          <tbody>
            {TICKET_IDS.map((tid) => {
              const row = ticketRows[tid] || {}
              const a = row.agent
              const w = row.workflow
              const isDep = DEP_TICKETS.has(tid)
              return (
                <tr key={tid} className={`border-b border-slate-100 ${isDep ? 'bg-amber-50' : ''}`}>
                  <td className="px-2 py-1.5 font-mono font-semibold text-slate-700">
                    {tid}
                    {isDep && <span className="ml-1 text-amber-500" title="Path-dependent ticket">⚡</span>}
                  </td>
                  <Cell val={a} passed={a?.passed} />
                  <NumCell val={a?.latency_ms} unit="ms" win={a && w && a.latency_ms <= w.latency_ms} />
                  <NumCell val={a?.total_tokens} win={a && w && a.total_tokens <= w.total_tokens} />
                  <NumCell val={a?.cost_usd?.toFixed(5)} win={a && w && a.cost_usd <= w.cost_usd} />
                  <Cell val={w} passed={w?.passed} />
                  <NumCell val={w?.latency_ms} unit="ms" win={a && w && w.latency_ms < a.latency_ms} />
                  <NumCell val={w?.total_tokens} win={a && w && w.total_tokens < a.total_tokens} />
                  <NumCell val={w?.cost_usd?.toFixed(5)} win={a && w && w.cost_usd < a.cost_usd} />
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
