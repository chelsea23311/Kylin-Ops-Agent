import { get } from './request.js'

/** GET /knowledge/search?q=...&top_k=5 */
export const searchKnowledge = (q, topK = 5) =>
  get(`/knowledge/search?q=${encodeURIComponent(q)}&top_k=${topK}`)
