import { useLiveCompare } from '../../hooks/useLiveCompare'
import CompareInput from './CompareInput'
import AgentStream from './AgentStream'
import WorkflowStream from './WorkflowStream'
import { RefreshCw } from 'lucide-react'

export default function LiveCompare() {
  const { agentPanel, workflowPanel, comparing, compare, reset } = useLiveCompare()

  const hasContent = agentPanel.tokens || workflowPanel.tokens || agentPanel.toolCalls.length || workflowPanel.steps.length

  return (
    <div className="space-y-3">
      <CompareInput onCompare={compare} disabled={comparing} />

      {hasContent && (
        <button
          onClick={reset}
          disabled={comparing}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 disabled:opacity-50"
        >
          <RefreshCw className="w-3 h-3" />
          Clear
        </button>
      )}

      {hasContent && (
        <div className="grid grid-cols-2 gap-3 border border-slate-200 rounded-lg p-3 min-h-48">
          <div className="border-r border-slate-100 pr-3">
            <AgentStream panel={agentPanel} />
          </div>
          <div>
            <WorkflowStream panel={workflowPanel} />
          </div>
        </div>
      )}
    </div>
  )
}
