import { FileText, ExternalLink } from 'lucide-react'

export function SourcePanel({ sources, onOpenModal }) {
  if (!sources?.length) return null

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onOpenModal}
        className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-slate-600 hover:text-blue-700 text-xs font-medium transition-all shadow-xs group"
        title="Open popup window to view all retrieved chunks and citations"
      >
        <FileText className="w-3.5 h-3.5 text-blue-600" />
        <span>
          {sources.length} source{sources.length > 1 ? 's' : ''} cited
        </span>
        <span className="text-[10px] font-semibold bg-blue-100 text-blue-700 px-1.5 py-0.2 rounded-full">
          View Chunks
        </span>
        <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-blue-600 ml-0.5" />
      </button>
    </div>
  )
}

export default SourcePanel
