<template>
  <div class="h-full flex flex-col overflow-hidden bg-background text-on-surface">
    <main class="flex-grow container mx-auto px-6 py-lg overflow-auto">
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-md border border-outline-variant/20 mb-lg">
        <div class="flex flex-col gap-xs pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">人员列表</h1>
        </div>

        <div class="flex flex-wrap gap-md items-center">
          <div class="relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline-variant text-[20px]">filter_list</span>
            <select v-model="riskFilter" class="pl-10 pr-8 py-2 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm h-[36px] appearance-none outline-none">
              <option value="">所有状态</option>
              <option value="normal">正常</option>
              <option value="risk">风险</option>
            </select>
          </div>

          <div class="relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline-variant text-[20px]">search</span>
            <input v-model="searchQuery" type="text" placeholder="搜索姓名、工号或部门..." class="pl-10 pr-4 py-2 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm h-[36px] w-72 outline-none placeholder-outline-variant" />
          </div>
        </div>
      </section>

      <div v-if="errorMsg" class="mb-lg rounded-lg border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">
        {{ errorMsg }}
      </div>

      <div class="bg-surface-container-low rounded-lg shadow-lg border border-outline-variant/30 overflow-hidden cyber-border-top">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant/50 bg-surface-container">
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">员工信息</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">工号</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">部门</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">职位</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">风险状态</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">高危指令数</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider text-center">操作</th>
              </tr>
            </thead>
            <tbody class="text-body-sm text-on-surface divide-y divide-outline-variant/20">
              <tr
                v-for="emp in filteredEmployees"
                :key="emp.id"
                :ref="el => setRowRef(emp.id, el)"
                :class="[
                  'transition-colors border-l-2 cursor-pointer',
                  highlightedId === emp.id ? 'bg-primary/10 border-l-primary' : 'border-l-transparent hover:bg-surface-variant/30 hover:border-l-primary',
                ]"
                @click="goToDetail(emp)"
              >
                <td class="py-sm px-md">
                  <div class="flex items-center gap-3">
                    <div class="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0" :style="{ backgroundColor: emp.avatar_color }">
                      {{ emp.name?.charAt(0) }}
                    </div>
                    <div>
                      <div class="font-medium">{{ emp.name }}</div>
                      <div class="text-[12px] text-on-surface-variant">{{ emp.username }}</div>
                    </div>
                  </div>
                </td>
                <td class="py-sm px-md text-on-surface-variant font-mono text-[12px]">{{ emp.employee_id }}</td>
                <td class="py-sm px-md text-on-surface-variant">{{ emp.department }}</td>
                <td class="py-sm px-md text-on-surface-variant">{{ emp.position }}</td>
                <td class="py-sm px-md">
                  <span :class="emp.risk_status === 'risk' ? 'bg-error/10 border-error/20 text-error' : 'bg-success/10 border-success/20 text-success'" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border font-medium text-[12px] leading-none">
                    <span class="w-2 h-2 rounded-full" :class="emp.risk_status === 'risk' ? 'bg-error' : 'bg-success'"></span>
                    {{ emp.risk_status === 'risk' ? '风险' : '正常' }}
                  </span>
                </td>
                <td class="py-sm px-md font-mono text-[13px]" :class="emp.risk_status === 'risk' ? 'text-error font-bold' : 'text-on-surface-variant'">
                  {{ emp.high_risk_count }}
                </td>
                <td class="py-sm px-md text-center" @click.stop>
                  <div class="flex items-center justify-center gap-2">
                    <button class="p-1.5 rounded-md text-on-surface-variant hover:text-primary hover:bg-primary/10 transition-colors" :title="emp.is_admin ? '设为普通运维' : '设为高级运维'" @click="toggleAdmin(emp)">
                      <span class="material-symbols-outlined text-[18px]">{{ emp.is_admin ? 'admin_panel_settings' : 'person_add' }}</span>
                    </button>
                    <button class="p-1.5 rounded-md text-on-surface-variant hover:text-primary hover:bg-primary/10 transition-colors" title="编辑员工信息" @click="openEdit(emp)">
                      <span class="material-symbols-outlined text-[18px]">edit</span>
                    </button>
                    <button class="p-1.5 rounded-md text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors" title="删除员工" @click="deleteEmployee(emp)">
                      <span class="material-symbols-outlined text-[18px]">delete</span>
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!loading && filteredEmployees.length === 0">
                <td colspan="7" class="py-xl text-center text-on-surface-variant">暂无人员数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="py-sm px-md border-t border-outline-variant/30 flex items-center justify-between bg-surface-container">
          <div class="text-on-surface-variant text-body-sm">显示第 1 至 {{ filteredEmployees.length }} 条，共 {{ employees.length }} 条</div>
          <div class="text-on-surface-variant text-body-sm">{{ loading ? '同步中' : '已连接后端数据' }}</div>
        </div>
      </div>
    </main>

    <Transition name="dialog-fade">
      <div v-if="showEditDialog" class="fixed inset-0 bg-black/30 z-50 flex items-center justify-center" @click.self="showEditDialog = false">
        <div class="bg-surface-container-lowest rounded-xl shadow-xl border border-outline-variant/30 w-full max-w-2xl mx-4 p-lg">
          <div class="flex items-center justify-between mb-lg">
            <h3 class="text-[18px] font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif;">编辑员工信息</h3>
            <button class="p-1 text-on-surface-variant hover:text-on-surface rounded transition-colors" @click="showEditDialog = false">
              <span class="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
            <label class="text-sm">
              <span class="block mb-1 text-on-surface-variant">姓名</span>
              <input v-model="editForm.name" class="w-full px-3 py-2.5 border border-outline-variant rounded bg-surface-container-low outline-none" />
            </label>
            <label class="text-sm">
              <span class="block mb-1 text-on-surface-variant">部门</span>
              <input v-model="editForm.department" class="w-full px-3 py-2.5 border border-outline-variant rounded bg-surface-container-low outline-none" />
            </label>
            <label class="text-sm">
              <span class="block mb-1 text-on-surface-variant">职位</span>
              <input v-model="editForm.position" class="w-full px-3 py-2.5 border border-outline-variant rounded bg-surface-container-low outline-none" />
            </label>
            <label class="text-sm">
              <span class="block mb-1 text-on-surface-variant">手机号</span>
              <input v-model="editForm.phone" class="w-full px-3 py-2.5 border border-outline-variant rounded bg-surface-container-low outline-none" />
            </label>
            <label class="text-sm md:col-span-2">
              <span class="block mb-1 text-on-surface-variant">邮箱</span>
              <input v-model="editForm.email" class="w-full px-3 py-2.5 border border-outline-variant rounded bg-surface-container-low outline-none" />
            </label>
            <label class="text-sm">
              <span class="block mb-1 text-on-surface-variant">权限</span>
              <select v-model="editForm.role" class="w-full px-3 py-2.5 border border-outline-variant rounded bg-surface-container-low outline-none">
                <option value="operator">普通运维人员</option>
                <option value="admin">高级运维人员</option>
                <option value="auditor">审计人员</option>
                <option value="user">普通用户</option>
              </select>
            </label>
          </div>

          <div class="flex gap-md mt-lg">
            <button class="flex-1 bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-variant py-2.5 rounded font-medium text-body-sm transition-colors" @click="showEditDialog = false">取消</button>
            <button class="flex-1 bg-primary text-on-primary py-2.5 rounded font-medium text-body-sm hover:bg-primary-container transition-colors" :disabled="saving" @click="saveEdit">
              {{ saving ? '保存中...' : '保存修改' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { deletePersonnel, getPersonnelList, updatePersonnel } from '@/api/auditor.js'

const router = useRouter()
const route = useRoute()

const employees = ref([])
const loading = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const riskFilter = ref('')
const searchQuery = ref('')
const highlightedId = ref(null)
const showEditDialog = ref(false)
const editingId = ref(null)
const rowRefs = {}
const editForm = reactive({ name: '', department: '', position: '', phone: '', email: '', role: 'operator' })

const filteredEmployees = computed(() =>
  employees.value.filter((emp) => {
    const matchRisk = !riskFilter.value || emp.risk_status === riskFilter.value
    const q = searchQuery.value.trim().toLowerCase()
    const matchQuery = !q || [emp.name, emp.employee_id, emp.department, emp.username].some((value) => String(value || '').toLowerCase().includes(q))
    return matchRisk && matchQuery
  }),
)

function setRowRef(id, el) {
  if (el) rowRefs[id] = el
}

async function loadEmployees() {
  loading.value = true
  errorMsg.value = ''
  try {
    employees.value = await getPersonnelList()
    await highlightFromRoute()
  } catch (error) {
    errorMsg.value = error.message || '加载人员列表失败'
  } finally {
    loading.value = false
  }
}

async function highlightFromRoute() {
  const highlightName = route.query.highlight
  if (!highlightName) return
  const emp = employees.value.find((item) => item.name === highlightName || item.employee_id === highlightName || item.username === highlightName)
  if (!emp) return
  highlightedId.value = emp.id
  searchQuery.value = String(highlightName)
  await nextTick()
  rowRefs[emp.id]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  window.setTimeout(() => { highlightedId.value = null }, 5000)
}

function goToDetail(emp) {
  router.push(`/auditor/personnel/${emp.id}`)
}

function openEdit(emp) {
  editingId.value = emp.id
  editForm.name = emp.name
  editForm.department = emp.department
  editForm.position = emp.position
  editForm.phone = emp.phone_raw || emp.phone
  editForm.email = emp.email
  editForm.role = emp.role
  showEditDialog.value = true
}

async function saveEdit() {
  if (!editingId.value) return
  saving.value = true
  try {
    await updatePersonnel(editingId.value, { ...editForm })
    showEditDialog.value = false
    await loadEmployees()
  } catch (error) {
    errorMsg.value = error.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function toggleAdmin(emp) {
  try {
    await updatePersonnel(emp.id, { role: emp.is_admin ? 'operator' : 'admin' })
    await loadEmployees()
  } catch (error) {
    errorMsg.value = error.message || '权限更新失败'
  }
}

async function deleteEmployee(emp) {
  if (!window.confirm(`确认删除 ${emp.name} 吗？`)) return
  try {
    await deletePersonnel(emp.id)
    await loadEmployees()
  } catch (error) {
    errorMsg.value = error.message || '删除失败'
  }
}

watch(() => route.query.highlight, () => {
  highlightFromRoute()
})

onMounted(() => {
  loadEmployees()
})
</script>

<style scoped>
.dialog-fade-enter-active {
  transition: all 0.2s ease-out;
}
.dialog-fade-leave-active {
  transition: all 0.15s ease-in;
}
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
