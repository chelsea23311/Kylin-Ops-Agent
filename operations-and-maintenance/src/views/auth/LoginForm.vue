<template>
  <div class="w-full max-w-form-width">
    <!-- Header -->
    <div class="mb-10">
      <h2
        class="font-hanken text-m-headline-lg-mobile md:text-m-headline-lg mb-2 font-normal"
        style="color: #4B5563;"
      >
        麒翼睿策
      </h2>
      <p class="font-hanken text-m-body-md text-m-outline">
        麒麟操作系统安全智能运维平台
      </p>
    </div>

    <!-- Form -->
    <form class="space-y-6" @submit.prevent="handleLogin">
      <!-- Username Input -->
      <div class="relative">
        <span
          class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-m-outline pointer-events-none"
          style="font-size: 20px;"
        >
          person
        </span>
        <input
          v-model="form.username"
          type="text"
          placeholder="用户名/邮箱"
          required
          class="auth-input w-full h-[48px] bg-m-surface-container-low border-0 focus:ring-1 focus:ring-m-primary-container rounded py-3 pl-10 pr-4 font-hanken text-m-body-md text-m-on-surface placeholder:text-m-outline transition-shadow outline-none"
        />
      </div>

      <!-- Password Input -->
      <div class="relative mt-gutter">
        <span
          class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-m-outline pointer-events-none"
          style="font-size: 20px;"
        >
          lock
        </span>
        <input
          v-model="form.password"
          type="password"
          placeholder="密码"
          required
          class="auth-input w-full h-[48px] bg-m-surface-container-low border-0 focus:ring-1 focus:ring-m-primary-container rounded py-3 pl-10 pr-4 font-hanken text-m-body-md text-m-on-surface placeholder:text-m-outline transition-shadow outline-none"
        />
      </div>

      <!-- Error message -->
      <div
        v-if="errorMsg"
        class="text-m-error text-m-label-sm bg-m-error-container/40 border border-m-error/30 rounded px-3 py-2.5"
      >
        {{ errorMsg }}
      </div>

      <!-- Options -->
      <div class="flex items-center justify-between pt-1 pb-2">
        <label class="flex items-center gap-2 cursor-pointer group">
          <input
            v-model="form.remember"
            type="checkbox"
            class="w-[18px] h-[18px] rounded-[2px] text-m-primary-container border-m-outline-variant bg-m-surface-container-lowest focus:ring-m-primary-container focus:ring-offset-m-surface-container-lowest"
          />
          <span class="font-hanken text-m-label-sm text-m-on-surface-variant group-hover:text-m-on-surface transition-colors">
            记住密码
          </span>
        </label>
        <a
          class="font-hanken text-m-label-sm text-m-primary-container hover:text-m-primary transition-colors hover:underline underline-offset-2 cursor-pointer"
        >
          忘记密码
        </a>
      </div>

      <!-- Submit Button -->
      <button
        type="submit"
        :disabled="loading"
        class="w-full h-[48px] bg-m-primary-container text-white font-hanken text-m-title-md rounded shadow-[0_4px_10px_rgba(70,88,255,0.1)] hover:bg-m-primary active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:scale-100"
      >
        {{ loading ? '登录中...' : '立即登录' }}
        <span class="material-symbols-outlined" style="font-size: 20px;">arrow_forward</span>
      </button>
    </form>

    <!-- Footer Links -->
    <div class="mt-10 text-center">
      <span class="font-hanken text-m-label-sm text-m-on-surface-variant">还没有账号？</span>
      <router-link
        to="/register"
        class="font-hanken text-m-label-sm text-m-primary-container hover:text-m-primary hover:underline underline-offset-2 ml-1 transition-colors"
      >
        注册账号
      </router-link>
    </div>

    <!-- 登录说明 -->
    <div class="mt-6 text-center">
      <p class="text-[10px] tracking-widest uppercase text-m-outline font-hanken">
        &copy; 2026 麒翼睿策 &middot; ALL RIGHTS RESERVED.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getDefaultRoute } from '@/router'
import { login } from '@/api/auth.js'

const router    = useRouter()
const authStore = useAuthStore()

const form     = reactive({ username: '', password: '', remember: false })
const loading  = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  errorMsg.value = ''
  loading.value  = true
  try {
    const data = await login(form.username, form.password)
    const target = getDefaultRoute(data.role)
    authStore.login({
      token:    data.access_token,
      role:     data.role,
      username: form.username,
    })
    loading.value = false
    window.location.assign(target)
    return
  } catch (e) {
    errorMsg.value = e.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ── Custom input styling ── */
.auth-input {
  background-color: #f2f4f5;
}
.auth-input::placeholder {
  color: #757688;
}
.auth-input:focus {
  outline: none;
  box-shadow: 0 0 0 1px #4658ff;
  background-color: #ffffff;
}

/* ── Checkbox styling ── */
input[type="checkbox"] {
  accent-color: #4658ff;
}
</style>
