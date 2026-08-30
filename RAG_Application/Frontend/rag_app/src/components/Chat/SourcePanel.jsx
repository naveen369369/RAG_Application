import { useState } from 'react'
import { FileText, ChevronDown } from 'lucide-react'

export function SourcePanel({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources?.length) return null

  return (
    <div className="mt-2.5">
      <button onClick={() => setOpen(o => !o)} className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-blue-600 font-medium transition-colors">
        <FileText className="w-3.5 h-3.5" />
        {sources.length} source{sources.length > 1 ? 's' : ''} cited
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((src, i) => (
            <div key={i} className="bg-white border border-slate-200 border-l-2 border-l-blue-500 rounded-lg p-3 shadow-sm">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-700 truncate mr-2">{src.source}</span>
                <span className="text-[11px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded flex-shrink-0">{(src.score * 100).toFixed(1)}% · #{src.chunk_index}</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">{src.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

