import { useState } from 'react'
import { 
  BarChart3, 
  ChevronDown, 
  Search, 
  Play, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Loader2 
} from 'lucide-react'
import { discoverChunks, evaluateHitRate } from '../../api/evaluation'
import { useAppContext } from '../../context/AppContext'

export function EvaluationPanel() {
  const { useHyde, useReranker } = useAppContext()
  const [discovering, setDiscovering] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [discoverMsg, setDiscoverMsg] = useState(null)
  const [evalResult, setEvalResult] = useState(null)
  const [breakdown, setBreakdown] = useState(false)
  const [open, setOpen] = useState(false)

  const handleDiscover = async () => {
    setDiscovering(true); setDiscoverMsg(null)
    try {
      const d = await discoverChunks()
      const found = (d.discovered ?? []).filter(x => x.correct_chunk_id).length
      setDiscoverMsg(`Mapped ${found}/12 chunks`)
    } catch (e) { setDiscoverMsg(`Error: ${e.message}`) }
    finally { setDiscovering(false) }
  }

  const handleEvaluate = async () => {
    setEvaluating(true)
    try { setEvalResult(await evaluateHitRate({ top_k: 3, use_reranker: useReranker, use_hyde: useHyde })) }
    catch (e) { console.error(e) }
    finally { setEvaluating(false) }
  }

  const pct = evalResult?.rate_pct ?? 0
  const [hitBg, hitText, hitBdr] = pct >= 70 ? ['bg-emerald-50','text-emerald-700','border-emerald-200'] : pct >= 40 ? ['bg-amber-50','text-amber-700','border-amber-200'] : ['bg-red-50','text-red-700','border-red-200']
  const modeLabel = evalResult ? (evalResult.use_reranker && evalResult.use_hyde ? 'Reranker + HyDE' : evalResult.use_reranker ? 'With Reranker' : evalResult.use_hyde ? 'HyDE Mode' : 'Semantic Only') : ''

  return (
    <div>
      <button onClick={() => setOpen(o => !o)} className="flex items-center justify-between w-full text-sm text-slate-700 font-semibold py-3 hover:text-blue-600 transition-colors">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4" />
          Evaluation
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform text-slate-400 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="pb-3 space-y-3">
          <p className="text-xs text-slate-400">Hit Rate @ 3 · 12 golden questions</p>
          <div className="flex gap-2">
            <button onClick={handleDiscover} disabled={discovering} className="flex-1 flex items-center justify-center gap-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-medium py-2 rounded-xl transition-colors disabled:opacity-50 shadow-sm">
              {discovering ? <Loader2 className="animate-spin w-3.5 h-3.5" /> : <Search className="w-3.5 h-3.5" />}
              Discover
            </button>
            <button onClick={handleEvaluate} disabled={evaluating} className="flex-1 flex items-center justify-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium py-2 rounded-xl transition-colors disabled:opacity-50 shadow-sm">
              {evaluating ? <Loader2 className="animate-spin w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
              Evaluate
            </button>
          </div>

          {discoverMsg && <p className="text-xs text-emerald-600 font-medium">{discoverMsg}</p>}

          {evalResult && (
            <div className={`rounded-xl border p-3 ${hitBg} ${hitBdr}`}>
              <div className="flex items-baseline justify-between">
                <span className={`text-3xl font-bold ${hitText}`}>{pct.toFixed(0)}%</span>
                <span className="text-xs text-slate-400">{evalResult.hits}/{evalResult.total} hits</span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">{modeLabel}</p>
              <button onClick={() => setBreakdown(o => !o)} className="text-xs text-blue-600 hover:text-blue-700 font-medium mt-2 block">
                {breakdown ? '▲ Hide' : '▼ Per-question breakdown'}
              </button>
              {breakdown && (
                <ul className="mt-2 space-y-1.5 max-h-40 overflow-y-auto">
                  {(evalResult.results ?? []).map(r => (
                    <li key={r.id} className="flex items-center gap-2 text-xs text-slate-600">
                      <span className="flex-shrink-0">
                        {r.is_hit === null ? (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                        ) : r.is_hit ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-rose-500" />
                        )}
                      </span>
                      <span className="font-medium">{r.id}</span>
                      <code className="text-slate-400 text-[10px] truncate">{r.correct_chunk_id ?? 'not mapped'}</code>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

