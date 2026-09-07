import { useState } from 'react'
import { Send } from 'lucide-react'

const CUSTOMER_IDS = ['C001', 'C002', 'C003', 'C004', 'C005']
const ITEM_STATUSES = ['unopened', 'opened', 'damaged', 'missing']

export default function CompareInput({ onCompare, disabled }) {
  const [question, setQuestion] = useState('')
  const [customerId, setCustomerId] = useState('C001')
  const [itemStatus, setItemStatus] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!question.trim() || disabled) return
    onCompare({
      question: question.trim(),
      customer_id: customerId,
      item_status: itemStatus || null,
      temperature: 0.2,
      namespace: 'all',
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask both agent and workflow the same question…"
          disabled={disabled}
          className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-violet-400 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !question.trim()}
          className="bg-violet-600 text-white rounded-lg px-3 py-2 hover:bg-violet-700 disabled:opacity-50 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <div className="flex gap-2">
        <select
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          disabled={disabled}
          className="text-xs border border-slate-200 rounded px-2 py-1 focus:outline-none"
        >
          {CUSTOMER_IDS.map((id) => <option key={id} value={id}>{id}</option>)}
        </select>
        <select
          value={itemStatus}
          onChange={(e) => setItemStatus(e.target.value)}
          disabled={disabled}
          className="text-xs border border-slate-200 rounded px-2 py-1 focus:outline-none"
        >
          <option value="">item_status (optional)</option>
          {ITEM_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
    </form>
  )
}
