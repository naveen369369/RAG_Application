import { useContext } from 'react'
import { AppContext } from '../../context/AppContext'
import { Bot, Info } from 'lucide-react'

export default function AgentControls() {
  const { agentMode, setAgentMode, sessionId } = useContext(AppContext)

  return (
    <div className="py-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-violet-500" />
          <span className="text-sm font-medium text-slate-700">Agent Mode</span>
        </div>
        <button
          onClick={() => setAgentMode((v) => !v)}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
            agentMode ? 'bg-violet-600' : 'bg-slate-200'
          }`}
        >
          <span
            className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
              agentMode ? 'translate-x-4.5' : 'translate-x-0.5'
            }`}
          />
        </button>
      </div>

      {agentMode && (
        <div className="mt-2 space-y-1.5">
          <div className="flex items-start gap-1.5 text-xs text-violet-600 bg-violet-50 rounded px-2 py-1.5">
            <Info className="w-3 h-3 flex-shrink-0 mt-0.5" />
            <span>Agent decides retrieval strategy automatically. HyDE & Reranker toggles are bypassed.</span>
          </div>
          <div className="text-xs text-slate-400 truncate">
            Session: <span className="font-mono">{sessionId?.slice(0, 8)}…</span>
          </div>
        </div>
      )}
    </div>
  )
}
