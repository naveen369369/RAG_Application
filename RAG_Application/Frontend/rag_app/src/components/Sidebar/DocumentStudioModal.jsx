import { useState, useRef, useEffect } from 'react'
import {
  FolderArchive,
  X,
  UploadCloud,
  Cpu,
  SplitSquareVertical,
  Sparkles,
  Folder,
  Pencil,
  Check,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronDown,
} from 'lucide-react'
import { useAppContext } from '../../context/AppContext'
import { useNamespaces } from '../../hooks/useNamespaces'
import { indexDocuments } from '../../api/documents'

const ACCEPT = '.txt,.md,.pdf,.docx,.csv,.json,.html,.htm'

const STRATEGIES = [
  { id: 'hybrid',        label: 'Hybrid Chunking',  desc: 'Paragraph split with token fallback',      icon: Cpu,               iconColor: 'text-blue-600',   iconBg: 'bg-blue-50'   },
  { id: 'fixed_overlap', label: 'Fixed + Overlap',   desc: 'Equal size with overlap sliding window',   icon: SplitSquareVertical, iconColor: 'text-indigo-600', iconBg: 'bg-indigo-50' },
]

export default function DocumentStudioModal() {
  const { docStudioOpen, setDocStudioOpen } = useAppContext()
  const { namespaces = [] } = useNamespaces()

  const [files, setFiles]               = useState([])
  const [strategy, setStrategy]         = useState('hybrid')
  const [strategyOpen, setStrategyOpen] = useState(false)
  const [nsChoice, setNsChoice]         = useState('__auto__')
  const [nsDropdownOpen, setNsDropdownOpen] = useState(false)
  const [nsSearch, setNsSearch]         = useState('')
  const [isCustomNs, setIsCustomNs]     = useState(false)
  const [customNs, setCustomNs]         = useState('')
  const [chunkSize, setChunkSize]       = useState(500)
  const [chunkOverlap, setChunkOverlap] = useState(50)
  const [loading, setLoading]           = useState(false)
  const [result, setResult]             = useState(null)
  const [error, setError]               = useState(null)

  const strategyRef    = useRef(null)
  const nsRef          = useRef(null)
  const nsSearchRef    = useRef(null)
  const customNsInputRef = useRef(null)

  const effectiveNs = nsChoice === '__auto__'
    ? 'auto'
    : nsChoice === '__custom__'
    ? (customNs || 'default')
    : nsChoice

  // Close dropdowns on outside click / Escape; close modal on Escape
  useEffect(() => {
    function handleClickOutside(e) {
      if (strategyRef.current && !strategyRef.current.contains(e.target)) setStrategyOpen(false)
      if (nsRef.current && !nsRef.current.contains(e.target)) setNsDropdownOpen(false)
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        if (strategyOpen || nsDropdownOpen) {
          setStrategyOpen(false)
          setNsDropdownOpen(false)
        } else {
          setDocStudioOpen(false)
        }
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [strategyOpen, nsDropdownOpen, setDocStudioOpen])

  useEffect(() => {
    if (nsDropdownOpen && nsSearchRef.current && !isCustomNs) nsSearchRef.current.focus()
  }, [nsDropdownOpen, isCustomNs])

  useEffect(() => {
    if (isCustomNs && customNsInputRef.current) customNsInputRef.current.focus()
  }, [isCustomNs])

  const handleIndex = async () => {
    if (!files.length) return
    setLoading(true); setResult(null); setError(null)
    try {
      const data = await indexDocuments({ files, namespace: effectiveNs, strategy, chunkSize, chunkOverlap })
      setResult(data)
      setFiles([])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const filteredNamespaces = namespaces.filter(ns =>
    ns.toLowerCase().includes(nsSearch.toLowerCase())
  )

  const currentStrategyObj = STRATEGIES.find(s => s.id === strategy) || STRATEGIES[0]
  const StrategyIcon = currentStrategyObj.icon

  const currentNsLabel =
    nsChoice === '__auto__'   ? 'Auto from filename' :
    nsChoice === '__custom__' ? (customNs ? `Custom: ${customNs}` : 'Custom namespace') :
    nsChoice

  const inputCls = "w-full bg-white text-slate-700 border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-sm transition"

  if (!docStudioOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        onClick={() => setDocStudioOpen(false)}
      >
        {/* Modal — stop propagation so clicking inside doesn't close */}
        <div
          className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center shadow-sm">
                <FolderArchive className="w-4.5 h-4.5 text-white" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-800">Document Studio</h2>
                <p className="text-xs text-slate-400">Upload, chunk, and index documents</p>
              </div>
            </div>
            <button
              onClick={() => setDocStudioOpen(false)}
              className="p-2 hover:bg-slate-100 rounded-xl transition-colors"
            >
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>

          {/* Scrollable body */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

            {/* Drop zone */}
            <label className="block w-full border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-xl p-6 text-center cursor-pointer transition-all bg-slate-50 hover:bg-blue-50">
              <input
                type="file"
                multiple
                accept={ACCEPT}
                className="hidden"
                onChange={e => { setFiles(Array.from(e.target.files)); setResult(null); setError(null) }}
              />
              {files.length ? (
                <div>
                  <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-blue-500" />
                  <p className="text-sm font-semibold text-blue-600">{files.length} file{files.length > 1 ? 's' : ''} selected</p>
                  <p className="text-xs text-slate-400 mt-1 truncate max-w-xs mx-auto">{files.map(f => f.name).join(', ')}</p>
                  <p className="text-xs text-blue-400 mt-1">Click to change selection</p>
                </div>
              ) : (
                <div>
                  <UploadCloud className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                  <p className="text-sm font-medium text-slate-500">Click to upload files</p>
                  <p className="text-xs text-slate-400 mt-1">PDF · TXT · MD · DOCX · CSV · JSON · HTML</p>
                </div>
              )}
            </label>

            {files.length > 0 && (
              <>
                {/* Chunking Strategy */}
                <div className="relative" ref={strategyRef}>
                  <label className="text-xs font-semibold text-slate-500 block mb-1.5">Chunking Strategy</label>
                  <button
                    type="button"
                    onClick={() => { setStrategyOpen(o => !o); setNsDropdownOpen(false) }}
                    className={`w-full flex items-center justify-between gap-2 px-3 py-2.5 bg-white rounded-xl border text-sm font-medium transition-all shadow-sm ${
                      strategyOpen ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className={`w-6 h-6 rounded-lg ${currentStrategyObj.iconBg} ${currentStrategyObj.iconColor} flex items-center justify-center flex-shrink-0`}>
                        <StrategyIcon className="w-3.5 h-3.5" />
                      </span>
                      <span className="font-semibold text-slate-800">{currentStrategyObj.label}</span>
                      <span className="text-xs text-slate-400 hidden sm:inline">{currentStrategyObj.desc}</span>
                    </div>
                    <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${strategyOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {strategyOpen && (
                    <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-2xl shadow-xl z-10 p-1 space-y-1">
                      {STRATEGIES.map(s => {
                        const Icon = s.icon
                        return (
                          <button
                            key={s.id}
                            type="button"
                            onClick={() => { setStrategy(s.id); setStrategyOpen(false) }}
                            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-left text-sm transition-colors ${
                              strategy === s.id ? 'bg-blue-50 text-blue-700' : 'text-slate-700 hover:bg-slate-50'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <span className={`w-6 h-6 rounded-lg ${s.iconBg} ${s.iconColor} flex items-center justify-center flex-shrink-0`}>
                                <Icon className="w-3.5 h-3.5" />
                              </span>
                              <div>
                                <p className="font-semibold text-slate-800 text-sm">{s.label}</p>
                                <p className="text-xs text-slate-400">{s.desc}</p>
                              </div>
                            </div>
                            {strategy === s.id && <Check className="w-4 h-4 text-blue-600" />}
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>

                {/* Target Namespace */}
                <div className="relative" ref={nsRef}>
                  <label className="text-xs font-semibold text-slate-500 block mb-1.5">Target Namespace</label>
                  <button
                    type="button"
                    onClick={() => { setNsDropdownOpen(o => !o); setStrategyOpen(false) }}
                    className={`w-full flex items-center justify-between gap-2 px-3 py-2.5 bg-white rounded-xl border text-sm font-medium transition-all shadow-sm ${
                      nsDropdownOpen ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="w-6 h-6 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                        {nsChoice === '__auto__'   ? <Sparkles className="w-3.5 h-3.5 text-blue-500" /> :
                         nsChoice === '__custom__' ? <Pencil className="w-3.5 h-3.5 text-amber-500" /> :
                                                    <Folder className="w-3.5 h-3.5 text-slate-500" />}
                      </span>
                      <span className="font-semibold text-slate-800 truncate">{currentNsLabel}</span>
                    </div>
                    <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform flex-shrink-0 ${nsDropdownOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {nsDropdownOpen && (
                    <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-2xl shadow-xl z-10 overflow-hidden flex flex-col max-h-56">
                      {namespaces.length > 3 && (
                        <div className="p-2 border-b border-slate-100">
                          <input
                            ref={nsSearchRef}
                            type="text"
                            value={nsSearch}
                            onChange={e => setNsSearch(e.target.value)}
                            placeholder="Filter namespaces…"
                            className="w-full px-3 py-1.5 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </div>
                      )}
                      <div className="overflow-y-auto p-1 space-y-0.5 flex-1">
                        {(!nsSearch || 'auto from filename'.includes(nsSearch.toLowerCase())) && (
                          <button type="button"
                            onClick={() => { setNsChoice('__auto__'); setNsDropdownOpen(false); setIsCustomNs(false) }}
                            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm text-left transition-colors ${nsChoice === '__auto__' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-700 hover:bg-slate-50'}`}
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="w-6 h-6 rounded-lg bg-blue-50 flex items-center justify-center"><Sparkles className="w-3.5 h-3.5 text-blue-500" /></span>
                              Auto from filename
                            </div>
                            {nsChoice === '__auto__' && <Check className="w-4 h-4 text-blue-600" />}
                          </button>
                        )}
                        {filteredNamespaces.map(ns => (
                          <button key={ns} type="button"
                            onClick={() => { setNsChoice(ns); setNsDropdownOpen(false); setIsCustomNs(false) }}
                            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm text-left transition-colors ${nsChoice === ns ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-slate-700 hover:bg-slate-50'}`}
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="w-6 h-6 rounded-lg bg-slate-100 flex items-center justify-center"><Folder className="w-3.5 h-3.5 text-slate-500" /></span>
                              {ns}
                            </div>
                            {nsChoice === ns && <Check className="w-4 h-4 text-blue-600" />}
                          </button>
                        ))}
                      </div>
                      <div className="p-1 border-t border-slate-100">
                        {isCustomNs ? (
                          <div className="flex gap-1.5 px-1">
                            <input
                              ref={customNsInputRef}
                              type="text"
                              value={customNs}
                              onChange={e => setCustomNs(e.target.value)}
                              placeholder="Namespace name…"
                              className="flex-1 px-3 py-1.5 text-sm bg-white border border-blue-400 rounded-lg focus:outline-none"
                            />
                            <button type="button"
                              onClick={() => { setNsChoice('__custom__'); setNsDropdownOpen(false) }}
                              className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg"
                            >Set</button>
                          </div>
                        ) : (
                          <button type="button"
                            onClick={() => { setIsCustomNs(true); setNsChoice('__custom__') }}
                            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm text-left transition-colors ${nsChoice === '__custom__' ? 'bg-amber-50 text-amber-800 font-semibold' : 'text-slate-600 hover:bg-slate-50'}`}
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="w-6 h-6 rounded-lg bg-amber-50 flex items-center justify-center"><Pencil className="w-3.5 h-3.5 text-amber-500" /></span>
                              {nsChoice === '__custom__' && customNs ? `Custom: ${customNs}` : 'Custom namespace…'}
                            </div>
                            {nsChoice === '__custom__' && <Check className="w-4 h-4 text-amber-600" />}
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Chunk size & overlap */}
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="text-xs font-semibold text-slate-500 block mb-1.5">Chunk Size</label>
                    <input type="number" value={chunkSize} onChange={e => setChunkSize(Number(e.target.value))} className={inputCls} />
                  </div>
                  <div className="flex-1">
                    <label className="text-xs font-semibold text-slate-500 block mb-1.5">Overlap</label>
                    <input type="number" value={chunkOverlap} onChange={e => setChunkOverlap(Number(e.target.value))} className={inputCls} />
                  </div>
                </div>
              </>
            )}

            {/* Status messages */}
            {result && (
              <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-emerald-700">Indexed successfully</p>
                  <p className="text-xs text-emerald-600">{result.vectors_stored?.toLocaleString()} vectors stored</p>
                </div>
              </div>
            )}
            {error && (
              <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
          </div>

          {/* Footer with action button */}
          <div className="px-6 py-4 border-t border-slate-200 flex-shrink-0 flex gap-3">
            <button
              onClick={() => setDocStudioOpen(false)}
              className="flex-1 py-2.5 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleIndex}
              disabled={!files.length || loading}
              className="flex-1 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 rounded-xl transition-colors shadow-sm flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="animate-spin w-4 h-4" />}
              {loading ? 'Indexing…' : 'Index Documents'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
