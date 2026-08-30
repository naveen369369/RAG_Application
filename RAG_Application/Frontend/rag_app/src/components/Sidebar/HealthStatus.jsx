import { useState, useEffect } from 'react'
import { fetchHealth } from '../../api/namespaces'

export function HealthStatus() {
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    const check = () =>
      fetchHealth()
        .then(d => setStatus(d.pipeline_ready ? 'ok' : 'initializing'))
        .catch(() => setStatus('error'))
    check()
    const id = setInterval(check, 15000)
    return () => clearInterval(id)
  }, [])

  const cfg = {
    ok: { dot: 'bg-emerald-400', label: 'Online & Ready', cls: 'text-emerald-600' },
    initializing: { dot: 'bg-amber-400', label: 'Initializing...', cls: 'text-amber-600' },
    loading: { dot: 'bg-slate-300 animate-pulse', label: 'Checking...', cls: 'text-slate-400' },
    error: { dot: 'bg-red-400', label: 'Disconnected', cls: 'text-red-500' },
  }[status] ?? { dot: 'bg-slate-300', label: '...', cls: 'text-slate-400' }

  return (
    <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-slate-100 border border-slate-200">
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
      <span className="text-xs text-slate-500 font-medium">Backend</span>
      <span className={`text-xs font-semibold ml-auto ${cfg.cls}`}>{cfg.label}</span>
    </div>
  )
}
