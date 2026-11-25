import { get, post, postWithTimeout } from './request.js'

/** GET /system/monitor/snapshot */
export const getSnapshot = () => get('/system/monitor/snapshot')

/** POST /system/monitor/resource-report */
export const getResourceReport = (payload = {}) =>
	postWithTimeout('/system/monitor/resource-report', payload, 45000)
