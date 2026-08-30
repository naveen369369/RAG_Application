const CHIPS = [
  { icon: '🔒', title: 'Account locked', prompt: 'What should I do if my account gets locked after multiple failed login attempts?' },
  { icon: '📦', title: 'Package not arrived', prompt: 'My tracking shows Delivered but I never received my package. What should I do?' },
  { icon: '💳', title: 'Refund timeline', prompt: 'How long does a refund take to appear after it is approved?' },
  { icon: '🔧', title: 'Error ERR-1001', prompt: 'What does error code ERR-1001 mean and how do I fix it?' },
]

export function SuggestionChips({ onSelect }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-[640px]">
      {CHIPS.map(chip => (
        <button key={chip.title} onClick={() => onSelect(chip.prompt)} className="group text-left p-4 bg-white border border-slate-200 hover:border-blue-300 hover:shadow-md rounded-xl transition-all duration-200">
          <div className="flex items-start gap-3">
            <span className="text-2xl flex-shrink-0">{chip.icon}</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-800 group-hover:text-blue-700 transition-colors">{chip.title}</p>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">{chip.prompt}</p>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}
