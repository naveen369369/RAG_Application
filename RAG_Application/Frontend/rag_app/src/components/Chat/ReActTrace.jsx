import { useState } from 'react'
import { ChevronDown, ChevronRight, Brain } from 'lucide-react'

const AGENT_COLORS = {
  triage_worker: 'bg-amber-100 text-amber-700',
  policy_worker: 'bg-indigo-100 text-indigo-700',
  agent: 'bg-violet-100 text-violet-700',
}

export default function ReActTrace({ thoughts = [] }) {
  const [open, setOpen] = useState(false)
  if (!thoughts.length) return null

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors"
      >
        <Brain className="w-3.5 h-3.5" />
        <span>ReAct trace ({thoughts.length} thought{thoughts.length > 1 ? 's' : ''})</span>
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      </button>

      {open && (
        <div className="mt-1.5 space-y-1.5 border-l-2 border-slate-200 pl-3">
          {thoughts.map((thought, i) => {
            // Support both string (single-agent) and {text, agent} (multi-agent)
            const text = typeof thought === 'string' ? thought : (thought.text || '')
            const agentLabel = typeof thought === 'object' ? thought.agent : null
            const isFinal = text.startsWith('Final Answer:')
            return (
              <div key={i} className="text-xs">
                {/* Agent label badge (multi-agent only) */}
                {agentLabel && agentLabel !== 'agent' && (
                  <span className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded mr-1.5 mb-0.5 ${AGENT_COLORS[agentLabel] || 'bg-slate-100 text-slate-600'}`}>
                    {agentLabel}
                  </span>
                )}
                {text.split('\n').map((line, j) => {
                  if (line.startsWith('Thought:')) {
                    return (
                      <div key={j} className="text-violet-700">
                        <span className="font-semibold">Thought:</span>
                        {line.slice(8)}
                      </div>
                    )
                  }
                  if (line.startsWith('Action:')) {
                    return (
                      <div key={j} className="text-blue-700">
                        <span className="font-semibold">Action:</span>
                        {line.slice(7)}
                      </div>
                    )
                  }
                  if (line.startsWith('Final Answer:')) {
                    return (
                      <div key={j} className="text-emerald-700 font-semibold">
                        {line}
                      </div>
                    )
                  }
                  return line ? <div key={j} className="text-slate-500">{line}</div> : null
                })}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
