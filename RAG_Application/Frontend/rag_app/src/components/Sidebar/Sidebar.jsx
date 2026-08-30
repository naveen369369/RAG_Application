import { Sparkles, Plus } from 'lucide-react'
import { useNamespaces } from '../../hooks/useNamespaces'
import { NamespaceSelector } from './NamespaceSelector'
import { RetrievalControls } from './RetrievalControls'
import { DocumentStudio } from './DocumentStudio'
import { HealthStatus } from './HealthStatus'
import { EvaluationPanel } from './EvaluationPanel'

export function Sidebar({ onNewChat }) {
  const { namespaces } = useNamespaces()

  return (
    <aside className="w-[280px] flex-shrink-0 bg-slate-50 h-screen flex flex-col border-r border-slate-200">
      {/* Header */}
      <div className="px-4 pt-5 pb-4 border-b border-slate-200 flex-shrink-0">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center shadow-sm text-white">
            <Sparkles className="w-4 h-4 fill-current" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800 leading-tight">RAG Studio</p>
            <p className="text-[11px] text-slate-400 font-medium">Enterprise · Production</p>
          </div>
        </div>
        <button onClick={onNewChat} className="flex items-center justify-center gap-2 w-full bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-300 text-slate-700 hover:text-blue-700 text-sm font-medium py-2.5 px-3 rounded-xl transition-all shadow-sm">
          <Plus className="w-4 h-4" />
          New Conversation
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
        <div>
          <NamespaceSelector namespaces={namespaces} />
        </div>

        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Retrieval Settings</p>
          <div className="bg-white rounded-xl border border-slate-200 px-3 shadow-sm">
            <RetrievalControls />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 px-3 shadow-sm">
          <DocumentStudio namespaces={namespaces} />
        </div>

        <div className="bg-white rounded-xl border border-slate-200 px-3 shadow-sm">
          <EvaluationPanel />
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-200 flex-shrink-0">
        <HealthStatus />
      </div>
    </aside>
  )
}
