import { get, post } from './request.js'

/** GET /api/v1/aiops/overview?auto_trigger=true */
export const getOverview = (autoTrigger = true) =>
  get(`/api/v1/aiops/overview?auto_trigger=${autoTrigger}`)

/** POST /api/v1/aiops/alerts/evaluate */
export const evaluateAlerts = () =>
  post('/api/v1/aiops/alerts/evaluate')

/** GET /api/v1/aiops/alerts */
export const getAlerts = (params = {}) => {
  const qs = new URLSearchParams()
  if (params.level) qs.set('level', params.level)
  if (params.status) qs.set('status', params.status)
  if (params.agent_approval_status) qs.set('agent_approval_status', params.agent_approval_status)
  const query = qs.toString()
  return get(`/api/v1/aiops/alerts${query ? '?' + query : ''}`)
}

/** GET /api/v1/aiops/alerts/{alert_id} */
export const getAlertDetail = (alertId) =>
  get(`/api/v1/aiops/alerts/${alertId}`)

/** POST /api/v1/aiops/alerts/{alert_id}/approve-agent */
export const approveAgent = (alertId, approved) =>
  post(`/api/v1/aiops/alerts/${alertId}/approve-agent`, { approved })

/** POST /api/v1/aiops/alerts/{alert_id}/rerun-agent */
export const rerunAgent = (alertId) =>
  post(`/api/v1/aiops/alerts/${alertId}/rerun-agent`)

/** POST /api/v1/aiops/alerts/{alert_id}/resolve */
export const resolveAlert = (alertId, resolve = true) =>
  post(`/api/v1/aiops/alerts/${alertId}/resolve`, { resolve })
