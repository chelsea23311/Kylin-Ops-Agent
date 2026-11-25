import { get, post } from './request.js'

/** GET /tools/config/ */
export const getTools = () => get('/tools/config/')

/** POST /tools/config/{name}/disable */
export const disableTool = (name) => post(`/tools/config/${name}/disable`)

/** POST /tools/config/{name}/enable */
export const enableTool = (name) => post(`/tools/config/${name}/enable`)
