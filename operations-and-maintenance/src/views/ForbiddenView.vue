<template>
  <div class="min-h-screen bg-surface-container-lowest text-on-surface flex items-center justify-center">
    <div class="text-center max-w-md px-8">
      <!-- Icon -->
      <div class="mb-6 flex justify-center">
        <div class="w-24 h-24 rounded-full bg-error/10 border border-error/30 flex items-center justify-center">
          <span class="material-symbols-outlined text-error text-[48px]">block</span>
        </div>
      </div>

      <!-- Code -->
      <h1 class="text-[72px] font-bold text-error/30 mb-2" style="font-family: 'Space Grotesk', sans-serif; line-height: 1;">
        403
      </h1>

      <!-- Title -->
      <h2 class="text-h3 font-semibold text-on-surface mb-3" style="font-family: 'Space Grotesk', sans-serif;">
        访问被拒绝
      </h2>

      <!-- Desc -->
      <p class="text-body-md text-on-surface-variant mb-8 leading-relaxed">
        您没有权限访问该页面。<br />
        请确认您已使用正确的账号登录，或联系管理员分配相应权限。
      </p>

      <!-- Actions -->
      <div class="flex gap-4 justify-center">
        <router-link
          to="/login"
          class="px-6 py-3 bg-primary text-on-primary rounded-lg font-medium hover:bg-primary-fixed transition-colors neon-glow flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-[18px]">login</span>
          重新登录
        </router-link>
        <button
          class="px-6 py-3 border border-outline-variant text-on-surface-variant rounded-lg font-medium hover:bg-surface-container transition-colors flex items-center gap-2"
          @click="$router.go(-1)"
        >
          <span class="material-symbols-outlined text-[18px]">arrow_back</span>
          返回上页
        </button>
      </div>

      <!-- Footer -->
      <p class="text-label-caps text-outline mt-12 uppercase tracking-widest">
        麒翼睿策 · 安全访问控制系统
      </p>
    </div>
  </div>
</template>

<script setup>
</script>
