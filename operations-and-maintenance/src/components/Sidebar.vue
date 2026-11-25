<template>
  <!-- 左侧导航栏 -->
  <aside
    class="flex flex-col h-screen bg-surface-container-low border-r border-outline-variant/30 shrink-0 select-none"
    style="width: 200px;"
  >
    <!-- Logo / 系统名称 -->
    <div class="h-16 flex items-center px-5 border-b border-outline-variant/20 shrink-0">
      <span
        class="text-xl font-bold tracking-tighter text-primary select-none"
        style="font-family: 'Space Grotesk', system-ui, sans-serif;"
      >
        麒翼睿策
      </span>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 overflow-y-auto py-3 px-3 flex flex-col gap-0.5">
      <router-link
        v-for="tab in currentTabs"
        :key="tab.to"
        :to="tab.to"
        :class="[
          'flex items-center gap-3 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-all duration-200 cursor-pointer active:opacity-80',
          isTabActive(tab.to)
            ? 'bg-primary/10 text-primary border border-primary/20'
            : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high border border-transparent'
        ]"
      >
        <span class="material-symbols-outlined text-[20px]">{{ tab.icon }}</span>
        <span>{{ tab.label }}</span>
      </router-link>
    </nav>

    <!-- 底部版本信息 -->
    <div class="px-5 py-3 border-t border-outline-variant/20 shrink-0">
      <p class="text-[11px] text-on-surface-variant/50">v0.1.0 · 麒翼睿策</p>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route     = useRoute()
const authStore = useAuthStore()

// ── Tab 配置（按角色） ──────────────────────────────────────
const tabsMap = {
  operator: [
    { label: '运维主页',  to: '/operator/dashboard', icon: 'dashboard'       },
    { label: '监控告警',  to: '/operator/warning',   icon: 'monitoring' },
    { label: '工具禁用',  to: '/operator/tools',     icon: 'build'            },
    { label: '文件',      to: '/operator/files',     icon: 'folder'           },
    { label: '日志审计',  to: '/operator/log-audit', icon: 'receipt_long'     },
    { label: '知识库',    to: '/operator/kb',        icon: 'menu_book'        },
  ],
  admin: [
    { label: '运维主页',  to: '/operator/dashboard', icon: 'dashboard'       },
    { label: '监控告警',  to: '/operator/warning',   icon: 'monitoring' },
    { label: '审批管理',  to: '/admin/approval',     icon: 'fact_check'       },
    { label: '工具禁用',  to: '/operator/tools',     icon: 'build'            },
    { label: '文件',      to: '/operator/files',     icon: 'folder'           },
    { label: '日志审计',  to: '/operator/log-audit', icon: 'receipt_long'     },
    { label: '知识库',    to: '/operator/kb',        icon: 'menu_book'        },
  ],
  auditor: [
    { label: '人员列表',  to: '/auditor/personnel',  icon: 'people'           },
    { label: '日志审计',  to: '/auditor/lobby',      icon: 'receipt_long'     },
    { label: '安全设置',  to: '/auditor/security',   icon: 'shield'           },
    { label: '消息推送',  to: '/auditor/messages',   icon: 'campaign'         },
  ],
}

const currentTabs = computed(() => tabsMap[authStore.role] || [])

const isTabActive = (to) => {
  // 精确匹配或子路径匹配
  if (route.path === to) return true
  if (to !== '/' && route.path.startsWith(to + '/')) return true
  // 对于 /operator 下的路由，特殊处理
  return false
}
</script>
