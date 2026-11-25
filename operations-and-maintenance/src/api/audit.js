import { get, post } from './request.js'

/** GET /tasks/audit/all-tasks?skip=0&limit=100 */
export const getAllTasks = (skip = 0, limit = 100) =>
  get(`/tasks/audit/all-tasks?skip=${skip}&limit=${limit}`)

/** GET /tasks/audit/full-trace/{task_id} */
export const getFullTrace = (taskId) =>
  get(`/tasks/audit/full-trace/${taskId}`)

/** GET /tasks/pending-approvals */
export const getPendingApprovals = () =>
  get('/tasks/pending-approvals')

/** POST /tasks/{task_id}/approve?action=approve|reject */
export const approveTask = (taskId, action, payload = {}) =>
  post(`/tasks/${taskId}/approve?action=${action}`, payload)
