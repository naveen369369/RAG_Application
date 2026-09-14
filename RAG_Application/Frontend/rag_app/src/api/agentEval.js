import { apiGet } from './client'

export const runTrajectoryEval  = () => apiGet('/agent/trajectory-eval', {})
export const runSecurityEval    = () => apiGet('/agent/security-eval', {})
