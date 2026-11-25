<template>
  <!-- 右侧顶部栏 -->
  <header
    class="h-16 flex items-center justify-between px-6 bg-surface-container-lowest/90 backdrop-blur-lg border-b border-outline-variant/20 shrink-0 relative z-10"
    style="font-family: 'Space Grotesk', system-ui, sans-serif;"
  >
    <!-- 左侧：用户名 | 系统名称 -->
    <div class="flex items-center gap-3">
      <span class="text-[14px] font-medium text-on-surface">
        {{ authStore.username || '用户' }}
      </span>
      <span class="text-outline-variant select-none">|</span>
      <span class="text-[13px] text-on-surface-variant">
        {{ systemName }}
      </span>
    </div>

    <!-- 右侧：通知图标 + 帮助入口 + 用户图标 -->
    <div class="flex items-center gap-2">
      <!-- 消息通知 -->
      <div class="relative">
        <button
          class="relative p-2 text-on-surface-variant hover:text-primary hover:bg-primary/5 rounded-full transition-colors"
          title="消息通知"
          @click="toggleInbox"
        >
          <span class="material-symbols-outlined text-[22px]">notifications</span>
          <span v-if="inbox.unreadCount > 0" class="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-error text-white text-[10px] leading-4 text-center">
            {{ inbox.unreadCount > 9 ? '9+' : inbox.unreadCount }}
          </span>
        </button>
        <div v-if="showInbox" class="absolute right-0 mt-2 w-[360px] bg-surface-container border border-outline-variant/30 rounded-xl shadow-xl overflow-hidden">
          <div class="px-4 py-3 border-b border-outline-variant/20 flex items-center justify-between">
            <div>
              <p class="text-[13px] font-medium text-on-surface">消息通知</p>
              <p class="text-[11px] text-on-surface-variant">最新 20 条推送</p>
            </div>
            <button class="text-[11px] text-primary hover:underline" @click="loadInbox">刷新</button>
          </div>
          <div v-if="inbox.error" class="px-4 py-3 text-[12px] text-error bg-error/5">{{ inbox.error }}</div>
          <div v-else-if="!inbox.items.length" class="px-4 py-6 text-[12px] text-on-surface-variant text-center">暂无消息</div>
          <div v-else class="max-h-[360px] overflow-auto">
            <button
              v-for="item in inbox.items"
              :key="item.id"
              class="w-full text-left px-4 py-3 border-b border-outline-variant/10 hover:bg-surface-container-low transition-colors"
              @click="markRead(item)"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-[12px] font-medium" :class="item.is_read ? 'text-on-surface-variant' : 'text-on-surface'">{{ item.category_label }}</p>
                  <p class="text-[12px] text-on-surface-variant mt-1 line-clamp-2">{{ item.content }}</p>
                </div>
                <span v-if="!item.is_read" class="mt-1 w-2 h-2 rounded-full bg-error shrink-0"></span>
              </div>
              <p class="text-[11px] text-outline mt-2">{{ item.send_time }}</p>
            </button>
          </div>
        </div>
      </div>

      <!-- 使用说明 -->
      <a
        class="p-2 text-on-surface-variant hover:text-primary hover:bg-primary/5 rounded-full transition-colors"
        title="项目使用说明"
        href="https://my.feishu.cn/docx/Zmh8dUnBnoK65ExHJ5wc2Cncn4b"
        target="_blank"
        rel="noopener noreferrer"
      >
        <span class="material-symbols-outlined text-[22px]">help</span>
      </a>

      <!-- 用户头像 + hover 下拉 -->
      <div
        class="relative ml-1"
        @mouseenter="avatarHover = true"
        @mouseleave="delayClose"
      >
        <div
          class="w-9 h-9 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center
                 text-primary text-sm font-bold cursor-pointer select-none hover:border-primary/60 transition-colors"
        >
          {{ avatarLetter }}
        </div>
        <!-- 下拉菜单 -->
        <Transition name="avatar-fade">
          <div
            v-show="avatarHover"
            class="absolute right-0 top-full mt-1.5 bg-surface-container border border-outline-variant/30 rounded-lg shadow-xl z-[9999] overflow-hidden min-w-[140px]"
            @mouseenter="avatarHover = true"
            @mouseleave="delayClose"
          >
            <div class="px-4 py-2.5 border-b border-outline-variant/20">
              <p class="text-[13px] text-on-surface font-medium">{{ authStore.username || 'User' }}</p>
              <p class="text-[11px] text-on-surface-variant mt-0.5">{{ roleLabel }}</p>
            </div>
            <button
              class="w-full px-4 py-2.5 text-[13px] text-error hover:bg-error/10 transition-colors flex items-center gap-2 text-left"
              @click="handleLogout"
            >
              <span class="material-symbols-outlined text-[18px]">logout</span>
              退出登录
            </button>
          </div>
        </Transition>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAlerts } from '@/api/aiops.js'
import { getInbox, markInboxRead } from '@/api/auditor.js'
import { useAuthStore } from '@/stores/auth'

const ALERT_SEEN_KEY = 'alert_notice_seen_ids_v2'
const ALERT_POLL_INTERVAL = 5000

const router    = useRouter()
const route     = useRoute()
const authStore = useAuthStore()

const avatarHover = ref(false)
const showInbox = ref(false)
let _hoverTimer = null
let _alertPollTimer = null
let _alertDialogOpen = false
const inbox = reactive({ unreadCount: 0, items: [], error: '' })

const roleLabel = computed(() => {
  const map = { operator: '运维人员', admin: '高级运维', auditor: '审计人员' }
  return map[authStore.role] || authStore.role || ''
})

const systemName = computed(() => {
  // 可根据实际业务动态修改
  return '麒翼睿策管理系统'
})

const avatarLetter = computed(() =>
  authStore.username?.charAt(0)?.toUpperCase() || 'U'
)

const canReceiveAlertNotice = computed(() => ['operator', 'admin'].includes(authStore.role))
const isAlertCenterPage = computed(() => route.path === '/operator/warning')

function delayClose() {
  clearTimeout(_hoverTimer)
  _hoverTimer = setTimeout(() => { avatarHover.value = false }, 300)
}

function readSeenAlertIds() {
  try {
    const parsed = JSON.parse(localStorage.getItem(ALERT_SEEN_KEY) || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveSeenAlertIds(ids) {
  try {
    localStorage.setItem(ALERT_SEEN_KEY, JSON.stringify([...new Set(ids)]))
  } catch {
    // ignore persistence failures; alert center remains accessible from nav
  }
}

async function checkNewAlerts() {
  if (!canReceiveAlertNotice.value || isAlertCenterPage.value || _alertDialogOpen) return

  try {
    const alerts = await getAlerts({ status: 'unresolved' })
    const activeAlerts = Array.isArray(alerts) ? alerts : []
    const activeIds = activeAlerts.map((item) => item.id).filter(Boolean)
    if (!activeIds.length) return

    const seenIds = readSeenAlertIds()
    const freshAlerts = activeAlerts.filter((item) => item.id && !seenIds.includes(item.id))
    if (!freshAlerts.length) return

    saveSeenAlertIds([...seenIds, ...activeIds])
    _alertDialogOpen = true
    const criticalCount = freshAlerts.filter((item) => item.level === 'critical').length
    const message = criticalCount > 0
      ? `告警中心新增 ${freshAlerts.length} 条告警，其中 ${criticalCount} 条为严重告警。是否立即前往处理？`
      : `告警中心新增 ${freshAlerts.length} 条告警。是否立即前往处理？`

    try {
      await ElMessageBox.confirm(message, '新告警提醒', {
        confirmButtonText: '前往告警中心',
        cancelButtonText: '稍后处理',
        type: criticalCount > 0 ? 'warning' : 'info',
      })
      await router.push('/operator/warning')
    } catch {
      // user chose to stay on dashboard
    } finally {
      _alertDialogOpen = false
    }
  } catch {
    // keep the top bar quiet if the alert API is temporarily unavailable
  }
}

function startAlertPolling() {
  checkNewAlerts()
  clearInterval(_alertPollTimer)
  _alertPollTimer = setInterval(checkNewAlerts, ALERT_POLL_INTERVAL)
}

async function loadInbox() {
  if (!authStore.token) return
  try {
    const data = await getInbox()
    inbox.unreadCount = data.unread_count || 0
    inbox.items = data.items || []
    inbox.error = ''
  } catch (error) {
    inbox.error = error.message || '消息加载失败'
  }
}

function toggleInbox() {
  showInbox.value = !showInbox.value
  if (showInbox.value) loadInbox()
}

async function markRead(item) {
  if (!item || item.is_read) return
  try {
    await markInboxRead(item.id)
    item.is_read = true
    inbox.unreadCount = Math.max(0, inbox.unreadCount - 1)
  } catch (error) {
    inbox.error = error.message || '消息更新失败'
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  loadInbox()
  startAlertPolling()
})

onUnmounted(() => {
  clearInterval(_alertPollTimer)
  clearTimeout(_hoverTimer)
})

watch(
  () => [authStore.role, route.path],
  () => {
    if (canReceiveAlertNotice.value && !isAlertCenterPage.value) checkNewAlerts()
  },
)

watch(
  () => authStore.token,
  (token) => {
    if (token) {
      loadInbox()
      checkNewAlerts()
    }
  },
)
</script>

<style scoped>
.avatar-fade-enter-active {
  transition: all 0.2s ease-out;
}
.avatar-fade-leave-active {
  transition: all 0.15s ease-in;
}
.avatar-fade-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
.avatar-fade-leave-to {
  opacity: 0;
  transform: translateY(-2px);
}
</style>
