import { FolderArchive, ExternalLink } from 'lucide-react'
import { useAppContext } from '../../context/AppContext'

export function DocumentStudio() {
  const { setDocStudioOpen } = useAppContext()

  return (
    <button
      onClick={() => setDocStudioOpen(true)}
      className="w-full flex items-center justify-between px-3 py-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors group"
    >
      <div className="flex items-center gap-2">
        <FolderArchive className="w-4 h-4 text-slate-500" />
        <span className="text-sm font-medium text-slate-700">Document Studio</span>
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-600 transition-colors" />
    </button>
  )
}
