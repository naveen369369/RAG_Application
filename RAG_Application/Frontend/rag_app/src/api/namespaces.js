import { apiGet } from './client'

export const fetchNamespaces = () =>
  apiGet('/namespaces').then(d => d.namespaces ?? [])

export const fetchHealth = () => apiGet('/health')
