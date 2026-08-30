import { Bot } from 'lucide-react'

export function WelcomeScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-16 px-6 text-center">
      <div className="w-16 h-16 rounded-2xl bg-blue-600 flex items-center justify-center mb-6 shadow-lg shadow-blue-200 text-white">
        <Bot className="w-8 h-8" />
      </div>
      <h1 className="text-2xl sm:text-3xl font-bold text-slate-800 mb-2">What can I help you with?</h1>
      <p className="text-slate-400 text-sm sm:text-base max-w-md leading-relaxed">
        Ask anything about your indexed documents. I'll search, retrieve, and synthesize answers in real time.
      </p>
    </div>
  )
}


