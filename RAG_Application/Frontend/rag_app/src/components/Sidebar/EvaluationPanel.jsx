import { BarChart3, ExternalLink } from 'lucide-react'
import { useAppContext } from '../../context/AppContext'

export function EvaluationPanel() {
  const { setEvalDrawerOpen } = useAppContext()

  return (
    <button
      onClick={() => setEvalDrawerOpen(true)}
      className="w-full flex items-center justify-between px-3 py-2.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-xl transition-colors group"
    >
      <div className="flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-blue-500" />
        <span className="text-sm font-medium text-blue-700">Retrieval Evaluation</span>
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-blue-400 group-hover:text-blue-600 transition-colors" />
    </button>
  )
}
