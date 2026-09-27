import { useState, useEffect } from 'react'
import {
  X,
  Ticket,
  Package,
  Plus,
  Bot,
  RefreshCw,
  Search,
  CheckCircle,
  Clock,
  AlertTriangle,
  Send,
  ExternalLink,
  ShieldAlert,
  History,
  Server,
} from 'lucide-react'
import { useAppContext } from '../../context/AppContext'
import McpHistoryTab from './McpHistoryTab'
import {
  fetchTickets,
  createTicket,
  fetchOrders,
  createOrder,
  fetchCustomers,
} from '../../api/tickets'

const TIER_COLORS = {
  basic: 'bg-slate-100 text-slate-700 border-slate-200',
  premium: 'bg-purple-100 text-purple-700 border-purple-200',
  vip: 'bg-amber-100 text-amber-800 border-amber-300 font-bold',
}

const STATUS_COLORS = {
  open: 'bg-blue-50 text-blue-700 border-blue-200',
  in_progress: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  escalated: 'bg-rose-50 text-rose-700 border-rose-300 font-semibold',
  waiting_customer: 'bg-slate-100 text-slate-600 border-slate-200',
  resolved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  closed: 'bg-slate-100 text-slate-500 border-slate-200',
  processing: 'bg-blue-50 text-blue-700 border-blue-200',
  shipped: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  delivered: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  cancelled: 'bg-red-50 text-red-700 border-red-200',
}

const CONDITION_COLORS = {
  unopened: 'bg-emerald-100 text-emerald-800',
  opened: 'bg-amber-100 text-amber-800',
  damaged: 'bg-rose-100 text-rose-800 font-medium',
  missing: 'bg-red-100 text-red-800 font-medium',
}

export default function TicketsDrawer({ onAskAboutTicket }) {
  const { ticketsDrawerOpen, setTicketsDrawerOpen, setAgentMode, ticketsDrawerTab, setTicketsDrawerTab } = useAppContext()
  const [activeTab, setActiveTab] = useState('mcp_history') // mcp_history | tickets | orders | new_ticket | new_order
  const [selectedMcpTicket, setSelectedMcpTicket] = useState('TCK-1004')
  const [tickets, setTickets] = useState([])
  const [orders, setOrders] = useState([])
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(false)
  const [filterCustomer, setFilterCustomer] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [feedbackMsg, setFeedbackMsg] = useState(null)

  useEffect(() => {
    if (ticketsDrawerTab) {
      setActiveTab(ticketsDrawerTab)
    }
  }, [ticketsDrawerTab])

  const switchTab = (tab) => {
    setActiveTab(tab)
    if (setTicketsDrawerTab) setTicketsDrawerTab(tab)
  }

  // New Ticket Form State
  const [newTicket, setNewTicket] = useState({
    customer_id: 'C001',
    order_id: '',
    subject: '',
    description: '',
    category: 'return_refund',
    priority: 'standard',
  })

  // New Order Form State
  const [newOrder, setNewOrder] = useState({
    customer_id: 'C001',
    status: 'processing',
    carrier: 'FedEx',
    tracking_number: '',
    order_total: 99.0,
    shipping_address: '123 Main St, Springfield, OR',
    product_name: 'Wireless Bluetooth Earbuds',
    sku: 'EAR-BT-01',
    quantity: 1,
    unit_price: 99.0,
    item_condition: 'unopened',
  })

  const loadData = async () => {
    setLoading(true)
    try {
      const ticketParams = {}
      if (filterCustomer && filterCustomer !== 'all') ticketParams.customer_id = filterCustomer
      if (filterStatus && filterStatus !== 'all') ticketParams.status = filterStatus

      const orderParams = {}
      if (filterCustomer && filterCustomer !== 'all') orderParams.customer_id = filterCustomer

      const results = await Promise.allSettled([
        fetchTickets(ticketParams),
        fetchOrders(orderParams),
        fetchCustomers(),
      ])
      if (results[0].status === 'fulfilled') setTickets(results[0].value || [])
      if (results[1].status === 'fulfilled') setOrders(results[1].value || [])
      if (results[2].status === 'fulfilled') setCustomers(results[2].value || [])
    } catch (err) {
      console.error('Failed to load CRM data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (ticketsDrawerOpen) {
      loadData()
    }
  }, [ticketsDrawerOpen, filterCustomer, filterStatus])

  const handleCreateTicket = async (e) => {
    e.preventDefault()
    if (!newTicket.subject.trim() || !newTicket.description.trim()) return
    try {
      await createTicket({
        ...newTicket,
        order_id: newTicket.order_id || null,
      })
      setFeedbackMsg('Ticket created successfully in SQL database!')
      setActiveTab('tickets')
      setNewTicket({
        customer_id: 'C001',
        order_id: '',
        subject: '',
        description: '',
        category: 'return_refund',
        priority: 'standard',
      })
      loadData()
      setTimeout(() => setFeedbackMsg(null), 4000)
    } catch (err) {
      alert(`Error creating ticket: ${err.message}`)
    }
  }

  const handleCreateOrder = async (e) => {
    e.preventDefault()
    try {
      const result = await createOrder({
        customer_id: newOrder.customer_id,
        status: newOrder.status,
        carrier: newOrder.carrier,
        tracking_number: newOrder.tracking_number,
        order_total: Number(newOrder.order_total),
        shipping_address: newOrder.shipping_address,
        items: [
          {
            product_name: newOrder.product_name,
            sku: newOrder.sku,
            quantity: Number(newOrder.quantity),
            unit_price: Number(newOrder.unit_price),
            item_condition: newOrder.item_condition,
          },
        ],
      })
      const generatedId = result?.order_id || result?.id || 'auto'
      setFeedbackMsg(`Order ${generatedId} auto-created in database!`)
      setActiveTab('orders')
      setNewOrder({
        customer_id: 'C001',
        status: 'processing',
        carrier: 'FedEx',
        tracking_number: '',
        order_total: 99.0,
        shipping_address: '123 Main St, Springfield, OR',
        product_name: 'Wireless Bluetooth Earbuds',
        sku: 'EAR-BT-01',
        quantity: 1,
        unit_price: 99.0,
        item_condition: 'unopened',
      })
      loadData()
      setTimeout(() => setFeedbackMsg(null), 4000)
    } catch (err) {
      alert(`Error creating order: ${err.message}`)
    }
  }

  const askAgentAbout = (ticket) => {
    setAgentMode(true)
    setTicketsDrawerOpen(false)
    const prompt = `Please look up ticket #${ticket.ticket_id} for customer ${ticket.customer_id}. Inspect their issue and any linked order, check company policy, and tell me what actions or resolution apply.`
    if (onAskAboutTicket) {
      onAskAboutTicket(prompt, ticket.customer_id)
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/40 z-40 transition-opacity duration-300 ${
          ticketsDrawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setTicketsDrawerOpen(false)}
      />

      {/* Drawer */}
      <div
        className={`fixed right-0 top-0 bottom-0 z-50 w-[90vw] max-w-4xl bg-slate-50 shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${
          ticketsDrawerOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white shadow-md">
              <Ticket className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-800">Support CRM &amp; MCP Operations</h2>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold border border-emerald-200">
                  Server 1 (SQL DB)
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-bold border border-indigo-200">
                  Server 2 (FastMCP)
                </span>
              </div>
              <p className="text-xs text-slate-400">Server 1: Local CRM database &bull; Server 2: Escalation audit trail &amp; MCP protocol</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadData}
              disabled={loading}
              title="Refresh database records"
              className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-500 hover:text-slate-700"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => setTicketsDrawerOpen(false)}
              className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-500 hover:text-slate-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Feedback Alert */}
        {feedbackMsg && (
          <div className="mx-6 mt-3 px-4 py-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 animate-fadeIn">
            <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{feedbackMsg}</span>
          </div>
        )}

        {/* Tabs Bar */}
        <div className="px-6 pt-3 bg-white border-b border-slate-200 flex items-center justify-between gap-4 flex-shrink-0">
          <div className="flex gap-2">
            <button
              onClick={() => switchTab('mcp_history')}
              className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
                activeTab === 'mcp_history'
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <History className="w-3.5 h-3.5 text-indigo-600" />
              <span>MCP &amp; Escalation History</span>
              <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded-full font-bold">
                Server 2
              </span>
            </button>
            <button
              onClick={() => switchTab('tickets')}
              className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
                activeTab === 'tickets'
                  ? 'border-emerald-600 text-emerald-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Ticket className="w-3.5 h-3.5 text-emerald-600" />
              <span>Tickets ({tickets.length})</span>
              <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded-full font-bold">
                Server 1 DB
              </span>
            </button>
            <button
              onClick={() => switchTab('orders')}
              className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
                activeTab === 'orders'
                  ? 'border-emerald-600 text-emerald-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Package className="w-3.5 h-3.5 text-emerald-600" />
              <span>Orders ({orders.length})</span>
              <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded-full font-bold">
                Server 1 DB
              </span>
            </button>
            <button
              onClick={() => switchTab('new_ticket')}
              className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
                activeTab === 'new_ticket'
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Ticket</span>
            </button>
            <button
              onClick={() => switchTab('new_order')}
              className={`pb-2.5 px-3 text-xs font-semibold flex items-center gap-1.5 border-b-2 transition-all ${
                activeTab === 'new_order'
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Order</span>
            </button>
          </div>

          {/* Filters */}
          {(activeTab === 'tickets' || activeTab === 'orders') && (
            <div className="flex items-center gap-2 pb-2">
              <select
                value={filterCustomer}
                onChange={(e) => setFilterCustomer(e.target.value)}
                className="text-xs border border-slate-200 rounded-lg px-2.5 py-1 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Customers</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.id} - {c.name} ({c.tier})
                  </option>
                ))}
              </select>
              {activeTab === 'tickets' && (
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="text-xs border border-slate-200 rounded-lg px-2.5 py-1 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">All Statuses</option>
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="escalated">Escalated</option>
                  <option value="resolved">Resolved</option>
                </select>
              )}
            </div>
          )}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* TAB: TICKETS LIST */}
          {activeTab === 'tickets' && (
            <div className="space-y-3">
              {tickets.length === 0 ? (
                <div className="text-center py-16 bg-white rounded-2xl border border-slate-200">
                  <Ticket className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No support tickets found</p>
                  <p className="text-xs text-slate-400 mt-1">
                    {filterCustomer || filterStatus ? 'No tickets match the selected filters.' : 'No tickets in the database.'}
                  </p>
                  {(filterCustomer || filterStatus) && (
                    <button
                      type="button"
                      onClick={() => {
                        setFilterCustomer('')
                        setFilterStatus('')
                      }}
                      className="mt-3 text-xs font-semibold px-3 py-1.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition-colors shadow-2xs"
                    >
                      Clear All Filters
                    </button>
                  )}
                </div>
              ) : (
                tickets.map((t) => (
                  <div
                    key={t.ticket_id}
                    className="bg-white rounded-xl p-4 border border-slate-200 hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">
                          #{t.ticket_id}
                        </span>
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-md border font-medium uppercase tracking-wider ${
                            STATUS_COLORS[t.status] || 'bg-slate-100'
                          }`}
                        >
                          {t.status.replace('_', ' ')}
                        </span>
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-md border uppercase font-medium ${
                            TIER_COLORS[t.customer_tier] || 'bg-slate-100'
                          }`}
                        >
                          {t.customer_tier} Tier
                        </span>
                        {t.order_id && (
                          <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200 flex items-center gap-1 font-mono">
                            <Package className="w-3 h-3" />
                            {t.order_id}
                          </span>
                        )}
                        <span className="text-[11px] text-slate-400">
                          {t.customer_name} ({t.customer_id})
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-800 truncate">{t.subject}</h4>
                      <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">{t.description}</p>
                    </div>

                    <div className="flex-shrink-0 flex items-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100">
                      <button
                        type="button"
                        onClick={() => {
                          const tid = t.ticket_id || t.id || 'TCK-1004'
                          setSelectedMcpTicket(tid)
                          switchTab('mcp_history')
                        }}
                        className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition-colors shadow-xs"
                        title="Inspect ticket escalation history & timeline via MCP Server 2"
                      >
                        <History className="w-3.5 h-3.5" />
                        <span>MCP History</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => askAgentAbout(t)}
                        className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white shadow-sm transition-colors"
                        title="Query agent about this ticket"
                      >
                        <Bot className="w-3.5 h-3.5" />
                        <span>Ask Agent</span>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* TAB: MCP TICKET HISTORY & AUDIT TRAIL */}
          {activeTab === 'mcp_history' && (
            <McpHistoryTab
              initialTicketId={selectedMcpTicket || 'TCK-1004'}
              dbTickets={tickets}
              onAskAgent={(prompt) => {
                setAgentMode(true)
                setTicketsDrawerOpen(false)
                if (onAskAboutTicket) onAskAboutTicket(prompt, 'C042')
              }}
            />
          )}

          {/* TAB: ORDERS LIST */}
          {activeTab === 'orders' && (
            <div className="space-y-3">
              {orders.length === 0 ? (
                <div className="text-center py-16 bg-white rounded-2xl border border-slate-200">
                  <Package className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No customer orders found</p>
                </div>
              ) : (
                orders.map((o) => (
                  <div
                    key={o.order_id}
                    className="bg-white rounded-xl p-4 border border-slate-200 hover:border-indigo-300 hover:shadow-sm transition-all space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">
                          {o.order_id}
                        </span>
                        <span className="text-xs text-slate-600 font-medium">Customer: {o.customer_id}</span>
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-md border font-medium capitalize ${
                            STATUS_COLORS[o.status] || 'bg-slate-100'
                          }`}
                        >
                          {o.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        {o.carrier && (
                          <span>
                            Carrier: <strong className="text-slate-700">{o.carrier}</strong>
                          </span>
                        )}
                        {o.tracking_number && (
                          <span className="font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-200 text-[11px]">
                            {o.tracking_number}
                          </span>
                        )}
                        <span className="font-bold text-slate-800">${o.order_total?.toFixed(2)}</span>
                      </div>
                    </div>

                    {/* Order Line Items */}
                    <div className="space-y-1.5">
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Order Items & Item Condition (Queried by Agent)
                      </p>
                      {o.items?.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between bg-slate-50 px-3 py-1.5 rounded-lg text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-slate-700">{item.product_name}</span>
                            <span className="text-slate-400 font-mono text-[11px]">x{item.quantity}</span>
                          </div>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-md font-semibold uppercase ${
                              CONDITION_COLORS[item.item_condition] || 'bg-slate-200'
                            }`}
                          >
                            Condition: {item.item_condition}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* TAB: CREATE TICKET FORM */}
          {activeTab === 'new_ticket' && (
            <div className="max-w-2xl mx-auto bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <h3 className="text-base font-bold text-slate-800 mb-1">Create Support Ticket</h3>
              <p className="text-xs text-slate-400 mb-5">
                Writes directly to the SQL database table so the ReAct agent can query it immediately.
              </p>

              <form onSubmit={handleCreateTicket} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Customer</label>
                    <select
                      value={newTicket.customer_id}
                      onChange={(e) => setNewTicket({ ...newTicket, customer_id: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      {customers.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.id} - {c.name} ({c.tier.toUpperCase()})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Linked Order ID (Optional)
                    </label>
                    <select
                      value={newTicket.order_id}
                      onChange={(e) => setNewTicket({ ...newTicket, order_id: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">No linked order</option>
                      {orders
                        .filter((o) => !newTicket.customer_id || o.customer_id === newTicket.customer_id)
                        .map((o) => (
                          <option key={o.order_id} value={o.order_id}>
                            {o.order_id} ({o.status})
                          </option>
                        ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Category</label>
                    <select
                      value={newTicket.category}
                      onChange={(e) => setNewTicket({ ...newTicket, category: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="return_refund">Return & Refund</option>
                      <option value="shipping">Shipping & Delivery</option>
                      <option value="billing">Billing & Payment</option>
                      <option value="account">Account & Security</option>
                      <option value="technical">Technical Support</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Priority</label>
                    <select
                      value={newTicket.priority}
                      onChange={(e) => setNewTicket({ ...newTicket, priority: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="standard">Standard</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Subject / Issue Title</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Broken item upon arrival"
                    value={newTicket.subject}
                    onChange={(e) => setNewTicket({ ...newTicket, subject: e.target.value })}
                    className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Description / Customer Message</label>
                  <textarea
                    rows={4}
                    required
                    placeholder="Provide details about the issue, package status, etc."
                    value={newTicket.description}
                    onChange={(e) => setNewTicket({ ...newTicket, description: e.target.value })}
                    className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    className="flex items-center gap-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-5 py-2.5 transition-colors shadow-sm"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Submit to Database</span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB: CREATE ORDER FORM */}
          {activeTab === 'new_order' && (
            <div className="max-w-2xl mx-auto bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <h3 className="text-base font-bold text-slate-800 mb-1">Create Customer Order</h3>
              <p className="text-xs text-slate-400 mb-5">
                Register a real order with item condition so the LLM can evaluate refund/exchange eligibility.
              </p>

              <form onSubmit={handleCreateOrder} className="space-y-4">
                {/* Auto-generated ID notice */}
                <div className="flex items-center gap-2 px-3 py-2 bg-indigo-50 border border-indigo-200 rounded-xl">
                  <span className="text-xs font-mono font-bold text-indigo-700">Order ID</span>
                  <span className="text-xs text-indigo-500">will be auto-generated by the database</span>
                  <span className="ml-auto text-[11px] font-mono bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-md">ORD-NNNN</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Customer</label>
                    <select
                      value={newOrder.customer_id}
                      onChange={(e) => setNewOrder({ ...newOrder, customer_id: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      {customers.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.id} - {c.name} ({c.tier})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Order Status</label>
                    <select
                      value={newOrder.status}
                      onChange={(e) => setNewOrder({ ...newOrder, status: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="processing">Processing</option>
                      <option value="shipped">Shipped</option>
                      <option value="delivered">Delivered</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Carrier</label>
                    <select
                      value={newOrder.carrier}
                      onChange={(e) => setNewOrder({ ...newOrder, carrier: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="FedEx">FedEx</option>
                      <option value="UPS">UPS</option>
                      <option value="DHL">DHL</option>
                      <option value="USPS">USPS</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Tracking Number</label>
                    <input
                      type="text"
                      placeholder="e.g. FDX-12345"
                      value={newOrder.tracking_number}
                      onChange={(e) => setNewOrder({ ...newOrder, tracking_number: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                    />
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                  <span className="text-xs font-bold text-slate-700">Purchased Item & Condition</span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">Product Name</label>
                      <input
                        type="text"
                        required
                        value={newOrder.product_name}
                        onChange={(e) => setNewOrder({ ...newOrder, product_name: e.target.value })}
                        className="w-full text-xs border border-slate-300 rounded-lg px-3 py-1.5 focus:outline-none bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                        Condition (Affects Refund Policy)
                      </label>
                      <select
                        value={newOrder.item_condition}
                        onChange={(e) => setNewOrder({ ...newOrder, item_condition: e.target.value })}
                        className="w-full text-xs border border-slate-300 rounded-lg px-3 py-1.5 bg-white focus:outline-none"
                      >
                        <option value="unopened">Unopened (Full Refund)</option>
                        <option value="opened">Opened (Subject to Policy)</option>
                        <option value="damaged">Damaged on Arrival (Immediate Replace/Refund)</option>
                        <option value="missing">Missing / Not Delivered (Replacement Claim)</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    className="flex items-center gap-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-5 py-2.5 transition-colors shadow-sm"
                  >
                    <Package className="w-3.5 h-3.5" />
                    <span>Create Order in Database</span>
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
