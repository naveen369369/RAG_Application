import { useState } from 'react'
import {
  X, Shield, Play, Loader2, CheckCircle2, XCircle,
  AlertTriangle, ChevronDown, ChevronRight, ArrowRight,
  Lock, Eye, Cpu, AlertOctagon
} from 'lucide-react'
import { useAppContext } from '../../context/AppContext'
import { runSecurityEval } from '../../api/agentEval'

// ── Helpers ───────────────────────────────────────────────────────────────────
const pct = v => `${(v * 100).toFixed(0)}%`

const CATEGORY_ICONS = {
  direct_prompt_injection:   <AlertOctagon className="w-4 h-4" />,
  indirect_prompt_injection: <AlertTriangle className="w-4 h-4" />,
  tool_sandboxing:           <Lock className="w-4 h-4" />,
  output_validation:         <Eye className="w-4 h-4" />,
  system_prompt_leakage:     <Cpu className="w-4 h-4" />,
}

const CATEGORY_LABELS = {
  direct_prompt_injection:   'Direct Injection',
  indirect_prompt_injection: 'Indirect Injection',
  tool_sandboxing:           'Tool Sandboxing',
  output_validation:         'Output Validation',
  system_prompt_leakage:     'Prompt Leakage',
}

const OWASP_COLORS = {
  'LLM01:2025': 'bg-rose-50 border-rose-200 text-rose-800',
  'LLM02:2025': 'bg-orange-50 border-orange-200 text-orange-800',
  'LLM05:2025': 'bg-amber-50 border-amber-200 text-amber-800',
  'LLM06:2025': 'bg-violet-50 border-violet-200 text-violet-800',
  'LLM07:2025': 'bg-blue-50 border-blue-200 text-blue-800',
  'LLM09:2025': 'bg-slate-50 border-slate-200 text-slate-800',
}

function Pill({ ok, children }) {
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

function OWASPBadge({ id }) {
  return (
    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${OWASP_COLORS[id] || 'bg-slate-50 border-slate-200 text-slate-700'}`}>
      {id}
    </span>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function SecurityTestDrawer() {
  const { secDrawerOpen, setSecDrawerOpen } = useAppContext()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [expandedTest, setExpandedTest] = useState(null)
  const [expandedOwasp, setExpandedOwasp] = useState(null)

  const handleRun = async () => {
    setLoading(true); setError(null)
    try {
      const res = await runSecurityEval()
      setData(res)
      setActiveTab('overview')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'overview',  label: 'Overview' },
    { id: 'tests',     label: 'All Tests' },
    { id: 'injection', label: 'Injection Deep-Dive' },
    { id: 'owasp',     label: 'OWASP Mapping' },
  ]

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-40 transition-opacity duration-300 ${
          secDrawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setSecDrawerOpen(false)}
      />

      {/* Drawer */}
      <div className={`fixed right-0 top-0 bottom-0 z-50 w-[90vw] max-w-4xl bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${
        secDrawerOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0 bg-gradient-to-r from-rose-600 to-orange-600">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Security Testing</h2>
              <p className="text-xs text-white/70">Injection · Sandboxing · Output Validation · OWASP LLM Top 10</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRun}
              disabled={loading}
              className="flex items-center gap-2 text-sm font-semibold bg-white text-rose-700 hover:bg-rose-50 rounded-xl px-4 py-2 transition-colors disabled:opacity-60 shadow-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              {loading ? 'Running…' : 'Run Tests'}
            </button>
            <button onClick={() => setSecDrawerOpen(false)} className="p-2 hover:bg-white/20 rounded-xl transition-colors">
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
                    ? 'border-rose-500 text-rose-700 bg-white'
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
              <div className="w-16 h-16 rounded-2xl bg-rose-50 flex items-center justify-center">
                <Shield className="w-8 h-8 text-rose-400" />
              </div>
              <div className="text-center">
                <p className="text-base font-semibold text-slate-600">LLM Security Testing</p>
                <p className="text-sm mt-1">Click <strong>Run Tests</strong> to start the security evaluation</p>
                <p className="text-xs mt-1 text-slate-400">Direct injection · Indirect injection · Tool sandboxing · Output guardrails · OWASP mapping</p>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center h-full gap-3 text-slate-500">
              <Loader2 className="w-6 h-6 animate-spin text-rose-500" />
              <span className="text-sm font-medium">Running 5 security attack/defense tests…</span>
            </div>
          )}

          {/* ── OVERVIEW TAB ────────────────────────────────────────────────── */}
          {data && activeTab === 'overview' && (() => {
            const s = data.summary
            const beforePct = Math.round(s.pass_rate_before * 100)
            const afterPct  = Math.round(s.pass_rate_after  * 100)
            return (
              <div className="space-y-6">
                {/* Big score cards */}
                <div className="grid grid-cols-2 gap-4">
                  <div className={`rounded-xl border p-5 ${beforePct >= 80 ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
                    <p className="text-xs font-semibold text-slate-500 mb-1">Safe Tests — Before Defense</p>
                    <p className={`text-5xl font-bold ${beforePct >= 80 ? 'text-emerald-700' : 'text-rose-700'}`}>{beforePct}%</p>
                    <p className="text-sm text-slate-500 mt-1">{s.safe_before}/{s.total_tests} tests safe</p>
                    <div className="mt-3 h-2 bg-white/60 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-700 ${beforePct >= 80 ? 'bg-emerald-500' : 'bg-rose-500'}`} style={{ width: `${beforePct}%` }} />
                    </div>
                  </div>
                  <div className="rounded-xl border bg-emerald-50 border-emerald-200 p-5">
                    <p className="text-xs font-semibold text-slate-500 mb-1">Safe Tests — After Defense</p>
                    <p className="text-5xl font-bold text-emerald-700">{afterPct}%</p>
                    <p className="text-sm text-slate-500 mt-1">{s.safe_after}/{s.total_tests} tests safe</p>
                    <div className="mt-3 h-2 bg-white/60 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-emerald-500 transition-all duration-700" style={{ width: `${afterPct}%` }} />
                    </div>
                  </div>
                </div>

                {/* Summary strip */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-center justify-between">
                  <span className="text-sm text-slate-600">Vulnerabilities fixed by defenses</span>
                  <span className="text-2xl font-bold text-emerald-600">{s.fixed_by_defenses}</span>
                </div>

                {/* Quick results grid */}
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">All 5 Tests at a Glance</p>
                  <div className="space-y-2">
                    {data.tests.map(t => (
                      <div key={t.test_id} className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl p-3">
                        <span className="text-xs font-mono font-bold text-slate-400 w-8">{t.test_id}</span>
                        <div className="w-6 h-6 flex items-center justify-center text-slate-500">
                          {CATEGORY_ICONS[t.category]}
                        </div>
                        <span className="flex-1 text-sm text-slate-700">{CATEGORY_LABELS[t.category] || t.category}</span>
                        <div className="flex items-center gap-2">
                          <Pill ok={t.before_safe}>{t.before_safe ? 'Safe' : 'Vuln'}</Pill>
                          <ArrowRight className="w-3.5 h-3.5 text-slate-300" />
                          <Pill ok={t.after_safe}>{t.after_safe ? 'Safe' : 'Vuln'}</Pill>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )
          })()}

          {/* ── TESTS TAB ──────────────────────────────────────────────────── */}
          {data && activeTab === 'tests' && (
            <div className="space-y-3">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Security Tests — Before / After Defenses</p>
              {data.tests.map(t => {
                const open = expandedTest === t.test_id
                return (
                  <div key={t.test_id} className="border border-slate-200 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setExpandedTest(open ? null : t.test_id)}
                      className="w-full flex items-center gap-3 p-3.5 hover:bg-slate-50 transition-colors text-left"
                    >
                      <span className="text-xs font-mono font-bold text-slate-400 w-8">{t.test_id}</span>
                      <div className="w-6 h-6 flex items-center justify-center text-slate-500 flex-shrink-0">
                        {CATEGORY_ICONS[t.category]}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-700 truncate">{t.description}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{CATEGORY_LABELS[t.category] || t.category}</p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Pill ok={t.before_safe}>Before</Pill>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-300" />
                        <Pill ok={t.after_safe}>After</Pill>
                        {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                      </div>
                    </button>
                    {open && (
                      <div className="border-t border-slate-100 bg-slate-50 p-4 space-y-4 text-sm">
                        {/* OWASP badges */}
                        <div className="flex flex-wrap gap-1.5">
                          {t.owasp_categories.map(c => <OWASPBadge key={c} id={c.split(' ')[0]} />)}
                        </div>
                        {/* Attack payload */}
                        <div>
                          <p className="text-xs font-semibold text-rose-500 mb-1">Attack Payload</p>
                          <pre className="bg-rose-950 text-rose-200 text-xs rounded-lg p-3 whitespace-pre-wrap font-mono overflow-x-auto">
                            {t.attack_payload}
                          </pre>
                        </div>
                        {/* Responses side by side */}
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <p className="text-xs font-semibold text-rose-500 mb-1">Without Defense {t.before_safe ? '(safe)' : '(VULNERABLE)'}</p>
                            <div className={`rounded-lg p-3 text-xs font-mono ${t.before_safe ? 'bg-emerald-50 border border-emerald-200' : 'bg-rose-50 border border-rose-200'}`}>
                              {t.response_without_defense}
                            </div>
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-emerald-600 mb-1">With Defense {t.after_safe ? '(SAFE ✓)' : '(still vulnerable)'}</p>
                            <div className={`rounded-lg p-3 text-xs font-mono ${t.after_safe ? 'bg-emerald-50 border border-emerald-200' : 'bg-rose-50 border border-rose-200'}`}>
                              {t.response_with_defense}
                            </div>
                          </div>
                        </div>
                        {/* Defense applied */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                          <p className="text-xs font-semibold text-blue-500 mb-1">Defense Applied</p>
                          <p className="text-xs text-blue-700 font-mono">{t.defense_applied}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* ── INJECTION DEEP-DIVE TAB ─────────────────────────────────────── */}
          {data && activeTab === 'injection' && (() => {
            const s02 = data.tests.find(t => t.test_id === 'S02')
            const s01 = data.tests.find(t => t.test_id === 'S01')
            if (!s02) return null
            return (
              <div className="space-y-6">
                {/* Direct injection */}
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">S01 — Direct Prompt Injection</p>
                  <div className="space-y-3">
                    <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                      <p className="text-xs font-semibold text-rose-500 mb-2">Attack Payload (user message)</p>
                      <p className="text-sm font-mono text-rose-800">{s01?.attack_payload}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-rose-50 border border-rose-200 rounded-xl p-3">
                        <p className="text-xs font-semibold text-rose-500 mb-1">Without Defense</p>
                        <p className="text-xs font-mono text-rose-700">{s01?.response_without_defense}</p>
                      </div>
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3">
                        <p className="text-xs font-semibold text-emerald-600 mb-1">With Defense ✓</p>
                        <p className="text-xs font-mono text-emerald-700">{s01?.response_with_defense}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Indirect injection — full deep-dive */}
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">S02 — Indirect Injection via Tool Output</p>
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-3">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <p className="text-xs font-semibold text-amber-700">How it works</p>
                    </div>
                    <p className="text-sm text-amber-800">
                      A malicious customer submits an email that contains system directives.
                      When <code className="bg-amber-200 px-1 rounded text-xs font-mono">rag_retrieval</code> returns
                      this email as a document chunk, the LLM may follow the embedded instructions as if they
                      came from the system prompt.
                    </p>
                  </div>

                  {/* Malicious email content */}
                  <div className="mb-3">
                    <p className="text-xs font-semibold text-rose-500 mb-2">Malicious Content Returned by Tool</p>
                    <pre className="bg-slate-900 text-rose-300 text-xs rounded-xl p-4 font-mono whitespace-pre-wrap overflow-x-auto border border-rose-900/20">
                      {s02.attack_payload}
                    </pre>
                  </div>

                  {/* Before / After */}
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <p className="text-xs font-semibold text-rose-500 mb-2">Agent WITHOUT defense</p>
                      <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs font-mono text-rose-700">
                        {s02.response_without_defense}
                      </div>
                      <div className="mt-2 flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5 text-rose-500" />
                        <span className="text-xs text-rose-600 font-medium">Agent followed malicious instruction</span>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-emerald-600 mb-2">Agent WITH defense</p>
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-xs font-mono text-emerald-700">
                        {s02.response_with_defense}
                      </div>
                      <div className="mt-2 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        <span className="text-xs text-emerald-600 font-medium">Directive stripped — normal response</span>
                      </div>
                    </div>
                  </div>

                  {/* Defense explanation */}
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                    <p className="text-xs font-semibold text-blue-500 mb-2">Defense: <code className="font-mono">sanitise_tool_output()</code></p>
                    <p className="text-sm text-blue-700">
                      All tool return values are passed through <code className="bg-blue-100 px-1 rounded text-xs font-mono">sanitise_tool_output()</code>
                      before being appended to the LLM context. Regex patterns strip{' '}
                      <code className="bg-blue-100 px-1 rounded text-xs font-mono">SYSTEM:</code>, override directives,
                      and data-exfiltration commands, replacing them with <code className="bg-blue-100 px-1 rounded text-xs font-mono">[REDACTED]</code>.
                    </p>
                  </div>
                </div>
              </div>
            )
          })()}

          {/* ── OWASP TAB ──────────────────────────────────────────────────── */}
          {data && activeTab === 'owasp' && (
            <div className="space-y-4">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">OWASP LLM Top 10 (2025) Mapping</p>
              <p className="text-xs text-slate-500 mb-4">Security findings mapped to OWASP LLM Top 10 categories with implemented mitigations.</p>
              {data.owasp_mapping.map(entry => {
                const open = expandedOwasp === entry.owasp_id
                return (
                  <div key={entry.owasp_id} className={`border rounded-xl overflow-hidden ${OWASP_COLORS[entry.owasp_id] ? 'border-' + OWASP_COLORS[entry.owasp_id].split('border-')[1].split(' ')[0] : 'border-slate-200'}`}>
                    <button
                      onClick={() => setExpandedOwasp(open ? null : entry.owasp_id)}
                      className="w-full flex items-center gap-3 p-4 text-left hover:bg-black/5 transition-colors"
                    >
                      <OWASPBadge id={entry.owasp_id} />
                      <span className="flex-1 text-sm font-semibold text-slate-800">{entry.title}</span>
                      <span className="text-xs text-slate-400">{entry.findings.length} finding{entry.findings.length !== 1 ? 's' : ''}</span>
                      {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                    </button>
                    {open && (
                      <div className="border-t border-slate-200 bg-white p-4 space-y-3">
                        <div>
                          <p className="text-xs font-semibold text-rose-500 mb-2">Findings</p>
                          <ul className="space-y-1">
                            {entry.findings.map((f, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                                <XCircle className="w-3.5 h-3.5 text-rose-400 mt-0.5 flex-shrink-0" />
                                {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-emerald-600 mb-2">Mitigations Implemented</p>
                          <ul className="space-y-1">
                            {entry.mitigations.map((m, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mt-0.5 flex-shrink-0" />
                                <code className="font-mono text-xs bg-slate-100 px-1 py-0.5 rounded">{m}</code>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
