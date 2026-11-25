<template>
  <div class="h-full flex flex-col overflow-hidden bg-background text-on-surface">
    <main class="flex-grow container mx-auto px-6 py-lg overflow-auto">
      <button class="flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors mb-md group" @click="goBack">
        <span class="material-symbols-outlined text-[20px] group-hover:-translate-x-1 transition-transform">arrow_back</span>
        <span class="text-body-sm font-medium">返回员工列表</span>
      </button>

      <div v-if="errorMsg" class="mb-lg rounded-lg border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">
        {{ errorMsg }}
      </div>

      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg border border-outline-variant/20 mb-lg" v-if="employee">
        <div class="flex flex-col md:flex-row items-start gap-lg">
          <div class="w-20 h-20 rounded-full flex items-center justify-center text-white text-3xl font-bold shrink-0" :style="{ backgroundColor: employee.avatar_color }">
            {{ employee.name?.charAt(0) }}
          </div>
          <div class="flex-1 grid grid-cols-1 md:grid-cols-3 gap-md">
            <InfoCell label="姓名" :value="employee.name" />
            <InfoCell label="工号" :value="employee.employee_id" mono />
            <InfoCell label="部门" :value="employee.department" />
            <InfoCell label="职位" :value="employee.position" />
            <InfoCell label="手机号" :value="employee.phone" />
            <InfoCell label="邮箱" :value="employee.email" />
            <InfoCell label="入职日期" :value="employee.join_date" />
            <InfoCell label="账号" :value="employee.username" />
            <div>
              <span class="block text-[11px] font-medium text-on-surface-variant uppercase mb-1 tracking-wide">权限</span>
              <span :class="employee.is_admin ? 'bg-primary/10 border-primary/20 text-primary' : 'bg-surface-variant/50 border-outline-variant/20 text-on-surface-variant'" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border font-medium text-[12px]">
                {{ employee.is_admin ? '高级运维人员' : employee.role_label }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg border border-outline-variant/20 mb-lg" v-if="employee">
        <h3 class="text-[14px] font-semibold text-on-surface uppercase mb-md flex items-center gap-sm" style="font-family: 'Space Grotesk', sans-serif;">
          <span class="material-symbols-outlined text-[20px]" :class="employee.risk_status === 'risk' ? 'text-error' : 'text-success'">
            {{ employee.risk_status === 'risk' ? 'warning' : 'check_circle' }}
          </span>
          风险评估与分析
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-md mb-md">
          <MetricCard :value="employee.high_risk_count" label="高危指令尝试次数" :danger="employee.risk_status === 'risk'" />
          <MetricCard :value="`${Math.round((employee.risk_score || 0) * 100)}%`" label="风险评分" />
          <MetricCard :value="employee.risk_rating" label="综合评级" :danger="employee.risk_status === 'risk'" />
        </div>
        <div class="bg-surface-container rounded-lg p-md border border-outline-variant/20">
          <h4 class="text-[12px] font-semibold text-on-surface-variant uppercase mb-sm tracking-wide">分析原因</h4>
          <p class="text-body-sm text-on-surface leading-relaxed">{{ employee.risk_analysis }}</p>
        </div>
      </section>

      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg border border-outline-variant/20" v-if="employee">
        <h3 class="text-[14px] font-semibold text-on-surface uppercase mb-md flex items-center gap-sm" style="font-family: 'Space Grotesk', sans-serif;">
          <span class="material-symbols-outlined text-[20px] text-primary">terminal</span>
          最近运行指令记录
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant/50 bg-surface-container">
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">任务 ID</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">任务描述</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">命令</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">工具</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">风险等级</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">状态</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">时间</th>
              </tr>
            </thead>
            <tbody class="text-body-sm text-on-surface divide-y divide-outline-variant/20">
              <tr v-for="cmd in employee.recent_commands || []" :key="cmd.id" :class="cmd.risk_level === 'high' ? 'bg-error/[0.04]' : ''">
                <td class="py-sm px-md text-primary font-mono text-[12px]">{{ cmd.task_id }}</td>
                <td class="py-sm px-md text-on-surface-variant max-w-[220px] truncate" :title="cmd.description">{{ cmd.description }}</td>
                <td class="py-sm px-md"><code class="font-mono text-[12px] text-on-surface bg-surface-container px-2 py-0.5 rounded border border-outline-variant/20">{{ cmd.command }}</code></td>
                <td class="py-sm px-md text-on-surface-variant font-mono text-[12px]">{{ cmd.tool }}</td>
                <td class="py-sm px-md">
                  <span :class="cmd.risk_level === 'high' ? 'bg-error/10 border-error/20 text-error' : 'bg-secondary/10 border-secondary/20 text-secondary'" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm border font-medium text-[11px]">
                    {{ cmd.risk_level === 'high' ? '高风险' : '中风险' }}
                  </span>
                </td>
                <td class="py-sm px-md">
                  <span :class="statusStyle(cmd.status).cls" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border font-medium text-[11px]">
                    <span class="w-1.5 h-1.5 rounded-full" :class="statusStyle(cmd.status).dot"></span>
                    {{ cmd.status_label }}
                  </span>
                </td>
                <td class="py-sm px-md text-on-surface-variant text-[12px]">{{ cmd.time }}</td>
              </tr>
              <tr v-if="!loading && !(employee.recent_commands || []).length">
                <td colspan="7" class="py-xl text-center text-on-surface-variant">暂无指令记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { defineComponent, h, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPersonnelDetail } from '@/api/auditor.js'

const route = useRoute()
const router = useRouter()
const employee = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const InfoCell = defineComponent({
  props: { label: String, value: String, mono: Boolean },
  setup(props) {
    return () => h('div', [
      h('span', { class: 'block text-[11px] font-medium text-on-surface-variant uppercase mb-1 tracking-wide' }, props.label),
      h('p', { class: props.mono ? 'text-on-surface font-mono text-[14px]' : 'text-on-surface text-[14px]' }, props.value || '-'),
    ])
  },
})

const MetricCard = defineComponent({
  props: { value: [String, Number], label: String, danger: Boolean },
  setup(props) {
    return () => h('div', { class: 'bg-surface-container rounded-lg p-md border border-outline-variant/20 text-center' }, [
      h('p', { class: `text-[36px] font-bold ${props.danger ? 'text-error' : 'text-primary'}`, style: "font-family: 'Space Grotesk', sans-serif;" }, String(props.value ?? '-')),
      h('p', { class: 'text-[12px] text-on-surface-variant mt-1' }, props.label),
    ])
  },
})

async function loadDetail() {
  loading.value = true
  errorMsg.value = ''
  try {
    employee.value = await getPersonnelDetail(route.params.id)
  } catch (error) {
    errorMsg.value = error.message || '加载人员详情失败'
    router.push('/auditor/personnel')
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/auditor/personnel')
}

function statusStyle(status) {
  if (status === 'success') return { cls: 'bg-success/10 border-success/20 text-success', dot: 'bg-success' }
  if (['blocked', 'failed', 'rejected'].includes(status)) return { cls: 'bg-error/10 border-error/20 text-error', dot: 'bg-error' }
  return { cls: 'bg-secondary/10 border-secondary/20 text-secondary', dot: 'bg-secondary' }
}

onMounted(() => {
  loadDetail()
})
</script>
