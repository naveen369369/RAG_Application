import { useState } from 'react'
import { ChevronDown, ChevronRight, Brain } from 'lucide-react'

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
          {thoughts.map((text, i) => {
            const isFinal = text.startsWith('Final Answer:')
            return (
              <div key={i} className="text-xs">
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
