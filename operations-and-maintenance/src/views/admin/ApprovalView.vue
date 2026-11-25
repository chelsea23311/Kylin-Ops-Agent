<template>
  <div class="h-full overflow-auto bg-background text-on-background">
    <main class="flex-1 max-w-[1920px] w-full mx-auto p-xl">

      <!-- Page Header Card -->
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-md border border-outline-variant/20 mb-lg">
        <div class="flex flex-col gap-xs pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">待审批任务</h1>
        </div>
      </section>

      <!-- Two-panel layout -->
      <div class="grid grid-cols-12 gap-gutter" style="height: calc(100vh - 200px);">

        <!-- ── Left: Task List (4 cols) ── -->
        <div class="col-span-12 lg:col-span-4 flex flex-col bg-surface-container rounded-xl shadow-card overflow-hidden border border-outline-variant/20 h-full">
          <div class="p-md border-b border-outline-variant/20 flex justify-between items-center bg-surface-container-high">
            <h3 class="text-primary uppercase tracking-widest font-semibold" style="font-family: 'Space Grotesk', sans-serif; font-size: 13px;">待审批任务</h3>
            <span class="bg-surface-container-highest text-primary px-3 py-1 rounded-full text-[12px] font-medium border border-primary/20">
              {{ tasks.filter(t => t.status === 'pending').length }} 个待处理
            </span>
          </div>

          <div class="flex-1 overflow-y-auto divide-y divide-outline-variant/10">
            <div v-if="loading" class="p-md text-body-sm text-on-surface-variant">正在加载待审批任务...</div>
            <div v-else-if="errorMsg" class="p-md text-body-sm text-error bg-error-container/20 border border-error/30 m-md rounded">
              {{ errorMsg }}
            </div>
            <div v-else-if="tasks.length === 0" class="p-md text-body-sm text-on-surface-variant">当前没有待审批任务。</div>
            <div
              v-else
              v-for="task in tasks"
              :key="task.id"
              :class="[
                'p-md border-l-4 cursor-pointer transition-colors relative',
                selectedTask?.id === task.id
                  ? 'bg-surface-variant/40 border-l-tertiary'
                  : 'border-l-transparent hover:bg-surface-variant/20'
              ]"
              @click="selectTask(task)"
            >
              <!-- Gradient overlay for active -->
              <div v-if="selectedTask?.id === task.id"
                   class="absolute inset-0 bg-gradient-to-r from-tertiary/5 to-transparent pointer-events-none"></div>

              <div class="flex justify-between items-start mb-2 relative z-10">
                <span class="text-on-surface-variant" style="font-family: 'Inter', monospace; font-size: 12px;">{{ task.id }}</span>
                <span :class="['inline-flex items-center gap-xs px-sm py-xs border rounded-sm font-semibold text-[11px] uppercase tracking-wide', riskBadge(task.risk).cls]">
                  <span class="material-symbols-outlined text-[14px]">{{ riskBadge(task.risk).icon }}</span>
                  {{ task.risk }}风险
                </span>
              </div>
              <p class="font-bold text-on-surface mb-2 text-[16px] relative z-10 leading-snug">{{ task.desc }}</p>
              <div class="flex flex-wrap gap-x-4 gap-y-1 text-body-sm text-on-surface-variant relative z-10">
                <div class="flex items-center gap-1">
                  <span class="material-symbols-outlined text-[16px] text-primary">person</span>
                  <span>{{ task.operator }}</span>
                </div>
                <div class="flex items-center gap-1">
                  <span class="material-symbols-outlined text-[16px] text-primary">schedule</span>
                  <span>{{ task.timeAgo }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Right: Task Detail (8 cols) ── -->
        <div class="col-span-12 lg:col-span-8 bg-surface-container/60 backdrop-blur-md rounded-xl shadow-card flex flex-col h-full border border-primary/20 relative overflow-hidden">
          <!-- Decorative glow -->
          <div class="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-[80px] pointer-events-none"></div>

          <!-- Placeholder when nothing selected -->
          <div v-if="!selectedTask" class="flex-1 flex items-center justify-center">
            <div class="text-center text-on-surface-variant">
              <span class="material-symbols-outlined text-[64px] text-outline mb-4 block">inbox</span>
              <p class="text-body-lg">选择左侧任务查看详情</p>
            </div>
          </div>

          <!-- Task Detail -->
          <template v-else>
            <!-- Detail Header -->
            <div class="p-xl border-b border-outline-variant/20 flex justify-between items-start bg-surface-container-high rounded-t-xl relative z-10">
              <div>
                <h2 class="font-semibold text-on-surface leading-snug" style="font-family: 'Space Grotesk', sans-serif; font-size: 20px;">
                  {{ selectedTask.desc }}
                </h2>
                <div class="flex gap-md mt-sm">
                  <span class="text-body-sm text-on-surface-variant flex items-center gap-1">
                    <span class="material-symbols-outlined text-[16px]">tag</span> {{ selectedTask.id }}
                  </span>
                  <span class="text-body-sm text-on-surface-variant">|</span>
                  <span class="text-body-sm text-on-surface-variant flex items-center gap-1">
                    <span class="material-symbols-outlined text-[16px]">input</span> 手动触发
                  </span>
                </div>
              </div>
              <span :class="['inline-flex items-center gap-xs px-md py-sm border rounded-sm font-semibold text-[12px] uppercase tracking-wide', riskBadge(selectedTask.risk).cls]">
                风险等级: {{ selectedTask.risk }} (Score: {{ selectedTask.score }})
              </span>
            </div>

            <!-- Detail Content -->
            <div class="p-xl flex-1 overflow-y-auto flex flex-col gap-xl relative z-10">

              <!-- Command Preview -->
              <div>
                <h4 class="text-label-caps font-semibold text-primary mb-sm uppercase tracking-wider flex items-center gap-2">
                  <span class="material-symbols-outlined text-[18px]">terminal</span>
                  待审批命令列表
                </h4>
                <div class="bg-[#252b33] p-md rounded-lg font-mono text-[13px] text-[#e8f1ff] border border-[#48515e] overflow-x-auto shadow-inner relative flex flex-col gap-2">
                  <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/70 to-transparent"></div>
                  <label v-for="cmd in selectedTask.commandOptions" :key="cmd.id" class="flex items-start gap-2 px-2 py-1 rounded border border-[#566170] bg-[#303743] hover:bg-[#36404d] transition-colors">
                    <input
                      type="checkbox"
                      class="mt-1 accent-[#2fbf7a]"
                      :value="cmd.id"
                      v-model="selectedTask.selectedCommandIds"
                    />
                    <div class="flex-1 min-w-0">
                      <div class="break-all text-[#f8fbff]">{{ cmd.command }}</div>
                      <div class="text-[11px] text-[#aeb9c8] mt-1 flex gap-3">
                        <span>工具: {{ cmd.tool }}</span>
                        <span>风险: {{ Number(cmd.risk_score ?? 0).toFixed(2) }}</span>
                        <span v-if="cmd.need_root" class="text-[#f6d365]">需要 root</span>
                      </div>
                    </div>
                  </label>
                  <div v-if="!selectedTask.commandOptions.length" class="text-[#aeb9c8]">（无可用命令预览）</div>
                </div>
              </div>

              <!-- Trigger Reason -->
              <div>
                <h4 class="text-label-caps font-semibold text-on-surface-variant mb-sm uppercase tracking-wider">触发原因</h4>
                <div class="bg-surface-container-high rounded-lg p-md border border-outline-variant/20">
                  <p class="text-body-md text-on-surface flex items-start gap-2">
                    <span class="material-symbols-outlined text-error text-[18px] mt-0.5">policy</span>
                    {{ selectedTask.reason }}
                  </p>
                </div>
              </div>

              <!-- Perception Summary -->
              <div>
                <h4 class="text-label-caps font-semibold text-secondary mb-sm uppercase tracking-wider">感知摘要</h4>
                <div class="bg-surface-container-high/80 p-md rounded-lg border-l-4 border-secondary shadow-sm flex items-start gap-md">
                  <span class="material-symbols-outlined text-secondary text-[24px] mt-[2px]">visibility</span>
                  <p class="text-body-sm text-on-surface">{{ selectedTask.perception }}</p>
                </div>
              </div>

              <!-- Reflection Note -->
              <div>
                <h4 class="text-label-caps font-semibold text-tertiary mb-sm uppercase tracking-wider">Agent反思说明</h4>
                <div class="bg-surface-container-high/80 p-md rounded-lg border-l-4 border-tertiary shadow-sm">
                  <p class="text-body-md text-on-surface flex gap-sm items-start">
                    <span class="material-symbols-outlined text-tertiary mt-[2px]">psychology</span>
                    <span>{{ selectedTask.reflection }}</span>
                  </p>
                </div>
              </div>
            </div>

            <!-- Action Footer -->
            <div class="p-xl border-t border-outline-variant/20 bg-surface-container-high rounded-b-xl flex justify-end gap-md relative z-10">
              <button
                class="h-[44px] px-xl border border-error text-error text-body-md font-medium rounded-lg hover:bg-error/10 hover:shadow-neon-error transition-all flex items-center gap-sm uppercase tracking-wider disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="actionLoading"
                @click="handleAction('reject')"
              >
                <span class="material-symbols-outlined">close</span>
                拒绝执行
              </button>
              <button
                class="h-[44px] px-xl bg-[#0b5d3f] text-white text-body-md font-bold rounded-lg hover:bg-[#0f704d] shadow-[0_0_18px_rgba(18,123,83,0.26)] transition-all flex items-center gap-sm uppercase tracking-wider disabled:opacity-60 disabled:cursor-not-allowed"
                :disabled="actionLoading"
                @click="handleAction('approve')"
              >
                <span class="material-symbols-outlined">{{ actionLoading ? 'hourglass_top' : 'check' }}</span>
                {{ actionLoading ? '处理中...' : '批准并执行' }}
              </button>
            </div>
          </template>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getPendingApprovals, approveTask } from '@/api/audit.js'

const selectedTask = ref(null)
const tasks = ref([])
const loading = ref(false)
const actionLoading = ref(false)
const errorMsg = ref('')

function formatTimeAgo(date) {
  const diff = Date.now() - date.getTime()
  const min = Math.floor(diff / 60000)
  if (min < 60)  return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24)   return `${hr} 小时前`
  return `${Math.floor(hr / 24)} 天前`
}

function mapApprovalTask(t) {
  const p = t.approval_payload ?? {}
  const score = p.risk_score ?? 0
  const commandOptions = Array.isArray(p.command_options) ? p.command_options : []
  return {
    id:         `#${t.task_id.slice(0, 8).toUpperCase()}`,
    fullId:     t.task_id,
    risk:       score >= 0.8 ? '高' : score >= 0.5 ? '中' : '低',
    score:      score.toFixed(2),
    desc:       t.task_text,
    operator:   t.operator,
    timeAgo:    formatTimeAgo(new Date(t.created_at)),
    status:     'pending',
    command:    p.command_preview    ?? '（无可用命令预览）',
    commandOptions,
    selectedCommandIds: commandOptions.filter(c => c.checked !== false).map(c => c.id),
    reason:     (p.trigger_reasons  ?? []).join('；') || '（未提供）',
    perception: p.perception_summary ?? '（未提供）',
    reflection: p.reflection_summary ?? '（未提供）',
  }
}

onMounted(async () => {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await getPendingApprovals()
    tasks.value = data.map(mapApprovalTask)
    if (tasks.value.length > 0) selectedTask.value = tasks.value[0]
  } catch (e) {
    console.error('[Approval] 加载失败:', e)
    errorMsg.value = `加载待审批任务失败：${e.message || '未知错误'}`
    ElMessage({ type: 'error', message: errorMsg.value })
  } finally {
    loading.value = false
  }
})

function selectTask(task) {
  selectedTask.value = task
}

function riskBadge(risk) {
  if (risk === '高') return { cls: 'bg-error-container/20 text-error border-error/30 shadow-[0_0_8px_rgba(255,180,171,0.2)]', icon: 'warning' }
  if (risk === '中') return { cls: 'bg-tertiary-container/20 text-tertiary border-tertiary/30', icon: 'info' }
  return                    { cls: 'bg-secondary-container/20 text-secondary border-secondary/30', icon: 'info' }
}

async function handleAction(type) {
  if (!selectedTask.value || actionLoading.value) return
  const task = selectedTask.value
  if (type === 'approve' && (!task.selectedCommandIds || task.selectedCommandIds.length === 0)) {
    ElMessage({ type: 'warning', message: '请至少勾选一条命令后再批准。' })
    return
  }
  actionLoading.value = true
  try {
    const action = type === 'approve' ? 'approve' : 'reject'
    const payload = action === 'approve' ? { selected_command_ids: task.selectedCommandIds || [] } : {}
    await approveTask(task.fullId, action, payload)
    if (type === 'approve') {
      ElMessage({ type: 'success', message: `已批准任务 ${task.id}，正在执行...` })
    } else {
      ElMessage({ type: 'error', message: `已拒绝任务 ${task.id}` })
    }
  } catch (e) {
    ElMessage({ type: 'warning', message: `操作失败：${e.message}` })
    actionLoading.value = false
    return
  }
  const idx = tasks.value.findIndex((t) => t.id === task.id)
  if (idx > -1) tasks.value.splice(idx, 1)
  selectedTask.value = tasks.value[0] ?? null
  actionLoading.value = false
}
</script>
