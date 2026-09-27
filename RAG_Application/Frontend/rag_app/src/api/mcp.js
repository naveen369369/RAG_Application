import { apiGet } from './client'

export async function fetchMcpServers() {
  return apiGet('/api/mcp/servers')
}

export async function fetchMcpTicketHistory(ticketId) {
  return apiGet(`/api/mcp/history/${encodeURIComponent(ticketId)}`)
}

export async function fetchMcpWire() {
  return apiGet('/api/mcp/wire')
}

export async function fetchMcpArtifacts() {
  return apiGet('/api/mcp/artifacts')
}
