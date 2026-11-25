<template>
  <div class="w-full max-w-form-width">
    <!-- Header -->
    <div class="mb-8">
      <h2
        class="font-hanken text-m-headline-lg-mobile md:text-m-headline-lg mb-2 font-normal"
        style="color: #4B5563;"
      >
        注册账号
      </h2>
      <p class="font-hanken text-m-body-md text-m-outline">
        麒麟操作系统安全智能运维平台
      </p>
    </div>

    <!-- Form -->
    <form class="space-y-5" @submit.prevent="handleRegister">
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
      <div class="relative">
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

      <!-- Role Select -->
      <div class="relative">
        <span
          class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-m-outline pointer-events-none"
          style="font-size: 20px;"
        >
          badge
        </span>
        <select
          v-model="form.role"
          required
          class="auth-input w-full h-[48px] bg-m-surface-container-low border-0 focus:ring-1 focus:ring-m-primary-container rounded py-3 pl-10 pr-10 font-hanken text-m-body-md text-m-on-surface transition-shadow outline-none appearance-none cursor-pointer"
          :class="{ 'text-m-outline': !form.role }"
        >
          <option value="" disabled>选择注册角色...</option>
          <option value="operator">运维人员 / Operator</option>
          <option value="auditor">审计人员 / Auditor</option>
        </select>
        <span
          class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-m-outline pointer-events-none"
          style="font-size: 20px;"
        >
          expand_more
        </span>
      </div>
      <p class="text-[12px] text-m-on-surface-variant -mt-3 pl-1">管理员账号仅可由管理员后台创建，不能自助注册。</p>

      <!-- Registration Key -->
      <div class="relative">
        <span
          class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-m-outline pointer-events-none"
          style="font-size: 20px;"
        >
          key
        </span>
        <input
          v-model="form.regKey"
          type="text"
          placeholder="输入系统授权密钥"
          required
          class="auth-input w-full h-[48px] bg-m-surface-container-low border-0 focus:ring-1 focus:ring-m-primary-container rounded py-3 pl-10 pr-4 font-hanken text-m-body-md text-m-on-surface placeholder:text-m-outline transition-shadow outline-none"
        />
      </div>

      <!-- Success msg -->
      <div
        v-if="successMsg"
        class="text-m-on-tertiary-fixed-variant text-m-label-sm bg-m-tertiary-container/20 border border-m-tertiary/30 rounded px-3 py-2.5"
      >
        {{ successMsg }}
      </div>

      <!-- Error msg -->
      <div
        v-if="errorMsg"
        class="text-m-error text-m-label-sm bg-m-error-container/40 border border-m-error/30 rounded px-3 py-2.5"
      >
        {{ errorMsg }}
      </div>

      <!-- Submit Button -->
      <button
        type="submit"
        :disabled="loading"
        class="w-full h-[48px] bg-m-primary-container text-white font-hanken text-m-title-md rounded shadow-[0_4px_10px_rgba(70,88,255,0.1)] hover:bg-m-primary active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:scale-100"
      >
        {{ loading ? '注册中...' : '立即注册' }}
        <span class="material-symbols-outlined" style="font-size: 20px;">arrow_forward</span>
      </button>
    </form>

    <!-- Footer Links -->
    <div class="mt-10 text-center">
      <span class="font-hanken text-m-label-sm text-m-on-surface-variant">已有账号？</span>
      <router-link
        to="/login"
        class="font-hanken text-m-label-sm text-m-primary-container hover:text-m-primary hover:underline underline-offset-2 ml-1 transition-colors"
      >
        返回登录
      </router-link>
    </div>

    <!-- Footer -->
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
import { register } from '@/api/auth.js'

const router = useRouter()

const form = reactive({ username: '', password: '', role: '', regKey: '' })
const loading    = ref(false)
const successMsg = ref('')
const errorMsg   = ref('')

async function handleRegister() {
  successMsg.value = ''
  errorMsg.value   = ''
  loading.value    = true

  try {
    await register(form.username, form.password, form.role, form.regKey)
    successMsg.value = '注册成功！正在跳转到登录页面...'
    await new Promise(r => setTimeout(r, 1000))
    loading.value = false
    window.location.assign('/login')
    return
  } catch (e) {
    errorMsg.value = e.message || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ── Custom input/select styling ── */
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

/* ── Select dropdown text color for placeholder state ── */
select.auth-input {
  color: #1a1b24;
}
select.auth-input.text-m-outline {
  color: #757688;
}
</style>
