import { Wrench, CheckCircle2, Loader2, ExternalLink, Database } from 'lucide-react'

export default function ToolCallBubble({ toolCalls = [], onOpenModal }) {
  if (!toolCalls || !toolCalls.length) return null

  return (
    <div className="flex flex-wrap gap-2 my-2">
      {toolCalls.map((tc, i) => {
        const isRunning = tc.status === 'running'
        const chunkCount = tc.result?.chunks?.length || 0

        return (
          <button
            key={i}
            type="button"
            onClick={onOpenModal}
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all duration-150 group shadow-xs ${
              isRunning
                ? 'bg-amber-50/80 border-amber-200 text-amber-800'
                : 'bg-slate-50 hover:bg-blue-50 border-slate-200 hover:border-blue-200 text-slate-700 hover:text-blue-700'
            }`}
            title="Click to open popup window with full chunk and tool details"
          >
            {isRunning ? (
              <Loader2 className="w-3.5 h-3.5 text-amber-600 animate-spin flex-shrink-0" />
            ) : (
              <div className="w-4 h-4 rounded-md bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <Database className="w-2.5 h-2.5" />
              </div>
            )}

            <div className="flex items-center gap-1.5">
              <span className="font-semibold">{tc.tool}</span>
              {isRunning ? (
                <span className="text-amber-600 text-[11px]">running…</span>
              ) : (
                <>
                  <span className="text-slate-300">·</span>
                  <span className="text-[11px] font-medium text-slate-500 group-hover:text-blue-600">
                    {chunkCount > 0 ? `${chunkCount} chunks retrieved` : 'completed'}
                  </span>
                </>
              )}
            </div>

            {!isRunning && (
              <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-blue-600 bg-blue-50 group-hover:bg-blue-100 px-1.5 py-0.5 rounded-md transition-colors ml-1">
                <span>View Details</span>
                <ExternalLink className="w-3 h-3 ml-0.5 opacity-70 group-hover:opacity-100" />
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
