import { createRouter, createWebHistory } from 'vue-router'

// ── Helper: read persisted auth from localStorage ─────────────────
function getPersistedAuth() {
  try {
    const raw = localStorage.getItem('auth')
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed
  } catch {
    return null
  }
}

function getDefaultRoute(role) {
  switch (role) {
    case 'operator': return '/operator/dashboard'
    case 'auditor':  return '/auditor/personnel'
    case 'admin':    return '/operator/dashboard'   // 管理员默认也进运维主页
    default:         return '/login'
  }
}

// ── Routes ─────────────────────────────────────────────────────────
const routes = [
  { path: '/', redirect: '/login' },

  // ── Public (AuthView: login & register share same component) ──
  {
    path: '/login',
    component: () => import('../views/auth/AuthView.vue'),
    meta: { public: true }
  },
  {
    path: '/register',
    component: () => import('../views/auth/AuthView.vue'),
    meta: { public: true }
  },
  {
    path: '/403',
    component: () => import('../views/ForbiddenView.vue'),
    meta: { public: true }
  },

  // ── Operator（运维人员 + 管理员均可访问） ──────────────────────
  {
    path: '/operator',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { roles: ['operator', 'admin'] },
    children: [
      { path: '',          redirect: '/operator/dashboard' },
      { path: 'dashboard', component: () => import('../views/operator/DashboardView.vue') },
      { path: 'tools',     component: () => import('../views/operator/ToolsView.vue') },
      { path: 'kb',        component: () => import('../views/operator/KnowledgeBaseView.vue') },
      { path: 'files',     component: () => import('../views/operator/FileView.vue') },
      { path: 'log-audit', component: () => import('../views/operator/LogAuditView.vue') },
      { path: 'warning',   component: () => import('../views/operator/WarningView.vue') },
    ]
  },

  // ── Auditor ──────────────────────────────────────────────────────
  {
    path: '/auditor',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { roles: ['auditor'] },
    children: [
      { path: '',              redirect: '/auditor/personnel' },
      { path: 'personnel',     component: () => import('../views/auditor/PersonnelList.vue') },
      { path: 'personnel/:id', component: () => import('../views/auditor/PersonnelDetail.vue') },
      { path: 'lobby',         component: () => import('../views/auditor/LobbyView.vue') },
      { path: 'trace/:id',     component: () => import('../views/auditor/LobbyView.vue') },
      { path: 'security',      component: () => import('../views/auditor/SecuritySettings.vue') },
      { path: 'messages',      component: () => import('../views/auditor/MessagePush.vue') },
    ]
  },

  // ── Admin（审批管理 — 仅管理员可访问） ──────────────────────────
  {
    path: '/admin',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { roles: ['admin'] },
    children: [
      { path: '',         redirect: '/admin/approval' },
      { path: 'approval', component: () => import('../views/admin/ApprovalView.vue') },
    ]
  },

  // ── Catch-all ─────────────────────────────────────────────────────
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ── Navigation Guard ──────────────────────────────────────────────
router.beforeEach((to, _from, next) => {
  const auth        = getPersistedAuth()
  const isLoggedIn  = !!(auth?.token)
  const userRole    = auth?.role

  // Public routes
  if (to.meta.public) {
    // Already logged in — redirect away from /login
    if (isLoggedIn && to.path === '/login') {
      return next(getDefaultRoute(userRole))
    }
    return next()
  }

  // Not logged in
  if (!isLoggedIn) return next('/login')

  // Role check (check parent meta via matched records)
  const requiredRoles = to.matched.find(r => r.meta?.roles)?.meta?.roles
  if (requiredRoles && !requiredRoles.includes(userRole)) {
    return next('/403')
  }

  next()
})

// 发布后若用户停留在旧页面，动态 chunk 可能失效并导致页面持续 loading。
// 这里自动强刷一次（仅一次）恢复到最新资源。
router.onError((err) => {
  const message = String(err?.message || err || '')
  const isChunkLoadError =
    /Failed to fetch dynamically imported module/i.test(message) ||
    /Importing a module script failed/i.test(message) ||
    /Loading chunk [\w-]+ failed/i.test(message)

  if (!isChunkLoadError) return

  const retryKey = '__chunk_reload_once__'
  if (sessionStorage.getItem(retryKey) === '1') return

  sessionStorage.setItem(retryKey, '1')
  const url = new URL(window.location.href)
  url.searchParams.set('_v', String(Date.now()))
  window.location.replace(url.toString())
})

export default router
export { getDefaultRoute }
