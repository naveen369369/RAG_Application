import { BarChart3, GitBranch, Shield, ExternalLink } from 'lucide-react'
import { useAppContext } from '../../context/AppContext'

export function EvaluationPanel() {
  const { setEvalDrawerOpen, setTrajDrawerOpen, setSecDrawerOpen } = useAppContext()

  const buttons = [
    {
      icon: <BarChart3 className="w-4 h-4 text-blue-500" />,
      label: 'Retrieval Evaluation',
      sub: 'Hit Rate @ 3 · golden chunks',
      onClick: () => setEvalDrawerOpen(true),
      colors: 'bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700',
    },
    {
      icon: <GitBranch className="w-4 h-4 text-violet-500" />,
      label: 'Trajectory Evaluation',
      sub: '10 cases · failure modes · cost',
      onClick: () => setTrajDrawerOpen(true),
      colors: 'bg-violet-50 hover:bg-violet-100 border-violet-200 text-violet-700',
    },
    {
      icon: <Shield className="w-4 h-4 text-rose-500" />,
      label: 'Security Testing',
      sub: 'Injection · sandboxing · OWASP',
      onClick: () => setSecDrawerOpen(true),
      colors: 'bg-rose-50 hover:bg-rose-100 border-rose-200 text-rose-700',
    },
  ]

  return (
    <div className="space-y-2">
      {buttons.map(b => (
        <button
          key={b.label}
          onClick={b.onClick}
          className={`w-full flex items-center justify-between px-3 py-2.5 border rounded-xl transition-colors group ${b.colors}`}
        >
          <div className="flex items-center gap-2 min-w-0">
            {b.icon}
            <div className="min-w-0 text-left">
              <p className="text-sm font-medium leading-tight truncate">{b.label}</p>
              <p className="text-[10px] opacity-60 truncate">{b.sub}</p>
            </div>
          </div>
          <ExternalLink className="w-3.5 h-3.5 opacity-40 group-hover:opacity-70 transition-opacity flex-shrink-0" />
        </button>
      ))}
    </div>
  )
}
