import { Zap, ExternalLink } from 'lucide-react'
import { useAppContext } from '../../context/AppContext'

export default function RacePanel() {
  const { setRaceDrawerOpen } = useAppContext()

  return (
    <button
      onClick={() => setRaceDrawerOpen(true)}
      className="w-full flex items-center justify-between px-3 py-2.5 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-xl transition-colors group"
    >
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-500" />
        <span className="text-sm font-medium text-amber-700">Agent vs Workflow Race</span>
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-amber-400 group-hover:text-amber-600 transition-colors" />
    </button>
  )
}
