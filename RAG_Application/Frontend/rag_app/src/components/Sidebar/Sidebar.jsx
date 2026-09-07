import { useState, useRef, useEffect, useCallback } from 'react'
import { Sparkles, Plus, ChevronDown, Settings, FileText, FlaskConical, Layers } from 'lucide-react'
import { useNamespaces } from '../../hooks/useNamespaces'
import { NamespaceSelector } from './NamespaceSelector'
import { RetrievalControls } from './RetrievalControls'
import { DocumentStudio } from './DocumentStudio'
import { HealthStatus } from './HealthStatus'
import { EvaluationPanel } from './EvaluationPanel'
import AgentControls from './AgentControls'
import RacePanel from './RacePanel'

function SidebarSection({ icon, title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-slate-100 last:border-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center justify-between w-full px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider hover:bg-slate-100/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span>{title}</span>
        </div>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="pb-3">{children}</div>}
    </div>
  )
}

export function Sidebar({ onNewChat, width, onWidthChange, onResizeStart, onResizeEnd, minWidth = 220, maxWidth = 520 }) {
  const { namespaces } = useNamespaces()
  const isResizing = useRef(false)
  const startX = useRef(0)
  const startWidth = useRef(0)

  const handleMouseMove = useCallback((e) => {
    if (!isResizing.current) return
    const delta = e.clientX - startX.current
    const newW = Math.min(maxWidth, Math.max(minWidth, startWidth.current + delta))
    onWidthChange(newW)
  }, [onWidthChange, minWidth, maxWidth])

  const handleMouseUp = useCallback(() => {
    if (!isResizing.current) return
    isResizing.current = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    onResizeEnd?.()
  }, [onResizeEnd])

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [handleMouseMove, handleMouseUp])

  const handleDragStart = (e) => {
    e.preventDefault()
    isResizing.current = true
    startX.current = e.clientX
    startWidth.current = width
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    onResizeStart?.()
  }

  return (
    <aside
      style={{ width }}
      className="flex-shrink-0 bg-slate-50 h-screen flex flex-col border-r border-slate-200 relative overflow-hidden"
    >
      {/* Header */}
      <div className="px-4 pt-5 pb-4 border-b border-slate-200 flex-shrink-0">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center shadow-sm text-white flex-shrink-0">
            <Sparkles className="w-4 h-4 fill-current" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-slate-800 leading-tight truncate">RAG Studio</p>
            <p className="text-[11px] text-slate-400 font-medium">Enterprise · Production</p>
          </div>
        </div>
        <button
          onClick={onNewChat}
          className="flex items-center justify-center gap-2 w-full bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-300 text-slate-700 hover:text-blue-700 text-sm font-medium py-2.5 px-3 rounded-xl transition-all shadow-sm"
        >
          <Plus className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">New Conversation</span>
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto min-h-0">

        <SidebarSection
          icon={<span className="w-3 h-3 rounded-full bg-violet-500 inline-block flex-shrink-0" />}
          title="Agent"
          defaultOpen={true}
        >
          <div className="px-4 space-y-2">
            <AgentControls />
            <RacePanel />
          </div>
        </SidebarSection>

        <SidebarSection
          icon={<FileText className="w-3.5 h-3.5 flex-shrink-0" />}
          title="Namespace"
          defaultOpen={true}
        >
          <div className="px-4">
            <NamespaceSelector namespaces={namespaces} />
          </div>
        </SidebarSection>

        <SidebarSection
          icon={<Settings className="w-3.5 h-3.5 flex-shrink-0" />}
          title="Retrieval Settings"
          defaultOpen={true}
        >
          <div className="px-4">
            <div className="bg-white rounded-xl border border-slate-200 px-3 shadow-sm">
              <RetrievalControls />
            </div>
          </div>
        </SidebarSection>

        <SidebarSection
          icon={<Layers className="w-3.5 h-3.5 flex-shrink-0" />}
          title="Tools"
          defaultOpen={true}
        >
          <div className="px-4 space-y-2">
            <DocumentStudio />
            <EvaluationPanel />
          </div>
        </SidebarSection>

      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-200 flex-shrink-0">
        <HealthStatus />
      </div>

      {/* Drag handle — right edge */}
      <div
        onMouseDown={handleDragStart}
        className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize z-20 group flex items-center justify-center"
        title="Drag to resize sidebar"
      >
        {/* Visible indicator bar */}
        <div className="w-0.5 h-12 rounded-full bg-slate-200 group-hover:bg-blue-400 group-active:bg-blue-500 transition-colors duration-150" />
      </div>
    </aside>
  )
}
