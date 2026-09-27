import {
  Wrench,
  CheckCircle2,
  Loader2,
  ExternalLink,
  Database,
  History,
  Ticket,
  Package,
  User,
  FileText,
  Layers,
  Server,
} from 'lucide-react'

// Map tool names to user-friendly categories and metadata
export function getToolMeta(toolName = '') {
  const name = toolName.toLowerCase()

  if (name === 'ticket_lookup') {
    return {
      category: 'CRM Ticket',
      typeLabel: 'CRM Database',
      icon: Ticket,
      badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      pillColor: 'bg-emerald-100 text-emerald-800',
    }
  }
  if (name === 'order_lookup') {
    return {
      category: 'CRM Order',
      typeLabel: 'CRM Database',
      icon: Package,
      badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      pillColor: 'bg-indigo-100 text-indigo-800',
    }
  }
  if (name === 'customer_lookup') {
    return {
      category: 'Customer Profile',
      typeLabel: 'CRM & SLA Tier',
      icon: User,
      badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
      pillColor: 'bg-purple-100 text-purple-800',
    }
  }
  if (name === 'rag_retrieval') {
    return {
      category: 'Knowledge RAG',
      typeLabel: 'Vector Knowledge Base',
      icon: FileText,
      badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
      pillColor: 'bg-blue-100 text-blue-800',
    }
  }
  if (name === 'multi_namespace') {
    return {
      category: 'Cross-Namespace',
      typeLabel: 'Multi-Category RAG',
      icon: Layers,
      badgeColor: 'bg-cyan-50 text-cyan-700 border-cyan-200',
      pillColor: 'bg-cyan-100 text-cyan-800',
    }
  }
  if (name === 'get_ticket') {
    return {
      category: 'MCP Ticket',
      typeLabel: 'MCP Server 2',
      icon: Server,
      badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      pillColor: 'bg-indigo-100 text-indigo-800',
    }
  }
  if (name === 'get_escalation_history' || name.includes('history')) {
    return {
      category: 'MCP Audit Trail',
      typeLabel: 'MCP Server 2',
      icon: History,
      badgeColor: 'bg-violet-50 text-violet-700 border-violet-200',
      pillColor: 'bg-violet-100 text-violet-800',
    }
  }

  return {
    category: 'Agent Tool',
    typeLabel: 'Agent Action',
    icon: Database,
    badgeColor: 'bg-slate-50 text-slate-700 border-slate-200',
    pillColor: 'bg-slate-100 text-slate-800',
  }
}

export default function ToolCallBubble({ toolCalls = [], onOpenModal }) {
  if (!toolCalls || !toolCalls.length) return null

  return (
    <div className="flex flex-wrap gap-2 my-2.5">
      {toolCalls.map((tc, i) => {
        const isRunning = tc.status === 'running'
        const meta = getToolMeta(tc.tool)
        const IconComponent = meta.icon

        // Summary details from result
        let summary = 'completed'
        if (tc.tool === 'rag_retrieval') {
          const count = tc.result?.chunks?.length || 0
          summary = count > 0 ? `${count} chunks retrieved` : 'knowledge searched'
        } else if (tc.tool === 'ticket_lookup') {
          summary = tc.result?.found ? `Ticket #${tc.result?.ticket_id || tc.args?.ticket_id}` : 'Ticket searched'
        } else if (tc.tool === 'order_lookup') {
          summary = tc.result?.found ? `Order #${tc.result?.order_id || tc.args?.order_id}` : 'Order searched'
        } else if (tc.tool === 'get_escalation_history') {
          const events = tc.result?.history?.length || 0
          summary = events > 0 ? `${events} timeline events` : 'escalation history'
        } else if (tc.tool === 'get_ticket') {
          summary = tc.result?.found ? `Live Ticket #${tc.result?.ticket_id || tc.args?.ticket_id}` : 'MCP Ticket'
        }

        return (
          <button
            key={i}
            type="button"
            onClick={() => onOpenModal && onOpenModal(i)}
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all duration-150 group shadow-xs hover:shadow-sm ${
              isRunning
                ? 'bg-amber-50/90 border-amber-200 text-amber-800 animate-pulse'
                : `${meta.badgeColor} hover:brightness-95`
            }`}
            title={`Tool: ${tc.tool} (${meta.typeLabel}). Click to view execution details and output.`}
          >
            {/* Tool Icon / Loader */}
            {isRunning ? (
              <Loader2 className="w-3.5 h-3.5 text-amber-600 animate-spin flex-shrink-0" />
            ) : (
              <div className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 bg-white/80 shadow-2xs border border-black/5">
                <IconComponent className="w-3 h-3 text-current" />
              </div>
            )}

            {/* Tool Name & Category */}
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-slate-900">{tc.tool}</span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.2 rounded-md ${meta.pillColor}`}>
                {meta.category}
              </span>
              <span className="text-slate-300">·</span>
              <span className="text-[11px] font-medium opacity-85">
                {isRunning ? 'running…' : summary}
              </span>
            </div>

            {/* Inspection Link */}
            {!isRunning && (
              <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold bg-white/70 px-1.5 py-0.5 rounded-md transition-colors ml-1 shadow-2xs">
                <span>Inspect</span>
                <ExternalLink className="w-2.5 h-2.5 ml-0.5 opacity-70 group-hover:opacity-100" />
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
