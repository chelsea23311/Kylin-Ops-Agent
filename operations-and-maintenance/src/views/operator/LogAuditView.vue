<template>
  <div class="h-full flex flex-col overflow-hidden bg-background text-on-surface">

    <!-- Main Content -->
    <main class="flex-grow container mx-auto px-6 py-lg overflow-auto max-w-full">

      <!-- Page Header Card -->
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-md border border-outline-variant/20 mb-lg">
        <div class="flex flex-col gap-xs pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">日志审计</h1>
        </div>

        <!-- Filters -->
        <div class="flex flex-wrap gap-md items-center">
          <div class="relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline-variant text-[20px]">filter_list</span>
            <select
              v-model="statusFilter"
              class="pl-10 pr-8 py-2 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm focus:border-primary-container focus:ring-1 focus:ring-primary-container h-[36px] appearance-none cursor-pointer outline-none transition-shadow"
            >
              <option value="">所有状态</option>
              <option value="success">执行成功</option>
              <option value="blocked">护栏拦截</option>
              <option value="pending">等待审批</option>
            </select>
            <span class="material-symbols-outlined absolute right-2 top-1/2 -translate-y-1/2 text-outline-variant pointer-events-none text-[20px]">expand_more</span>
          </div>

          <div class="relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline-variant text-[20px]">search</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索任务描述关键字..."
              class="pl-10 pr-4 py-2 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm focus:border-primary-container focus:ring-1 focus:ring-primary-container h-[36px] w-64 outline-none transition-shadow placeholder-outline-variant"
            />
          </div>
        </div>
      </section>

      <!-- Data Table Card -->
      <div class="bg-surface-container-low rounded-lg shadow-lg border border-outline-variant/30 overflow-hidden cyber-border-top">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant/50 bg-surface-container">
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">任务 ID</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">操作员</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">任务描述</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">状态</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">风险分</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">创建时间</th>
              </tr>
            </thead>
            <tbody class="text-body-sm text-on-surface divide-y divide-outline-variant/20">
              <tr
                v-for="row in filteredRows"
                :key="row.id"
                class="hover:bg-surface-variant/30 transition-colors border-l-2 border-l-transparent hover:border-l-primary cursor-pointer"
                @click="openTrace(row)"
              >
                <td class="py-sm px-md">
                  <span class="text-primary hover:text-primary-container transition-colors font-medium cursor-pointer">{{ row.id }}</span>
                </td>
                <td class="py-sm px-md text-on-surface-variant" style="font-family: 'Inter', monospace; font-size: 12px;">{{ row.operator }}</td>
                <td class="py-sm px-md truncate max-w-[300px]" :title="row.desc">{{ row.desc }}</td>
                <td class="py-sm px-md">
                  <span :class="statusStyle(row.status).cls" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border font-medium text-[12px] leading-none">
                    <span class="material-symbols-outlined text-[14px]">{{ statusStyle(row.status).icon }}</span>
                    {{ row.statusLabel }}
                  </span>
                </td>
                <td :class="['py-sm px-md font-medium', row.riskHigh ? 'text-error font-bold' : 'text-success']"
                    style="font-family: 'Inter', monospace; font-size: 13px;">{{ row.risk }}</td>
                <td class="py-sm px-md text-on-surface-variant">{{ row.time }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="py-sm px-md border-t border-outline-variant/30 flex items-center justify-between bg-surface-container">
          <div class="text-on-surface-variant text-body-sm">
            显示第 1 至 {{ filteredRows.length }} 条，共 {{ rows.length }} 条
          </div>
          <div class="flex items-center gap-md">
            <div class="flex items-center gap-2">
              <span class="text-on-surface-variant text-body-sm">每页</span>
              <select class="py-1 px-2 border border-outline-variant rounded bg-surface-container-lowest text-on-surface text-body-sm outline-none">
                <option>20</option><option>50</option><option>100</option>
              </select>
              <span class="text-on-surface-variant text-body-sm">条</span>
            </div>
            <div class="flex items-center gap-1">
              <button class="p-1 rounded text-outline-variant cursor-not-allowed" disabled>
                <span class="material-symbols-outlined text-[20px]">chevron_left</span>
              </button>
              <button class="w-8 h-8 rounded bg-primary text-on-primary text-body-sm flex items-center justify-center font-medium">1</button>
              <button class="w-8 h-8 rounded hover:bg-surface-variant text-on-surface text-body-sm flex items-center justify-center transition-colors">2</button>
              <button class="w-8 h-8 rounded hover:bg-surface-variant text-on-surface text-body-sm flex items-center justify-center transition-colors">3</button>
              <span class="w-8 h-8 flex items-center justify-center text-on-surface-variant">...</span>
              <button class="px-2 h-8 rounded hover:bg-surface-variant text-on-surface text-body-sm flex items-center justify-center transition-colors">下一页</button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- ── Trace Detail Drawer ─────────────────────────────── -->
    <el-drawer
      v-model="drawerVisible"
      title=""
      direction="rtl"
      size="45%"
      :show-close="false"
    >
      <template #header>
        <div class="flex items-center justify-between w-full">
          <h2 class="font-bold tracking-tight" style="font-family:'Space Grotesk',sans-serif;font-size:20px;color:#1e293b;">审计链追溯</h2>
          <button class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors" style="color:#64748b;" @click="drawerVisible = false">
            <span class="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
      </template>

      <div v-if="selectedRow" class="h-full overflow-y-auto p-lg space-y-lg" style="background:#f1f1f1;">
        <!-- Section 1: 任务信息 -->
        <section class="rounded-lg p-md border border-outline-variant/20" style="background:#ffffff;">
          <h3 class="font-semibold uppercase mb-md flex items-center gap-2" style="color:#1544ad;font-size:12px;">任务信息</h3>
          <div class="grid grid-cols-2 gap-y-sm gap-x-md">
            <div>
              <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">任务ID</span>
              <p class="text-[14px] break-all" style="color:#1544ad;">{{ selectedRow.id }}</p>
            </div>
            <div>
              <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">操作员</span>
              <p class="text-body-sm font-medium" style="color:#1e293b;">{{ selectedRow.operator }}</p>
            </div>
            <div>
              <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">最终状态</span>
              <span :class="statusStyle(selectedRow.status).cls" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border font-medium text-[11px] uppercase tracking-wide">
                <div class="w-1.5 h-1.5 rounded-full" :class="statusStyle(selectedRow.status).dot"></div>
                {{ selectedRow.statusLabel }}
              </span>
            </div>
            <div>
              <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">创建时间</span>
              <p class="text-body-sm" style="color:#1e293b;">{{ selectedRow.time }}</p>
            </div>
          </div>
        </section>

        <!-- Section 2: 审计溯源 -->
        <section class="rounded-lg p-md border border-outline-variant/20" style="background:#ffffff;">
          <h3 class="font-semibold uppercase mb-md flex items-center gap-2" style="color:#1544ad;font-size:12px;">审计溯源</h3>
          <div class="space-y-md">
            <div class="grid grid-cols-2 gap-y-sm gap-x-md">
              <div>
                <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">请求ID</span>
                <p class="text-[14px]" style="color:#1e293b;">{{ selectedRow.fullId }}</p>
              </div>
              <div>
                <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">主机ID</span>
                <p class="text-[14px]" style="color:#1544ad;">{{ selectedRow.hostId || '—' }}</p>
              </div>
            </div>
            <div class="pt-sm border-t border-outline-variant/30 mt-sm">
              <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">任务描述</span>
              <p class="text-body-sm" style="color:#1e293b;">{{ selectedRow.desc }}</p>
            </div>
          </div>
        </section>

        <!-- Section 3: 执行日志 -->
        <section class="rounded-lg p-md border" style="background:#f0f4fa;border-color:#bfd6f0;">
          <h3 class="font-semibold uppercase mb-md flex items-center gap-2" style="color:#1544ad;font-size:12px;">执行日志 (Raw Log)</h3>
          <div class="space-y-md">
            <div class="grid grid-cols-2 gap-y-sm gap-x-md">
              <div>
                <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">工具</span>
                <p class="px-2 py-1 rounded inline-block border text-[12px]" style="background:#ffffff;border-color:#e2e8f0;color:#1e293b;">{{ selectedRow.tool }}</p>
              </div>
              <div>
                <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">状态</span>
                <span :class="statusStyle(selectedRow.status).cls" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border font-medium text-[11px] uppercase tracking-wide">
                  <div class="w-1.5 h-1.5 rounded-full" :class="statusStyle(selectedRow.status).dot"></div>
                  {{ selectedRow.statusLabel }}
                </span>
              </div>
            </div>
            <div>
              <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">目标</span>
              <p class="text-[14px] break-all" style="color:#1544ad;">{{ selectedRow.target }}</p>
            </div>
            <div class="rounded-md p-sm border" style="background:#ffffff;border-color:#e2e8f0;">
              <span class="block text-[11px] font-medium uppercase mb-1 tracking-wide" style="color:#64748b;">描述</span>
              <p class="text-[12px] leading-relaxed break-words" style="color:#475569;">{{ selectedRow.logDesc }}</p>
            </div>
            <div class="rounded-md p-sm border" style="background:#ffffff;border-color:#e2e8f0;">
              <span class="block text-[11px] font-medium uppercase mb-2 tracking-wide" style="color:#64748b;">命令明细</span>
              <div v-if="selectedRow.rawCommands.length" class="space-y-2">
                <div v-for="(cmd, idx) in selectedRow.rawCommands" :key="`${cmd.id || idx}-${cmd.tool || 'unknown'}`" class="rounded border p-2" style="background:#f8fafc;border-color:#e2e8f0;">
                  <div class="flex flex-wrap items-center gap-2 mb-1">
                    <span class="text-[11px]" style="color:#1544ad;">#{{ idx + 1 }}</span>
                    <span class="text-[11px]" style="color:#1e293b;">{{ cmd.tool || '-' }}</span>
                    <span :class="statusStyle(cmd.status || 'failed').cls" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px]">
                      <span class="w-1.5 h-1.5 rounded-full" :class="statusStyle(cmd.status || 'failed').dot"></span>
                      {{ STATUS_LABEL_MAP[cmd.status] || cmd.status || '未知' }}
                    </span>
                  </div>
                  <div class="text-[12px] break-all" style="color:#1e293b;">{{ cmd.command || '（无命令字符串）' }}</div>
                  <div class="text-[11px] mt-1" style="color:#64748b;">目标: {{ cmd.target || '-' }}</div>
                  <div v-if="cmd.stderr" class="text-[11px] text-error mt-1 break-all">stderr: {{ cmd.stderr }}</div>
                </div>
              </div>
              <p v-else class="text-[12px]" style="color:#94a3b8;">（无命令明细）</p>
            </div>
          </div>
        </section>

        <!-- Section 4: 回滚结果 -->
        <section class="rounded-lg p-md border border-outline-variant/20" style="background:#ffffff;">
          <h3 class="font-semibold uppercase mb-md flex items-center gap-2" style="color:#1544ad;font-size:12px;">回滚结果</h3>
          <div v-if="selectedRow.rollbackStatus" class="space-y-sm">
            <div class="text-body-sm">
              <span style="color:#64748b;">状态: </span>
              <span :class="selectedRow.rollbackStatus === 'success' ? 'text-success' : 'text-error'">{{ selectedRow.rollbackStatus }}</span>
            </div>
            <div v-if="selectedRow.rollbackRuns.length" class="space-y-2">
              <div v-for="(rb, idx) in selectedRow.rollbackRuns" :key="`${rb.id || idx}-${rb.tool || 'rb'}`" class="rounded border p-2" style="background:#f8fafc;border-color:#e2e8f0;">
                <div class="flex items-center justify-between">
                  <span class="text-[11px]" style="color:#1544ad;">{{ rb.tool || '-' }}</span>
                  <span :class="rb.status === 'success' ? 'text-success' : 'text-error'" class="text-[11px]">{{ rb.status }}</span>
                </div>
                <div class="text-[12px] break-all mt-1" style="color:#1e293b;">原命令: {{ rb.original_command || '-' }}</div>
                <div class="text-[12px] break-all mt-1" style="color:#475569;">回滚命令: {{ rb.rollback_command || '-' }}</div>
                <div v-if="rb.stderr" class="text-[11px] text-error mt-1 break-all">stderr: {{ rb.stderr }}</div>
              </div>
            </div>
          </div>
          <p v-else class="text-body-sm" style="color:#94a3b8;">该任务未执行回滚。</p>
        </section>

        <!-- Section 5: 审批记录 -->
        <section class="rounded-lg p-md border border-outline-variant/20 mb-lg" style="background:#ffffff;">
          <h3 class="font-semibold uppercase mb-md flex items-center gap-2" style="color:#1544ad;font-size:12px;">审批记录</h3>
          <div class="flex items-start gap-md">
            <div class="w-10 h-10 rounded-full border flex items-center justify-center font-bold shadow-sm shrink-0 mt-1" style="background:#e8f0fe;border-color:#bfd6f0;color:#1544ad;">A</div>
            <div class="flex-1">
              <div class="flex justify-between items-center mb-xs">
                <span class="text-body-sm font-medium" style="color:#1e293b;">{{ selectedRow.approvedBy || '—' }}</span>
                <span class="text-[11px]" style="color:#94a3b8;">{{ selectedRow.approveTime || '—' }}</span>
              </div>
              <div class="flex items-center gap-md">
                <p class="text-[12px]" style="color:#475569;">审批ID: <span style="color:#1544ad;">{{ selectedRow.approvalId || '—' }}</span></p>
                <div v-if="selectedRow.approved === true" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm bg-success/10 border border-success/20 text-success text-[11px] font-medium uppercase tracking-wide">
                  <div class="w-1.5 h-1.5 rounded-full bg-success"></div>
                  批准
                </div>
                <div v-else-if="selectedRow.approved === false" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm bg-error/10 border border-error/20 text-error text-[11px] font-medium uppercase tracking-wide">
                  <div class="w-1.5 h-1.5 rounded-full bg-error"></div>
                  拒绝
                </div>
                <div v-else class="text-[11px]" style="color:#94a3b8;">无审批记录</div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- Footer -->
      <template #footer>
        <div class="p-md border-t flex gap-md" style="background:#ffffff;border-color:#e2e8f0;">
          <button
            class="flex-1 py-2 rounded font-medium text-body-sm transition-colors" style="background:#f1f5f9;border:1px solid #e2e8f0;color:#475569;"
            @click="drawerVisible = false"
          >关闭详情</button>
        </div>
      </template>
    </el-drawer>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getAllTasks, getFullTrace } from '@/api/audit.js'

const route = useRoute()
const drawerVisible  = ref(false)
const selectedRow    = ref(null)
const statusFilter   = ref('')
const searchQuery    = ref('')

const rows = ref([])

const STATUS_LABEL_MAP = {
  success:           '执行成功',
  blocked:           '护栏拦截',
  awaiting_approval: '等待审批',
  failed:            '执行失败',
  rejected:          '已拒绝',
}
const STATUS_FE_MAP = { awaiting_approval: 'pending' }

function mapTask(t) {
  const status = STATUS_FE_MAP[t.status] ?? t.status
  return {
    id:          t.task_id.slice(0, 13).toUpperCase(),
    fullId:      t.task_id,
    operator:    t.operator,
    desc:        t.task_text,
    status,
    statusLabel: STATUS_LABEL_MAP[t.status] ?? t.status,
    risk:        (t.risk_score ?? 0).toFixed(2),
    riskHigh:    (t.risk_score ?? 0) > 0.7,
    time:        new Date(t.created_at).toLocaleString('zh-CN'),
    tool:        '',
    target:      '',
    logDesc:     '',
    approvalId:  '',
    approvedBy:  '',
    approveTime: '',
    approved:    null,
    hostId:      '',
    rawCommands: [],
    rollbackStatus: '',
    rollbackRuns: [],
  }
}

onMounted(async () => {
  try {
    const data = await getAllTasks()
    rows.value = data.map(mapTask)
    await openTaskById(typeof route.query.task_id === 'string' ? route.query.task_id : '')
  } catch (e) {
    console.error('[LogAudit] 加载任务列表失败:', e)
  }
})

watch(() => route.query.task_id, (taskId) => {
  if (typeof taskId === 'string') openTaskById(taskId)
})

const filteredRows = computed(() => {
  return rows.value.filter((r) => {
    const matchStatus = !statusFilter.value || r.status === statusFilter.value
    const q = searchQuery.value.trim()
    const matchQuery  = !q || r.desc.includes(q) || r.id.includes(q) || r.fullId.includes(q) || r.operator.includes(q)
    return matchStatus && matchQuery
  })
})

async function openTaskById(taskId) {
  if (!taskId) return
  const target = rows.value.find((row) => row.fullId === taskId || row.id === taskId)
  if (!target) {
    searchQuery.value = taskId
    return
  }
  searchQuery.value = taskId
  await openTrace(target)
}

async function openTrace(row) {
  selectedRow.value   = row
  drawerVisible.value = true
  if (row.tool || row.logDesc) return
  try {
    const trace = await getFullTrace(row.fullId)
    const audit = trace.step11_audit
    if (audit) {
      row.hostId      = audit.audit_trace?.host_id ?? ''
      row.tool        = audit.raw_log?.task        ?? ''
      row.target      = audit.raw_log?.target      ?? ''
      row.logDesc     = audit.raw_log?.description ?? ''
      row.rawCommands = Array.isArray(audit.raw_log?.commands) ? audit.raw_log.commands : []
      row.rollbackStatus = trace.step14_rollback_result?.status ?? ''
      row.rollbackRuns = Array.isArray(trace.step14_rollback_result?.runs)
        ? trace.step14_rollback_result.runs
        : (Array.isArray(audit.raw_log?.rollback?.runs) ? audit.raw_log.rollback.runs : [])
      if (audit.approval_log) {
        row.approvalId  = audit.approval_log.approval_id  ?? ''
        row.approvedBy  = audit.approval_log.approved_by  ?? ''
        row.approveTime = audit.approval_log.approve_time
          ? new Date(audit.approval_log.approve_time).toLocaleString('zh-CN') : ''
        row.approved    = audit.approval_log.approved
      }
    }
  } catch (e) {
    console.error('[LogAudit] 加载溯源失败:', e)
  }
}

function statusStyle(status) {
  if (status === 'success') return { cls: 'bg-success/10 border-success/20 text-success', dot: 'bg-success',  icon: 'check_circle' }
  if (status === 'blocked' || status === 'failed' || status === 'rejected') {
    return { cls: 'bg-error/10 border-error/20 text-error', dot: 'bg-error', icon: 'block' }
  }
  return { cls: 'bg-warning/10 border-warning/20 text-warning', dot: 'bg-warning', icon: 'pending' }
}
</script>
