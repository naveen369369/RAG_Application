import { useAppContext } from '../../context/AppContext'

function Toggle({ label, hint, checked, onChange, disabled = false }) {
  return (
    <div className={`flex items-center justify-between py-3 ${disabled ? 'opacity-40' : ''}`}>
      <div className="pr-3 min-w-0">
        <p className="text-sm text-slate-700 font-medium leading-tight">{label}</p>
        {hint && <p className="text-xs text-slate-400 mt-0.5 leading-tight">{hint}</p>}
      </div>
      <button
        type="button"
        onClick={() => !disabled && onChange(!checked)}
        className={`relative flex-shrink-0 inline-flex h-5 w-9 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${checked ? 'bg-blue-600' : 'bg-slate-200'} ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-200 mt-0.5 ${checked ? 'translate-x-4' : 'translate-x-0.5'}`} />
      </button>
    </div>
  )
}

export function RetrievalControls() {
  const { showSources, setShowSources, useHyde, setUseHyde, useReranker, setUseReranker } = useAppContext()

  const handleHyde = (val) => {
    setUseHyde(val)
    if (val) setUseReranker(false)
  }

  return (
    <div className="divide-y divide-slate-100">
      <Toggle label="Show Sources" hint="Attach citations to answers" checked={showSources} onChange={setShowSources} />
      <Toggle label="HyDE Retrieval" hint="Hypothetical doc embedding" checked={useHyde} onChange={handleHyde} />
      <Toggle label="Cross-Encoder Reranking" hint={useHyde ? 'Disabled with HyDE' : 'Rerank 2× candidates'} checked={useReranker} onChange={setUseReranker} disabled={useHyde} />
    </div>
  )
}
