import { useContext } from 'react'
import { AppContext } from '../../context/AppContext'
import { Bot, Info, Users, User, GitBranch, ArrowRight } from 'lucide-react'

export default function AgentControls() {
  const { agentMode, setAgentMode, agentArchitecture, setAgentArchitecture, sessionId } = useContext(AppContext)

  return (
    <div className="py-1 space-y-3">
      {/* Agent Mode master toggle */}
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

      {/* Architecture toggle — only when Agent Mode is ON */}
      {agentMode && (
        <div className="space-y-2">
          {/* Pill toggle: Single | Multi */}
          <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
            <button
              onClick={() => setAgentArchitecture('single')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                agentArchitecture === 'single'
                  ? 'bg-white text-violet-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <User className="w-3 h-3" />
              Single
            </button>
            <button
              onClick={() => setAgentArchitecture('multi')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                agentArchitecture === 'multi'
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <Users className="w-3 h-3" />
              Multi
            </button>
          </div>

          {/* Architecture description */}
          {agentArchitecture === 'single' ? (
            <div className="flex items-start gap-1.5 text-xs text-violet-600 bg-violet-50 rounded-lg px-2 py-1.5">
              <Info className="w-3 h-3 flex-shrink-0 mt-0.5" />
              <span>Single ReAct agent handles everything. Fast, minimal overhead.</span>
            </div>
          ) : (
            <div className="flex items-start gap-1.5 text-xs text-indigo-600 bg-indigo-50 rounded-lg px-2 py-1.5">
              <GitBranch className="w-3 h-3 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold mb-0.5">Orchestrator → Workers</p>
                <div className="flex items-center gap-1 text-[10px] text-indigo-500">
                  <span className="bg-indigo-100 px-1 py-0.5 rounded">Orchestrator</span>
                  <ArrowRight className="w-2.5 h-2.5" />
                  <span className="bg-indigo-100 px-1 py-0.5 rounded">Triage</span>
                  <ArrowRight className="w-2.5 h-2.5" />
                  <span className="bg-indigo-100 px-1 py-0.5 rounded">Policy</span>
                </div>
              </div>
            </div>
          )}

          {/* Session ID */}
          <div className="text-xs text-slate-400 truncate">
            Session: <span className="font-mono">{sessionId?.slice(0, 8)}…</span>
          </div>
        </div>
      )}
    </div>
  )
}
