import { useRef } from 'react'
import { Send } from 'lucide-react'

export function ChatInput({ onSend, disabled }) {
  const ref = useRef(null)

  const submit = () => {
    const val = ref.current?.value?.trim()
    if (!val || disabled) return
    ref.current.value = ''
    autoResize()
    onSend(val)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }

  const autoResize = () => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  return (
    <div className="border-t border-slate-200 bg-white px-4 py-4 flex-shrink-0">
      <div className="max-w-[720px] mx-auto">
        <div className="flex items-end gap-3 bg-white border border-slate-300 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 rounded-2xl px-4 py-3 transition-all shadow-sm">
          <textarea
            ref={ref}
            rows={1}
            placeholder="Ask anything about your documents..."
            onKeyDown={handleKey}
            onInput={autoResize}
            disabled={disabled}
            className="flex-1 resize-none bg-transparent text-slate-800 placeholder-slate-300 text-sm focus:outline-none leading-relaxed disabled:opacity-50"
            style={{ maxHeight: '160px' }}
          />
          <button onClick={submit} disabled={disabled} className="w-8 h-8 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-200 text-white rounded-xl flex items-center justify-center flex-shrink-0 transition-colors shadow-sm">
            <Send className="w-4 h-4 ml-0.5" />
          </button>
        </div>
        <p className="text-center text-[11px] text-slate-300 mt-2">
          <kbd className="px-1 py-0.5 rounded text-[10px] border border-slate-200 bg-slate-50 text-slate-400">Enter</kbd> to send ·
          <kbd className="px-1 py-0.5 rounded text-[10px] border border-slate-200 bg-slate-50 text-slate-400 ml-1">Shift+Enter</kbd> for new line
        </p>
      </div>
    </div>
  )
}

