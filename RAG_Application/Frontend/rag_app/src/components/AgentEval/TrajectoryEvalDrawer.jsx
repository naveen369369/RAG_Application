import { useState } from 'react'
import {
  X, GitBranch, Play, Loader2, CheckCircle2, XCircle,
  AlertTriangle, ChevronDown, ChevronRight, TrendingUp, DollarSign,
  Activity, Zap, BarChart3, ArrowRight, Radio
} from 'lucide-react'
import { useAppContext } from '../../context/AppContext'
import { runTrajectoryEval, runLiveEvalAll } from '../../api/agentEval'

// ── Helpers ──────────────────────────────────────────────────────────────────
const pct = v => `${(v * 100).toFixed(1)}%`
const musd = v => `$${(v * 1e6).toFixed(2)} µ`

function Pill({ ok, children }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${ok ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
      : 'bg-rose-50 text-rose-700 border border-rose-200'
      }`}>
      {ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
      {children}
    </span>
  )
}

function MetricCard({ label, value, sub, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    rose: 'bg-rose-50 border-rose-200 text-rose-700',
    violet: 'bg-violet-50 border-violet-200 text-violet-700',
  }
  return (
    <div className={`rounded-xl border p-3.5 ${colors[color]}`}>
      <p className="text-xs font-medium opacity-70 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs mt-1 opacity-60">{sub}</p>}
    </div>
  )
}

function SectionHeader({ icon, title, badge }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-6 h-6 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500 flex-shrink-0">
        {icon}
      </div>
      <h3 className="text-sm font-bold text-slate-800">{title}</h3>
      {badge && (
        <span className="ml-auto text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-medium">
          {badge}
        </span>
      )}
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function TrajectoryEvalDrawer() {
  const { trajDrawerOpen, setTrajDrawerOpen } = useAppContext()
  const [loading, setLoading] = useState(false)
  const [liveLoading, setLiveLoading] = useState(false)
  const [data, setData] = useState(null)
  const [liveData, setLiveData] = useState(null)
  const [error, setError] = useState(null)
  const [liveError, setLiveError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [expandedCase, setExpandedCase] = useState(null)
  const [expandedLiveCase, setExpandedLiveCase] = useState(null)

  const handleRun = async () => {
    setLoading(true); setError(null)
    try {
      const res = await runTrajectoryEval()
      setData(res)
      setActiveTab('overview')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRunLive = async () => {
    setLiveLoading(true); setLiveError(null)
    try {
      const res = await runLiveEvalAll()
      setLiveData(res)
      setActiveTab('live')
    } catch (e) {
      setLiveError(e.message)
    } finally {
      setLiveLoading(false)
    }
  }

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'cases', label: '10 Cases' },
    { id: 'mitigation', label: 'Mitigation' },
    { id: 'regression', label: 'Regression' },
    { id: 'wrongpath', label: 'Wrong Path' },
    ...(liveData ? [{ id: 'live', label: '🔴 Live Eval' }] : []),
  ]

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-40 transition-opacity duration-300 ${trajDrawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
        onClick={() => setTrajDrawerOpen(false)}
      />

      {/* Drawer */}
      <div className={`fixed right-0 top-0 bottom-0 z-50 w-[90vw] max-w-4xl bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${trajDrawerOpen ? 'translate-x-0' : 'translate-x-full'
        }`}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0 bg-gradient-to-r from-violet-600 to-blue-600">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
              <GitBranch className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Trajectory Evaluation</h2>
              <p className="text-xs text-white/70">10 ticket cases · failure modes · mitigation · regression</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRun}
              disabled={loading || liveLoading}
              className="flex items-center gap-2 text-sm font-semibold bg-white text-violet-700 hover:bg-violet-50 rounded-xl px-4 py-2 transition-colors disabled:opacity-60 shadow-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              {loading ? 'Running…' : 'Mock Eval'}
            </button>
            <button
              onClick={handleRunLive}
              disabled={loading || liveLoading}
              className="flex items-center gap-2 text-sm font-semibold bg-rose-500 text-white hover:bg-rose-400 rounded-xl px-4 py-2 transition-colors disabled:opacity-60 shadow-sm"
              title="Run all 10 cases against the real agent + SQL DB"
            >
              {liveLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />}
              {liveLoading ? 'Live Running…' : 'Live Eval All'}
            </button>
            <button onClick={() => setTrajDrawerOpen(false)} className="p-2 hover:bg-white/20 rounded-xl transition-colors">
              <X className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        {data && (
          <div className="flex border-b border-slate-200 bg-slate-50 flex-shrink-0 overflow-x-auto">
            {tabs.map(t => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${activeTab === t.id
                  ? 'border-violet-500 text-violet-700 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100'
                  }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-sm text-rose-700">
              <strong>Error:</strong> {error}
            </div>
          )}

          {!data && !loading && !error && (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-4">
              <div className="w-16 h-16 rounded-2xl bg-violet-50 flex items-center justify-center">
                <GitBranch className="w-8 h-8 text-violet-400" />
              </div>
              <div className="text-center">
                <p className="text-base font-semibold text-slate-600">Trajectory Evaluation</p>
                <p className="text-sm mt-1">Click <strong>Run Evaluation</strong> to analyse 10 ticket cases</p>
                <p className="text-xs mt-1 text-slate-400">Measures tool-choice accuracy · trajectory correctness · cost · failure modes</p>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center h-full gap-3 text-slate-500">
              <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
              <span className="text-sm font-medium">Evaluating 10 ticket trajectories…</span>
            </div>
          )}

          {/* ── OVERVIEW TAB ────────────────────────────────────────────────── */}
          {data && activeTab === 'overview' && (() => {
            const b = data.before
            const a = data.after
            const gap = b.outcome_trajectory_gap

            return (
              <div className="space-y-6">
                {/* Before / After metric comparison */}
                <div>
                  <SectionHeader icon={<BarChart3 className="w-3.5 h-3.5" />} title="Before vs After Mitigation" />
                  <div className="grid grid-cols-2 gap-4">
                    {/* Before */}
                    <div className="space-y-3">
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Before</p>
                      <MetricCard label="Outcome Pass Rate" value={pct(b.outcome_pass_rate)} color="blue" />
                      <MetricCard label="Trajectory Pass Rate" value={pct(b.trajectory_pass_rate)} color="amber" />
                      <MetricCard label="Tool-Choice Accuracy" value={pct(b.tool_choice_accuracy)} color="blue" />
                      <MetricCard label="Arg Validity Rate" value={pct(b.arg_validity_rate)} color={b.arg_validity_rate >= 0.8 ? 'emerald' : 'rose'} />
                    </div>
                    {/* After */}
                    <div className="space-y-3">
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">After</p>
                      <MetricCard label="Outcome Pass Rate" value={pct(a.outcome_pass_rate)} color="emerald" />
                      <MetricCard label="Trajectory Pass Rate" value={pct(a.trajectory_pass_rate)} color="emerald" />
                      <MetricCard label="Tool-Choice Accuracy" value={pct(a.tool_choice_accuracy)} color="blue" />
                      <MetricCard label="Arg Validity Rate" value={pct(a.arg_validity_rate)} color="emerald" />
                    </div>
                  </div>
                </div>

                {/* Outcome-vs-Trajectory Gap */}
                <div className={`rounded-xl border p-4 ${gap > 0.1 ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 mb-1">Outcome-vs-Trajectory Gap (Before)</p>
                      <p className={`text-3xl font-bold ${gap > 0.1 ? 'text-amber-700' : 'text-emerald-700'}`}>
                        +{pct(gap)}
                      </p>
                    </div>
                    <AlertTriangle className={`w-8 h-8 ${gap > 0.1 ? 'text-amber-400' : 'text-emerald-400'}`} />
                  </div>
                  <p className="text-xs text-slate-500 mt-2">
                    {gap > 0
                      ? `${pct(gap)} of cases had correct outcomes but used wrong tool paths — agent got lucky.`
                      : 'Outcomes and trajectories are aligned.'}
                  </p>
                </div>

                {/* Cost metrics */}
                <div>
                  <SectionHeader icon={<DollarSign className="w-3.5 h-3.5" />} title="Cost per Task" badge="Before mitigation" />
                  <div className="grid grid-cols-3 gap-3">
                    <MetricCard label="Mean" value={musd(b.cost_mean_usd)} sub="per task" color="blue" />
                    <MetricCard label="P50 (Median)" value={musd(b.cost_p50_usd)} color="blue" />
                    <MetricCard label="P99" value={musd(b.cost_p99_usd)} color="violet" />
                  </div>
                </div>

                {/* Top failure mode */}
                <div>
                  <SectionHeader icon={<Activity className="w-3.5 h-3.5" />} title="Top Failure Mode" />
                  <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-bold text-rose-700 font-mono">{data.top_failure_mode}</p>
                      <p className="text-xs text-rose-500 mt-1">
                        {data.top_failure_count_before} cases before → {data.top_failure_count_after} after mitigation
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-bold text-rose-400">{data.top_failure_count_before}</span>
                      <ArrowRight className="w-4 h-4 text-slate-400" />
                      <span className="text-2xl font-bold text-emerald-600">{data.top_failure_count_after}</span>
                    </div>
                  </div>
                </div>

                {/* Step efficiency */}
                <div>
                  <SectionHeader icon={<Zap className="w-3.5 h-3.5" />} title="Step Efficiency" />
                  <MetricCard
                    label="Mean Efficiency (actual / required steps)"
                    value={`${b.mean_step_efficiency.toFixed(2)}×`}
                    sub={b.mean_step_efficiency <= 1.1 ? '≈ optimal' : 'agent takes more steps than needed'}
                    color={b.mean_step_efficiency <= 1.1 ? 'emerald' : 'amber'}
                  />
                </div>
              </div>
            )
          })()}

          {/* ── CASES TAB ──────────────────────────────────────────────────── */}
          {data && activeTab === 'cases' && (
            <div className="space-y-3">
              <SectionHeader icon={<GitBranch className="w-3.5 h-3.5" />} title="10 Ticket Cases — Before Mitigation" badge="click to expand" />
              {data.before.cases.map((c, i) => {
                const tc = data.ticket_cases.find(t => t.id === c.id)
                const open = expandedCase === c.id
                return (
                  <div key={c.id} className="border border-slate-200 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setExpandedCase(open ? null : c.id)}
                      className="w-full flex items-center gap-3 p-3.5 hover:bg-slate-50 transition-colors text-left"
                    >
                      <span className="text-xs font-mono font-bold text-slate-500 w-8">{c.id}</span>
                      <span className="flex-1 text-sm text-slate-700 truncate">{c.question}</span>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Pill ok={c.trajectory_pass}>Traj</Pill>
                        <Pill ok={c.outcome_pass}>Out</Pill>
                        <Pill ok={c.args_valid}>Args</Pill>
                        {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                      </div>
                    </button>
                    {open && (
                      <div className="border-t border-slate-100 bg-slate-50 p-4 space-y-3 text-xs">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <p className="font-semibold text-slate-400 mb-1">Expected Tools</p>
                            <p className="font-mono text-slate-700">{tc?.expected_tools.join(' → ')}</p>
                            {tc?.alt_tools?.length > 0 && (
                              <p className="text-slate-400 mt-1">Alt: {tc.alt_tools.map(a => a.join(' → ')).join(' | ')}</p>
                            )}
                          </div>
                          <div>
                            <p className="font-semibold text-slate-400 mb-1">Actual Tools</p>
                            <p className="font-mono text-slate-700">{c.actual_tools.join(' → ')}</p>
                          </div>
                          <div>
                            <p className="font-semibold text-slate-400 mb-1">Step Efficiency</p>
                            <p className={`font-bold ${c.step_efficiency > 1.1 ? 'text-amber-600' : 'text-emerald-600'}`}>
                              {c.step_efficiency.toFixed(2)}×
                            </p>
                          </div>
                          <div>
                            <p className="font-semibold text-slate-400 mb-1">Cost</p>
                            <p className="font-mono text-slate-700">{musd(c.cost_usd)}</p>
                          </div>
                          <div>
                            <p className="font-semibold text-slate-400 mb-1">Latency</p>
                            <p className="font-mono text-slate-700">{c.latency_ms} ms</p>
                          </div>
                          {c.failure_mode && (
                            <div>
                              <p className="font-semibold text-slate-400 mb-1">Failure Mode</p>
                              <span className="bg-rose-100 text-rose-700 px-2 py-0.5 rounded font-mono">{c.failure_mode}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* ── MITIGATION TAB ─────────────────────────────────────────────── */}
          {data && activeTab === 'mitigation' && (
            <div className="space-y-6">
              <SectionHeader icon={<Zap className="w-3.5 h-3.5" />} title="Applied Mitigation (ONE only)" />
              <div className="bg-violet-50 border border-violet-200 rounded-xl p-5">
                <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider mb-2">Strategy</p>
                <p className="text-lg font-bold text-violet-800 font-mono">{data.mitigation.name}</p>
                <p className="text-sm text-slate-600 mt-2">{data.mitigation.description}</p>
                <div className="grid grid-cols-3 gap-3 mt-4">
                  <div className="bg-white rounded-lg border border-violet-100 p-3 text-center">
                    <p className="text-xs text-slate-400 mb-1">Latency overhead</p>
                    <p className="font-bold text-violet-700">+{data.mitigation.latency_overhead_ms} ms</p>
                  </div>
                  <div className="bg-white rounded-lg border border-violet-100 p-3 text-center">
                    <p className="text-xs text-slate-400 mb-1">Token overhead</p>
                    <p className="font-bold text-violet-700">+{data.mitigation.token_overhead} tokens</p>
                  </div>
                  <div className="bg-white rounded-lg border border-violet-100 p-3 text-center">
                    <p className="text-xs text-slate-400 mb-1">Cost overhead</p>
                    <p className="font-bold text-violet-700">${data.mitigation.cost_overhead_usd.toFixed(6)}</p>
                  </div>
                </div>
                <p className="text-xs text-violet-500 mt-3">Target: <strong>{data.mitigation.target_mode}</strong></p>
              </div>

              {/* After metrics comparison */}
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Impact of Mitigation</p>
                <div className="space-y-2">
                  {[
                    { label: 'Outcome pass rate', b: data.before.outcome_pass_rate, a: data.after.outcome_pass_rate },
                    { label: 'Trajectory pass rate', b: data.before.trajectory_pass_rate, a: data.after.trajectory_pass_rate },
                    { label: 'Arg validity rate', b: data.before.arg_validity_rate, a: data.after.arg_validity_rate },
                  ].map(row => (
                    <div key={row.label} className="flex items-center gap-3 bg-slate-50 rounded-xl p-3">
                      <span className="text-sm text-slate-600 flex-1">{row.label}</span>
                      <span className="text-sm font-mono text-rose-500">{pct(row.b)}</span>
                      <ArrowRight className="w-4 h-4 text-slate-400" />
                      <span className="text-sm font-mono font-bold text-emerald-600">{pct(row.a)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── REGRESSION TAB ─────────────────────────────────────────────── */}
          {data && activeTab === 'regression' && (
            <div className="space-y-4">
              <SectionHeader icon={<TrendingUp className="w-3.5 h-3.5" />} title="Per-Mode Regression Table" />
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="text-left px-4 py-3 font-semibold text-slate-500 text-xs">Failure Mode</th>
                      <th className="text-center px-4 py-3 font-semibold text-slate-500 text-xs">Before</th>
                      <th className="text-center px-4 py-3 font-semibold text-slate-500 text-xs">After</th>
                      <th className="text-center px-4 py-3 font-semibold text-slate-500 text-xs">Delta</th>
                      <th className="text-center px-4 py-3 font-semibold text-slate-500 text-xs">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.regression_table.map(row => (
                      <tr key={row.failure_mode} className="border-b border-slate-100 last:border-0">
                        <td className="px-4 py-3 font-mono text-slate-700 text-xs">{row.failure_mode}</td>
                        <td className="px-4 py-3 text-center font-bold text-rose-500">{row.before}</td>
                        <td className="px-4 py-3 text-center font-bold text-emerald-600">{row.after}</td>
                        <td className="px-4 py-3 text-center font-mono text-slate-500">{row.delta > 0 ? '+' : ''}{row.delta}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-xs font-semibold px-2 py-1 rounded-full ${row.status === 'fixed' ? 'bg-emerald-50 text-emerald-700' :
                            row.status === 'regressed' ? 'bg-rose-50 text-rose-700' :
                              'bg-slate-100 text-slate-500'
                            }`}>
                            {row.status === 'fixed' ? '✓ fixed' : row.status === 'regressed' ? '✗ regressed' : '= unchanged'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── WRONG PATH TAB ─────────────────────────────────────────────── */}
          {data && activeTab === 'wrongpath' && (
            <div className="space-y-4">
              <SectionHeader icon={<AlertTriangle className="w-3.5 h-3.5" />} title="Right Answer · Wrong Path Trace" />
              {data.before.wrong_path_trace ? (() => {
                const wp = data.before.wrong_path_trace
                return (
                  <div className="space-y-4">
                    {/* Case banner */}
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-mono font-bold bg-amber-200 text-amber-800 px-2 py-0.5 rounded">{wp.id}</span>
                        <span className="text-sm font-semibold text-amber-800">Outcome PASS · Trajectory FAIL</span>
                      </div>
                      <p className="text-sm text-slate-700 mt-1">{wp.question}</p>
                    </div>

                    {/* Path comparison */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                        <p className="text-xs font-semibold text-emerald-500 mb-2">Expected Path</p>
                        <div className="flex flex-wrap gap-2">
                          {wp.expected_tools.map((t, i) => (
                            <div key={i} className="flex items-center gap-1">
                              <span className="bg-white border border-emerald-200 text-emerald-700 text-xs font-mono px-2 py-1 rounded">{t}</span>
                              {i < wp.expected_tools.length - 1 && <ArrowRight className="w-3 h-3 text-emerald-400" />}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                        <p className="text-xs font-semibold text-rose-500 mb-2">Actual (Wrong) Path</p>
                        <div className="flex flex-wrap gap-2">
                          {wp.actual_tools.map((t, i) => (
                            <div key={i} className="flex items-center gap-1">
                              <span className="bg-white border border-rose-200 text-rose-700 text-xs font-mono px-2 py-1 rounded">{t}</span>
                              {i < wp.actual_tools.length - 1 && <ArrowRight className="w-3 h-3 text-rose-400" />}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Explanation */}
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Why this matters</p>
                      <p className="text-sm text-slate-700">
                        The agent skipped <code className="bg-slate-200 px-1 rounded font-mono text-xs">customer_lookup</code> and jumped straight to{' '}
                        <code className="bg-slate-200 px-1 rounded font-mono text-xs">rag_retrieval</code>.
                        The final answer sounded correct because the policy text was retrieved, but it was
                        <strong> not personalised</strong> — the agent cited the generic SLA instead of the
                        customer's actual tier-specific SLA.
                      </p>
                      <p className="text-sm text-slate-700">
                        <strong>Outcome evaluations alone would miss this.</strong> Only trajectory
                        evaluation catches the wrong tool path.
                      </p>
                    </div>

                    {/* Metrics */}
                    <div className="grid grid-cols-3 gap-3">
                      <MetricCard label="Outcome" value="PASS ✓" color="emerald" />
                      <MetricCard label="Trajectory" value="FAIL ✗" color="rose" />
                      <MetricCard label="Step Efficiency" value={`${wp.step_efficiency?.toFixed(2) ?? '—'}×`} color="amber" />
                    </div>
                  </div>
                )
              })() : (
                <div className="text-slate-400 text-sm text-center py-8">
                  No right-answer/wrong-path case found in this evaluation.
                </div>
              )}
            </div>
          )}

          {/* ── LIVE EVAL TAB ──────────────────────────────────────────────── */}
          {activeTab === 'live' && (() => {
            if (liveLoading) return (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
                <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
                <p className="text-sm font-medium">Running all 10 cases against live agent + DB…</p>
                <p className="text-xs text-slate-400">This may take 1–3 minutes (real LLM calls)</p>
              </div>
            )
            if (liveError) return (
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-sm text-rose-700">
                <strong>Live Eval Error:</strong> {liveError}
              </div>
            )
            if (!liveData) return null

            const agg = liveData.aggregate
            return (
              <div className="space-y-6">
                {/* Header banner */}
                <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-center gap-3">
                  <Radio className="w-5 h-5 text-rose-500 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-bold text-rose-800">Live Evaluation — Real Agent + SQL DB</p>
                    <p className="text-xs text-rose-600">{liveData.total_cases} cases · {liveData.eval_runtime_ms.toLocaleString()} ms total · actual tool calls, no mocks</p>
                  </div>
                </div>

                {/* Aggregate metrics */}
                <div className="grid grid-cols-3 gap-3">
                  <MetricCard label="Overall Pass" value={pct(agg.overall_pass_rate)} color={agg.overall_pass_rate >= 0.7 ? 'emerald' : 'rose'} />
                  <MetricCard label="Trajectory Pass" value={pct(agg.trajectory_pass_rate)} color={agg.trajectory_pass_rate >= 0.7 ? 'emerald' : 'amber'} />
                  <MetricCard label="Outcome Pass" value={pct(agg.outcome_pass_rate)} color={agg.outcome_pass_rate >= 0.7 ? 'emerald' : 'rose'} />
                  <MetricCard label="Tool-Choice Accuracy" value={pct(agg.tool_choice_accuracy)} color="blue" />
                  <MetricCard label="Arg Validity" value={pct(agg.arg_validity_rate)} color={agg.arg_validity_rate >= 0.8 ? 'emerald' : 'rose'} />
                  <MetricCard label="Mean Latency" value={`${agg.mean_latency_ms.toFixed(0)} ms`} color="violet" />
                </div>

                {/* Per-case results */}
                <div className="space-y-2">
                  <SectionHeader icon={<Activity className="w-3.5 h-3.5" />} title="Per-Case Live Results" badge={`${liveData.total_cases} cases`} />
                  {liveData.cases.map(c => (
                    <div key={c.case_id} className="border border-slate-200 rounded-xl overflow-hidden">
                      <button
                        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                        onClick={() => setExpandedLiveCase(expandedLiveCase === c.case_id ? null : c.case_id)}
                      >
                        <span className="text-xs font-mono font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded flex-shrink-0">{c.case_id}</span>
                        <span className="text-sm text-slate-700 flex-1 truncate">{c.question?.slice(0, 75)}…</span>
                        <div className="flex gap-1 flex-shrink-0">
                          <Pill ok={c.trajectory_pass}>Traj</Pill>
                          <Pill ok={c.outcome_pass}>Out</Pill>
                          <Pill ok={c.args_valid}>Args</Pill>
                        </div>
                        {expandedLiveCase === c.case_id
                          ? <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          : <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />}
                      </button>

                      {expandedLiveCase === c.case_id && (
                        <div className="border-t border-slate-100 p-4 bg-slate-50 space-y-3">
                          {/* Question */}
                          <p className="text-xs text-slate-600">{c.question}</p>

                          {/* Tool sequences */}
                          <div className="grid grid-cols-2 gap-3">
                            <div className="bg-white border border-slate-200 rounded-lg p-3">
                              <p className="text-xs font-semibold text-slate-400 mb-2">Expected Tools</p>
                              <div className="flex flex-wrap gap-1">
                                {(c.expected_tools || []).map((t, i) => (
                                  <span key={i} className="bg-violet-100 text-violet-700 text-xs font-mono px-2 py-0.5 rounded">{t}</span>
                                ))}
                              </div>
                            </div>
                            <div className="bg-white border border-slate-200 rounded-lg p-3">
                              <p className="text-xs font-semibold text-slate-400 mb-2">Actual Tools Called</p>
                              <div className="flex flex-wrap gap-1">
                                {(c.tools_called || []).length > 0
                                  ? c.tools_called.map((t, i) => (
                                    <span key={i} className="bg-emerald-100 text-emerald-700 text-xs font-mono px-2 py-0.5 rounded">{t}</span>
                                  ))
                                  : <span className="text-xs text-slate-400 italic">none</span>
                                }
                              </div>
                            </div>
                          </div>

                          {/* Metrics row */}
                          <div className="grid grid-cols-4 gap-2">
                            <div className="bg-white border border-slate-200 rounded-lg p-2 text-center">
                              <p className="text-xs text-slate-400">Latency</p>
                              <p className="text-sm font-bold text-slate-700">{c.latency_ms?.toFixed(0)} ms</p>
                            </div>
                            <div className="bg-white border border-slate-200 rounded-lg p-2 text-center">
                              <p className="text-xs text-slate-400">Steps</p>
                              <p className="text-sm font-bold text-slate-700">{c.step_count}</p>
                            </div>
                            <div className="bg-white border border-slate-200 rounded-lg p-2 text-center">
                              <p className="text-xs text-slate-400">Complexity</p>
                              <p className="text-sm font-bold text-slate-700 capitalize">{c.complexity || '—'}</p>
                            </div>
                            <div className="bg-white border border-slate-200 rounded-lg p-2 text-center">
                              <p className="text-xs text-slate-400">Verdict</p>
                              <p className={`text-xs font-bold ${c.passed ? 'text-emerald-600' : 'text-rose-600'}`}>
                                {c.passed ? '✓ PASS' : '✗ FAIL'}
                              </p>
                            </div>
                          </div>

                          {/* Diagnostics */}
                          {c.diagnostics?.length > 0 && (
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                              <p className="text-xs font-semibold text-blue-500 mb-1">Diagnostics</p>
                              <ul className="space-y-1">
                                {c.diagnostics.map((d, i) => (
                                  <li key={i} className="text-xs text-blue-700">• {d}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Answer preview */}
                          {c.final_answer && (
                            <div className="bg-white border border-slate-200 rounded-lg p-3">
                              <p className="text-xs font-semibold text-slate-400 mb-1">Agent Answer Preview</p>
                              <p className="text-xs text-slate-700 line-clamp-4">{c.final_answer.slice(0, 350)}{c.final_answer.length > 350 ? '…' : ''}</p>
                            </div>
                          )}

                          {/* Error */}
                          {c.error && (
                            <div className="bg-rose-50 border border-rose-200 rounded-lg p-3">
                              <p className="text-xs font-semibold text-rose-500 mb-1">Error</p>
                              <p className="text-xs text-rose-700">{c.error}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Errors summary */}
                {liveData.errors?.length > 0 && (
                  <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                    <p className="text-sm font-bold text-rose-700 mb-2">{liveData.errors.length} case(s) errored</p>
                    {liveData.errors.map((e, i) => (
                      <p key={i} className="text-xs text-rose-600">• {e.case_id}: {e.error}</p>
                    ))}
                  </div>
                )}
              </div>
            )
          })()}
        </div>
      </div>
    </>
  )
}
