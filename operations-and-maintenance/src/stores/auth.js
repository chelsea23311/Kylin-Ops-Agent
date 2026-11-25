import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

function readPersistedAuth() {
  try {
    const raw = localStorage.getItem('auth')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function persistAuth(payload) {
  try {
    localStorage.setItem('auth', JSON.stringify(payload))
  } catch {
    // ignore persistence failures and keep in-memory auth usable
  }
}

const persisted = readPersistedAuth()

export const useAuthStore = defineStore('auth', () => {
  const token    = ref(persisted?.token ?? null)
  const role     = ref(persisted?.role ?? null)
  const username = ref(persisted?.username ?? null)

  const isLoggedIn = computed(() => !!token.value)

  function login(userData) {
    token.value    = userData.token
    role.value     = userData.role
    username.value = userData.username
    persistAuth({
      token: token.value,
      role: role.value,
      username: username.value,
    })
  }

  function logout() {
    token.value    = null
    role.value     = null
    username.value = null
    try {
      localStorage.removeItem('auth')
    } catch {
      // ignore cleanup failures
    }
  }

  return { token, role, username, isLoggedIn, login, logout }
}, {
  persist: true
})
