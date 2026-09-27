import { apiGet, apiPost } from './client'

export const runTrajectoryEval  = () => apiGet('/agent/trajectory-eval', {})
export const runSecurityEval    = () => apiGet('/agent/security-eval', {})
export const evaluateLiveTicket = (data) => apiPost('/agent/evaluate-live', data).then(r => r.json())
export const runLiveEvalAll     = () => apiPost('/agent/evaluate-live-all', {}).then(r => r.json())
