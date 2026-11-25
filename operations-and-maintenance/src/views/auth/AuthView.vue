<template>
  <div class="auth-page min-h-screen flex flex-col font-hanken bg-m-surface text-m-on-surface antialiased selection:bg-m-primary-container selection:text-white">
    <main class="flex-1 flex flex-col md:flex-row min-h-screen w-full overflow-hidden">
      <!-- Left Panel: Brand Imagery (Hidden on mobile, always static) -->
      <div class="hidden md:flex md:w-1/2 relative overflow-hidden bg-m-surface-container-highest flex-col justify-start">
        <img
          :src="loginBg"
          alt=""
          class="absolute inset-0 w-full h-full object-cover z-0"
        />
        <!-- Gradient Overlay -->
        <div class="absolute inset-0 bg-gradient-to-t from-m-inverse-surface/40 to-transparent z-10 pointer-events-none"></div>
        <div class="relative z-20 w-full flex justify-center" style="padding-top: 80px;">
          <div
            class="text-center space-y-2 select-none"
            style="color: rgba(26, 35, 126, 0.8); letter-spacing: 1.8em; font-weight: 300;"
          >
            <p class="text-lg uppercase">全方位守护</p>
            <p class="text-lg uppercase">智领运维新高度</p>
          </div>
        </div>
      </div>

      <!-- Right Panel: Form Area with transition -->
      <div
        class="auth-right-panel w-full md:w-[calc(50%+6rem)] flex items-center justify-center bg-m-surface-container-lowest px-margin-mobile md:px-margin-desktop py-12 relative z-10 shadow-[-4px_0_24px_rgba(0,0,0,0.02)]"
      >
        <Transition name="form-slide" mode="out-in">
          <LoginForm v-if="isLogin" key="login" />
          <RegisterForm v-else key="register" />
        </Transition>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import loginBg from '@/images/login_bg.jpg'
import LoginForm from './LoginForm.vue'
import RegisterForm from './RegisterForm.vue'

const route = useRoute()
const isLogin = computed(() => route.path === '/login')
</script>

<style scoped>
/* ── Right panel clip-path curve (desktop) ── */
@media (min-width: 768px) {
  .auth-right-panel {
    clip-path: ellipse(100% 100% at 100% 50%);
    background-color: #ffffff;
    margin-left: -6rem;
  }
}

/* ── Form slide transition (right panel only) ── */
.form-slide-enter-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.form-slide-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.form-slide-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.form-slide-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}
</style>
