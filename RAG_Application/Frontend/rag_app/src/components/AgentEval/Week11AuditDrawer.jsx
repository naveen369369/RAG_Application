import { useState } from 'react'
import {
  X, ClipboardList, Play, Loader2, CheckCircle2, XCircle,
  AlertTriangle, ArrowRight, Activity, DollarSign, Zap,
  BarChart3, Clock, TrendingUp, Shield, Search, FileText,
  GitBranch, ChevronDown, ChevronRight
} from 'lucide-react'
import { useAppContext } from '../../context/AppContext'
import { runTrajectoryEval } from '../../api/agentEval'

// ── Shared helpers (same style as TrajectoryEvalDrawer) ───────────────────────
const pct = v => `${(v * 100).toFixed(1)}%`
const musd = v => `$${(v * 1e6).toFixed(2)} µ`

function Pill({ ok, warn, children }) {
  if (warn) return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
      <AlertTriangle className="w-3 h-3" />{children}
    </span>
  )
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${ok
      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
      : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
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
    slate: 'bg-slate-50 border-slate-200 text-slate-600',
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

function CodeBlock({ children }) {
  return (
    <pre className="bg-slate-900 text-slate-200 rounded-xl p-4 text-xs font-mono overflow-x-auto leading-relaxed">
      {children}
    </pre>
  )
}

// ── Static audit data (Week-11 findings, not fetched from API) ────────────────
const DRILL_DATA = {
  drill1: { time: '04:23', method: 'Manual scan of analysis/traces.jsonl + trajectory_eval.py mock', planted: 'T01 answer: "15% restocking fee" (not in Hr-3.md)' },
  drill2: { time: '01:07', method: 'Filter by failure_category = "policy_hallucination"', improvement: '-74%' },
  missingFields: [
    { field: 'policy_claim_check', desc: 'Boolean — True if answer contains a numeric fee/deadline not in retrieved chunks' },
    { field: 'failure_category', desc: 'Enum: policy_hallucination | argument_fabrication | wrong_tool_sequence | retrieval_miss | none' },
    { field: 'forbidden_terms_detected', desc: 'List of policy terms in answer not grounded in context' },
  ],
}

const TRACE_DATA = {
  traceId: 'trace-005',
  promptVersion: 'v1.0',
  model: 'groq/compound-mini',
  question: 'Can I return an electronic item that I have already opened?',
  answer: 'No. For electronics the policy states they must be unopened (or verified defective) to be eligible for return.',
  totalLatencyMs: 2774,
  spans: [
    { name: 'embedding', op: 'sentence_transformer_encode', latencyMs: 312, inputTok: null, outputTok: null, costUsd: 0, note: 'Local CPU — no API cost' },
    { name: 'retrieval', op: 'pinecone_query', latencyMs: 187, inputTok: null, outputTok: null, costUsd: 0.0000013, note: '5 chunks, top score 0.727; cache miss' },
    { name: 'generation', op: 'groq_chat_completion', latencyMs: 2275, inputTok: 623, outputTok: 87, costUsd: 0.0000209, note: 'compound-mini, temp 0.2; cache miss' },
    { name: 'judge_faithfulness', op: 'llm_judge (async)', latencyMs: 0, inputTok: null, outputTok: null, costUsd: 0.0000062, note: 'Score: 0.95' },
    { name: 'judge_relevancy', op: 'llm_judge (async)', latencyMs: 0, inputTok: null, outputTok: null, costUsd: 0.0000058, note: 'Score: 1.00' },
    { name: 'judge_context', op: 'llm_judge (async)', latencyMs: 0, inputTok: null, outputTok: null, costUsd: 0.0000061, note: 'Score: 0.90' },
  ],
  retrievedChunks: [
    { id: 'Product Returns & Refund Policy.docx:chunk-1', score: 0.7272 },
    { id: 'Product Returns & Refund Policy.docx:chunk-9', score: 0.6865 },
    { id: 'Product Returns & Refund Policy.docx:chunk-2', score: 0.6805 },
    { id: 'Product Returns & Refund Policy.docx:chunk-4', score: 0.6750 },
    { id: 'Product Returns & Refund Policy.docx:chunk-25', score: 0.6639 },
  ],
}

const COST_DATA = {
  stages: [
    { stage: 'Embedding', cost: '$0.000000', detail: 'BAAI/bge-large-en-v1.5, local CPU', type: 'M' },
    { stage: 'Retrieval (Pinecone)', cost: '~$0.0000013', detail: '5 results × ~50 read units × $0.025/1M RU', type: 'E' },
    { stage: 'Generation — simple RAG', cost: '~$0.0000213', detail: '535 input + 87 output tokens, compound-mini', type: 'E' },
    { stage: 'Generation — agent path', cost: '~$0.0001738', detail: '391 avg input + 94 avg output, llama-70b pricing', type: 'M' },
    { stage: 'Tool execution (SQLite)', cost: '$0.000000', detail: 'ticket_lookup, order_lookup, customer_lookup — local', type: 'M' },
    { stage: 'LLM Judge (3 calls)', cost: '~$0.0000234', detail: '3 × ~200 input + 30 output tokens, async', type: 'E' },
  ],
  totals: [
    { path: 'Simple RAG (compound-mini)', total: '~$0.000046' },
    { path: 'Agent path (llama-70b budget)', total: '~$0.000199' },
  ],
}

const TENX_DATA = {
  bottleneck: 'Groq free-tier TPM limit on the agent path',
  proof: { limit: '6,000 TPM', at10x: '~9,750 TPM', excess: '+3,750 TPM (62.5% over)' },
  baseline: [
    { metric: 'Traced queries', val: '25 (batch)', type: 'M' },
    { metric: 'Wall-clock for 25 queries', val: '~88 seconds', type: 'M' },
    { metric: 'Sequential throughput', val: '0.28 qps', type: 'M' },
    { metric: 'Assumed daily traffic', val: '~250 queries/day', type: 'E' },
    { metric: 'Cost per RAG query', val: '~$0.000046', type: 'E' },
    { metric: 'Daily cost (RAG)', val: '~$0.012', type: 'E' },
  ],
  mitigations: [
    { issue: 'Free-tier TPM exhausted', fix: 'Upgrade to Groq paid tier', tradeoff: '+~$15/month at 10× agent volume' },
    { issue: 'No retry budget', fix: 'Exponential backoff + circuit breaker on Groq 429s', tradeoff: 'Prevents retry storms; small latency increase' },
    { issue: 'No prompt caching', fix: 'Enable Groq prefix caching for system prompt', tradeoff: '~22% input token savings; verify SDK support first' },
  ],
}

const TOPICS = [
  { num: '01', name: 'What to log per request', status: 'Improved', color: 'blue', evidence: 'failure_category + policy_claim_check fields added. Gap: streaming tokens (Groq SDK limitation).' },
  { num: '02', name: 'Traces and spans', status: 'Already implemented', color: 'emerald', evidence: 'Full span hierarchy in observability/langfuse_client.py. trace.json documents actual spans.' },
  { num: '03', name: 'Langfuse', status: 'Already implemented', color: 'emerald', evidence: 'LANGFUSE_HOST=us.cloud.langfuse.com, singleton client, all /chat traces, judge scores pushed.' },
  { num: '04', name: 'The support drill', status: 'Implemented', color: 'violet', evidence: 'Drill 1: 04:23 (manual). Drill 2: 01:07 (failure_category). −74%. See drill.md.' },
  { num: '05', name: 'Cost per query', status: 'Implemented', color: 'violet', evidence: 'cost_by_stage.md: ~$0.000046 simple RAG, ~$0.000199 agent. M/E clearly separated.' },
  { num: '06', name: 'Prompt caching', status: 'Deferred', color: 'amber', evidence: 'Groq caching support unconfirmed for models in use. Savings modest (~$0.0000035/query).' },
  { num: '07', name: 'Semantic caching', status: 'Deferred — not safe yet', color: 'amber', evidence: 'Unsafe without policy-version cache keys. Returns namespace excluded until policy_claim_check is live.' },
  { num: '08', name: 'Model routing (LiteLLM)', status: 'Deferred', color: 'amber', evidence: 'Only Groq configured. BudgetTracker already caps cost. Revisit at 10× volume.' },
  { num: '09', name: 'Fallbacks and rate limits', status: 'Improved (gaps)', color: 'blue', evidence: 'Existing: Langfuse no-op, BudgetTracker, guardrails. Gap: no Groq backoff, no Pinecone circuit breaker.' },
  { num: '10', name: 'The data flywheel', status: 'Improved', color: 'blue', evidence: 'T01 failure → T11 regression case → RED→GREEN cycle working. failure_category field searchable.' },
  { num: '11', name: 'The 10× plan', status: 'Implemented', color: 'violet', evidence: 'First bottleneck: Groq free TPM at 62.5% over limit. Load-test plan provided. tenx.md.' },
  { num: '12', name: 'Fine-tuning', status: 'Not applicable', color: 'slate', evidence: 'Failure was prompt behavior, not model gap. Retrieval correct (score 0.727). Prompt v1.2 resolved it.' },
]

const STATUS_COLORS = {
  'Improved': 'bg-blue-50 text-blue-700 border border-blue-200',
  'Already implemented': 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  'Implemented': 'bg-violet-50 text-violet-700 border border-violet-200',
  'Deferred': 'bg-amber-50 text-amber-700 border border-amber-200',
  'Deferred — not safe yet': 'bg-amber-50 text-amber-700 border border-amber-200',
  'Improved (gaps)': 'bg-blue-50 text-blue-700 border border-blue-200',
  'Not applicable': 'bg-slate-100 text-slate-500 border border-slate-200',
}

const REGRESSION_CASES = [
  {
    id: 'W11-R01', desc: 'Opened electronics — agent must NOT confirm restocking fee',
    before: { answer: '"…opened items qualify for return with 15% restocking fee…"', pass: false, forbiddenFound: ['with a 15%', '15% restocking'] },
    after: { answer: '"…opened headphones that are not defective are not eligible for return. There is no restocking fee…"', pass: true },
  },
  {
    id: 'W11-R02', desc: 'Direct question — opened electronics return eligibility',
    before: { answer: '"Opened electronics may be returned within 30 days subject to a restocking fee…"', pass: false, forbiddenFound: ['subject to a restocking fee'] },
    after: { answer: '"No. Electronics must be unopened or verified defective…"', pass: true },
  },
]

// ── Main Component ─────────────────────────────────────────────────────────────
export default function Week11AuditDrawer() {
  const { week11DrawerOpen, setWeek11DrawerOpen } = useAppContext()
  const [loading, setLoading] = useState(false)
  const [suiteData, setSuiteData] = useState(null)
  const [suiteError, setSuiteError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [expandedCase, setExpandedCase] = useState(null)
  const [expandedTopic, setExpandedTopic] = useState(null)

  const handleRunSuite = async () => {
    setLoading(true); setSuiteError(null)
    try {
      const res = await runTrajectoryEval()
      setSuiteData(res)
      setActiveTab('suite')
    } catch (e) {
      setSuiteError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'overview', label: '📋 Overview' },
    { id: 'drill', label: '🔍 Drill' },
    { id: 'trace', label: '🔗 Trace' },
    { id: 'suite', label: '🧪 Suite Output' },
    { id: 'cost', label: '💰 Cost' },
    { id: 'tenx', label: '📈 10× Plan' },
    { id: 'topics', label: '✅ Topics' },
    { id: 'regression', label: '🔴 Regression' },
  ]

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-40 transition-opacity duration-300 ${week11DrawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        onClick={() => setWeek11DrawerOpen(false)}
      />

      {/* Drawer */}
      <div className={`fixed right-0 top-0 bottom-0 z-50 w-[92vw] max-w-5xl bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${week11DrawerOpen ? 'translate-x-0' : 'translate-x-full'}`}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0 bg-gradient-to-r from-slate-800 to-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
              <ClipboardList className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Week-11 Refund Failure Audit</h2>
              <p className="text-xs text-white/60">8 tabs · drill · trace · suite · cost · 10× · topics · regression</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs bg-emerald-500 text-white font-semibold px-3 py-1 rounded-full">GREEN 11/11</span>
            <span className="text-xs bg-white/20 text-white font-mono px-3 py-1 rounded-full">prompt v1.2</span>
            <button
              onClick={handleRunSuite}
              disabled={loading}
              className="flex items-center gap-2 text-sm font-semibold bg-white text-slate-700 hover:bg-slate-50 rounded-xl px-4 py-2 transition-colors disabled:opacity-60 shadow-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              {loading ? 'Running…' : 'Run Suite'}
            </button>
            <button onClick={() => setWeek11DrawerOpen(false)} className="p-2 hover:bg-white/20 rounded-xl transition-colors">
              <X className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex border-b border-slate-200 bg-slate-50 flex-shrink-0 overflow-x-auto">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${activeTab === t.id
                ? 'border-slate-700 text-slate-900 bg-white'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100'}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">

          {/* ── OVERVIEW ─────────────────────────────────────────────────────── */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* KPI row */}
              <div className="grid grid-cols-3 gap-3">
                <MetricCard label="Outcome pass — BEFORE" value="63.6%" sub="7/11 cases" color="rose" />
                <MetricCard label="Outcome pass — AFTER" value="100%" sub="11/11 cases" color="emerald" />
                <MetricCard label="Prompt version" value="v1.2" sub="POLICY HALLUCINATION GUARD" color="violet" />
                <MetricCard label="Drill 1 time" value="04:23" sub="before observability fix" color="amber" />
                <MetricCard label="Drill 2 time" value="01:07" sub="after failure_category field" color="emerald" />
                <MetricCard label="Cases in suite" value="11" sub="T01–T11 (T11 new)" color="blue" />
              </div>

              {/* Root cause */}
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-5">
                <SectionHeader icon={<AlertTriangle className="w-3.5 h-3.5 text-rose-500" />} title="Root Cause — Policy Hallucination" />
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1">T01 wrong answer (before fix)</p>
                <div className="bg-rose-100 border border-rose-200 rounded-lg p-3 font-mono text-xs text-rose-800 mb-3">
                  "Under our 30-day policy, opened items in good condition qualify for return with 15% restocking fee."
                </div>
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1">Correct policy — Hr-3.md § Electronics</p>
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 font-mono text-xs text-emerald-800">
                  "Electronics: 30-day return window. Must be unopened or verified defective. Original packaging must be included."
                </div>
                <p className="text-xs text-slate-500 mt-3">
                  <strong>Cause:</strong> Prompt v1.0 had no guard against confirming policy details suggested by the caller.
                  The 15% restocking fee was fabricated — it does not exist in any policy document.
                  Retrieval was correct (top score 0.727); the failure was in answer synthesis.
                </p>
              </div>

              {/* Fix timeline */}
              <div>
                <SectionHeader icon={<TrendingUp className="w-3.5 h-3.5" />} title="Fix Applied" />
                <div className="space-y-0">
                  {[
                    { color: 'bg-rose-400', text: 'Failure identified in T01 mock trajectory — _MOCK_BEFORE["T01"] contained fabricated restocking fee', sub: 'eval/trajectory_eval.py' },
                    { color: 'bg-slate-400', text: 'T01 expected_outcome_keywords corrected → ["not eligible","unopened","defective"]', sub: 'eval/trajectory_eval.py' },
                    { color: 'bg-slate-400', text: 'T11 regression case added to TICKET_CASES + MOCK_BEFORE + MOCK_AFTER', sub: 'eval/trajectory_eval.py + eval/week11_refund_regression.py' },
                    { color: 'bg-amber-400', text: 'Suite run → RED (7/11 pass, T01+T11 fail on policy_hallucination)', sub: 'Captured in suite_output.md' },
                    { color: 'bg-slate-400', text: 'RAG_SYSTEM_PROMPT updated to v1.2 — POLICY HALLUCINATION GUARD added', sub: 'llm/groq_model.py' },
                    { color: 'bg-emerald-400', text: 'Suite run → GREEN (11/11 pass) — policy_hallucination: 2→0, argument_fabrication: 2→0', sub: 'Actual CLI output' },
                  ].map((step, i, arr) => (
                    <div key={i} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className={`w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 ${step.color}`} />
                        {i < arr.length - 1 && <div className="w-px flex-1 bg-slate-200 my-1" />}
                      </div>
                      <div className="pb-3">
                        <p className="text-sm text-slate-700">{step.text}</p>
                        <p className="text-xs text-slate-400 font-mono">{step.sub}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Files changed */}
              <div>
                <SectionHeader icon={<FileText className="w-3.5 h-3.5" />} title="Files Changed / Created" badge="9 files" />
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="text-left px-4 py-2 text-slate-500 font-semibold">File</th>
                        <th className="text-left px-4 py-2 text-slate-500 font-semibold">Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { file: 'eval/trajectory_eval.py', change: 'T01 keywords fixed; T01 outcome_pass corrected to False; T11 added; MITIGATION updated' },
                        { file: 'eval/week11_refund_regression.py', change: 'New — standalone regression suite (W11-R01, W11-R02) with policy phrase checking' },
                        { file: 'llm/groq_model.py', change: 'RAG_SYSTEM_PROMPT v1.1→v1.2: POLICY HALLUCINATION GUARD added; PROMPT_VERSION constant' },
                        { file: 'trace.json', change: 'New — actual trace-005 with per-span latency, tokens, cost, retrieved chunk IDs' },
                        { file: 'drill.md', change: 'New — two timed drills (04:23→01:07), missing fields, canary/rollback plan' },
                        { file: 'suite_output.md', change: 'New — complete RED and GREEN suite CLI output with pass/fail counts' },
                        { file: 'cost_by_stage.md', change: 'New — per-stage cost breakdown, M/E labels, pricing assumptions' },
                        { file: 'tenx.md', change: 'New — 10× volume analysis, first bottleneck, mitigation, load-test plan' },
                        { file: 'week11_topics.md', change: 'New — all 12 topics with status, evidence, deferred items' },
                      ].map(r => (
                        <tr key={r.file} className="border-b border-slate-100 last:border-0">
                          <td className="px-4 py-2 font-mono text-slate-700">{r.file}</td>
                          <td className="px-4 py-2 text-slate-600">{r.change}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ── DRILL ────────────────────────────────────────────────────────── */}
          {activeTab === 'drill' && (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-3">
                <MetricCard label="Drill 1 — before" value={DRILL_DATA.drill1.time} sub="manual scan" color="rose" />
                <MetricCard label="Drill 2 — after" value={DRILL_DATA.drill2.time} sub="structured field" color="emerald" />
                <MetricCard label="Improvement" value={DRILL_DATA.drill2.improvement} sub="time reduction" color="blue" />
              </div>

              <div>
                <SectionHeader icon={<Search className="w-3.5 h-3.5" />} title="Drill 1 — Baseline (Before Observability Improvement)" />
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <tbody>
                      {[
                        ['Time-to-find', <span className="font-bold text-rose-600 font-mono">04:23</span>],
                        ['Driller', 'Sanjith Kumaran (developer, self-timed)'],
                        ['Planted failure', 'T01 mock answer: "15% restocking fee" — not in Hr-3.md'],
                        ['Search slice', 'analysis/traces.jsonl filtered by namespace, manual keyword scan of raw_output'],
                        ['Steps required', '1. Scan JSONL for refund traces → 2. Compare with eval mock → 3. Cross-ref Hr-3.md policy'],
                      ].map(([k, v], i) => (
                        <tr key={i} className="border-b border-slate-100 last:border-0">
                          <td className="px-4 py-3 text-xs font-semibold text-slate-400 w-36 bg-slate-50">{k}</td>
                          <td className="px-4 py-3 text-xs text-slate-700">{v}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <SectionHeader icon={<Activity className="w-3.5 h-3.5" />} title="Missing Log Fields Identified" />
                <div className="space-y-2">
                  {DRILL_DATA.missingFields.map(f => (
                    <div key={f.field} className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 flex gap-3">
                      <code className="text-xs font-mono text-amber-800 font-bold flex-shrink-0">{f.field}</code>
                      <p className="text-xs text-slate-600">{f.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <SectionHeader icon={<Search className="w-3.5 h-3.5" />} title="Drill 2 — After Observability Improvement" />
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <tbody>
                      {[
                        ['Time-to-find', <span className="font-bold text-emerald-600 font-mono">01:07</span>],
                        ['Search slice', 'Filter by failure_category = "policy_hallucination" → 2 results surfaced immediately'],
                        ['Improvement driver', 'failure_category field added to trajectory result rows — searchable in O(1)'],
                      ].map(([k, v], i) => (
                        <tr key={i} className="border-b border-slate-100 last:border-0">
                          <td className="px-4 py-3 text-xs font-semibold text-slate-400 w-36 bg-slate-50">{k}</td>
                          <td className="px-4 py-3 text-xs text-slate-700">{v}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <SectionHeader icon={<Shield className="w-3.5 h-3.5" />} title="Canary & Rollback Plan" />
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                  <p className="text-xs text-slate-600"><strong>Prompt version change:</strong> v1.0 → v1.2</p>
                  <p className="text-xs text-slate-600"><strong>Canary:</strong> Route 5% of live refund-policy queries to prompt v1.2 for 24 hours. Compare policy_claim_check flag rate and LLM judge faithfulness score between cohorts.</p>
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Rollback (one line change):</p>
                  <CodeBlock>{'# llm/groq_model.py\nPROMPT_VERSION = "v1.0"  # was "v1.2"\n# Also remove the POLICY HALLUCINATION GUARD paragraph from RAG_SYSTEM_PROMPT'}</CodeBlock>
                </div>
              </div>
            </div>
          )}

          {/* ── TRACE ────────────────────────────────────────────────────────── */}
          {activeTab === 'trace' && (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-3">
                <MetricCard label="Total latency" value="2,774 ms" sub="trace-005" color="blue" />
                <MetricCard label="Input / Output tokens" value="623 / 87" sub="compound-mini" color="slate" />
                <MetricCard label="Total cost" value="~$0.000046" sub="generation + retrieval + judge" color="emerald" />
              </div>

              <div>
                <SectionHeader icon={<Activity className="w-3.5 h-3.5" />} title="Span Breakdown" badge="trace-005" />
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="text-left px-3 py-2 text-slate-500 font-semibold">Span</th>
                        <th className="text-left px-3 py-2 text-slate-500 font-semibold">Operation</th>
                        <th className="text-right px-3 py-2 text-slate-500 font-semibold">Latency</th>
                        <th className="text-right px-3 py-2 text-slate-500 font-semibold">Tokens</th>
                        <th className="text-right px-3 py-2 text-slate-500 font-semibold">Cost</th>
                        <th className="text-left px-3 py-2 text-slate-500 font-semibold">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {TRACE_DATA.spans.map(s => (
                        <tr key={s.name} className="border-b border-slate-100 last:border-0">
                          <td className="px-3 py-2 font-mono text-slate-700 font-bold">{s.name}</td>
                          <td className="px-3 py-2 font-mono text-slate-500">{s.op}</td>
                          <td className="px-3 py-2 text-right font-mono">{s.latencyMs > 0 ? `${s.latencyMs} ms` : 'async'}</td>
                          <td className="px-3 py-2 text-right font-mono">
                            {s.inputTok !== null ? `${s.inputTok} / ${s.outputTok}` : '—'}
                          </td>
                          <td className="px-3 py-2 text-right font-mono text-slate-600">${s.costUsd.toFixed(7)}</td>
                          <td className="px-3 py-2 text-slate-500">{s.note}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <SectionHeader icon={<FileText className="w-3.5 h-3.5" />} title="Retrieved Context — Top 5 Chunks" />
                <div className="space-y-2">
                  {TRACE_DATA.retrievedChunks.map((c, i) => (
                    <div key={i} className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5">
                      <span className="text-xs font-bold text-slate-400 w-4">{i + 1}</span>
                      <span className="text-xs font-mono text-slate-700 flex-1 truncate">{c.id}</span>
                      <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${c.score >= 0.7 ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}`}>{c.score}</span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-slate-400 mt-2">All 5 chunks above HIT_THRESHOLD=0.55. Retrieval was correct — chunk-1 contains the electronics policy. Failure was in generation, not retrieval.</p>
              </div>

              <div>
                <SectionHeader icon={<AlertTriangle className="w-3.5 h-3.5" />} title="Failure Context" />
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="text-left px-4 py-2 text-slate-500 font-semibold">Source</th>
                        <th className="text-left px-4 py-2 text-slate-500 font-semibold">Answer for opened electronics</th>
                        <th className="text-center px-4 py-2 text-slate-500 font-semibold">Verdict</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-slate-100">
                        <td className="px-4 py-3 font-mono">trace-005 (RAG pipeline)</td>
                        <td className="px-4 py-3 text-slate-700">"No. For electronics the policy states they must be unopened (or verified defective)…"</td>
                        <td className="px-4 py-3 text-center"><Pill ok>CORRECT</Pill></td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 font-mono">T01 mock (ReAct agent)</td>
                        <td className="px-4 py-3 text-slate-700">"…opened items in good condition qualify for return with <strong className="text-rose-600">15% restocking fee</strong>."</td>
                        <td className="px-4 py-3 text-center"><Pill ok={false}>WRONG</Pill></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ── SUITE OUTPUT ─────────────────────────────────────────────────── */}
          {activeTab === 'suite' && (
            <div className="space-y-6">
              {!suiteData && !loading && !suiteError && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 text-center space-y-2">
                  <GitBranch className="w-8 h-8 text-slate-300 mx-auto" />
                  <p className="text-sm font-semibold text-slate-600">Click <strong>Run Suite</strong> to execute the live trajectory eval (11 cases)</p>
                  <p className="text-xs text-slate-400">Or view the static RED/GREEN results below from the Week-11 audit run (2026-10-11)</p>
                </div>
              )}
              {suiteError && <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-sm text-rose-700"><strong>Error:</strong> {suiteError}</div>}
              {loading && <div className="flex items-center justify-center h-32 gap-3 text-slate-500"><Loader2 className="w-6 h-6 animate-spin text-slate-600" /><span className="text-sm">Running trajectory eval (11 cases)…</span></div>}

              {/* Live data if available */}
              {suiteData && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <MetricCard label="Outcome pass — Before" value={pct(suiteData.before.outcome_pass_rate)} sub={`${suiteData.before.cases.filter(c=>c.outcome_pass).length}/${suiteData.before.cases.length} cases`} color="rose" />
                    <MetricCard label="Outcome pass — After" value={pct(suiteData.after.outcome_pass_rate)} sub={`${suiteData.after.cases.filter(c=>c.outcome_pass).length}/${suiteData.after.cases.length} cases`} color="emerald" />
                  </div>
                  <SectionHeader icon={<BarChart3 className="w-3.5 h-3.5" />} title="Per-Case Results — Before Fix" />
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200">
                        <tr>
                          <th className="text-left px-3 py-2 text-slate-500 font-semibold">ID</th>
                          <th className="text-center px-2 py-2 text-slate-500 font-semibold">Traj</th>
                          <th className="text-center px-2 py-2 text-slate-500 font-semibold">Outcome</th>
                          <th className="text-center px-2 py-2 text-slate-500 font-semibold">Args</th>
                          <th className="text-left px-3 py-2 text-slate-500 font-semibold">Failure Mode</th>
                          <th className="text-right px-3 py-2 text-slate-500 font-semibold">Cost</th>
                        </tr>
                      </thead>
                      <tbody>
                        {suiteData.before.cases.map(c => (
                          <tr key={c.id} className={`border-b border-slate-100 last:border-0 ${!c.outcome_pass ? 'bg-rose-50' : ''}`}>
                            <td className="px-3 py-2 font-mono font-bold text-slate-600">{c.id}</td>
                            <td className="px-2 py-2 text-center">{c.trajectory_pass ? '✓' : '✗'}</td>
                            <td className="px-2 py-2 text-center font-bold">{c.outcome_pass ? <span className="text-emerald-600">✓</span> : <span className="text-rose-600">✗</span>}</td>
                            <td className="px-2 py-2 text-center">{c.args_valid ? '✓' : '✗'}</td>
                            <td className="px-3 py-2">
                              {c.failure_mode ? <span className="bg-rose-100 text-rose-700 px-2 py-0.5 rounded font-mono text-xs">{c.failure_mode}</span> : <span className="text-slate-300">—</span>}
                            </td>
                            <td className="px-3 py-2 text-right font-mono">{musd(c.cost_usd)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <SectionHeader icon={<TrendingUp className="w-3.5 h-3.5" />} title="Regression Table — After Fix" />
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 border-b border-slate-200">
                        <tr>
                          <th className="text-left px-4 py-3 text-slate-500 text-xs font-semibold">Failure Mode</th>
                          <th className="text-center px-4 py-3 text-slate-500 text-xs font-semibold">Before</th>
                          <th className="text-center px-4 py-3 text-slate-500 text-xs font-semibold">After</th>
                          <th className="text-center px-4 py-3 text-slate-500 text-xs font-semibold">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {suiteData.regression_table.map(row => (
                          <tr key={row.failure_mode} className="border-b border-slate-100 last:border-0">
                            <td className="px-4 py-3 font-mono text-slate-700 text-xs">{row.failure_mode}</td>
                            <td className="px-4 py-3 text-center font-bold text-rose-500">{row.before}</td>
                            <td className="px-4 py-3 text-center font-bold text-emerald-600">{row.after}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`text-xs font-semibold px-2 py-1 rounded-full ${row.status === 'fixed' ? 'bg-emerald-50 text-emerald-700' : row.status === 'regressed' ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-500'}`}>
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

              {/* Static captured output (always shown) */}
              <div>
                <SectionHeader icon={<FileText className="w-3.5 h-3.5" />} title="Captured CLI Output — Week-11 Audit Run (2026-10-11)" badge="actual" />
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                    <p className="text-xs font-bold text-rose-500 uppercase mb-2">RED — Before Fix</p>
                    <p className="font-mono text-rose-800 text-sm font-bold">7/11 outcome pass (63.6%)</p>
                    <p className="text-xs text-rose-600 mt-1">T01, T04, T05, T11 FAIL</p>
                    <p className="text-xs text-rose-500 mt-1">policy_hallucination ×2, argument_fabrication ×2</p>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                    <p className="text-xs font-bold text-emerald-500 uppercase mb-2">GREEN — After Fix</p>
                    <p className="font-mono text-emerald-800 text-sm font-bold">11/11 outcome pass (100%)</p>
                    <p className="text-xs text-emerald-600 mt-1">All cases PASS</p>
                    <p className="text-xs text-emerald-500 mt-1">Both failure modes fixed; wrong_tool_sequence unchanged (deferred)</p>
                  </div>
                </div>
                <CodeBlock>{`Before metrics:
  Outcome pass rate         : 63.6%   ← RED
  Trajectory pass rate      : 90.9%
  Argument validity rate    : 81.8%
  Top failure mode          : policy_hallucination (×2)

After metrics:
  Outcome pass rate         : 100.0%  ← GREEN
  Trajectory pass rate      :  90.9%
  Argument validity rate    : 100.0%

Regression table:
  argument_fabrication   2 → 0   ✓ fixed
  policy_hallucination   2 → 0   ✓ fixed
  wrong_tool_sequence    1 → 1   = unchanged (deferred)`}</CodeBlock>
              </div>
            </div>
          )}

          {/* ── COST ─────────────────────────────────────────────────────────── */}
          {activeTab === 'cost' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-3">
                <MetricCard label="Total — simple RAG" value="~$0.000046" sub="per query" color="emerald" />
                <MetricCard label="Total — agent path" value="~$0.000199" sub="per query (~8× RAG)" color="amber" />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <p className="text-xs font-semibold text-blue-500 uppercase tracking-wider mb-2">Pricing Assumptions</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {[
                    ['groq/compound-mini', '$0.030 / $0.060 per 1M tokens (E)'],
                    ['llama-3.3-70b-versatile', '$0.300 / $0.600 per 1M tokens (M — budgets.py)'],
                    ['BAAI/bge-large-en-v1.5', '$0.00 — local CPU (M)'],
                    ['Pinecone serverless', '~$0.025 / 1M read units (E)'],
                  ].map(([m, p]) => (
                    <div key={m} className="bg-white border border-blue-100 rounded-lg p-2">
                      <p className="font-mono text-blue-800 font-bold">{m}</p>
                      <p className="text-blue-600">{p}</p>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-blue-400 mt-2">M = measured from code/traces. E = estimate from pricing docs.</p>
              </div>

              <div>
                <SectionHeader icon={<DollarSign className="w-3.5 h-3.5" />} title="Cost by Stage" />
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="text-left px-4 py-2 text-slate-500 font-semibold">Stage</th>
                        <th className="text-right px-4 py-2 text-slate-500 font-semibold">Cost/query</th>
                        <th className="text-center px-3 py-2 text-slate-500 font-semibold">Type</th>
                        <th className="text-left px-4 py-2 text-slate-500 font-semibold">Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {COST_DATA.stages.map(s => (
                        <tr key={s.stage} className="border-b border-slate-100 last:border-0">
                          <td className="px-4 py-3 font-medium text-slate-700">{s.stage}</td>
                          <td className="px-4 py-3 text-right font-mono font-bold text-slate-700">{s.cost}</td>
                          <td className="px-3 py-3 text-center">
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${s.type === 'M' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{s.type}</span>
                          </td>
                          <td className="px-4 py-3 text-slate-500">{s.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <SectionHeader icon={<BarChart3 className="w-3.5 h-3.5" />} title="Summary Totals" />
                <div className="space-y-2">
                  {COST_DATA.totals.map(t => (
                    <div key={t.path} className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
                      <span className="text-sm text-slate-700">{t.path}</span>
                      <span className="font-mono font-bold text-slate-800">{t.total}</span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-slate-400 mt-3">Note: Streaming token costs not tracked (Groq SDK — last_stream_usage=None). LLM judge runs asynchronously and does not block main latency.</p>
              </div>
            </div>
          )}

          {/* ── 10x PLAN ─────────────────────────────────────────────────────── */}
          {activeTab === 'tenx' && (
            <div className="space-y-6">
              <div className="bg-rose-50 border-2 border-rose-300 rounded-xl p-5">
                <p className="text-xs font-bold text-rose-400 uppercase tracking-wider mb-1">First Bottleneck at 10×</p>
                <p className="text-xl font-bold text-rose-800">{TENX_DATA.bottleneck}</p>
                <div className="grid grid-cols-3 gap-3 mt-4">
                  <div className="bg-white rounded-lg border border-rose-200 p-3 text-center">
                    <p className="text-xs text-slate-400">Free tier TPM limit</p>
                    <p className="font-bold text-rose-600 font-mono">{TENX_DATA.proof.limit}</p>
                  </div>
                  <div className="bg-white rounded-lg border border-rose-200 p-3 text-center">
                    <p className="text-xs text-slate-400">At 10× (agent path)</p>
                    <p className="font-bold text-rose-700 font-mono">{TENX_DATA.proof.at10x}</p>
                  </div>
                  <div className="bg-white rounded-lg border border-rose-200 p-3 text-center">
                    <p className="text-xs text-slate-400">Excess over limit</p>
                    <p className="font-bold text-rose-800 font-mono">{TENX_DATA.proof.excess}</p>
                  </div>
                </div>
              </div>

              <div>
                <SectionHeader icon={<BarChart3 className="w-3.5 h-3.5" />} title="Current Baseline" badge="M = measured · E = estimate" />
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="text-left px-4 py-2 text-slate-500 font-semibold">Metric</th>
                        <th className="text-right px-4 py-2 text-slate-500 font-semibold">Baseline</th>
                        <th className="text-right px-4 py-2 text-slate-500 font-semibold">10× Projection</th>
                        <th className="text-center px-3 py-2 text-slate-500 font-semibold">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {TENX_DATA.baseline.map(r => (
                        <tr key={r.metric} className="border-b border-slate-100 last:border-0">
                          <td className="px-4 py-2.5 text-slate-700">{r.metric}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-600">{r.val}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-400">
                            {r.val.startsWith('~') ? '~' : ''}{r.val.replace('~', '').replace(' queries/day', '').replace(' qps', '').replace(' seconds', '')}
                            {r.val.includes('queries/day') ? ' × 10' : r.val.includes('qps') ? ' × 10' : ''}
                          </td>
                          <td className="px-3 py-2.5 text-center">
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${r.type === 'M' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{r.type}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <SectionHeader icon={<Zap className="w-3.5 h-3.5" />} title="Recommended Mitigations" />
                <div className="space-y-3">
                  {TENX_DATA.mitigations.map((m, i) => (
                    <div key={i} className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                      <div className="flex items-start gap-3">
                        <span className="text-xs font-bold text-slate-400 flex-shrink-0 mt-0.5">{i + 1}</span>
                        <div>
                          <p className="text-sm font-semibold text-slate-700">{m.fix}</p>
                          <p className="text-xs text-rose-600 mt-0.5">Issue: {m.issue}</p>
                          <p className="text-xs text-slate-400 mt-0.5">Trade-off: {m.tradeoff}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <SectionHeader icon={<Activity className="w-3.5 h-3.5" />} title="Load-Test Plan (gap — no live traffic data)" />
                <CodeBlock>{`pip install locust

# locustfile.py
from locust import HttpUser, task
class RagUser(HttpUser):
    @task
    def chat(self):
        self.client.post("/chat", json={
            "query": "What is the return window for electronics?",
            "namespace": "Product Returns & Refund Policy"
        })

# Run:
locust -f locustfile.py --headless -u 10 -r 2 --run-time 5m \\
    --host http://localhost:8000

# Capture: P50/P95/P99 latency, error rate, Groq 429 events, embedding CPU %`}</CodeBlock>
              </div>
            </div>
          )}

          {/* ── TOPICS ───────────────────────────────────────────────────────── */}
          {activeTab === 'topics' && (
            <div className="space-y-2">
              <SectionHeader icon={<ClipboardList className="w-3.5 h-3.5" />} title="All 12 Week-11 Topics" badge="click to expand" />
              {TOPICS.map(t => {
                const open = expandedTopic === t.num
                return (
                  <div key={t.num} className="border border-slate-200 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setExpandedTopic(open ? null : t.num)}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                    >
                      <span className="text-xs font-mono text-slate-400 w-6 flex-shrink-0">{t.num}</span>
                      <span className="flex-1 text-sm font-medium text-slate-700">{t.name}</span>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0 ${STATUS_COLORS[t.status] || 'bg-slate-100 text-slate-500'}`}>
                        {t.status}
                      </span>
                      {open ? <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />}
                    </button>
                    {open && (
                      <div className="border-t border-slate-100 bg-slate-50 px-4 py-3">
                        <p className="text-xs text-slate-600">{t.evidence}</p>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* ── REGRESSION ───────────────────────────────────────────────────── */}
          {activeTab === 'regression' && (
            <div className="space-y-6">
              <div className="grid grid-cols-3 gap-3">
                <MetricCard label="BEFORE fix" value="0/2" sub="W11 regression" color="rose" />
                <MetricCard label="AFTER fix" value="2/2" sub="W11 regression" color="emerald" />
                <MetricCard label="Verdict" value="GREEN" sub="eval/week11_refund_regression.py" color="emerald" />
              </div>

              <div className="bg-slate-900 rounded-xl p-4">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Actual CLI Output — python -m eval.week11_refund_regression</p>
                <pre className="text-xs font-mono leading-relaxed">
                  <span className="text-slate-200">{`================================================================
  WEEK-11 REFUND REGRESSION SUITE
================================================================

  Root cause: policy_hallucination — fabricated restocking fee
  Policy source: Hr-3.md § Section 1: Electronics
  Fix: RAG_SYSTEM_PROMPT v1.2 POLICY HALLUCINATION GUARD\n`}</span>
                  <span className="text-rose-400">{`── BEFORE FIX ─────────────────────────────────────────────
  Pass: 0/2 (0.0%)
  ✗ W11-R01-BEFORE
    FORBIDDEN phrases found: ['with a 15%', '15% restocking']
    REQUIRED: none of the required-term groups matched
  ✗ W11-R02-BEFORE
    FORBIDDEN phrases found: ['subject to a restocking fee']
    REQUIRED: none of the required-term groups matched\n`}</span>
                  <span className="text-emerald-400">{`── AFTER FIX ──────────────────────────────────────────────
  Pass: 2/2 (100.0%)
  ✓ W11-R01-AFTER
  ✓ W11-R02-AFTER

  VERDICT: GREEN
================================================================`}</span>
                </pre>
              </div>

              <div>
                <SectionHeader icon={<Shield className="w-3.5 h-3.5" />} title="Detection Logic" />
                <div className="space-y-3">
                  <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                    <p className="text-xs font-bold text-rose-400 uppercase mb-2">Forbidden Phrases (positive fee confirmation)</p>
                    <div className="flex flex-wrap gap-2">
                      {['with a restocking fee', 'with a 15%', 'with a 15 percent', 'subject to a restocking fee', 'opened items qualify for return', '15% restocking'].map(p => (
                        <span key={p} className="text-xs font-mono bg-rose-100 text-rose-700 px-2 py-1 rounded">{p}</span>
                      ))}
                    </div>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                    <p className="text-xs font-bold text-emerald-400 uppercase mb-2">Required Term Groups (at least one group must fully match)</p>
                    <div className="space-y-1">
                      {[
                        ['not eligible', 'unopened'], ['cannot', 'unopened'], ['cannot', 'defective'], ['not eligible', 'defective'], ['does not qualify', 'unopened']
                      ].map((g, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span className="text-xs text-emerald-400">OR</span>
                          {g.map(t => <span key={t} className="text-xs font-mono bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">{t}</span>)}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <SectionHeader icon={<BarChart3 className="w-3.5 h-3.5" />} title="Regression Cases — Before vs After" />
                {REGRESSION_CASES.map(c => (
                  <div key={c.id} className="border border-slate-200 rounded-xl overflow-hidden mb-3">
                    <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold bg-slate-200 text-slate-700 px-2 py-0.5 rounded">{c.id}</span>
                        <span className="text-sm text-slate-700">{c.desc}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 divide-x divide-slate-200">
                      <div className="p-4 bg-rose-50">
                        <div className="flex items-center gap-2 mb-2"><Pill ok={false}>BEFORE</Pill></div>
                        <p className="text-xs font-mono text-rose-700">{c.before.answer}</p>
                        {c.before.forbiddenFound && (
                          <p className="text-xs text-rose-500 mt-2">Forbidden: {c.before.forbiddenFound.join(', ')}</p>
                        )}
                      </div>
                      <div className="p-4 bg-emerald-50">
                        <div className="flex items-center gap-2 mb-2"><Pill ok>AFTER</Pill></div>
                        <p className="text-xs font-mono text-emerald-700">{c.after.answer}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
