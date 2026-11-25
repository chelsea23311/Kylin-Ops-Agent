<template>
  <div class="h-full flex flex-col overflow-hidden bg-background text-on-surface">
    <main class="flex-grow container mx-auto px-6 py-lg overflow-auto">
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-md border border-outline-variant/20 mb-lg">
        <div class="flex flex-col gap-xs pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">消息推送</h1>
        </div>

        <button class="flex items-center gap-2 px-4 py-2.5 bg-primary text-on-primary rounded-lg font-medium text-body-sm hover:bg-primary-container transition-colors active:opacity-80" @click="showSendDialog = true">
          <span class="material-symbols-outlined text-[18px]">add</span>
          新建消息
        </button>
      </section>

      <div v-if="notice" class="mb-lg rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-primary">{{ notice }}</div>
      <div v-if="errorMsg" class="mb-lg rounded-lg border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">{{ errorMsg }}</div>

      <div class="grid grid-cols-1 md:grid-cols-4 gap-md mb-lg">
        <StatCard icon="campaign" color="primary" :value="messages.length" label="全部消息" />
        <StatCard icon="check_circle" color="tertiary" :value="sentCount" label="已发送" />
        <StatCard icon="schedule" color="secondary" :value="scheduledCount" label="定时发送" />
        <StatCard icon="error" color="error" :value="failedCount" label="发送失败" />
      </div>

      <div class="flex flex-wrap gap-md items-center mb-lg">
        <div class="relative">
          <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline-variant text-[20px]">filter_list</span>
          <select v-model="statusFilter" class="pl-10 pr-8 py-2 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm h-[36px] appearance-none outline-none">
            <option value="">全部状态</option>
            <option value="sent">已发送</option>
            <option value="scheduled">定时发送</option>
            <option value="failed">发送失败</option>
          </select>
        </div>

        <div class="relative">
          <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline-variant text-[20px]">search</span>
          <input v-model="searchQuery" type="text" placeholder="搜索消息内容或接收人..." class="pl-10 pr-4 py-2 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm h-[36px] w-64 outline-none placeholder-outline-variant" />
        </div>
      </div>

      <div class="bg-surface-container-low rounded-lg shadow-lg border border-outline-variant/30 overflow-hidden cyber-border-top">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-outline-variant/50 bg-surface-container">
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">接收员工</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">消息种类</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">消息内容</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">状态</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider">发送时间</th>
                <th class="py-sm px-md text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider text-center">操作</th>
              </tr>
            </thead>
            <tbody class="text-body-sm text-on-surface divide-y divide-outline-variant/20">
              <tr v-for="msg in filteredMessages" :key="msg.id" class="hover:bg-surface-variant/30 transition-colors border-l-2 border-l-transparent hover:border-l-primary">
                <td class="py-sm px-md">
                  <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0" :style="{ backgroundColor: msg.avatar_color }">
                      {{ msg.receiver?.charAt(0) }}
                    </div>
                    <span class="text-on-surface font-medium">{{ msg.receiver }}</span>
                  </div>
                </td>
                <td class="py-sm px-md">
                  <span :class="categoryStyle(msg.category).cls" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm border font-medium text-[11px]">
                    <span class="material-symbols-outlined text-[14px]">{{ categoryStyle(msg.category).icon }}</span>
                    {{ msg.category_label }}
                  </span>
                </td>
                <td class="py-sm px-md text-on-surface-variant max-w-[320px] truncate" :title="msg.content">{{ msg.content }}</td>
                <td class="py-sm px-md">
                  <span :class="statusBadge(msg.status).cls" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm border font-medium text-[11px]">
                    <span class="w-1.5 h-1.5 rounded-full" :class="statusBadge(msg.status).dot"></span>
                    {{ msg.status_label }}
                  </span>
                </td>
                <td class="py-sm px-md text-on-surface-variant text-[12px]">{{ msg.send_time }}</td>
                <td class="py-sm px-md text-center">
                  <button class="p-1.5 rounded-md text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors" title="删除消息" @click="removeMessage(msg.id)">
                    <span class="material-symbols-outlined text-[16px]">delete</span>
                  </button>
                </td>
              </tr>
              <tr v-if="!loading && filteredMessages.length === 0">
                <td colspan="6" class="py-xl text-center text-on-surface-variant">暂无消息记录</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="py-sm px-md border-t border-outline-variant/30 flex items-center justify-between bg-surface-container">
          <div class="text-on-surface-variant text-body-sm">显示第 1 至 {{ filteredMessages.length }} 条，共 {{ messages.length }} 条</div>
          <div class="text-on-surface-variant text-body-sm">{{ loading ? '同步中' : '已连接真实消息中心' }}</div>
        </div>
      </div>
    </main>

    <Transition name="dialog-fade">
      <div v-if="showSendDialog" class="fixed inset-0 bg-black/30 z-50 flex items-center justify-center" @click.self="showSendDialog = false">
        <div class="bg-surface-container-lowest rounded-xl shadow-xl border border-outline-variant/30 w-full max-w-lg mx-4 p-lg">
          <div class="flex items-center justify-between mb-lg">
            <h3 class="text-[18px] font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif;">新建消息</h3>
            <button class="p-1 text-on-surface-variant hover:text-on-surface rounded transition-colors" @click="showSendDialog = false">
              <span class="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>

          <div class="space-y-md">
            <div>
              <label class="block text-[12px] font-medium text-on-surface-variant uppercase mb-1 tracking-wide">接收员工</label>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-md">
                <select v-model="newMessage.department" class="w-full pl-4 pr-8 py-2.5 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm outline-none transition-shadow">
                  <option value="">请选择部门</option>
                  <option v-for="department in departments" :key="department" :value="department">{{ department }}</option>
                </select>
                <select
                  v-model="newMessage.recipient_user_id"
                  class="w-full pl-4 pr-8 py-2.5 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm outline-none transition-shadow disabled:opacity-60 disabled:cursor-not-allowed"
                  :disabled="!newMessage.department"
                >
                  <option value="">{{ newMessage.department ? '请选择员工' : '先选择部门' }}</option>
                  <option v-for="emp in filteredRecipients" :key="emp.id" :value="emp.id">{{ emp.name }}（{{ emp.username }}）</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-[12px] font-medium text-on-surface-variant uppercase mb-1 tracking-wide">消息种类</label>
              <select v-model="newMessage.category" class="w-full pl-4 pr-4 py-2.5 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm outline-none transition-shadow">
                <option value="">请选择种类</option>
                <option value="notification">系统通知</option>
                <option value="warning">安全警告</option>
                <option value="task">任务提醒</option>
                <option value="announcement">公告通知</option>
              </select>
            </div>

            <div>
              <label class="block text-[12px] font-medium text-on-surface-variant uppercase mb-1 tracking-wide">消息内容</label>
              <textarea v-model="newMessage.content" rows="4" placeholder="请输入消息内容..." class="w-full pl-4 pr-4 py-2.5 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm outline-none transition-shadow resize-none"></textarea>
            </div>

            <div class="flex items-center justify-between bg-surface-container rounded-lg p-md border border-outline-variant/20">
              <div>
                <p class="text-body-sm font-medium text-on-surface">定时发送</p>
                <p class="text-[12px] text-on-surface-variant mt-0.5">设置消息在指定时间自动发送</p>
              </div>
              <button :class="newMessage.isScheduled ? 'bg-tertiary' : 'bg-outline-variant'" class="relative w-11 h-6 rounded-full transition-colors duration-200" @click="newMessage.isScheduled = !newMessage.isScheduled">
                <span :class="newMessage.isScheduled ? 'translate-x-5' : 'translate-x-0'" class="absolute left-0.5 top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200"></span>
              </button>
            </div>

            <div v-if="newMessage.isScheduled">
              <label class="block text-[12px] font-medium text-on-surface-variant uppercase mb-1 tracking-wide">发送时间</label>
              <input v-model="newMessage.scheduleTime" type="datetime-local" class="w-full pl-4 pr-4 py-2.5 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm outline-none transition-shadow" />
            </div>
          </div>

          <div class="flex gap-md mt-lg">
            <button class="flex-1 bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-variant py-2.5 rounded font-medium text-body-sm transition-colors" @click="showSendDialog = false">取消</button>
            <button class="flex-1 bg-primary text-on-primary py-2.5 rounded font-medium text-body-sm hover:bg-primary-container transition-colors active:opacity-80 disabled:opacity-50" :disabled="submitting" @click="sendMessage">
              {{ submitting ? '发送中...' : '发送消息' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from 'vue'
import { createMessage, deleteMessage, getMessages, getPersonnelList } from '@/api/auditor.js'

const showSendDialog = ref(false)
const statusFilter = ref('')
const searchQuery = ref('')
const messages = ref([])
const recipients = ref([])
const loading = ref(false)
const submitting = ref(false)
const errorMsg = ref('')
const notice = ref('')

const StatCard = defineComponent({
  props: { icon: String, color: String, value: Number, label: String },
  setup(props) {
    const colorMap = {
      primary: 'bg-primary/10 border-primary/20 text-primary',
      tertiary: 'bg-tertiary/10 border-tertiary/20 text-tertiary',
      secondary: 'bg-secondary/10 border-secondary/20 text-secondary',
      error: 'bg-error/10 border-error/20 text-error',
    }
    return () => h('div', { class: 'bg-surface-container-lowest rounded-lg shadow-card p-md border border-outline-variant/20 flex items-center gap-md' }, [
      h('div', { class: `w-10 h-10 rounded-full border flex items-center justify-center shrink-0 ${colorMap[props.color] || colorMap.primary}` }, [
        h('span', { class: 'material-symbols-outlined text-[20px]' }, props.icon),
      ]),
      h('div', [
        h('p', { class: 'text-[24px] font-bold text-on-surface', style: "font-family: 'Space Grotesk', sans-serif;" }, String(props.value ?? 0)),
        h('p', { class: 'text-[12px] text-on-surface-variant' }, props.label),
      ]),
    ])
  },
})

const newMessage = reactive({
  department: '',
  recipient_user_id: '',
  category: '',
  content: '',
  isScheduled: false,
  scheduleTime: '',
})

const sentCount = computed(() => messages.value.filter((m) => m.status === 'sent').length)
const scheduledCount = computed(() => messages.value.filter((m) => m.status === 'scheduled').length)
const failedCount = computed(() => messages.value.filter((m) => m.status === 'failed').length)

const departments = computed(() => {
  const names = recipients.value.map((item) => item.department || '未分配部门')
  return [...new Set(names)].sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

const filteredRecipients = computed(() =>
  recipients.value.filter((item) => (item.department || '未分配部门') === newMessage.department),
)

const filteredMessages = computed(() =>
  messages.value.filter((msg) => {
    const matchStatus = !statusFilter.value || msg.status === statusFilter.value
    const q = searchQuery.value.trim().toLowerCase()
    const matchQuery = !q || [msg.content, msg.receiver, msg.category_label].some((value) => String(value || '').toLowerCase().includes(q))
    return matchStatus && matchQuery
  }),
)

async function loadData() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [messageData, personnel] = await Promise.all([getMessages(), getPersonnelList()])
    messages.value = messageData
    recipients.value = personnel.filter((item) => ['operator', 'admin'].includes(item.role))
  } catch (error) {
    errorMsg.value = error.message || '加载消息失败'
  } finally {
    loading.value = false
  }
}

async function sendMessage() {
  submitting.value = true
  errorMsg.value = ''
  notice.value = ''
  try {
    if (!newMessage.department || !newMessage.recipient_user_id) {
      throw new Error('请先选择部门和接收员工')
    }
    const created = await createMessage({
      recipient_user_id: newMessage.recipient_user_id,
      category: newMessage.category,
      content: newMessage.content,
      schedule_time: newMessage.isScheduled ? newMessage.scheduleTime : '',
    })
    messages.value.unshift(created)
    showSendDialog.value = false
    notice.value = created.status === 'scheduled' ? '消息已加入定时发送队列' : '消息已发送'
    newMessage.department = ''
    newMessage.recipient_user_id = ''
    newMessage.category = ''
    newMessage.content = ''
    newMessage.isScheduled = false
    newMessage.scheduleTime = ''
  } catch (error) {
    errorMsg.value = error.message || '发送消息失败'
  } finally {
    submitting.value = false
  }
}

async function removeMessage(messageId) {
  if (!window.confirm('确认删除这条消息吗？')) return
  try {
    await deleteMessage(messageId)
    messages.value = messages.value.filter((item) => item.id !== messageId)
  } catch (error) {
    errorMsg.value = error.message || '删除消息失败'
  }
}

function categoryStyle(cat) {
  const map = {
    notification: { cls: 'bg-primary/10 border-primary/20 text-primary', icon: 'notifications' },
    warning: { cls: 'bg-error/10 border-error/20 text-error', icon: 'warning' },
    task: { cls: 'bg-tertiary/10 border-tertiary/20 text-tertiary', icon: 'task_alt' },
    announcement: { cls: 'bg-secondary/10 border-secondary/20 text-secondary', icon: 'campaign' },
  }
  return map[cat] || { cls: 'bg-surface-variant/50 border-outline-variant/20 text-on-surface-variant', icon: 'info' }
}

function statusBadge(status) {
  if (status === 'sent') return { cls: 'bg-tertiary/10 border-tertiary/20 text-tertiary', dot: 'bg-tertiary' }
  if (status === 'scheduled') return { cls: 'bg-secondary/10 border-secondary/20 text-secondary', dot: 'bg-secondary' }
  if (status === 'failed') return { cls: 'bg-error/10 border-error/20 text-error', dot: 'bg-error' }
  return { cls: 'bg-surface-variant/50 border-outline-variant/20 text-on-surface-variant', dot: 'bg-outline-variant' }
}

onMounted(() => {
  loadData()
})

watch(
  () => newMessage.department,
  () => {
    newMessage.recipient_user_id = ''
  },
)
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
