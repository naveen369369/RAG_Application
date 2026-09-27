import { useState, useEffect } from 'react'
import {
  Server,
  History,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  User,
  ShieldAlert,
  ArrowRight,
  Code2,
  Copy,
  Check,
  RefreshCw,
  Search,
  Bot,
  ExternalLink,
  Layers,
  Sparkles,
  FileCode2,
  FileText,
  GitCompare,
  Shield,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
} from 'lucide-react'
import { fetchMcpServers, fetchMcpTicketHistory, fetchMcpWire, fetchMcpArtifacts } from '../../api/mcp'

const ACTION_COLORS = {
  opened: 'bg-blue-50 text-blue-700 border-blue-200',
  escalated: 'bg-rose-50 text-rose-700 border-rose-200 font-semibold',
  approved_replacement: 'bg-amber-50 text-amber-800 border-amber-200 font-semibold',
  replacement_shipped: 'bg-indigo-50 text-indigo-700 border-indigo-200 font-semibold',
  resolved: 'bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold',
  pending_customer: 'bg-slate-100 text-slate-700 border-slate-200',
}

const ACTOR_ICONS = {
  system: Layers,
  'billing-bot': Bot,
}

// ── Artifact inner-tab definitions ─────────────────────────────────────────
const ARTIFACT_TABS = [
  {
    key: 'tool_counts',
    label: 'Tool Count Log',
    icon: FileText,
    color: 'text-violet-600',
    bg: 'bg-violet-50',
    border: 'border-violet-200',
    activeBg: 'bg-violet-600',
    description: 'Detailed breakdown comparing Server 1 (9 tools) vs Server 2 (2 tools) totaling 11 tools',
  },
  {
    key: 'config_diff',
    label: 'Config Diff',
    icon: FileCode2,
    color: 'text-indigo-600',
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    activeBg: 'bg-indigo-600',
    description: 'Shows mcp_config.py diff registering both Server 1 (In-Process) and Server 2 (HTTP/SSE)',
  },
  {
    key: 'agent_diff',
    label: 'Agent Diff',
    icon: GitCompare,
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    activeBg: 'bg-emerald-600',
    description: 'Proves 0 lines changed in react_agent.py across both Server 1 and Server 2 integrations',
  },
  {
    key: 'error_before_after',
    label: 'Error Before / After',
    icon: AlertTriangle,
    color: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    activeBg: 'bg-amber-600',
    description: 'BEFORE vs AFTER recoverable error comparison for both Server 1 and Server 2',
  },
  {
    key: 'risk_note',
    label: 'Supply-Chain Risk',
    icon: Shield,
    color: 'text-rose-600',
    bg: 'bg-rose-50',
    border: 'border-rose-200',
    activeBg: 'bg-rose-600',
    description: '5-line risk assessment contrasting Server 1 (CRM/RAG) vs Server 2 (Audit/SSE) boundaries',
  },
]

// ── Simple markdown renderer for headers + code blocks ────────────────────
function ArtifactContent({ content, fileKey }) {
  if (!content) return <span className="text-slate-400 text-xs italic">Loading…</span>

  // risk_note.md: render each line with side-by-side Server 1 vs Server 2 pills
  if (fileKey === 'risk_note') {
    const lines = content.trim().split('\n').filter(Boolean)
    return (
      <div className="space-y-3">
        {lines.map((line, idx) => {
          const colonIdx = line.indexOf(':')
          const label = colonIdx > -1 ? line.slice(0, colonIdx) : `Dimension ${idx + 1}`
          const value = colonIdx > -1 ? line.slice(colonIdx + 1).trim() : line
          const parts = value.split(' | ')
          const s1Part = parts[0]?.replace(/^\[Server 1\]\s*/i, '') || ''
          const s2Part = parts[1]?.replace(/^\[Server 2\]\s*/i, '') || ''

          return (
            <div key={idx} className="bg-white rounded-xl border border-rose-100 p-3.5 shadow-xs space-y-2">
              <span className="text-[11px] font-bold text-rose-700 uppercase tracking-wider block">
                {label}
              </span>
              {parts.length === 2 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                  <div className="bg-emerald-50/70 border border-emerald-200 rounded-lg p-2.5">
                    <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wide block mb-1">
                      MCP Server 1 (CRM &amp; Local)
                    </span>
                    <span className="text-slate-700 leading-relaxed text-[11px]">{s1Part}</span>
                  </div>
                  <div className="bg-indigo-50/70 border border-indigo-200 rounded-lg p-2.5">
                    <span className="text-[10px] font-bold text-indigo-800 uppercase tracking-wide block mb-1">
                      MCP Server 2 (Escalation &amp; Remote)
                    </span>
                    <span className="text-slate-700 leading-relaxed text-[11px]">{s2Part}</span>
                  </div>
                </div>
              ) : (
                <span className="text-xs text-slate-700 leading-relaxed">{value}</span>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  // agent_diff.txt: show as styled diff block with Server 1 and Server 2 highlighting
  if (fileKey === 'agent_diff') {
    return (
      <div className="bg-slate-950 rounded-xl border border-slate-700 p-4 font-mono text-xs space-y-1 overflow-x-auto">
        {content.trim().split('\n').map((line, i) => {
          const isComment = line.startsWith('#')
          const isS1 = line.includes('Server 1')
          const isS2 = line.includes('Server 2')
          return (
            <div
              key={i}
              className={
                isS1
                  ? 'text-emerald-300 font-semibold'
                  : isS2
                  ? 'text-indigo-300 font-semibold'
                  : isComment
                  ? 'text-slate-400'
                  : line.startsWith('+')
                  ? 'text-emerald-400'
                  : line.startsWith('-')
                  ? 'text-rose-400'
                  : 'text-slate-300'
              }
            >
              {line || '\u00a0'}
            </div>
          )
        })}
      </div>
    )
  }

  // config_diff.txt: syntax-highlighted diff
  if (fileKey === 'config_diff') {
    return (
      <div className="bg-slate-950 rounded-xl border border-slate-700 p-4 font-mono text-xs space-y-0.5 overflow-x-auto">
        {content.trim().split('\n').map((line, i) => {
          const isS1Header = line.includes('MCP SERVER 1')
          const isS2Header = line.includes('MCP SERVER 2')
          const isPlus = line.trimStart().startsWith('+')
          const isMinus = line.trimStart().startsWith('-')
          const isComment = line.startsWith('#')

          return (
            <div
              key={i}
              className={
                isS1Header
                  ? 'text-emerald-300 font-bold bg-emerald-950/60 px-2 py-0.5 rounded mt-2'
                  : isS2Header
                  ? 'text-indigo-300 font-bold bg-indigo-950/60 px-2 py-0.5 rounded mt-2'
                  : isComment
                  ? 'text-slate-500 italic'
                  : isPlus
                  ? 'text-emerald-400 bg-emerald-950/30 px-1 rounded'
                  : isMinus
                  ? 'text-rose-400 bg-rose-950/30 px-1 rounded'
                  : 'text-slate-300'
              }
            >
              {line || '\u00a0'}
            </div>
          )
        })}
      </div>
    )
  }

  // tool_counts.txt: styled list differentiating Server 1 (emerald) and Server 2 (indigo)
  if (fileKey === 'tool_counts') {
    return (
      <div className="bg-slate-950 rounded-xl border border-slate-700 p-4 font-mono text-xs space-y-0.5 overflow-x-auto">
        {content.trim().split('\n').map((line, i) => {
          const isDivider = line.startsWith('====') || line.startsWith('----')
          const isS1Header = line.includes('MCP SERVER 1')
          const isS2Header = line.includes('MCP SERVER 2')
          const isS1Tool = line.includes('[MCP Server 1')
          const isS2Tool = line.includes('[MCP Server 2')
          const isBefore = line.startsWith('BEFORE')
          const isAfter = line.startsWith('AFTER')
          const isFeature = line.startsWith('Feature') || line.startsWith('Server ID') || line.startsWith('Domain') || line.startsWith('Tool Count')

          return (
            <div
              key={i}
              className={
                isS1Header
                  ? 'text-emerald-400 font-bold text-sm bg-emerald-950/50 px-2 py-1 rounded my-1'
                  : isS2Header
                  ? 'text-indigo-400 font-bold text-sm bg-indigo-950/50 px-2 py-1 rounded my-1'
                  : isDivider
                  ? 'text-slate-700'
                  : isS1Tool
                  ? 'text-emerald-300'
                  : isS2Tool
                  ? 'text-indigo-300 font-semibold'
                  : isBefore
                  ? 'text-amber-400 font-bold'
                  : isAfter
                  ? 'text-cyan-400 font-bold'
                  : isFeature
                  ? 'text-violet-300 font-semibold'
                  : 'text-slate-300'
              }
            >
              {line || '\u00a0'}
            </div>
          )
        })}
      </div>
    )
  }

  // error_before_after.md: render with markdown-like styling + table support
  return (
    <div className="space-y-1 text-xs font-mono">
      {content.trim().split('\n').map((line, i) => {
        if (line.startsWith('# '))
          return <h3 key={i} className="text-sm font-bold text-slate-800 mt-3 mb-1">{line.slice(2)}</h3>
        if (line.startsWith('## '))
          return <h4 key={i} className="text-xs font-bold text-indigo-700 mt-3 mb-1 uppercase tracking-wide">{line.slice(3)}</h4>
        if (line.startsWith('### '))
          return <h5 key={i} className="text-xs font-semibold text-slate-700 mt-2">{line.slice(4)}</h5>
        if (line.startsWith('```'))
          return null
        if (line.startsWith('|')) {
          const cells = line.split('|').map(c => c.trim()).filter(Boolean)
          const isHeader = line.includes('---')
          if (isHeader) return null
          return (
            <div key={i} className="grid grid-cols-3 gap-2 bg-slate-100 p-1.5 rounded font-mono text-[11px] text-slate-800">
              {cells.map((cell, cIdx) => (
                <span key={cIdx} className={cIdx === 0 ? 'font-bold text-slate-900' : 'text-slate-700'}>
                  {cell.replace(/\*\*/g, '')}
                </span>
              ))}
            </div>
          )
        }
        if (line.startsWith('* **') || line.startsWith('- **'))
          return <p key={i} className="text-slate-600 pl-2 border-l-2 border-indigo-200 leading-relaxed">{line.replace(/\*\*/g, '')}</p>
        if (line.startsWith('> '))
          return <blockquote key={i} className="bg-emerald-50 border-l-4 border-emerald-400 px-3 py-1.5 text-emerald-800 rounded-r-lg italic">{line.slice(2)}</blockquote>
        if (line === '---') return <hr key={i} className="border-slate-200 my-2" />
        return <p key={i} className={`text-slate-600 leading-relaxed ${line === '' ? 'h-2' : ''}`}>{line}</p>
      })}
    </div>
  )
}

export default function McpHistoryTab({ initialTicketId = 'TCK-1004', dbTickets = [], onAskAgent }) {
  const [ticketId, setTicketId] = useState(initialTicketId)
  const [searchInput, setSearchInput] = useState(initialTicketId)
  const [loading, setLoading] = useState(false)
  const [serverInfo, setServerInfo] = useState(null)
  const [historyData, setHistoryData] = useState(null)
  const [wireData, setWireData] = useState(null)
  const [artifacts, setArtifacts] = useState(null)
  const [activeWireStep, setActiveWireStep] = useState(2)
  const [copiedWire, setCopiedWire] = useState(false)
  const [showWire, setShowWire] = useState(false)
  const [activeArtifactTab, setActiveArtifactTab] = useState('tool_counts')
  const [showArtifacts, setShowArtifacts] = useState(true)
  const [expandedServer, setExpandedServer] = useState(null) // null | 'server1' | 'server2'

  useEffect(() => {
    if (initialTicketId) {
      setTicketId(initialTicketId)
      setSearchInput(initialTicketId)
    }
  }, [initialTicketId])

  useEffect(() => {
    loadServerData()
  }, [])

  useEffect(() => {
    if (ticketId) loadTicketHistory(ticketId)
  }, [ticketId])

  const loadServerData = async () => {
    try {
      const [servers, wire, arts] = await Promise.all([
        fetchMcpServers(),
        fetchMcpWire(),
        fetchMcpArtifacts(),
      ])
      setServerInfo(servers)
      setWireData(wire?.wire)
      setArtifacts(arts)
    } catch (err) {
      console.error('Failed to load MCP server info:', err)
    }
  }

  const loadTicketHistory = async (id) => {
    setLoading(true)
    try {
      const data = await fetchMcpTicketHistory(id)
      setHistoryData(data)
    } catch (err) {
      console.error('Failed to fetch ticket history:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    if (!searchInput.trim()) return
    setTicketId(searchInput.trim().toUpperCase())
  }

  const handlePresetSelect = (id) => {
    setSearchInput(id)
    setTicketId(id)
  }

  const copyJson = (data) => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    setCopiedWire(true)
    setTimeout(() => setCopiedWire(false), 2000)
  }

  const ticket = historyData?.ticket || {}
  const history = historyData?.history?.history || []
  const isRecoverable = historyData?.is_recoverable_error || false
  const conversations = wireData?.conversations || []

  const currentArtifactTab = ARTIFACT_TABS.find(t => t.key === activeArtifactTab)

  // Extract server entries from API response
  const server1 = serverInfo?.servers?.find(s => s.server_id === 'crm-agent-server-v1')
  const server2 = serverInfo?.servers?.find(s => s.server_id === 'ticket-history-v2')

  // Category colors for tool badges
  const categoryColors = {
    'CRM':           'bg-cyan-500/20 text-cyan-200 border-cyan-500/30',
    'RAG / Documents': 'bg-violet-500/20 text-violet-200 border-violet-500/30',
    'Admin':         'bg-amber-500/20 text-amber-200 border-amber-500/30',
    'Ticket Audit':  'bg-indigo-500/20 text-indigo-200 border-indigo-500/30',
  }

  const ToolBadge = ({ name, category }) => (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono border ${categoryColors[category] || 'bg-slate-500/20 text-slate-200 border-slate-500/30'}`}>
      {name}
    </span>
  )

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-8">

      {/* ── 1. MCP Architecture Header ────────────────────────────────────────── */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl p-5 shadow-xl border border-slate-700/60 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-transparent to-indigo-500/5 pointer-events-none rounded-2xl" />

        {/* Header row */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-slate-700 border border-slate-600 flex items-center justify-center">
              <Server className="w-5 h-5 text-slate-300" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">MCP Server Architecture</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {serverInfo ? `${serverInfo.total_servers} Servers · ${serverInfo.total_tools} Total Tools` : 'Loading…'}
              </p>
            </div>
          </div>
          <button
            onClick={loadServerData}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            title="Refresh server status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Two-server grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* ── Server 1: CRM Agent Server ──────────────────────────────────── */}
          <div className="bg-gradient-to-br from-cyan-950/60 to-slate-900 rounded-xl border border-cyan-700/40 p-4 relative">
            <div className="absolute top-3 right-3">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Online · In-Process
              </span>
            </div>

            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center">
                <span className="text-base font-black text-cyan-400">1</span>
              </div>
              <div>
                <p className="text-sm font-bold text-cyan-300">CRM Agent Server</p>
                <p className="text-[10px] text-slate-400">Local · FastAPI in-process · No port</p>
              </div>
            </div>

            {/* Tool count */}
            <div className="flex items-baseline gap-2 mb-3">
              <span className="text-2xl font-black text-cyan-400">{server1?.tool_count ?? 9}</span>
              <span className="text-xs text-slate-400">tools registered</span>
            </div>

            {/* Tool categories */}
            <div className="space-y-2">
              {Object.entries(server1?.tool_categories || {
                'CRM': ['ticket_lookup', 'order_lookup', 'customer_lookup'],
                'RAG / Documents': ['rag_retrieval', 'route_namespace', 'summarize_document', 'multi_namespace_search', 'inspect_documents'],
                'Admin': ['run_evaluation'],
              }).map(([cat, tools]) => (
                <div key={cat}>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1">{cat}</p>
                  <div className="flex flex-wrap gap-1">
                    {tools.map(t => <ToolBadge key={t} name={t} category={cat} />)}
                  </div>
                </div>
              ))}
            </div>

            {/* Transport */}
            <div className="mt-3 pt-3 border-t border-slate-700/50 flex items-center gap-2 text-[10px] text-slate-500">
              <span className="px-1.5 py-0.5 rounded bg-slate-700 font-mono text-slate-300">local</span>
              <span>No TCP · Auth: None · Always available</span>
            </div>
          </div>

          {/* ── Server 2: Ticket History Server ─────────────────────────────── */}
          <div className={`bg-gradient-to-br from-indigo-950/60 to-slate-900 rounded-xl border p-4 relative transition-all ${
            server2?.status === 'online' ? 'border-indigo-700/40' : 'border-rose-700/40'
          }`}>
            <div className="absolute top-3 right-3">
              {server2?.status === 'online' ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Online · Port 8100
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  Offline
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
                <span className="text-base font-black text-indigo-400">2</span>
              </div>
              <div>
                <p className="text-sm font-bold text-indigo-300">TicketHistoryServer</p>
                <p className="text-[10px] text-slate-400">Remote · HTTP/SSE · Bearer Token Auth</p>
              </div>
            </div>

            {/* Tool count */}
            <div className="flex items-baseline gap-2 mb-3">
              <span className="text-2xl font-black text-indigo-400">{server2?.tool_count ?? 2}</span>
              <span className="text-xs text-slate-400">tools discovered</span>
            </div>

            {/* Tool categories */}
            <div className="space-y-2">
              {Object.entries(server2?.tool_categories || { 'Ticket Audit': ['get_ticket', 'get_escalation_history'] }).map(([cat, tools]) => (
                <div key={cat}>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1">{cat}</p>
                  <div className="flex flex-wrap gap-1">
                    {tools.map(t => <ToolBadge key={t} name={t} category={cat} />)}
                  </div>
                </div>
              ))}
            </div>

            {/* Transport */}
            <div className="mt-3 pt-3 border-t border-slate-700/50 flex items-center gap-2 text-[10px] text-slate-500">
              <span className="px-1.5 py-0.5 rounded bg-slate-700 font-mono text-slate-300">HTTP/SSE</span>
              <span>FastMCP · Bearer Token · Reads DB directly</span>
            </div>

            {/* Start command hint if offline */}
            {server2?.status !== 'online' && (
              <div className="mt-2 p-2 bg-rose-950/40 rounded-lg border border-rose-700/30">
                <p className="text-[10px] text-rose-400 font-mono">$ python mcp/ticket_history_server.py</p>
              </div>
            )}
          </div>
        </div>

        {/* Total tools summary bar */}
        <div className="mt-4 flex items-center justify-between bg-white/5 rounded-xl px-4 py-2.5 border border-white/10">
          <span className="text-xs text-slate-400">Total agent tool pool</span>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-300"><span className="font-bold text-cyan-400">9</span> Server 1</span>
            <span className="text-slate-600">+</span>
            <span className="text-xs text-slate-300"><span className="font-bold text-indigo-400">2</span> Server 2</span>
            <span className="text-slate-600">=</span>
            <span className="text-sm font-black text-white">{serverInfo?.total_tools ?? 11} Tools</span>
          </div>
          <button
            onClick={() => setShowWire(!showWire)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition-all ${
              showWire
                ? 'bg-indigo-600 text-white border-indigo-500'
                : 'bg-white/10 hover:bg-white/15 text-indigo-200 border-white/10'
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>{showWire ? 'Hide JSON-RPC' : 'Inspect JSON-RPC 2.0'}</span>
          </button>
        </div>
      </div>

      {/* ── 2. JSON-RPC 2.0 Wire Inspector (Collapsible) ─────────────────────── */}
      {showWire && wireData && (
        <div className="bg-slate-900 text-slate-100 rounded-2xl p-5 border border-slate-700 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-indigo-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                Live JSON-RPC 2.0 Protocol Wire Exchange
              </h4>
            </div>
            <button
              onClick={() => copyJson(conversations[activeWireStep] || wireData)}
              className="flex items-center gap-1 text-xs text-slate-300 hover:text-white bg-slate-800 px-2.5 py-1 rounded-lg transition-colors border border-slate-700"
            >
              {copiedWire ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedWire ? 'Copied' : 'Copy JSON'}</span>
            </button>
          </div>

          {/* Step selector */}
          <div className="flex flex-wrap gap-2">
            {conversations.map((c, idx) => {
              const label =
                idx === 0 ? '1. initialize'
                : idx === 1 ? '2. tools/list'
                : idx === 2 ? '3. tools/call: escalation_history'
                : '4. tools/call: bad_ticket (error)'
              return (
                <button
                  key={idx}
                  onClick={() => setActiveWireStep(idx)}
                  className={`text-xs px-3 py-1.5 rounded-xl font-medium transition-all ${
                    activeWireStep === idx
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60'
                  }`}
                >
                  {label}
                </button>
              )
            })}
          </div>

          {/* Request / Response panels */}
          {conversations[activeWireStep] && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div className="space-y-1.5">
                <span className="text-[11px] text-indigo-400 font-bold tracking-wider uppercase block">
                  &rarr; Host Request (JSON-RPC)
                </span>
                <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 max-h-72 overflow-y-auto">
                  <pre className="text-indigo-200 whitespace-pre-wrap">
                    {JSON.stringify(conversations[activeWireStep].request, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="text-[11px] text-emerald-400 font-bold tracking-wider uppercase block">
                  &larr; Server 2 Response (JSON-RPC)
                </span>
                <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 max-h-72 overflow-y-auto">
                  <pre className="text-emerald-300 whitespace-pre-wrap">
                    {JSON.stringify(conversations[activeWireStep].response, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Field annotations */}
          {conversations[activeWireStep]?.field_annotations && (
            <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
              <span className="font-semibold text-slate-300 block mb-1">Top-Level Field Annotations:</span>
              {Object.entries(conversations[activeWireStep].field_annotations).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <code className="text-indigo-400 font-mono font-bold flex-shrink-0">{k}:</code>
                  <span>{v}</span>
                </div>
              ))}
              {conversations[activeWireStep]?.architecture_note && (
                <div className="mt-2 pt-2 border-t border-slate-800 flex gap-2 text-amber-300">
                  <span className="font-semibold flex-shrink-0">Architecture:</span>
                  <span>{conversations[activeWireStep].architecture_note}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── 3. Deliverable Artifacts Panel ───────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setShowArtifacts(a => !a)}
          className="w-full flex items-center justify-between px-5 py-4 bg-gradient-to-r from-slate-50 to-white border-b border-slate-100 hover:bg-slate-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <div className="text-left">
              <span className="text-sm font-bold text-slate-800 block">Week-9 Deliverable Artifacts (Server 1 vs Server 2 Differentiated)</span>
              <span className="text-[11px] text-slate-500">Tool Counts · Config Diff · Agent Diff · Error Recovery · Supply-Chain Risk</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-bold">5 files</span>
            {showArtifacts ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
          </div>
        </button>

        {showArtifacts && (
          <div className="flex">
            {/* Sidebar tabs */}
            <div className="w-44 flex-shrink-0 border-r border-slate-100 bg-slate-50/60 py-2">
              {ARTIFACT_TABS.map(tab => {
                const Icon = tab.icon
                const isActive = activeArtifactTab === tab.key
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveArtifactTab(tab.key)}
                    className={`w-full flex items-center gap-2 px-3 py-2.5 text-left transition-all ${
                      isActive
                        ? 'bg-white border-r-2 border-indigo-500 shadow-sm'
                        : 'hover:bg-white/70 border-r-2 border-transparent'
                    }`}
                  >
                    <div className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isActive ? tab.bg : 'bg-slate-100'
                    }`}>
                      <Icon className={`w-3.5 h-3.5 ${isActive ? tab.color : 'text-slate-400'}`} />
                    </div>
                    <span className={`text-[11px] font-semibold leading-tight ${isActive ? 'text-slate-800' : 'text-slate-500'}`}>
                      {tab.label}
                    </span>
                  </button>
                )
              })}
            </div>

            {/* Content pane */}
            <div className="flex-1 min-w-0 p-4 overflow-auto max-h-[500px]">
              {currentArtifactTab && (
                <>
                  {/* Tab header */}
                  <div className={`flex items-start gap-3 p-3 rounded-xl border mb-4 ${currentArtifactTab.bg} ${currentArtifactTab.border}`}>
                    <div className="w-7 h-7 rounded-lg bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
                      {(() => { const Icon = currentArtifactTab.icon; return <Icon className={`w-4 h-4 ${currentArtifactTab.color}`} /> })()}
                    </div>
                    <div>
                      <span className={`text-xs font-bold block ${currentArtifactTab.color}`}>{currentArtifactTab.label}</span>
                      <span className="text-[11px] text-slate-600 leading-tight">{currentArtifactTab.description}</span>
                    </div>
                  </div>

                  {/* File content */}
                  {artifacts
                    ? <ArtifactContent content={artifacts[currentArtifactTab.key]} fileKey={currentArtifactTab.key} />
                    : (
                      <div className="flex items-center gap-2 text-slate-400 text-xs py-8 justify-center">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Loading artifacts…</span>
                      </div>
                    )
                  }
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── 4. Ticket Search & Preset Bar ────────────────────────────────────── */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm space-y-3">
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Enter Ticket ID (e.g. TCK-1004, TCK-1001, TCK-1002, or invalid TCK-9999)"
              className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono font-semibold text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition-colors flex items-center gap-1.5"
          >
            {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <History className="w-3.5 h-3.5" />}
            <span>Fetch History</span>
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] text-slate-400 font-medium">Database Tickets:</span>
          {[
            { id: 'TCK-1004', label: 'TCK-1004 (Tax Invoices · Escalated · 4 Events)', rose: false },
            { id: 'TCK-1001', label: 'TCK-1001 (Headphones Refund · Open · 2 Events)', rose: false },
            { id: 'TCK-1002', label: 'TCK-1002 (Address Change · In Progress · 2 Events)', rose: false },
            { id: 'TCK-1003', label: 'TCK-1003 (Damaged Box · Open · 2 Events)', rose: false },
            { id: 'TCK-9999', label: 'TCK-9999 (Test Invalid / Recoverable Error)', rose: true },
          ].map(({ id, label, rose }) => (
            <button
              key={id}
              type="button"
              onClick={() => handlePresetSelect(id)}
              className={`text-xs px-2.5 py-1 rounded-lg border font-mono transition-all ${
                ticketId === id
                  ? rose ? 'bg-rose-50 border-rose-300 text-rose-700 font-bold' : 'bg-indigo-50 border-indigo-300 text-indigo-700 font-bold'
                  : rose ? 'bg-rose-50/50 border-rose-200 text-rose-600 hover:bg-rose-50' : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── 5. Recoverable Error Display ─────────────────────────────────────── */}
      {isRecoverable && (
        <div className="bg-rose-50 border-2 border-rose-200 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-rose-100 text-rose-600 flex items-center justify-center flex-shrink-0 mt-0.5">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div className="space-y-1 flex-1">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-rose-900">Structured Recoverable Model Error</h4>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-200 text-rose-800 font-mono font-bold">
                  {ticket.error || 'TICKET_NOT_FOUND'}
                </span>
              </div>
              <p className="text-xs text-rose-800 leading-relaxed font-mono bg-white/80 p-2.5 rounded-lg border border-rose-200">
                "{ticket.message}"
              </p>
            </div>
          </div>

          <div className="bg-white/90 rounded-xl p-3.5 border border-rose-100 text-xs text-slate-700 space-y-1.5">
            <span className="font-bold text-rose-900 block flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              How the Agent LLM Recovers Gracefully:
            </span>
            <p className="leading-relaxed">
              Instead of throwing an unhandled runtime crash (e.g. <code>Error 3</code> or <code>500</code>), Server 2 returns a domain-specific hint explaining ticket formatting (<code>TCK-nnnn</code>). The agent LLM reads this guidance and informs the customer cleanly:
            </p>
            <div className="italic bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-slate-600">
              "I searched our database, but ticket <strong>{ticketId}</strong> was not found. Ticket IDs follow the format TCK-nnnn (for example, TCK-1004). Could you please verify your ticket number?"
            </div>
          </div>
        </div>
      )}

      {/* ── 6. Ticket Summary Card ────────────────────────────────────────────── */}
      {!isRecoverable && ticket.found && (
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200">
                {ticket.id}
              </span>
              <h4 className="text-sm font-bold text-slate-800">{ticket.subject}</h4>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[11px] px-2.5 py-0.5 rounded-full border uppercase font-bold tracking-wider ${
                ticket.priority === 'high' ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}>
                {ticket.priority} Priority
              </span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-semibold uppercase">
                {ticket.status}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-slate-400 block text-[11px]">Customer ID</span>
              <span className="font-semibold text-slate-700">{ticket.customer_id}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Category</span>
              <span className="font-semibold text-slate-700 capitalize">{ticket.category}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Created At</span>
              <span className="font-semibold text-slate-700">{ticket.created_at?.split('T')[0]}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Resolution Notes</span>
              <span className="font-medium text-slate-600 truncate block">
                {ticket.resolution_notes || 'Pending resolution'}
              </span>
            </div>
          </div>

          {onAskAgent && (
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() =>
                  onAskAgent(
                    `Please inspect the escalation history for ticket ${ticket.id} and summarize the key actions taken and final resolution.`
                  )
                }
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white shadow-sm transition-colors"
              >
                <Bot className="w-3.5 h-3.5" />
                <span>Ask ReAct Agent About This History</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── 7. Escalation Timeline ───────────────────────────────────────────── */}
      {!isRecoverable && history.length > 0 && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-indigo-600" />
              <h4 className="text-sm font-bold text-slate-800">
                Audit Trail &amp; Chronological Escalation History ({history.length} Events)
              </h4>
            </div>
            <span className="text-xs text-slate-400 font-mono">Queried via get_escalation_history</span>
          </div>

          <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-indigo-100">
            {history.map((event, idx) => {
              const Icon = ACTOR_ICONS[event.actor] || User
              return (
                <div key={idx} className="relative group">
                  <div className="absolute -left-6 top-1.5 w-5 h-5 rounded-full bg-white border-2 border-indigo-600 flex items-center justify-center text-[10px] font-bold text-indigo-600 shadow-xs">
                    {idx + 1}
                  </div>
                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/20 transition-all space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="flex items-center gap-1 text-xs font-bold text-slate-800 bg-white px-2 py-0.5 rounded-md border border-slate-200">
                          <Icon className="w-3 h-3 text-indigo-600" />
                          {event.actor}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-md border uppercase font-bold tracking-wider ${
                          ACTION_COLORS[event.action] || 'bg-slate-200 text-slate-700'
                        }`}>
                          {event.action.replace('_', ' ')}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {event.timestamp}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed font-medium bg-white p-2.5 rounded-lg border border-slate-100">
                      {event.note}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
