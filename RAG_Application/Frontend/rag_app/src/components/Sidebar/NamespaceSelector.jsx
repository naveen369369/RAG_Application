import { useState, useRef, useEffect } from 'react'
import { Globe, Layers, Pencil, ChevronDown, Search, Check } from 'lucide-react'
import { useAppContext } from '../../context/AppContext'

export function NamespaceSelector({ namespaces = [] }) {
  const { namespace, setNamespace } = useAppContext()
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [isEditingCustom, setIsEditingCustom] = useState(false)
  const [customVal, setCustomVal] = useState('')
  const dropdownRef = useRef(null)
  const searchInputRef = useRef(null)
  const customInputRef = useRef(null)

  const isCustom = namespace !== 'all' && !namespaces.includes(namespace)
  const currentLabel = namespace === 'all' 
    ? 'All Namespaces' 
    : isCustom 
      ? namespace 
      : namespace

  // Close dropdown on click outside or Escape
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
        setIsEditingCustom(false)
      }
    }
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsOpen(false)
        setIsEditingCustom(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchInputRef.current && !isEditingCustom) {
      searchInputRef.current.focus()
    }
  }, [isOpen, isEditingCustom])

  // Focus custom input when editing custom
  useEffect(() => {
    if (isEditingCustom && customInputRef.current) {
      customInputRef.current.focus()
    }
  }, [isEditingCustom])

  const filteredNamespaces = namespaces.filter(ns => 
    ns.toLowerCase().includes(search.toLowerCase())
  )

  const handleSelectNamespace = (ns) => {
    setNamespace(ns)
    setIsOpen(false)
    setIsEditingCustom(false)
    setSearch('')
  }

  const handleApplyCustom = (e) => {
    e?.preventDefault()
    const trimmed = customVal.trim()
    if (trimmed) {
      setNamespace(trimmed)
    }
    setIsOpen(false)
    setIsEditingCustom(false)
    setSearch('')
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-2">
        Search Space
      </label>

      {/* Main Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(prev => !prev)}
        className={`w-full flex items-center justify-between gap-2.5 px-3 py-2.5 bg-white rounded-xl border text-left text-sm font-medium transition-all shadow-sm group ${
          isOpen
            ? 'border-blue-500 ring-2 ring-blue-500/20 text-slate-900'
            : 'border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50/70'
        }`}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          {namespace === 'all' ? (
            <span className="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
              <Globe className="w-3.5 h-3.5" />
            </span>
          ) : isCustom ? (
            <span className="w-6 h-6 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0">
              <Pencil className="w-3.5 h-3.5" />
            </span>
          ) : (
            <span className="w-6 h-6 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center flex-shrink-0">
              <Layers className="w-3.5 h-3.5" />
            </span>
          )}
          <span className="truncate text-xs font-semibold text-slate-800">
            {currentLabel}
          </span>
        </div>

        <ChevronDown
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 flex-shrink-0 ${
            isOpen ? 'rotate-180 text-blue-600' : 'group-hover:text-slate-600'
          }`}
        />
      </button>

      {/* Dropdown Menu Popover */}
      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-slate-200/90 rounded-2xl shadow-xl shadow-slate-300/40 z-50 overflow-hidden flex flex-col max-h-80 animate-in fade-in zoom-in-95 duration-150">
          {/* Quick Search */}
          {namespaces.length > 4 && (
            <div className="p-2 border-b border-slate-100 bg-slate-50/60">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter namespaces..."
                  className="w-full pl-8 pr-3 py-1.5 bg-white text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800 placeholder-slate-400"
                />
              </div>
            </div>
          )}

          {/* List options */}
          <div className="overflow-y-auto p-1.5 space-y-1 flex-1">
            {/* All Namespaces option */}
            {(!search || 'all namespaces'.includes(search.toLowerCase())) && (
              <button
                type="button"
                onClick={() => handleSelectNamespace('all')}
                className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-left text-xs transition-colors ${
                  namespace === 'all'
                    ? 'bg-blue-50 text-blue-700 font-semibold'
                    : 'text-slate-700 hover:bg-slate-100/80'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="w-5 h-5 rounded-md bg-blue-100 text-blue-700 flex items-center justify-center flex-shrink-0">
                    <Globe className="w-3 h-3" />
                  </span>
                  <span className="truncate">All Namespaces</span>
                </div>
                {namespace === 'all' && (
                  <Check className="w-4 h-4 text-blue-600 flex-shrink-0 ml-1" />
                )}
              </button>
            )}

            {/* Individual Namespaces */}
            {filteredNamespaces.map((ns) => {
              const isSelected = namespace === ns
              return (
                <button
                  key={ns}
                  type="button"
                  onClick={() => handleSelectNamespace(ns)}
                  className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-left text-xs transition-colors ${
                    isSelected
                      ? 'bg-blue-50 text-blue-700 font-semibold'
                      : 'text-slate-700 hover:bg-slate-100/80'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="w-5 h-5 rounded-md bg-slate-100 text-slate-500 flex items-center justify-center flex-shrink-0">
                      <Layers className="w-3 h-3" />
                    </span>
                    <span className="truncate">{ns}</span>
                  </div>
                  {isSelected && (
                    <Check className="w-4 h-4 text-blue-600 flex-shrink-0 ml-1" />
                  )}
                </button>
              )
            })}

            {filteredNamespaces.length === 0 && search && (
              <div className="py-3 text-center text-xs text-slate-400">
                No matching namespaces
              </div>
            )}
          </div>

          {/* Custom Option / Inline Input */}
          <div className="p-1.5 border-t border-slate-100 bg-slate-50/50">
            {isEditingCustom ? (
              <form onSubmit={handleApplyCustom} className="flex items-center gap-1.5">
                <input
                  ref={customInputRef}
                  type="text"
                  value={customVal}
                  onChange={(e) => setCustomVal(e.target.value)}
                  placeholder="Enter namespace..."
                  className="flex-1 px-2.5 py-1.5 bg-white text-xs border border-blue-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-800"
                />
                <button
                  type="submit"
                  className="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg transition-colors shadow-sm"
                >
                  Set
                </button>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setIsEditingCustom(true)
                  setCustomVal(isCustom ? namespace : '')
                }}
                className={`w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-left text-xs transition-colors ${
                  isCustom
                    ? 'bg-amber-50 text-amber-800 font-semibold'
                    : 'text-slate-600 hover:bg-slate-100/80'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="w-5 h-5 rounded-md bg-amber-100 text-amber-700 flex items-center justify-center flex-shrink-0">
                    <Pencil className="w-3 h-3" />
                  </span>
                  <span className="truncate">
                    {isCustom ? `Custom: ${namespace}` : 'Custom namespace...'}
                  </span>
                </div>
                {isCustom && (
                  <Check className="w-4 h-4 text-amber-600 flex-shrink-0 ml-1" />
                )}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}


