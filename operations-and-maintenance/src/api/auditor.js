import { get, post, request } from './request.js'

export const getPersonnelList = () => get('/api/v1/audit/personnel')

export const getPersonnelDetail = (userId) =>
  get(`/api/v1/audit/personnel/${encodeURIComponent(userId)}`)

export const updatePersonnel = (userId, payload) =>
  request(`/api/v1/audit/personnel/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const deletePersonnel = (userId) =>
  request(`/api/v1/audit/personnel/${encodeURIComponent(userId)}`, { method: 'DELETE' })

export const getSecuritySettings = () => get('/api/v1/audit/security-settings')

export const updateSecuritySettings = (payload) =>
  request('/api/v1/audit/security-settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const getMessages = () => get('/api/v1/audit/messages')

export const createMessage = (payload) => post('/api/v1/audit/messages', payload)

export const deleteMessage = (messageId) =>
  request(`/api/v1/audit/messages/${messageId}`, { method: 'DELETE' })

export const getInbox = () => get('/api/v1/audit/messages/inbox')

export const markInboxRead = (messageId) =>
  post(`/api/v1/audit/messages/inbox/${messageId}/read`)

export const getFileList = (path) =>
  get(`/api/v1/audit/files/list?path=${encodeURIComponent(path)}`)

export const readFileContent = (path) =>
  post('/api/v1/audit/files/read', { path })

export const writeFileContent = (path, content) =>
  post('/api/v1/audit/files/write', { path, content })

export const deleteFileEntry = (path) =>
  post('/api/v1/audit/files/delete', { path })
