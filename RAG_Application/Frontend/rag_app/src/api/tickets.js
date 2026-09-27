import { apiGet, apiPost, API_BASE } from './client'

export async function fetchTickets(params = {}) {
  return apiGet('/api/tickets', params)
}

export async function createTicket(ticketData) {
  const res = await apiPost('/api/tickets', ticketData)
  return res.json()
}

export async function updateTicket(ticketId, updateData) {
  const res = await fetch(`${API_BASE}/api/tickets/${ticketId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updateData),
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json()
}

export async function fetchOrders(params = {}) {
  return apiGet('/api/orders', params)
}

export async function createOrder(orderData) {
  const res = await apiPost('/api/orders', orderData)
  return res.json()
}

export async function fetchCustomers() {
  return apiGet('/api/customers')
}
