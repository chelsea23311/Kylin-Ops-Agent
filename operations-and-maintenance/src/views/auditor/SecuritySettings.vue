<template>
  <div class="h-full flex flex-col overflow-hidden bg-background text-on-surface">
    <main class="flex-grow container mx-auto px-6 py-lg overflow-auto">
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col gap-xs border border-outline-variant/20 mb-lg">
        <div class="pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">安全设置</h1>
        </div>
      </section>

      <div v-if="notice" class="mb-lg rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-primary">{{ notice }}</div>
      <div v-if="errorMsg" class="mb-lg rounded-lg border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">{{ errorMsg }}</div>

      <div class="max-w-2xl">
        <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg border border-outline-variant/20">
          <h3 class="text-[16px] font-semibold text-on-surface mb-lg flex items-center gap-sm" style="font-family: 'Space Grotesk', sans-serif;">
            <span class="material-symbols-outlined text-[22px] text-primary">key</span>
            修改密钥
          </h3>

          <div class="space-y-md">
            <PasswordInput v-model="form.currentKey" label="当前密钥" />
            <PasswordInput v-model="form.newKey" label="新密钥" />
            <PasswordInput v-model="form.confirmKey" label="确认新密钥" />

            <div v-if="form.newKey" class="bg-surface-container rounded-lg p-sm border border-outline-variant/20">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-[12px] text-on-surface-variant">密钥强度：</span>
                <div class="flex gap-1">
                  <div v-for="i in 4" :key="i" class="w-12 h-1.5 rounded-full transition-colors" :class="i <= keyStrength ? 'bg-tertiary' : 'bg-outline-variant/30'"></div>
                </div>
              </div>
              <p class="text-[11px] text-on-surface-variant">{{ keyStrengthTip }}</p>
            </div>
          </div>
        </section>

      </div>

      <div class="mt-lg flex justify-end">
        <button class="px-6 py-2.5 bg-primary text-on-primary rounded font-medium text-body-sm hover:bg-primary-container transition-colors active:opacity-80 disabled:opacity-50" :disabled="saving" @click="saveSettings">
          {{ saving ? '保存中...' : '保存全部设置' }}
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, reactive, ref } from 'vue'
import { updateSecuritySettings } from '@/api/auditor.js'

const form = reactive({
  currentKey: '',
  newKey: '',
  confirmKey: '',
})

const saving = ref(false)
const errorMsg = ref('')
const notice = ref('')

const PasswordInput = defineComponent({
  props: { modelValue: String, label: String },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const visible = ref(false)
    return () => h('div', [
      h('label', { class: 'block text-[12px] font-medium text-on-surface-variant uppercase mb-1 tracking-wide' }, props.label),
      h('div', { class: 'relative' }, [
        h('input', {
          type: visible.value ? 'text' : 'password',
          value: props.modelValue || '',
          placeholder: `请输入${props.label}`,
          class: 'w-full pl-4 pr-10 py-2.5 border border-outline-variant rounded bg-surface-container-low text-on-surface text-body-sm outline-none transition-shadow',
          onInput: (event) => emit('update:modelValue', event.target.value),
        }),
        h('button', {
          class: 'absolute right-2 top-1/2 -translate-y-1/2 p-1 text-outline-variant hover:text-primary transition-colors',
          onClick: (event) => {
            event.preventDefault()
            visible.value = !visible.value
          },
        }, [h('span', { class: 'material-symbols-outlined text-[20px]' }, visible.value ? 'visibility_off' : 'visibility')]),
      ]),
    ])
  },
})

const keyStrength = computed(() => {
  const val = form.newKey
  if (!val) return 0
  let score = 0
  if (val.length >= 8) score++
  if (/[a-z]/.test(val) && /[A-Z]/.test(val)) score++
  if (/\d/.test(val)) score++
  if (/[^a-zA-Z0-9]/.test(val)) score++
  return score
})

const keyStrengthTip = computed(() => {
  const tips = ['', '较弱 - 建议增加复杂度和长度', '中等 - 可进一步增加特殊字符', '较强 - 安全性较好', '强 - 密钥强度优秀']
  return tips[keyStrength.value] || ''
})

async function saveSettings() {
  saving.value = true
  errorMsg.value = ''
  notice.value = ''
  try {
    await updateSecuritySettings({
      current_password: form.currentKey,
      new_password: form.newKey,
      confirm_password: form.confirmKey,
    })
    notice.value = '安全设置已保存'
    form.currentKey = ''
    form.newKey = ''
    form.confirmKey = ''
  } catch (error) {
    errorMsg.value = error.message || '保存失败'
  } finally {
    saving.value = false
  }
}

</script>

<style scoped>
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 300px;
}
</style>
