import { X, Zap, StopCircle } from 'lucide-react'
import { useAppContext } from '../../context/AppContext'
import { useRace } from '../../hooks/useRace'
import RaceTable from './RaceTable'
import VerdictCard from './VerdictCard'

export default function RaceDrawer() {
  const { raceDrawerOpen, setRaceDrawerOpen } = useAppContext()
  const { racing, ticketRows, summary, verdict, runRace, stopRace } = useRace()

  const hasResults = summary || Object.values(ticketRows).some(r => r.agent || r.workflow)

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-40 transition-opacity duration-300 ${raceDrawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        onClick={() => setRaceDrawerOpen(false)}
      />

      {/* Drawer — always mounted so race state survives close/reopen */}
      <div className={`fixed right-0 top-0 bottom-0 z-50 w-[85vw] max-w-5xl bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${raceDrawerOpen ? 'translate-x-0' : 'translate-x-full'}`}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-amber-500 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-800">Agent vs Workflow Race</h2>
              <p className="text-xs text-slate-400">10 tickets · 4 metrics · live streaming</p>
            </div>
          </div>
          <button
            onClick={() => setRaceDrawerOpen(false)}
            className="p-2 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Run / Stop controls */}
          <div className="flex items-center gap-3">
            <button
              onClick={runRace}
              disabled={racing}
              className="flex items-center gap-2 text-sm font-medium bg-amber-500 hover:bg-amber-600 text-white rounded-xl px-5 py-2.5 disabled:opacity-50 transition-colors shadow-sm"
            >
              <Zap className="w-4 h-4" />
              {racing ? 'Racing…' : 'Run 10-Ticket Race'}
            </button>
            {racing && (
              <button
                onClick={stopRace}
                className="flex items-center gap-2 text-sm font-medium text-red-600 border border-red-200 rounded-xl px-4 py-2.5 hover:bg-red-50 transition-colors"
              >
                <StopCircle className="w-4 h-4" />
                Stop
              </button>
            )}
            {summary && !racing && (
              <span className="text-xs text-slate-400 ml-2">
                Agent {summary.agent?.pass_rate ?? 0}% · Workflow {summary.workflow?.pass_rate ?? 0}%
              </span>
            )}
          </div>

          {hasResults && <RaceTable ticketRows={ticketRows} summary={summary} />}
          {verdict && <VerdictCard verdict={verdict} summary={summary} />}

          {!hasResults && !racing && (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <Zap className="w-10 h-10 mb-3 opacity-30" />
              <p className="text-sm">Click "Run 10-Ticket Race" to start the benchmark</p>
              <p className="text-xs mt-1">Runs Agent and Workflow on the same 10 support tickets in parallel</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
