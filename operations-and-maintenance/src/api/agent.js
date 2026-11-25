import { get, post } from './request.js'

/**
 * 提交 Agent 任务
 * POST /tasks/run  { task_text: string }
 * → { task_id, status: "running" }
 */
export const runTask = (taskText) => post('/tasks/run', { task_text: taskText })

/**
 * 轮询任务状态
 * GET /tasks/status/{task_id}
 * → { task_id, status, history: string[], context_data: {} }
 */
export const pollTask = (taskId) => get(`/tasks/status/${encodeURIComponent(taskId)}`)

/**
 * 发起任务回滚
 * POST /tasks/{task_id}/rollback { selected_command_ids: string[] }
 */
export const rollbackTask = (taskId, payload = {}) =>
	post(`/tasks/${encodeURIComponent(taskId)}/rollback`, payload)
