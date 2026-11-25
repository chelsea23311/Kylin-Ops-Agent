<template>
  <div class="h-full overflow-auto bg-background text-on-surface">
    <main class="p-lg">
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-md border border-outline-variant/20 mb-lg">
        <div class="flex flex-col gap-xs pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">文件管理</h1>
        </div>

        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="text-body-sm text-on-surface-variant whitespace-nowrap">当前路径：</span>
            <div class="flex items-center bg-surface-container-low rounded-lg border border-outline-variant/30 px-3 py-2 max-w-[520px]">
              <span class="material-symbols-outlined text-on-surface-variant text-[18px] mr-2">folder</span>
              <span class="text-body-sm text-on-surface font-mono truncate">{{ currentPath }}</span>
            </div>
          </div>
          <div class="flex gap-2">
            <button
              class="h-9 px-4 rounded-lg border border-outline-variant text-on-surface-variant hover:bg-surface-container transition-colors text-body-sm flex items-center gap-1.5 disabled:opacity-50"
              :disabled="!canGoParent || loading"
              @click="goParent"
            >
              <span class="material-symbols-outlined text-[18px]">arrow_upward</span>
              上一级
            </button>
            <button
              class="h-9 px-4 rounded-lg bg-primary-container text-on-primary hover:bg-primary transition-colors text-body-sm font-medium flex items-center gap-1.5 disabled:opacity-50"
              :disabled="loading"
              @click="loadFiles(currentPath)"
            >
              <span class="material-symbols-outlined text-[18px]">refresh</span>
              刷新
            </button>
          </div>
        </div>
      </section>

      <div v-if="errorMsg" class="mb-lg rounded-lg border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">
        {{ errorMsg }}
      </div>
      <div v-if="successMsg" class="mb-lg rounded-lg border border-tertiary/20 bg-tertiary/5 px-4 py-3 text-sm text-tertiary">
        {{ successMsg }}
      </div>

      <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-outline-variant/20 bg-surface-container">
              <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">文件名</th>
              <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">大小</th>
              <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">修改时间</th>
              <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase">权限</th>
              <th class="py-3 px-4 text-label-caps font-semibold text-on-surface-variant uppercase text-right">操作</th>
            </tr>
          </thead>
          <tbody class="text-body-sm divide-y divide-outline-variant/10">
            <tr
              v-for="file in fileList"
              :key="`${currentPath}:${file.name}`"
              class="hover:bg-surface-variant/30 transition-colors"
              :class="file.is_dir ? 'cursor-pointer' : ''"
              @click="openEntry(file)"
            >
              <td class="py-2.5 px-4">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-[20px]" :class="file.is_dir ? 'text-tertiary-container' : 'text-on-surface-variant'">
                    {{ file.is_dir ? 'folder' : 'description' }}
                  </span>
                  <span class="text-on-surface" :class="{ 'text-primary font-medium': file.is_dir }">{{ file.name }}</span>
                </div>
              </td>
              <td class="py-2.5 px-4 text-on-surface-variant font-mono text-[13px]">{{ file.is_dir ? '—' : file.size_display }}</td>
              <td class="py-2.5 px-4 text-on-surface-variant">{{ formatTime(file.modified) }}</td>
              <td class="py-2.5 px-4">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-[12px] text-on-surface-variant">{{ file.permission }}</span>
                  <span class="flex items-center gap-1">
                    <span class="material-symbols-outlined text-[17px]" :class="permissionIconClass(file, 'read')" title="读权限">visibility</span>
                    <span class="material-symbols-outlined text-[17px]" :class="permissionIconClass(file, 'write')" title="改权限">edit</span>
                    <span class="material-symbols-outlined text-[17px]" :class="permissionIconClass(file, 'delete')" title="删权限">delete</span>
                  </span>
                </div>
              </td>
              <td class="py-2.5 px-4">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    class="w-8 h-8 rounded-md text-on-surface-variant hover:text-primary hover:bg-primary/10 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="file.is_dir || actionLoading"
                    title="读取文件"
                    @click.stop="openFileDialog(file, 'read')"
                  >
                    <span class="material-symbols-outlined text-[18px]">visibility</span>
                  </button>
                  <button
                    class="w-8 h-8 rounded-md text-on-surface-variant hover:text-tertiary-container hover:bg-tertiary/10 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="file.is_dir || actionLoading"
                    title="修改文件"
                    @click.stop="openFileDialog(file, 'edit')"
                  >
                    <span class="material-symbols-outlined text-[18px]">edit</span>
                  </button>
                  <button
                    class="w-8 h-8 rounded-md text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="actionLoading"
                    title="删除条目"
                    @click.stop="deleteEntry(file)"
                  >
                    <span class="material-symbols-outlined text-[18px]">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="loading" class="py-16 text-center text-on-surface-variant">
          <span class="material-symbols-outlined text-[40px] animate-spin">progress_activity</span>
          <p class="text-body-md mt-3">正在读取目录...</p>
        </div>

        <div v-else-if="fileList.length === 0" class="py-16 text-center text-on-surface-variant">
          <span class="material-symbols-outlined text-[48px] text-outline mb-3 block">folder_off</span>
          <p class="text-body-md">此目录为空</p>
        </div>

        <div class="py-3 px-4 border-t border-outline-variant/20 flex justify-between items-center bg-surface-container-lowest/50 text-body-sm text-on-surface-variant">
          <span>显示 {{ fileList.length }} 个条目</span>
          <span>{{ loading ? '同步中' : '真实服务器目录' }}</span>
        </div>
      </div>

      <div v-if="dialogVisible" class="fixed inset-0 z-50 bg-black/30 flex items-center justify-center px-4">
        <section class="w-full max-w-4xl bg-surface-container-lowest border border-outline-variant/30 rounded-xl shadow-xl overflow-hidden">
          <header class="px-5 py-4 border-b border-outline-variant/20 flex items-center justify-between gap-4">
            <div class="min-w-0">
              <h2 class="text-[18px] font-semibold text-on-surface">{{ dialogMode === 'edit' ? '修改文件' : '读取文件' }}</h2>
              <p class="text-[12px] text-on-surface-variant font-mono truncate mt-1">{{ selectedPath }}</p>
            </div>
            <button class="w-8 h-8 rounded-md text-on-surface-variant hover:bg-surface-container transition-colors" title="关闭" @click="closeDialog">
              <span class="material-symbols-outlined text-[20px]">close</span>
            </button>
          </header>

          <div class="p-5">
            <div v-if="fileTruncated" class="mb-3 rounded-md border border-tertiary/20 bg-tertiary/5 px-3 py-2 text-[12px] text-tertiary">
              文件较大，仅显示前 1 MB 内容。
            </div>
            <textarea
              v-model="fileContent"
              class="w-full h-[52vh] resize-none rounded-lg border border-outline-variant/30 bg-surface-container-low px-3 py-2 font-mono text-[13px] leading-6 text-on-surface outline-none focus:border-primary"
              :readonly="dialogMode !== 'edit'"
            ></textarea>
          </div>

          <footer class="px-5 py-4 border-t border-outline-variant/20 flex justify-end gap-2">
            <button class="h-9 px-4 rounded-lg border border-outline-variant text-on-surface-variant hover:bg-surface-container transition-colors text-body-sm" @click="closeDialog">取消</button>
            <button
              v-if="dialogMode === 'edit'"
              class="h-9 px-4 rounded-lg bg-primary-container text-on-primary hover:bg-primary transition-colors text-body-sm font-medium disabled:opacity-50"
              :disabled="actionLoading"
              @click="saveFile"
            >
              保存
            </button>
          </footer>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { deleteFileEntry, getFileList, readFileContent, writeFileContent } from '@/api/auditor.js'

const currentPath = ref('.')
const fileList = ref([])
const loading = ref(false)
const actionLoading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const dialogVisible = ref(false)
const dialogMode = ref('read')
const selectedPath = ref('')
const fileContent = ref('')
const fileTruncated = ref(false)

const canGoParent = computed(() => currentPath.value && currentPath.value !== '/')

async function loadFiles(path) {
  loading.value = true
  errorMsg.value = ''
  successMsg.value = ''
  try {
    const data = await getFileList(path)
    currentPath.value = data.current_path
    fileList.value = data.entries || []
  } catch (error) {
    errorMsg.value = error.message || '目录读取失败'
  } finally {
    loading.value = false
  }
}

function openEntry(file) {
  if (!file?.is_dir) return
  const nextPath = currentPath.value.endsWith('/')
    ? `${currentPath.value}${file.name}`
    : `${currentPath.value}/${file.name}`
  loadFiles(nextPath)
}

function goParent() {
  if (!canGoParent.value) return
  const parent = currentPath.value.split('/').filter(Boolean)
  parent.pop()
  loadFiles(`/${parent.join('/')}` || '/')
}

function entryPath(file) {
  return currentPath.value.endsWith('/')
    ? `${currentPath.value}${file.name}`
    : `${currentPath.value}/${file.name}`
}

function permissionIconClass(file, action) {
  const allowed = Boolean(file?.access?.[action])
  return allowed ? 'text-tertiary-container' : 'text-outline/40'
}

async function openFileDialog(file, mode) {
  if (!file || file.is_dir) return
  actionLoading.value = true
  errorMsg.value = ''
  successMsg.value = ''
  try {
    const data = await readFileContent(entryPath(file))
    dialogMode.value = mode
    selectedPath.value = data.path
    fileContent.value = data.content || ''
    fileTruncated.value = Boolean(data.truncated)
    dialogVisible.value = true
  } catch (error) {
    errorMsg.value = error.message || '文件读取失败'
  } finally {
    actionLoading.value = false
  }
}

function closeDialog() {
  dialogVisible.value = false
  selectedPath.value = ''
  fileContent.value = ''
  fileTruncated.value = false
}

async function saveFile() {
  if (!selectedPath.value) return
  actionLoading.value = true
  errorMsg.value = ''
  successMsg.value = ''
  try {
    await writeFileContent(selectedPath.value, fileContent.value)
    closeDialog()
    await loadFiles(currentPath.value)
    successMsg.value = '文件已保存'
  } catch (error) {
    errorMsg.value = error.message || '文件保存失败'
  } finally {
    actionLoading.value = false
  }
}

async function deleteEntry(file) {
  if (!file) return
  const target = entryPath(file)
  if (!window.confirm(`确认删除 ${target}？`)) return
  actionLoading.value = true
  errorMsg.value = ''
  successMsg.value = ''
  try {
    await deleteFileEntry(target)
    await loadFiles(currentPath.value)
    successMsg.value = '条目已删除'
  } catch (error) {
    errorMsg.value = error.message || '删除失败'
  } finally {
    actionLoading.value = false
  }
}

function formatTime(value) {
  if (!value) return ''
  return value.replace('T', ' ').replace(/\.\d+$/, '')
}

onMounted(() => {
  loadFiles(currentPath.value)
})
</script>
