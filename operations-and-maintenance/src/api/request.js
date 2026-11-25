/**
 * 基础请求工具
 * - 自动附加 Authorization 头（从 localStorage 读取 Pinia 持久化的 token）
 * - 统一错误处理
 */
function getToken() {
  try {
    const stored = localStorage.getItem('auth')
    return stored ? JSON.parse(stored).token : null
  } catch {
    return null
  }
}

const EXPLICIT_API_BASE_URL = String(import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

function getApiBaseUrl() {
  if (EXPLICIT_API_BASE_URL) return EXPLICIT_API_BASE_URL

  if (typeof window !== 'undefined' && window.location?.origin) {
    if (import.meta.env.PROD && window.location.port === '5174') {
      return `${window.location.protocol}//${window.location.hostname}:8000`
    }
    return window.location.origin
  }

  return 'http://127.0.0.1:8000'
}

export { getApiBaseUrl }

export function buildApiUrl(url) {
  if (/^https?:\/\//i.test(url)) return url
  if (!EXPLICIT_API_BASE_URL && typeof window !== 'undefined' && window.location?.origin && !(import.meta.env.PROD && window.location.port === '5174')) {
    return url.startsWith('/') ? url : `/${url}`
  }
  const base = getApiBaseUrl()
  return `${base}${url.startsWith('/') ? url : `/${url}`}`
}

export async function request(url, options = {}) {
  const token = getToken()
  const headers = { ...options.headers }
  const timeoutMs = Number(options.timeoutMs || 0)
  const controller = timeoutMs > 0 ? new AbortController() : null
  const timeoutId = controller ? setTimeout(() => controller.abort(), timeoutMs) : null
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let resp
  try {
    resp = await fetch(buildApiUrl(url), { ...options, headers, signal: controller?.signal })
  } catch (err) {
    if (err?.name === 'AbortError') {
      throw new Error(`请求超时（${timeoutMs}ms）`)
    }
    throw err
  } finally {
    if (timeoutId) clearTimeout(timeoutId)
  }

  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`
    try {
      const err = await resp.json()
      msg = err.detail || err.message || msg
    } catch { /* ignore */ }
    if (resp.status === 401) {
      try {
        localStorage.removeItem('auth')
        sessionStorage.removeItem('__chunk_reload_once__')
      } catch { /* ignore */ }
      if (typeof window !== 'undefined' && window.location?.pathname !== '/login') {
        const next = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `/login?next=${next}`
      }
    }
    throw new Error(msg)
  }

  return resp.json()
}

export const get = (url) => request(url)

export const post = (url, body = {}) =>
  request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export const postWithTimeout = (url, body = {}, timeoutMs = 0) =>
  request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    timeoutMs,
  })

export const postForm = (url, params) =>
  request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params).toString(),
  })
