import { useState, useEffect } from 'react'
import {
  X,
  Database,
  Wrench,
  Brain,
  Copy,
  Check,
  Search,
  ExternalLink,
  Layers,
  Sparkles,
  FileText,
  Percent,
} from 'lucide-react'

export default function RetrievalModal({
  isOpen,
  onClose,
  message,
}) {
  const [activeTab, setActiveTab] = useState('chunks')
  const [copiedIndex, setCopiedIndex] = useState(null)
  const [copiedAll, setCopiedAll] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen || !message) return null

  // Extract chunks from sources or toolCalls
  let chunks = []
  if (Array.isArray(message.sources) && message.sources.length > 0) {
    chunks = message.sources
  } else if (Array.isArray(message.toolCalls)) {
    const retCall = message.toolCalls.find((tc) => tc.tool === 'rag_retrieval' && tc.result?.chunks)
    if (retCall?.result?.chunks) {
      chunks = retCall.result.chunks
    }
  }

  const toolCalls = message.toolCalls || []
  const thoughts = message.thoughts || []

  // Filter chunks by search query
  const filteredChunks = chunks.filter((c) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      (c.source && c.source.toLowerCase().includes(q)) ||
      (c.text && c.text.toLowerCase().includes(q)) ||
      (c.namespace && c.namespace.toLowerCase().includes(q))
    )
  })

  const copyChunk = (text, idx) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(idx)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const copyAllChunks = () => {
    const combined = chunks
      .map(
        (c, i) =>
          `--- Chunk #${c.chunk_index ?? i} | Source: ${c.source || 'Unknown'} | Score: ${(c.score * 100).toFixed(1)}% ---\n${c.text}`
      )
      .join('\n\n')
    navigator.clipboard.writeText(combined)
    setCopiedAll(true)
    setTimeout(() => setCopiedAll(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/60 backdrop-blur-sm transition-opacity">
      <div
        className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/75">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">
                  Retrieval & Tool Inspection
                </h2>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                  {message.agentMode ? 'Agent Mode' : 'Standard RAG'}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Detailed breakdown of retrieved document chunks, tool execution, and context citations
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-lg transition-colors"
            title="Close (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center justify-between px-6 border-b border-slate-200 bg-white">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('chunks')}
              className={`flex items-center gap-2 py-3 text-xs font-semibold border-b-2 transition-all ${
                activeTab === 'chunks'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Retrieved Chunks</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-700 font-bold">
                {chunks.length}
              </span>
            </button>

            {toolCalls.length > 0 && (
              <button
                onClick={() => setActiveTab('tools')}
                className={`flex items-center gap-2 py-3 text-xs font-semibold border-b-2 transition-all ${
                  activeTab === 'tools'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <Wrench className="w-4 h-4" />
                <span>Tool Calls</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-700 font-bold">
                  {toolCalls.length}
                </span>
              </button>
            )}

            {thoughts.length > 0 && (
              <button
                onClick={() => setActiveTab('thoughts')}
                className={`flex items-center gap-2 py-3 text-xs font-semibold border-b-2 transition-all ${
                  activeTab === 'thoughts'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <Brain className="w-4 h-4" />
                <span>Agent Thoughts</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-700 font-bold">
                  {thoughts.length}
                </span>
              </button>
            )}
          </div>

          {activeTab === 'chunks' && chunks.length > 0 && (
            <button
              onClick={copyAllChunks}
              className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-blue-600 font-medium px-2 py-1 rounded hover:bg-slate-50 transition-colors"
            >
              {copiedAll ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-emerald-600">Copied All Chunks</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy All</span>
                </>
              )}
            </button>
          )}
        </div>

        {/* Modal Content Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50 space-y-4">
          {/* TAB 1: CHUNKS */}
          {activeTab === 'chunks' && (
            <div className="space-y-4">
              {/* Search within chunks */}
              {chunks.length > 1 && (
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search keywords inside retrieved chunks..."
                    className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                    >
                      Clear
                    </button>
                  )}
                </div>
              )}

              {filteredChunks.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  {chunks.length === 0
                    ? 'No document chunks were retrieved for this response.'
                    : 'No chunks matched your filter query.'}
                </div>
              ) : (
                filteredChunks.map((chunk, idx) => {
                  const scorePct = chunk.score ? (chunk.score * 100).toFixed(1) : null
                  const scoreVal = chunk.score || 0
                  const isHighConf = scoreVal >= 0.75
                  const isMediumConf = scoreVal >= 0.55

                  return (
                    <div
                      key={idx}
                      className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-colors"
                    >
                      {/* Chunk metadata header */}
                      <div className="flex flex-wrap items-start justify-between gap-2 mb-3 pb-2.5 border-b border-slate-100">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-bold text-slate-800">
                              {chunk.source || 'Document Source'}
                            </span>
                            {chunk.chunk_index !== undefined && (
                              <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                Chunk #{chunk.chunk_index}
                              </span>
                            )}
                            {chunk.namespace && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-medium text-blue-700 bg-blue-50 border border-blue-100 px-1.5 py-0.5 rounded">
                                <Layers className="w-2.5 h-2.5" />
                                {chunk.namespace}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {scorePct && (
                            <div
                              className={`flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full ${
                                isHighConf
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : isMediumConf
                                  ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                  : 'bg-amber-50 text-amber-700 border border-amber-200'
                              }`}
                              title={`Similarity score: ${chunk.score}`}
                            >
                              <Percent className="w-3 h-3" />
                              <span>{scorePct}% match</span>
                            </div>
                          )}

                          <button
                            onClick={() => copyChunk(chunk.text, idx)}
                            className="p-1 text-slate-400 hover:text-blue-600 hover:bg-slate-100 rounded transition-colors"
                            title="Copy chunk text"
                          >
                            {copiedIndex === idx ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Chunk full text */}
                      <div className="text-xs text-slate-700 leading-relaxed font-normal whitespace-pre-wrap bg-slate-50/70 p-3 rounded-lg border border-slate-100 max-h-60 overflow-y-auto selection:bg-blue-100">
                        {chunk.text}
                      </div>

                      {/* Hybrid breakdown if present */}
                      {(chunk.dense_score !== undefined || chunk.bm25_score !== undefined) && (
                        <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400">
                          {chunk.dense_score !== undefined && (
                            <span>Dense Score: {chunk.dense_score}</span>
                          )}
                          {chunk.bm25_score !== undefined && (
                            <span>BM25 Score: {chunk.bm25_score}</span>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          )}

          {/* TAB 2: TOOL CALLS */}
          {activeTab === 'tools' && (
            <div className="space-y-4">
              {toolCalls.map((tc, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-3"
                >
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center">
                        <Wrench className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-slate-800">
                          {tc.tool}
                        </span>
                        <span
                          className={`ml-2 text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            tc.status === 'done'
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-amber-50 text-amber-700'
                          }`}
                        >
                          {tc.status === 'done' ? 'Completed' : 'Running'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Arguments */}
                  {tc.args && Object.keys(tc.args).length > 0 && (
                    <div>
                      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                        Arguments Passed
                      </span>
                      <div className="bg-slate-50 rounded-lg p-2.5 border border-slate-200/80 text-xs font-mono text-slate-800 overflow-x-auto">
                        <pre>{JSON.stringify(tc.args, null, 2)}</pre>
                      </div>
                    </div>
                  )}

                  {/* Result preview */}
                  {tc.result && (
                    <div>
                      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                        Tool Output Result
                      </span>
                      <div className="bg-slate-900 rounded-lg p-3 text-xs font-mono text-emerald-300 max-h-48 overflow-y-auto">
                        <pre>{JSON.stringify(tc.result, null, 2)}</pre>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: AGENT THOUGHTS */}
          {activeTab === 'thoughts' && (
            <div className="space-y-3">
              {thoughts.map((text, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Brain className="w-4 h-4 text-violet-600" />
                    <span className="text-xs font-bold text-violet-700">
                      Step #{idx + 1}
                    </span>
                  </div>
                  <div className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap pl-6 border-l-2 border-violet-200">
                    {text}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-100 bg-white flex items-center justify-between">
          <div className="text-xs text-slate-400">
            Press <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-mono">Esc</kbd> to exit
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
