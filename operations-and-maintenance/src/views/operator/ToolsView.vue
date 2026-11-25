<template>
  <div class="h-full flex flex-col overflow-auto bg-background text-on-surface">
    <main class="flex-grow p-xl max-w-7xl mx-auto w-full">

      <!-- Page Header Card -->
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-md border border-outline-variant/20 mb-lg">
        <div class="flex flex-col gap-xs pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">工具管理</h1>
        </div>
      </section>

      <!-- Data Table Card -->
      <div class="bg-surface-container-lowest rounded-xl shadow-card border border-surface-variant overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-surface-variant bg-surface-container-low">
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase">工具名</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase">风险等级</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase">风险描述</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase text-center">需要Root</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase text-center">后端允许</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase text-center">当前状态</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase text-right">操作</th>
              </tr>
            </thead>
            <tbody class="text-body-sm">
              <tr v-if="toolsLoading">
                <td colspan="7" class="py-md px-md text-on-surface-variant">加载中...</td>
              </tr>
              <tr v-else-if="tools.length === 0">
                <td colspan="7" class="py-md px-md text-on-surface-variant">
                  {{ toolsError || '暂无工具数据' }}
                </td>
              </tr>
              <tr
                v-for="tool in tools"
                :key="tool.name"
                :class="['border-b border-surface-variant transition-colors', tool.enabled ? 'hover:bg-surface-container' : 'opacity-40 grayscale hover:opacity-60']"
              >
                <!-- Tool Name -->
                <td class="py-md px-md font-medium text-primary" style="font-family: 'Inter', monospace; font-size: 13px;">{{ tool.name }}</td>

                <!-- Risk Level -->
                <td class="py-md px-md">
                  <span :class="['inline-flex items-center px-2 py-1 rounded text-[12px] font-medium', riskStyle(tool.risk).bg, riskStyle(tool.risk).text]">
                    {{ tool.risk }}
                  </span>
                </td>

                <!-- Risk Desc -->
                <td class="py-md px-md text-on-surface-variant">{{ tool.desc }}</td>

                <!-- Needs Root -->
                <td class="py-md px-md text-center">
                  <span :class="['material-symbols-outlined text-[20px]', tool.needsRoot ? 'text-primary-container' : 'text-outline-variant']">
                    {{ tool.needsRoot ? 'check_circle' : 'cancel' }}
                  </span>
                </td>

                <!-- Backend Allowed -->
                <td class="py-md px-md text-center">
                  <span :class="['material-symbols-outlined text-[20px]', tool.backendAllowed ? 'text-primary-container' : 'text-outline-variant']">
                    {{ tool.backendAllowed ? 'check_circle' : 'cancel' }}
                  </span>
                </td>

                <!-- Status Badge -->
                <td class="py-md px-md text-center">
                  <span v-if="tool.enabled" class="inline-flex items-center gap-xs px-2 py-1 rounded bg-success/10 text-success font-medium text-[12px] border border-success/20">
                    <span class="w-1.5 h-1.5 rounded-full bg-success"></span> 启用
                  </span>
                  <span v-else class="inline-flex items-center gap-xs px-2 py-1 rounded bg-surface-variant text-on-surface-variant font-medium text-[12px]">
                    <span class="w-1.5 h-1.5 rounded-full bg-outline"></span> 已禁用
                  </span>
                </td>

                <!-- Toggle -->
                <td class="py-md px-md text-right">
                  <el-switch
                    :model-value="tool.enabled"
                    :active-color="'#0ea5e9'"
                    :inactive-color="'#bec8d2'"
                    size="small"
                    @change="(val) => toggleTool(tool, val)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination Footer -->
        <div class="px-md py-sm border-t border-surface-variant flex justify-between items-center bg-surface-container-lowest text-on-surface-variant text-body-sm">
          <span>共 {{ tools.length }} 个已注册工具</span>
          <div class="flex gap-xs">
            <button class="px-2 py-1 border border-outline-variant rounded text-outline disabled:opacity-50 text-[12px]" disabled>上一页</button>
            <button class="px-2 py-1 border border-outline-variant rounded text-outline disabled:opacity-50 text-[12px]" disabled>下一页</button>
          </div>
        </div>
      </div>
    </main>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTools, disableTool, enableTool } from '@/api/tools.js'

const LEVEL_MAP = { low: '低风险', medium: '中风险', high: '高风险', critical: '极高风险' }

function mapTool(t) {
  return {
    name:           t.tool_name,
    risk:           LEVEL_MAP[t.level] ?? (Number(t.level) >= 0.7 ? '高风险' : Number(t.level) >= 0.4 ? '中风险' : '低风险'),
    desc:           t.reason,
    needsRoot:      t.need_root,
    backendAllowed: t.backend_allowed,
    enabled:        !t.user_disabled,
  }
}

const tools = ref([])
const toolsLoading = ref(false)
const toolsError = ref('')

onMounted(async () => {
  toolsLoading.value = true
  toolsError.value = ''
  try {
    const data = await getTools()
    const list = Array.isArray(data)
      ? data
      : Array.isArray(data?.data)
        ? data.data
        : Array.isArray(data?.items)
          ? data.items
          : []
    tools.value = list.map(mapTool).filter((t) => !!t.name)
    if (tools.value.length === 0) {
      toolsError.value = '接口已返回，但没有可展示的工具数据'
    }
  } catch (e) {
    console.error('[Tools] 加载失败:', e)
    toolsError.value = `加载失败：${e.message || '未知错误'}`
  } finally {
    toolsLoading.value = false
  }
})

async function toggleTool(tool, newVal) {
  const prev = tool.enabled
  tool.enabled = newVal   // 乐观更新
  try {
    const api = newVal ? enableTool : disableTool
    const resp = await api(tool.name)
    tool.enabled = !resp.user_disabled
  } catch (e) {
    tool.enabled = prev  // 失败回滚
    console.error('[Tools] 切换失败:', e)
  }
}

function riskStyle(risk) {
  if (risk === '高风险' || risk === '极高风险') return { bg: 'bg-error/10', text: 'text-error' }
  if (risk === '中风险')                           return { bg: 'bg-tertiary/20',  text: 'text-tertiary'  }
  return                                               { bg: 'bg-primary/10',   text: 'text-primary'   }
}

</script>

