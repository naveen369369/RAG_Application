import { apiPost, apiGet } from './client'

export const discoverChunks = () =>
  apiPost('/golden/discover', {}).then(r => r.json())

export const evaluateHitRate = ({ top_k, use_reranker, use_hyde }) =>
  apiGet('/golden/evaluate', { top_k, use_reranker, use_hyde })
