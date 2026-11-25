<template>
  <!-- 整体布局：左侧边栏 + 右侧（顶部栏 + 内容区） -->
  <div class="flex h-screen bg-background overflow-hidden">
    <!-- 左侧导航栏 -->
    <Sidebar />

    <!-- 右侧区域 -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- 顶部栏 -->
      <TopBar />

      <!-- 内容区域 -->
      <div class="flex-1 overflow-hidden">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import Sidebar from '@/components/Sidebar.vue'
import TopBar from '@/components/TopBar.vue'
</script>
