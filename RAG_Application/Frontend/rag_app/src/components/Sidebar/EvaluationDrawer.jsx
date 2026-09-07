import { useState } from 'react'
import { X, BarChart3, Search, Play, CheckCircle2, XCircle, AlertTriangle, Loader2 } from 'lucide-react'
import { useAppContext } from '../../context/AppContext'
import { discoverChunks, evaluateHitRate } from '../../api/evaluation'

export default function EvaluationDrawer() {
  const { evalDrawerOpen, setEvalDrawerOpen, useHyde, useReranker } = useAppContext()

  const [discovering, setDiscovering] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [discoverMsg, setDiscoverMsg] = useState(null)
  const [discoverData, setDiscoverData] = useState(null)
  const [evalResult, setEvalResult] = useState(null)
  const [breakdown, setBreakdown] = useState(true)

  const handleDiscover = async () => {
    setDiscovering(true)
    setDiscoverMsg(null)
    try {
      const d = await discoverChunks()
      setDiscoverData(d.discovered ?? [])
      const found = (d.discovered ?? []).filter(x => x.correct_chunk_id).length
      setDiscoverMsg(`Mapped ${found}/${(d.discovered ?? []).length} chunks`)
    } catch (e) {
      setDiscoverMsg(`Error: ${e.message}`)
    } finally {
      setDiscovering(false)
    }
  }

  const handleEvaluate = async () => {
    setEvaluating(true)
    try {
      setEvalResult(await evaluateHitRate({ top_k: 3, use_reranker: useReranker, use_hyde: useHyde }))
    } catch (e) {
      console.error(e)
    } finally {
      setEvaluating(false)
    }
  }

  const pct = evalResult?.rate_pct ?? 0
  const [hitBg, hitText, hitBdr] =
    pct >= 70
      ? ['bg-emerald-50', 'text-emerald-700', 'border-emerald-200']
      : pct >= 40
      ? ['bg-amber-50', 'text-amber-700', 'border-amber-200']
      : ['bg-red-50', 'text-red-700', 'border-red-200']

  const modeLabel = evalResult
    ? evalResult.use_reranker && evalResult.use_hyde
      ? 'Reranker + HyDE'
      : evalResult.use_reranker
      ? 'With Reranker'
      : evalResult.use_hyde
      ? 'HyDE Mode'
      : 'Semantic Only'
    : ''

  return (
    <>
      <div
        className={`fixed inset-0 bg-black/40 z-40 transition-opacity duration-300 ${evalDrawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        onClick={() => setEvalDrawerOpen(false)}
      />

      <div className={`fixed right-0 top-0 bottom-0 z-50 w-[85vw] max-w-3xl bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${evalDrawerOpen ? 'translate-x-0' : 'translate-x-full'}`}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-800">Retrieval Evaluation</h2>
              <p className="text-xs text-slate-400">Hit Rate @ 3 · 12 golden questions</p>
            </div>
          </div>
          <button
            onClick={() => setEvalDrawerOpen(false)}
            className="p-2 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* Config info */}
          <div className="flex gap-3">
            <div className="flex-1 bg-slate-50 rounded-xl p-3 border border-slate-200">
              <p className="text-xs text-slate-400 mb-1">Mode</p>
              <p className="text-sm font-semibold text-slate-700">
                {useReranker && useHyde ? 'Reranker + HyDE' : useReranker ? 'With Reranker' : useHyde ? 'HyDE Mode' : 'Semantic Only'}
              </p>
            </div>
            <div className="flex-1 bg-slate-50 rounded-xl p-3 border border-slate-200">
              <p className="text-xs text-slate-400 mb-1">Top-K</p>
              <p className="text-sm font-semibold text-slate-700">3 chunks</p>
            </div>
            <div className="flex-1 bg-slate-50 rounded-xl p-3 border border-slate-200">
              <p className="text-xs text-slate-400 mb-1">Questions</p>
              <p className="text-sm font-semibold text-slate-700">12 golden</p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleDiscover}
              disabled={discovering}
              className="flex items-center gap-2 text-sm font-medium bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl px-5 py-2.5 transition-colors disabled:opacity-50 shadow-sm"
            >
              {discovering ? <Loader2 className="animate-spin w-4 h-4" /> : <Search className="w-4 h-4" />}
              {discovering ? 'Discovering…' : 'Discover Chunks'}
            </button>
            <button
              onClick={handleEvaluate}
              disabled={evaluating}
              className="flex items-center gap-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 py-2.5 transition-colors disabled:opacity-50 shadow-sm"
            >
              {evaluating ? <Loader2 className="animate-spin w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
              {evaluating ? 'Evaluating…' : 'Run Evaluation'}
            </button>
          </div>

          {discoverMsg && (
            <p className="text-sm text-emerald-600 font-medium bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-2.5">
              {discoverMsg}
            </p>
          )}

          {/* Discover results table */}
          {discoverData && discoverData.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Chunk Mapping</p>
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="text-left px-4 py-2.5 font-semibold text-slate-500">Question ID</th>
                      <th className="text-left px-4 py-2.5 font-semibold text-slate-500">Chunk ID</th>
                      <th className="text-left px-4 py-2.5 font-semibold text-slate-500">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {discoverData.map((r, i) => (
                      <tr key={i} className="border-b border-slate-100 last:border-0">
                        <td className="px-4 py-2.5 font-mono text-slate-600">{r.id ?? `Q${i + 1}`}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-400 truncate max-w-[200px]">{r.correct_chunk_id ?? '—'}</td>
                        <td className="px-4 py-2.5">
                          {r.correct_chunk_id ? (
                            <span className="text-emerald-600 font-medium">Mapped</span>
                          ) : (
                            <span className="text-amber-500 font-medium">Not mapped</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Evaluation results */}
          {evalResult && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Results</p>

              {/* Big score card */}
              <div className={`rounded-xl border p-5 ${hitBg} ${hitBdr} mb-4`}>
                <div className="flex items-center justify-between">
                  <div>
                    <span className={`text-5xl font-bold ${hitText}`}>{pct.toFixed(0)}%</span>
                    <p className="text-sm text-slate-500 mt-1">Hit Rate @ 3</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-2xl font-bold ${hitText}`}>{evalResult.hits}/{evalResult.total}</p>
                    <p className="text-xs text-slate-400 mt-1">{modeLabel}</p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mt-4 h-2 bg-white/60 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>

              {/* Per-question breakdown */}
              <div>
                <button
                  onClick={() => setBreakdown(o => !o)}
                  className="text-xs font-semibold text-blue-600 hover:text-blue-700 mb-2 flex items-center gap-1"
                >
                  {breakdown ? '▲ Hide' : '▼ Show'} per-question breakdown
                </button>
                {breakdown && (
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200">
                        <tr>
                          <th className="text-left px-4 py-2.5 font-semibold text-slate-500 w-8"></th>
                          <th className="text-left px-4 py-2.5 font-semibold text-slate-500">ID</th>
                          <th className="text-left px-4 py-2.5 font-semibold text-slate-500">Chunk</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(evalResult.results ?? []).map(r => (
                          <tr key={r.id} className="border-b border-slate-100 last:border-0">
                            <td className="px-4 py-2.5">
                              {r.is_hit === null ? (
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                              ) : r.is_hit ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                              ) : (
                                <XCircle className="w-3.5 h-3.5 text-rose-500" />
                              )}
                            </td>
                            <td className="px-4 py-2.5 font-semibold text-slate-600">{r.id}</td>
                            <td className="px-4 py-2.5 font-mono text-slate-400 truncate max-w-[200px]">
                              {r.correct_chunk_id ?? 'not mapped'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {!evalResult && !evaluating && !discovering && (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <BarChart3 className="w-10 h-10 mb-3 opacity-30" />
              <p className="text-sm">Run Discover first, then Evaluate</p>
              <p className="text-xs mt-1">Measures how often the correct chunk appears in the top-3 results</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
