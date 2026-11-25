<template>
  <div class="h-full overflow-auto bg-background text-on-surface">
    <main class="p-lg">

      <!-- Page Header Card -->
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-md border border-outline-variant/20 mb-lg">
        <div class="flex flex-col gap-xs pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">监控告警</h1>
        </div>
      </section>

      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-lg mb-lg">
        <div class="bg-surface-container-low rounded-xl border border-error/30 p-lg relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-0.5 bg-error"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-label-caps font-semibold text-error uppercase tracking-wider">严重告警</span>
            <span class="material-symbols-outlined text-error text-[24px]">error</span>
          </div>
          <p class="text-h2 font-bold text-error" style="font-family: 'Space Grotesk', sans-serif;">{{ alertStats.critical }}</p>
          <p class="text-body-sm text-on-surface-variant mt-1">需立即处理</p>
        </div>

        <div class="bg-surface-container-low rounded-xl border border-tertiary-container/30 p-lg relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-0.5 bg-tertiary-container"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-label-caps font-semibold text-tertiary uppercase tracking-wider">警告</span>
            <span class="material-symbols-outlined text-tertiary-container text-[24px]">warning</span>
          </div>
          <p class="text-h2 font-bold text-tertiary" style="font-family: 'Space Grotesk', sans-serif;">{{ alertStats.warning }}</p>
          <p class="text-body-sm text-on-surface-variant mt-1">需关注处理</p>
        </div>

        <div class="bg-surface-container-low rounded-xl border border-primary/30 p-lg relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-0.5 bg-primary"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-label-caps font-semibold text-primary uppercase tracking-wider">信息</span>
            <span class="material-symbols-outlined text-primary text-[24px]">info</span>
          </div>
          <p class="text-h2 font-bold text-primary" style="font-family: 'Space Grotesk', sans-serif;">{{ alertStats.info }}</p>
          <p class="text-body-sm text-on-surface-variant mt-1">常规通知</p>
        </div>

        <div class="bg-surface-container-low rounded-xl border border-tertiary/30 p-lg relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-0.5 bg-tertiary"></div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-label-caps font-semibold text-tertiary uppercase tracking-wider">已恢复</span>
            <span class="material-symbols-outlined text-tertiary text-[24px]">check_circle</span>
          </div>
          <p class="text-h2 font-bold text-tertiary" style="font-family: 'Space Grotesk', sans-serif;">{{ alertStats.resolved }}</p>
          <p class="text-body-sm text-on-surface-variant mt-1">历史归档</p>
        </div>
      </div>

      <!-- Alert Table Card -->
      <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 overflow-hidden">
        <!-- Filters -->
        <div class="px-lg py-md border-b border-outline-variant/20 flex flex-wrap gap-3 items-center">
          <h2 class="text-body-md font-semibold text-on-surface mr-2">告警列表</h2>

          <div class="relative">
            <select v-model="filterLevel" class="py-1.5 pl-3 pr-8 border border-outline-variant rounded bg-surface-container text-on-surface text-body-sm outline-none focus:border-primary transition-colors h-[34px] appearance-none cursor-pointer">
              <option value="">全部级别</option>
              <option value="critical">严重</option>
              <option value="warning">警告</option>
              <option value="info">信息</option>
            </select>
            <span class="material-symbols-outlined absolute right-1.5 top-1/2 -translate-y-1/2 text-outline-variant pointer-events-none text-[18px]">expand_more</span>
          </div>

          <div class="relative">
            <select v-model="filterStatus" class="py-1.5 pl-3 pr-8 border border-outline-variant rounded bg-surface-container text-on-surface text-body-sm outline-none focus:border-primary transition-colors h-[34px] appearance-none cursor-pointer">
              <option value="">全部状态</option>
              <option value="unresolved">未处理</option>
              <option value="resolved">已恢复</option>
            </select>
            <span class="material-symbols-outlined absolute right-1.5 top-1/2 -translate-y-1/2 text-outline-variant pointer-events-none text-[18px]">expand_more</span>
          </div>

          <div class="relative">
            <select v-model="filterApproval" class="py-1.5 pl-3 pr-8 border border-outline-variant rounded bg-surface-container text-on-surface text-body-sm outline-none focus:border-primary transition-colors h-[34px] appearance-none cursor-pointer">
              <option value="">全部审批状态</option>
              <option value="pending">待审批</option>
              <option value="approved">已批准</option>
              <option value="rejected">已拒绝</option>
            </select>
            <span class="material-symbols-outlined absolute right-1.5 top-1/2 -translate-y-1/2 text-outline-variant pointer-events-none text-[18px]">expand_more</span>
          </div>

          <button class="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-[12px] text-on-surface-variant border border-outline-variant rounded hover:bg-surface-container-high transition-colors" @click="loadAlerts" :disabled="alertsLoading">
            <span class="material-symbols-outlined text-[16px]" :class="alertsLoading ? 'animate-spin' : ''">refresh</span>
            刷新
          </button>
        </div>

        <!-- Table -->
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant/20 bg-surface-container">
                <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">级别</th>
                <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">标题</th>
                <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">主机</th>
                <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">告警信息</th>
                <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">状态</th>
                <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">审批状态</th>
                <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">创建时间</th>
                <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase text-right">操作</th>
              </tr>
            </thead>
            <tbody class="text-body-sm divide-y divide-outline-variant/10">
              <tr v-for="alert in filteredAlerts" :key="alert.id" class="hover:bg-surface-variant/30 transition-colors">
                <td class="py-3 px-4">
                  <span :class="levelBadge(alert.level).cls" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border font-medium text-[11px] uppercase">
                    <span class="w-1.5 h-1.5 rounded-full" :class="levelBadge(alert.level).dot"></span>
                    {{ levelLabel(alert.level) }}
                  </span>
                </td>
                <td class="py-3 px-4 font-medium text-on-surface max-w-[180px] truncate" :title="alert.title">{{ alert.title }}</td>
                <td class="py-3 px-4 text-on-surface-variant font-mono text-[12px]">{{ alert.host_id }}</td>
                <td class="py-3 px-4 text-on-surface-variant max-w-[260px] truncate" :title="alert.message">{{ alert.message }}</td>
                <td class="py-3 px-4">
                  <span :class="alert.status === 'unresolved' ? 'bg-tertiary-container/20 text-tertiary-container' : 'bg-tertiary/10 text-tertiary'" class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium">
                    {{ alert.status === 'unresolved' ? '未处理' : '已恢复' }}
                  </span>
                </td>
                <td class="py-3 px-4">
                  <span :class="approvalBadge(alert.agent_approval_status)" class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium">
                    {{ approvalLabel(alert.agent_approval_status) }}
                  </span>
                  <span
                    v-if="alert.linked_task_status"
                    :class="taskStatusBadge(alert.linked_task_status)"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium ml-2"
                  >
                    {{ taskStatusLabel(alert.linked_task_status) }}
                  </span>
                </td>
                <td class="py-3 px-4 text-on-surface-variant text-[12px]">{{ formatTime(alert.created_at) }}</td>
                <td class="py-3 px-4 text-right">
                  <div class="flex gap-2 justify-end flex-wrap">
                    <template v-if="alert.status === 'unresolved' && alert.agent_approval_status === 'pending' && isOperator">
                      <button class="px-3 py-1.5 text-[12px] text-tertiary border border-tertiary/30 rounded hover:bg-tertiary/10 transition-colors" @click="handleApproveAgent(alert, true)" :disabled="actionLoading[alert.id]">批准接手</button>
                      <button class="px-3 py-1.5 text-[12px] text-error border border-error/30 rounded hover:bg-error/10 transition-colors" @click="handleApproveAgent(alert, false)" :disabled="actionLoading[alert.id]">拒绝接手</button>
                    </template>
                    <template v-if="alert.agent_approval_status === 'approved' && alert.linked_task_id">
                      <button class="px-3 py-1.5 text-[12px] text-primary border border-primary/30 rounded hover:bg-primary/10 transition-colors" @click="viewTask(alert.linked_task_id)">查看任务</button>
                      <button v-if="alert.linked_task_status === 'failed' && alert.status === 'unresolved' && isOperator" class="px-3 py-1.5 text-[12px] text-tertiary border border-tertiary/30 rounded hover:bg-tertiary/10 transition-colors" @click="handleRerunAgent(alert)" :disabled="actionLoading[alert.id]">重新执行</button>
                    </template>
                    <template v-if="alert.agent_approval_status !== 'pending'">
                      <button v-if="alert.status === 'unresolved'" class="px-3 py-1.5 text-[12px] text-tertiary border border-tertiary/30 rounded hover:bg-tertiary/10 transition-colors" @click="handleResolve(alert, true)" :disabled="actionLoading[alert.id]">标记已恢复</button>
                      <button v-else class="px-3 py-1.5 text-[12px] text-on-surface-variant border border-outline-variant rounded hover:bg-surface-container-high transition-colors" @click="handleResolve(alert, false)" :disabled="actionLoading[alert.id]">重新打开</button>
                    </template>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="alertsLoading && filteredAlerts.length === 0" class="py-16 text-center text-on-surface-variant">
          <span class="material-symbols-outlined animate-spin text-[32px] mb-3 block">sync</span>
          <p class="text-body-md">加载告警列表中...</p>
        </div>
        <div v-if="alertsError" class="py-16 text-center text-error bg-error/5">
          <p class="text-body-md">{{ alertsError }}</p>
        </div>
        <div v-if="!alertsLoading && !alertsError && filteredAlerts.length === 0" class="py-16 text-center text-on-surface-variant">
          <span class="material-symbols-outlined text-[48px] text-outline mb-3 block">notifications_off</span>
          <p class="text-body-md">暂无告警记录</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getAlerts, approveAgent, rerunAgent, resolveAlert } from '@/api/aiops'

const router = useRouter()
const authStore = useAuthStore()

const isOperator = computed(() => authStore.role === 'operator')

const alerts = ref([])
const alertsLoading = ref(false)
const alertsError = ref('')
const actionLoading = ref({})

const filterLevel = ref('')
const filterStatus = ref('')
const filterApproval = ref('')

const alertStats = computed(() => {
  const all = alerts.value
  const unresolved = all.filter(a => a.status === 'unresolved')
  return {
    critical: unresolved.filter(a => a.level === 'critical').length,
    warning: unresolved.filter(a => a.level === 'warning').length,
    info: unresolved.filter(a => a.level === 'info').length,
    resolved: all.filter(a => a.status === 'resolved').length,
  }
})

const filteredAlerts = computed(() => {
  let list = alerts.value
  if (filterLevel.value) list = list.filter(a => a.level === filterLevel.value)
  if (filterStatus.value) list = list.filter(a => a.status === filterStatus.value)
  if (filterApproval.value) list = list.filter(a => a.agent_approval_status === filterApproval.value)
  return list
})

function levelBadge(level) {
  if (level === 'critical') return { cls: 'bg-error/10 border-error/20 text-error', dot: 'bg-error' }
  if (level === 'warning')  return { cls: 'bg-tertiary/10 border-tertiary/20 text-tertiary', dot: 'bg-tertiary-container' }
  return { cls: 'bg-primary/10 border-primary/20 text-primary', dot: 'bg-primary' }
}
function levelLabel(level) {
  if (level === 'critical') return '严重'
  if (level === 'warning')  return '警告'
  return '信息'
}
function approvalBadge(status) {
  if (status === 'pending')  return 'bg-yellow-50 text-yellow-700 border border-yellow-200'
  if (status === 'approved') return 'bg-tertiary/10 text-tertiary'
  return 'bg-error/10 text-error'
}
function approvalLabel(status) {
  if (status === 'pending')  return '待审批'
  if (status === 'approved') return '已批准'
  return '已拒绝'
}
function taskStatusBadge(status) {
  if (status === 'success') return 'bg-tertiary/10 text-tertiary'
  if (status === 'failed' || status === 'blocked') return 'bg-error/10 text-error'
  if (status === 'awaiting_approval') return 'bg-yellow-50 text-yellow-700 border border-yellow-200'
  return 'bg-primary/10 text-primary'
}
function taskStatusLabel(status) {
  const map = {
    init: '任务初始化',
    perceiving: '任务感知中',
    planning: '任务规划中',
    drafting: '任务生成中',
    reflecting: '任务反思中',
    auditing: '任务审计中',
    guardrail_checking: '护栏检查中',
    approved: '任务已批准',
    awaiting_approval: '待管理员审批',
    success: '任务已完成',
    failed: '任务失败',
    blocked: '任务已拦截',
  }
  return map[status] || `任务${status}`
}
function formatTime(isoStr) {
  if (!isoStr) return ''
  return isoStr.replace('T', ' ').slice(0, 19)
}

async function loadAlerts() {
  alertsLoading.value = true
  alertsError.value = ''
  try {
    const data = await getAlerts({
      level: filterLevel.value || undefined,
      status: filterStatus.value || undefined,
      agent_approval_status: filterApproval.value || undefined,
    })
    alerts.value = data
  } catch (err) {
    alertsError.value = err.message || '加载告警列表失败'
  } finally {
    alertsLoading.value = false
  }
}

async function handleApproveAgent(alert, approved) {
  actionLoading.value = { ...actionLoading.value, [alert.id]: true }
  try {
    const result = await approveAgent(alert.id, approved)
    alert.agent_approval_status = result.agent_approval_status
    if (result.linked_task_id) {
      alert.linked_task_id = result.linked_task_id
      alert.linked_task_status = result.task_status || alert.linked_task_status
      alert.refined_task_text = result.refined_task_text || ''
    }
    const idx = alerts.value.findIndex(a => a.id === alert.id)
    if (idx >= 0) alerts.value[idx] = { ...alert }
    await loadAlerts()
    if (approved && result.linked_task_id) {
      sessionStorage.setItem('pending_agent_task_id', result.linked_task_id)
      await router.push({ path: '/operator/dashboard', query: { agent_task_id: result.linked_task_id, agent_open: '1' } })
    }
  } catch (err) {
    window.alert(`操作失败: ${err.message}`)
  } finally {
    actionLoading.value = { ...actionLoading.value, [alert.id]: false }
  }
}

async function handleResolve(alert, resolve) {
  actionLoading.value = { ...actionLoading.value, [alert.id]: true }
  try {
    const result = await resolveAlert(alert.id, resolve)
    alert.status = result.new_status
    const idx = alerts.value.findIndex(a => a.id === alert.id)
    if (idx >= 0) alerts.value[idx] = { ...alert }
  } catch (err) {
    window.alert(`操作失败: ${err.message}`)
  } finally {
    actionLoading.value = { ...actionLoading.value, [alert.id]: false }
  }
}

async function handleRerunAgent(alert) {
  if (!window.confirm('当前关联任务执行失败，是否重新交给 Agent 执行？')) return
  actionLoading.value = { ...actionLoading.value, [alert.id]: true }
  try {
    const result = await rerunAgent(alert.id)
    alert.linked_task_id = result.linked_task_id
    alert.linked_task_status = result.task_status || 'running'
    alert.refined_task_text = result.refined_task_text || alert.refined_task_text || ''
    const idx = alerts.value.findIndex(a => a.id === alert.id)
    if (idx >= 0) alerts.value[idx] = { ...alert }
    sessionStorage.setItem('pending_agent_task_id', result.linked_task_id)
    await router.push({ path: '/operator/dashboard', query: { agent_task_id: result.linked_task_id, agent_open: '1' } })
  } catch (err) {
    window.alert(`重新执行失败: ${err.message}`)
  } finally {
    actionLoading.value = { ...actionLoading.value, [alert.id]: false }
  }
}

function viewTask(taskId) {
  router.push({ path: '/operator/log-audit', query: { task_id: taskId } })
}

onMounted(() => {
  loadAlerts()
})
</script>
