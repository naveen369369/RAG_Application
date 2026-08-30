import { useState, useRef, useEffect } from 'react'
import { 
  FolderArchive, 
  ChevronDown, 
  UploadCloud, 
  Cpu, 
  SplitSquareVertical, 
  Sparkles, 
  Folder, 
  Pencil, 
  Check, 
  CheckCircle2, 
  AlertCircle, 
  Loader2 
} from 'lucide-react'
import { indexDocuments } from '../../api/documents'

const ACCEPT = '.txt,.md,.pdf,.docx,.csv,.json,.html,.htm'

const STRATEGIES = [
  { id: 'hybrid', label: 'Hybrid Chunking', desc: 'Paragraph split with token fallback', icon: Cpu, iconColor: 'text-blue-600', iconBg: 'bg-blue-50' },
  { id: 'fixed_overlap', label: 'Fixed + Overlap', desc: 'Equal size with overlap sliding window', icon: SplitSquareVertical, iconColor: 'text-indigo-600', iconBg: 'bg-indigo-50' }
]

export function DocumentStudio({ namespaces = [] }) {
  const [open, setOpen] = useState(false)
  const [files, setFiles] = useState([])
  const [strategy, setStrategy] = useState('hybrid')
  const [strategyOpen, setStrategyOpen] = useState(false)
  const [nsChoice, setNsChoice] = useState('__auto__')
  const [nsDropdownOpen, setNsDropdownOpen] = useState(false)
  const [nsSearch, setNsSearch] = useState('')
  const [isCustomNs, setIsCustomNs] = useState(false)
  const [customNs, setCustomNs] = useState('')
  const [chunkSize, setChunkSize] = useState(500)
  const [chunkOverlap, setChunkOverlap] = useState(50)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const strategyRef = useRef(null)
  const nsRef = useRef(null)
  const nsSearchRef = useRef(null)
  const customNsInputRef = useRef(null)

  const effectiveNs = nsChoice === '__auto__' ? 'auto' : nsChoice === '__custom__' ? (customNs || 'default') : nsChoice

  // Close dropdowns on click outside / escape
  useEffect(() => {
    function handleClickOutside(e) {
      if (strategyRef.current && !strategyRef.current.contains(e.target)) {
        setStrategyOpen(false)
      }
      if (nsRef.current && !nsRef.current.contains(e.target)) {
        setNsDropdownOpen(false)
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setStrategyOpen(false)
        setNsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  useEffect(() => {
    if (nsDropdownOpen && nsSearchRef.current && !isCustomNs) {
      nsSearchRef.current.focus()
    }
  }, [nsDropdownOpen, isCustomNs])

  useEffect(() => {
    if (isCustomNs && customNsInputRef.current) {
      customNsInputRef.current.focus()
    }
  }, [isCustomNs])

  const handleIndex = async () => {
    if (!files.length) return
    setLoading(true); setResult(null); setError(null)
    try {
      const data = await indexDocuments({ files, namespace: effectiveNs, strategy, chunkSize, chunkOverlap })
      setResult(data); setFiles([])
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const filteredNamespaces = namespaces.filter(ns => 
    ns.toLowerCase().includes(nsSearch.toLowerCase())
  )

  const currentStrategyObj = STRATEGIES.find(s => s.id === strategy) || STRATEGIES[0]
  const StrategyIcon = currentStrategyObj.icon
  const currentNsLabel = nsChoice === '__auto__' 
    ? 'Auto from filename' 
    : nsChoice === '__custom__' 
      ? (customNs ? `Custom: ${customNs}` : 'Custom namespace') 
      : nsChoice

  const inputCls = "w-full bg-white text-slate-700 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-sm transition"

  return (
    <div>
      <button onClick={() => setOpen(o => !o)} className="flex items-center justify-between w-full text-sm text-slate-700 font-semibold py-3 hover:text-blue-600 transition-colors">
        <div className="flex items-center gap-2">
          <FolderArchive className="w-4 h-4" />
          Document Studio
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform text-slate-400 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="pb-3 space-y-2.5">
          <label className="block w-full border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-xl p-4 text-center cursor-pointer transition-all bg-slate-50 hover:bg-blue-50">
            <input type="file" multiple accept={ACCEPT} className="hidden" onChange={e => setFiles(Array.from(e.target.files))} />
            {files.length ? (
              <div>
                <p className="text-sm font-semibold text-blue-600">{files.length} file(s) ready</p>
                <p className="text-[11px] text-slate-400 mt-0.5 truncate">{files.map(f => f.name).join(', ')}</p>
              </div>
            ) : (
              <div>
                <UploadCloud className="w-7 h-7 mx-auto mb-2 text-slate-300" />
                <p className="text-xs font-medium text-slate-500">Click to upload files</p>
                <p className="text-[11px] text-slate-400 mt-0.5">PDF, TXT, MD, DOCX, CSV, JSON, HTML</p>
              </div>
            )}
          </label>

          {files.length > 0 && (
            <div className="space-y-2.5">
              {/* Strategy Custom Dropdown */}
              <div className="relative" ref={strategyRef}>
                <label className="text-[11px] font-medium text-slate-400 block mb-1">Chunking Strategy</label>
                <button
                  type="button"
                  onClick={() => { setStrategyOpen(o => !o); setNsDropdownOpen(false) }}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-2 bg-white rounded-xl border text-xs font-medium transition-all shadow-sm ${
                    strategyOpen ? 'border-blue-500 ring-2 ring-blue-500/20 text-slate-900' : 'border-slate-200 hover:border-slate-300 text-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className={`w-5 h-5 rounded-md ${currentStrategyObj.iconBg} ${currentStrategyObj.iconColor} flex items-center justify-center flex-shrink-0`}>
                      <StrategyIcon className="w-3.5 h-3.5" />
                    </span>
                    <span className="font-semibold text-slate-800 truncate">{currentStrategyObj.label}</span>
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${strategyOpen ? 'rotate-180 text-blue-600' : ''}`} />
                </button>

                {strategyOpen && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200/90 rounded-2xl shadow-xl shadow-slate-300/40 z-50 p-1 space-y-1 animate-in fade-in zoom-in-95">
                    {STRATEGIES.map(s => {
                      const Icon = s.icon
                      return (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => { setStrategy(s.id); setStrategyOpen(false) }}
                          className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-left text-xs transition-colors ${
                            strategy === s.id ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-700 hover:bg-slate-100/80'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <span className={`w-5 h-5 rounded-md ${s.iconBg} ${s.iconColor} flex items-center justify-center flex-shrink-0`}>
                              <Icon className="w-3.5 h-3.5" />
                            </span>
                            <div>
                              <p className="font-medium text-slate-800 leading-tight">{s.label}</p>
                              <p className="text-[10px] text-slate-400 leading-tight mt-0.5">{s.desc}</p>
                            </div>
                          </div>
                          {strategy === s.id && (
                            <Check className="w-4 h-4 text-blue-600 flex-shrink-0 ml-1" />
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Target Namespace Custom Dropdown */}
              <div className="relative" ref={nsRef}>
                <label className="text-[11px] font-medium text-slate-400 block mb-1">Target Namespace</label>
                <button
                  type="button"
                  onClick={() => { setNsDropdownOpen(o => !o); setStrategyOpen(false) }}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-2 bg-white rounded-xl border text-xs font-medium transition-all shadow-sm ${
                    nsDropdownOpen ? 'border-blue-500 ring-2 ring-blue-500/20 text-slate-900' : 'border-slate-200 hover:border-slate-300 text-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className="w-5 h-5 rounded-md bg-slate-100 text-slate-600 flex items-center justify-center flex-shrink-0">
                      {nsChoice === '__auto__' ? (
                        <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                      ) : nsChoice === '__custom__' ? (
                        <Pencil className="w-3.5 h-3.5 text-amber-600" />
                      ) : (
                        <Folder className="w-3.5 h-3.5 text-slate-600" />
                      )}
                    </span>
                    <span className="font-semibold text-slate-800 truncate">{currentNsLabel}</span>
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${nsDropdownOpen ? 'rotate-180 text-blue-600' : ''}`} />
                </button>

                {nsDropdownOpen && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200/90 rounded-2xl shadow-xl shadow-slate-300/40 z-50 overflow-hidden flex flex-col max-h-64 animate-in fade-in zoom-in-95">
                    {/* Search if several */}
                    {namespaces.length > 3 && (
                      <div className="p-1.5 border-b border-slate-100 bg-slate-50/60">
                        <input
                          ref={nsSearchRef}
                          type="text"
                          value={nsSearch}
                          onChange={e => setNsSearch(e.target.value)}
                          placeholder="Filter namespaces..."
                          className="w-full px-2.5 py-1 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                    )}

                    <div className="overflow-y-auto p-1 space-y-0.5 flex-1">
                      {/* Auto option */}
                      {(!nsSearch || 'auto from filename'.includes(nsSearch.toLowerCase())) && (
                        <button
                          type="button"
                          onClick={() => { setNsChoice('__auto__'); setNsDropdownOpen(false); setIsCustomNs(false) }}
                          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-left text-xs transition-colors ${
                            nsChoice === '__auto__' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-700 hover:bg-slate-100/80'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 truncate">
                            <span className="w-5 h-5 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                              <Sparkles className="w-3.5 h-3.5" />
                            </span>
                            <span className="truncate">Auto from filename</span>
                          </div>
                          {nsChoice === '__auto__' && (
                            <Check className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                          )}
                        </button>
                      )}

                      {/* Namespace list */}
                      {filteredNamespaces.map(ns => (
                        <button
                          key={ns}
                          type="button"
                          onClick={() => { setNsChoice(ns); setNsDropdownOpen(false); setIsCustomNs(false) }}
                          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-left text-xs transition-colors ${
                            nsChoice === ns ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-700 hover:bg-slate-100/80'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 truncate">
                            <span className="w-5 h-5 rounded-md bg-slate-100 text-slate-600 flex items-center justify-center flex-shrink-0">
                              <Folder className="w-3.5 h-3.5" />
                            </span>
                            <span className="truncate">{ns}</span>
                          </div>
                          {nsChoice === ns && (
                            <Check className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                          )}
                        </button>
                      ))}
                    </div>

                    {/* Custom Namespace Section */}
                    <div className="p-1 border-t border-slate-100 bg-slate-50/50">
                      {isCustomNs ? (
                        <div className="flex items-center gap-1">
                          <input
                            ref={customNsInputRef}
                            type="text"
                            value={customNs}
                            onChange={e => setCustomNs(e.target.value)}
                            placeholder="Namespace name..."
                            className="flex-1 px-2 py-1 text-xs bg-white border border-blue-400 rounded-lg focus:outline-none"
                          />
                          <button
                            type="button"
                            onClick={() => { setNsChoice('__custom__'); setNsDropdownOpen(false); }}
                            className="px-2 py-1 bg-blue-600 text-white text-xs font-medium rounded-lg"
                          >
                            Set
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => { setIsCustomNs(true); setNsChoice('__custom__') }}
                          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-left text-xs transition-colors ${
                            nsChoice === '__custom__' ? 'bg-amber-50 text-amber-800 font-semibold' : 'text-slate-600 hover:bg-slate-100/80'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 truncate">
                            <span className="w-5 h-5 rounded-md bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0">
                              <Pencil className="w-3.5 h-3.5" />
                            </span>
                            <span className="truncate">{nsChoice === '__custom__' && customNs ? `Custom: ${customNs}` : 'Custom namespace...'}</span>
                          </div>
                          {nsChoice === '__custom__' && (
                            <Check className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Chunk size & Overlap inputs */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-[11px] font-medium text-slate-400 block mb-1">Chunk Size</label>
                  <input type="number" value={chunkSize} onChange={e => setChunkSize(Number(e.target.value))} className={inputCls} />
                </div>
                <div className="flex-1">
                  <label className="text-[11px] font-medium text-slate-400 block mb-1">Overlap</label>
                  <input type="number" value={chunkOverlap} onChange={e => setChunkOverlap(Number(e.target.value))} className={inputCls} />
                </div>
              </div>

              <button onClick={handleIndex} disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold py-2.5 rounded-xl transition-colors shadow-sm flex items-center justify-center gap-2">
                {loading && <Loader2 className="animate-spin w-4 h-4" />}
                {loading ? 'Indexing…' : 'Index Documents'}
              </button>
            </div>
          )}

          {result && (
            <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-xl px-3 py-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
              <p className="text-xs text-emerald-700 font-medium">Stored {result.vectors_stored?.toLocaleString()} vectors</p>
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <p className="text-xs text-red-600">{error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


