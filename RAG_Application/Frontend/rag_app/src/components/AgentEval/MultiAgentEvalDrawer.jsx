import { useState, useEffect } from 'react'
import {
  X, GitBranch, Play, Loader2, CheckCircle2, XCircle,
  AlertTriangle, ChevronDown, ChevronRight, TrendingUp, DollarSign,
  Activity, Zap, BarChart3, ArrowRight, Shield, Users, FileText, Award
} from 'lucide-react'
import { useAppContext } from '../../context/AppContext'
import { runMultiAgentEval } from '../../api/agentEval'

// ─── Helpers ────────────────────────────────────────────────────────────────
const pct = v => `${(v * 100).toFixed(0)}%`
const musd = v => `$${(v * 1e6).toFixed(2)} µ`
const ms = v => `${v} ms`

function Badge({ ok, children }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
      ok ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
         : 'bg-rose-50 text-rose-700 border border-rose-200'
    }`}>
      {ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
      {children}
    </span>
  )
}

function StatCard({ label, sa, ma, unit = '', good = 'high' }) {
  const saNum = typeof sa === 'number' ? sa : 0
  const maNum = typeof ma === 'number' ? ma : 0
  const delta = maNum - saNum
  const pctDelta = saNum !== 0 ? (delta / saNum * 100).toFixed(1) : '0.0'
  const isGood = good === 'high' ? delta >= 0 : delta <= 0
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <p className="text-xs font-medium text-slate-500 mb-2">{label}</p>
      <div className="flex items-end justify-between gap-2">
        <div>
          <p className="text-xs text-slate-400 mb-0.5">Single Agent</p>
          <p className="text-lg font-bold text-slate-700">{sa}{unit}</p>
        </div>
        <ArrowRight className="w-4 h-4 text-slate-300 mb-1" />
        <div>
          <p className="text-xs text-slate-400 mb-0.5">Multi-Agent</p>
          <p className={`text-lg font-bold ${isGood ? 'text-emerald-600' : 'text-rose-600'}`}>{ma}{unit}</p>
        </div>
        <div className={`text-xs font-bold px-2 py-1 rounded-lg mb-1 ${isGood ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
          {delta >= 0 ? '+' : ''}{pctDelta}%
        </div>
      </div>
    </div>
  )
}

function MarkdownViewer({ content, title }) {
  if (!content) return (
    <div className="flex items-center justify-center h-48 text-slate-400 text-sm">No content yet.</div>
  )
  const lines = content.split('\n')
  return (
    <div className="bg-slate-50 rounded-xl border border-slate-200 p-5 font-mono text-xs overflow-x-auto">
      {title && <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-200">
        <FileText className="w-4 h-4 text-violet-500" />
        <span className="font-semibold text-slate-700 font-sans text-sm">{title}</span>
      </div>}
      {lines.map((line, i) => {
        if (line.startsWith('# ')) return <p key={i} className="text-base font-bold text-slate-800 mt-2 mb-1 font-sans">{line.slice(2)}</p>
        if (line.startsWith('## ')) return <p key={i} className="text-sm font-semibold text-violet-700 mt-3 mb-1 font-sans">{line.slice(3)}</p>
        if (line.startsWith('> ')) return <blockquote key={i} className="border-l-4 border-amber-400 pl-3 text-amber-800 bg-amber-50 rounded py-1 my-1 font-sans text-xs">{line.slice(2)}</blockquote>
        if (line.startsWith('|') && line.endsWith('|')) {
          const cells = line.split('|').filter(Boolean)
          const isHeader = i > 0 && lines[i+1]?.includes('---')
          const isSep = line.includes('---')
          if (isSep) return null
          return (
            <div key={i} className={`flex gap-2 py-1 border-b border-slate-100 ${isHeader ? 'font-semibold text-slate-700 border-slate-300 bg-white rounded-t' : ''}`}>
              {cells.map((c, j) => (
                <span key={j} className="min-w-[80px] flex-1 truncate">{c.trim()}</span>
              ))}
            </div>
          )
        }
        if (line.startsWith('- ') || line.startsWith('* ')) return <p key={i} className="text-slate-600 ml-2">• {line.slice(2)}</p>
        if (line.startsWith('**') && line.endsWith('**')) return <p key={i} className="font-semibold text-slate-800">{line.replace(/\*\*/g, '')}</p>
        if (line === '') return <div key={i} className="h-2" />
        return <p key={i} className="text-slate-600 leading-relaxed">{line}</p>
      })}
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────────────────
export default function MultiAgentEvalDrawer() {
  const { multiAgentDrawerOpen, setMultiAgentDrawerOpen } = useAppContext()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  const handleRun = async (forceRefresh = true) => {
    setLoading(true); setError(null)
    try {
      const res = await runMultiAgentEval(forceRefresh)
      setData(res)
      setActiveTab('overview')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (multiAgentDrawerOpen && !data && !loading) {
      handleRun(false)
    }
  }, [multiAgentDrawerOpen])

  const tabs = [
    { id: 'overview',     label: 'Overview' },
    { id: 'race_table',   label: 'Race Table' },
    { id: 'handoffs',     label: 'Handoffs Log' },
    { id: 'failure',      label: 'Failure Case' },
    { id: 'verdict',      label: 'Verdict' },
    { id: 'agent_card',   label: 'AgentCard / A2A' },
  ]

  const sa = data?.single_agent?.summary
  const ma = data?.multi_agent?.summary
  const resend = data?.context_resend

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-40 transition-opacity duration-300 ${
          multiAgentDrawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setMultiAgentDrawerOpen(false)}
      />

      {/* Drawer */}
      <div className={`fixed right-0 top-0 bottom-0 z-50 w-[92vw] max-w-5xl bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${
        multiAgentDrawerOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0 bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
              <Users className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Single Agent vs Multi-Agent Race</h2>
              <p className="text-xs text-white/70">Week-7 · Same 10 cases · Same judge · A2A · AgentCard</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRun}
              disabled={loading}
              className="flex items-center gap-2 text-sm font-semibold bg-white text-indigo-700 hover:bg-indigo-50 rounded-xl px-4 py-2 transition-colors disabled:opacity-60 shadow-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              {loading ? 'Running…' : 'Run Eval'}
            </button>
            <button onClick={() => setMultiAgentDrawerOpen(false)} className="p-2 hover:bg-white/20 rounded-xl transition-colors">
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
                className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${
                  activeTab === t.id
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
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-sm text-rose-700 mb-4">
              <strong>Error:</strong> {error}
            </div>
          )}

          {!data && !loading && !error && (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-4">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-50 to-violet-50 border border-violet-100 flex items-center justify-center">
                <Users className="w-10 h-10 text-violet-400" />
              </div>
              <div className="text-center max-w-md">
                <p className="text-base font-semibold text-slate-600">Single Agent vs Multi-Agent Race</p>
                <p className="text-sm mt-1 text-slate-400">Compare both architectures on the same 10 Week-6 cases using the same judge</p>
                <p className="text-xs mt-2 text-slate-300">race_table · handoffs · failure case · verdict · A2A AgentCard</p>
              </div>
              <button
                onClick={handleRun}
                className="mt-2 flex items-center gap-2 text-sm font-semibold bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-xl px-6 py-3 shadow-md hover:shadow-lg hover:opacity-90 transition-all"
              >
                <Play className="w-4 h-4 fill-current" />
                Run Evaluation
              </button>
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center h-full gap-3 text-slate-500">
              <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
              <span className="text-sm font-medium">Comparing Single Agent vs Multi-Agent…</span>
            </div>
          )}

          {/* ── OVERVIEW TAB ─────────────────────────────────────────────── */}
          {data && activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Summary cards */}
              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  label="Pass Rate"
                  sa={pct(sa.pass_rate)}
                  ma={pct(ma.pass_rate)}
                  good="high"
                />
                <StatCard
                  label="p50 Latency"
                  sa={sa.p50_latency_ms}
                  ma={ma.p50_latency_ms}
                  unit=" ms"
                  good="low"
                />
                <StatCard
                  label="Total Tokens"
                  sa={sa.total_tokens}
                  ma={ma.total_tokens}
                  good="low"
                />
                <StatCard
                  label="Cost / Ticket"
                  sa={musd(sa.cost_per_ticket)}
                  ma={musd(ma.cost_per_ticket)}
                  good="low"
                />
              </div>

              {/* Context re-send */}
              {resend && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Zap className="w-4 h-4 text-amber-600" />
                    <h3 className="text-sm font-bold text-amber-800">Context Re-send Analysis</h3>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-amber-600 mb-1">Re-send Multiplier</p>
                      <p className="text-3xl font-bold text-amber-700">{resend.multiplier}x</p>
                    </div>
                    <div>
                      <p className="text-xs text-amber-600 mb-1">Total Hand-offs</p>
                      <p className="text-3xl font-bold text-amber-700">{resend.handoff_count}</p>
                    </div>
                    <div>
                      <p className="text-xs text-amber-600 mb-1">Hand-off Tokens</p>
                      <p className="text-3xl font-bold text-amber-700">{resend.total_handoff_tokens}</p>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-amber-200">
                    <p className="text-xs text-amber-700">
                      <span className="font-semibold">Dominant hand-off:</span> {resend.dominant_handoff} on {resend.dominant_case} — {resend.dominant_tokens} tokens ({resend.dominant_pct}% of all hand-off tokens)
                    </p>
                  </div>
                </div>
              )}

              {/* Per-case grid */}
              <div>
                <h3 className="text-sm font-bold text-slate-700 mb-3">Per-Case Comparison</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-slate-100 rounded-lg">
                        <th className="text-left px-3 py-2 font-semibold text-slate-600 rounded-l-lg">Case</th>
                        <th className="text-center px-3 py-2 font-semibold text-slate-600">SA Pass</th>
                        <th className="text-center px-3 py-2 font-semibold text-slate-600">MA Pass</th>
                        <th className="text-right px-3 py-2 font-semibold text-slate-600">SA Lat</th>
                        <th className="text-right px-3 py-2 font-semibold text-slate-600">MA Lat</th>
                        <th className="text-right px-3 py-2 font-semibold text-slate-600">SA Tok</th>
                        <th className="text-right px-3 py-2 font-semibold text-slate-600 rounded-r-lg">MA Tok</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.single_agent?.cases || []).map((sa_c, i) => {
                        const ma_c = (data.multi_agent?.cases || [])[i]
                        const sa_tok = sa_c.input_tokens + sa_c.output_tokens
                        const ma_tok = ma_c ? ma_c.input_tokens + ma_c.output_tokens : 0
                        return (
                          <tr key={sa_c.id} className="border-b border-slate-100 hover:bg-slate-50">
                            <td className="px-3 py-2 font-mono font-bold text-slate-700">{sa_c.id}</td>
                            <td className="px-3 py-2 text-center">
                              {sa_c.outcome_pass
                                ? <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" />
                                : <XCircle className="w-4 h-4 text-rose-500 mx-auto" />}
                            </td>
                            <td className="px-3 py-2 text-center">
                              {ma_c?.outcome_pass
                                ? <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" />
                                : <XCircle className="w-4 h-4 text-rose-500 mx-auto" />}
                            </td>
                            <td className="px-3 py-2 text-right text-slate-600">{sa_c.latency_ms}ms</td>
                            <td className={`px-3 py-2 text-right font-medium ${ma_c?.latency_ms > sa_c.latency_ms ? 'text-amber-600' : 'text-emerald-600'}`}>
                              {ma_c?.latency_ms}ms
                            </td>
                            <td className="px-3 py-2 text-right text-slate-600">{sa_tok}</td>
                            <td className={`px-3 py-2 text-right font-medium ${ma_tok > sa_tok ? 'text-rose-600' : 'text-emerald-600'}`}>
                              {ma_tok}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ── RACE TABLE TAB ───────────────────────────────────────────── */}
          {data && activeTab === 'race_table' && (
            <MarkdownViewer content={data.race_table_md} title="race_table.md" />
          )}

          {/* ── HANDOFFS TAB ─────────────────────────────────────────────── */}
          {data && activeTab === 'handoffs' && (
            <div className="space-y-4">
              {/* Summary */}
              {resend && (
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: 'Multiplier', value: resend.multiplier + 'x', color: 'amber' },
                    { label: 'Hand-offs', value: resend.handoff_count, color: 'blue' },
                    { label: 'SA Tokens', value: resend.sa_total_tokens, color: 'emerald' },
                    { label: 'MA Tokens', value: resend.ma_total_tokens, color: 'rose' },
                  ].map(m => (
                    <div key={m.label} className={`rounded-xl border p-3 ${
                      m.color === 'amber' ? 'bg-amber-50 border-amber-200 text-amber-700' :
                      m.color === 'blue'  ? 'bg-blue-50 border-blue-200 text-blue-700' :
                      m.color === 'emerald' ? 'bg-emerald-50 border-emerald-200 text-emerald-700' :
                      'bg-rose-50 border-rose-200 text-rose-700'
                    }`}>
                      <p className="text-xs opacity-70 mb-1">{m.label}</p>
                      <p className="text-xl font-bold">{m.value}</p>
                    </div>
                  ))}
                </div>
              )}
              <MarkdownViewer content={data.handoffs_log} title="handoffs.log" />
            </div>
          )}

          {/* ── FAILURE CASE TAB ─────────────────────────────────────────── */}
          {data && activeTab === 'failure' && (
            <div className="space-y-4">
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600" />
                  <h3 className="text-sm font-bold text-rose-800">Worker Failure Injection</h3>
                </div>
                {data.failure_case && (
                  <div className="space-y-2 text-xs">
                    <p><span className="font-semibold text-rose-700">Case:</span> {data.failure_case.case_id}</p>
                    <p><span className="font-semibold text-rose-700">Injected:</span> {data.failure_case.injected_fault}</p>
                    <p><span className="font-semibold text-rose-700">Classification:</span>
                      <span className="ml-1 px-2 py-0.5 bg-orange-100 text-orange-700 rounded font-bold uppercase">
                        {data.failure_case.classification}
                      </span>
                    </p>
                    <p><span className="font-semibold text-rose-700">Retries:</span> {data.failure_case.retry_count}</p>
                    <p className="text-rose-600 mt-2 leading-relaxed">{data.failure_case.behavior}</p>
                  </div>
                )}
              </div>
              {data.failure_case?.a2a_lifecycle && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="w-4 h-4 text-slate-600" />
                    <h3 className="text-sm font-bold text-slate-700">A2A Task Lifecycle</h3>
                  </div>
                  <div className="flex items-center gap-2 text-sm mb-3">
                    {['submitted','working','failed'].map((s, i) => (
                      <span key={s} className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-lg font-semibold text-xs ${
                          s === 'failed' ? 'bg-rose-100 text-rose-700 border border-rose-300' :
                          'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}>{s}</span>
                        {i < 2 && <ArrowRight className="w-3 h-3 text-slate-300" />}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">{data.failure_case.a2a_lifecycle.a2a_vs_rest}</p>
                </div>
              )}
              <MarkdownViewer content={data.failure_case_md} title="failure_case.md" />
            </div>
          )}

          {/* ── VERDICT TAB ──────────────────────────────────────────────── */}
          {data && activeTab === 'verdict' && (
            <div className="space-y-4">
              <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 text-white">
                <div className="flex items-center gap-3 mb-4">
                  <Award className="w-6 h-6 text-amber-400" />
                  <h3 className="text-base font-bold">Verdict</h3>
                </div>
                {sa && ma && resend && (() => {
                  const passDelta = ((ma.pass_rate - sa.pass_rate) * 100).toFixed(1)
                  const latDelta  = ma.p50_latency_ms - sa.p50_latency_ms
                  const isKill    = !(parseFloat(passDelta) > 5 && latDelta < 200)
                  return (
                    <>
                      <div className="bg-amber-500/20 border border-amber-400/30 rounded-lg p-3 mb-4 text-sm text-amber-200">
                        ⚠️ <strong>Sunk-cost bias:</strong> Do not keep multi-agent simply because it was built.
                      </div>
                      <div className="grid grid-cols-2 gap-3 mb-4">
                        <div className="bg-white/10 rounded-lg p-3">
                          <p className="text-xs text-white/60 mb-1">Pass Rate Delta</p>
                          <p className={`text-xl font-bold ${parseFloat(passDelta) > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {passDelta >= 0 ? '+' : ''}{passDelta} pp
                          </p>
                        </div>
                        <div className="bg-white/10 rounded-lg p-3">
                          <p className="text-xs text-white/60 mb-1">p50 Latency Delta</p>
                          <p className={`text-xl font-bold ${latDelta > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {latDelta > 0 ? '+' : ''}{latDelta} ms
                          </p>
                        </div>
                        <div className="bg-white/10 rounded-lg p-3">
                          <p className="text-xs text-white/60 mb-1">Token Multiplier</p>
                          <p className="text-xl font-bold text-rose-400">{resend.multiplier}x overhead</p>
                        </div>
                        <div className="bg-white/10 rounded-lg p-3">
                          <p className="text-xs text-white/60 mb-1">Decision</p>
                          <p className={`text-xl font-bold ${isKill ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {isKill ? 'KILL' : 'KEEP'}
                          </p>
                        </div>
                      </div>
                    </>
                  )
                })()}
              </div>
              <MarkdownViewer content={data.verdict_md} title="verdict.md" />
            </div>
          )}

          {/* ── AGENT CARD / A2A TAB ─────────────────────────────────────── */}
          {data && activeTab === 'agent_card' && (
            <div className="space-y-4">
              {data.agent_card && (
                <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5">
                  <div className="flex items-center gap-3 mb-4">
                    <Shield className="w-5 h-5 text-indigo-600" />
                    <div>
                      <h3 className="text-sm font-bold text-indigo-800">{data.agent_card.name}</h3>
                      <p className="text-xs text-indigo-600">v{data.agent_card.version} · {data.agent_card.url}</p>
                    </div>
                  </div>
                  <p className="text-xs text-indigo-700 mb-4">{data.agent_card.description}</p>

                  <div className="space-y-2 mb-4">
                    <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">Skills</p>
                    {data.agent_card.skills?.map(s => (
                      <div key={s.id} className="bg-white border border-indigo-100 rounded-lg p-3">
                        <p className="text-xs font-bold text-indigo-700">{s.name}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{s.description}</p>
                        <div className="flex gap-1 mt-1.5">
                          {s.tags?.map(t => (
                            <span key={t} className="text-[10px] bg-indigo-100 text-indigo-600 px-1.5 py-0.5 rounded font-medium">{t}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-white border border-indigo-100 rounded-lg p-3">
                      <p className="font-semibold text-indigo-700 mb-1">Input Modes</p>
                      {data.agent_card.defaultInputModes?.map(m => (
                        <p key={m} className="text-slate-600">{m}</p>
                      ))}
                    </div>
                    <div className="bg-white border border-indigo-100 rounded-lg p-3">
                      <p className="font-semibold text-indigo-700 mb-1">Output Modes</p>
                      {data.agent_card.defaultOutputModes?.map(m => (
                        <p key={m} className="text-slate-600">{m}</p>
                      ))}
                    </div>
                    <div className="bg-white border border-indigo-100 rounded-lg p-3 col-span-2">
                      <p className="font-semibold text-indigo-700 mb-1">Authentication</p>
                      <p className="text-slate-600">{data.agent_card.authentication?.schemes?.join(', ')} — {data.agent_card.authentication?.note}</p>
                    </div>
                    <div className="bg-white border border-indigo-100 rounded-lg p-3 col-span-2">
                      <p className="font-semibold text-indigo-700 mb-1">A2A Task States</p>
                      <div className="flex gap-2 flex-wrap">
                        {data.agent_card.taskStates?.map(s => (
                          <span key={s} className={`px-2 py-0.5 rounded text-xs font-medium ${
                            s === 'failed' ? 'bg-rose-100 text-rose-700' :
                            s === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                            s === 'working' ? 'bg-blue-100 text-blue-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>{s}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
