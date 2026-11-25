<template>
  <div class="h-full overflow-auto bg-background text-on-surface">
    <main class="flex-grow container mx-auto px-lg py-xl max-w-[1200px] flex flex-col gap-lg pb-16">

      <!-- Search Section -->
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col gap-md border border-outline-variant/20">
        <h1 class="text-h2 font-semibold text-on-surface pt-1" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">知识库搜索</h1>

        <div class="flex flex-col md:flex-row gap-4 mt-sm">
          <!-- Search Input -->
          <div class="flex-grow relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">search</span>
            <input
              v-model="query"
              type="text"
              placeholder="输入关键词或短语..."
              class="w-full pl-10 pr-4 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-body-md text-on-surface focus:border-primary focus:ring-2 focus:ring-primary/50 outline-none transition-all h-[44px]"
              @keydown.enter="doSearch"
            />
          </div>

          <!-- Confidence Rank -->
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
              <label class="text-label-caps font-semibold text-on-surface-variant whitespace-nowrap">置信度排名:</label>
              <select
                v-model="topK"
                class="bg-surface-container-lowest border border-outline-variant rounded-lg text-body-sm text-on-surface py-2 pl-3 pr-8 focus:border-primary outline-none h-[44px] cursor-pointer"
              >
                <option>3</option>
                <option>5</option>
                <option>10</option>
              </select>
            </div>
            <button
              class="bg-primary text-on-primary text-body-md font-medium px-6 py-2 rounded-lg hover:bg-primary-fixed transition-colors h-[44px] flex items-center justify-center min-w-[100px] neon-glow"
              @click="doSearch"
            >搜索</button>
          </div>
        </div>
      </section>

      <!-- Results Section -->
      <section v-if="searched" class="flex flex-col gap-md">
        <div class="flex items-center justify-between">
          <h2 class="text-h3 font-semibold text-on-surface mb-xs" style="font-family: 'Space Grotesk', sans-serif; font-size: 22px;">搜索结果</h2>
          <span class="text-label-caps font-semibold text-on-surface-variant">共 {{ results.length }} 条</span>
        </div>

        <!-- Loading skeleton -->
        <div v-if="loading" class="flex flex-col gap-md">
          <div v-for="i in 3" :key="i" class="bg-surface-container-lowest rounded-xl p-lg border border-outline-variant/20 animate-pulse">
            <div class="h-4 bg-surface-container-high rounded w-1/3 mb-3"></div>
            <div class="h-3 bg-surface-container-high rounded w-2/3 mb-2"></div>
            <div class="h-3 bg-surface-container-high rounded w-full"></div>
          </div>
        </div>

        <!-- Result Cards -->
        <article
          v-for="(res, i) in results"
          :key="i"
          class="bg-surface-container-lowest rounded-xl p-lg border border-outline-variant/20 flex flex-col gap-4 shadow-panel"
        >
          <header class="flex justify-between items-start">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">article</span>
              <h3 class="font-medium text-on-surface" style="font-family: 'Inter', monospace; font-size: 13px;">{{ res.id }}</h3>
            </div>
            <div :class="['px-2 py-1 rounded border flex items-center gap-1 text-[12px]', scoreStyle(res.score).class]"
                 style="font-family: 'Inter', monospace; font-size: 12px;">
              <span class="material-symbols-outlined text-[14px]">{{ scoreStyle(res.score).icon }}</span>
              分数: {{ res.score }}
            </div>
          </header>
          <div class="pl-8 flex flex-col gap-2">
            <p class="text-body-md text-on-surface"><strong class="font-semibold text-on-surface">问：</strong>{{ res.q }}</p>
            <p class="text-body-md text-on-surface-variant"><strong class="font-semibold text-on-surface">答：</strong>{{ res.a }}</p>
          </div>
        </article>

        <!-- No results -->
        <div v-if="!loading && results.length === 0" class="text-center py-16 text-on-surface-variant">
          <span class="material-symbols-outlined text-[48px] text-outline mb-4 block">search_off</span>
          <p class="text-body-lg">未找到相关结果，请尝试其他关键词</p>
        </div>
      </section>

    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { searchKnowledge } from '@/api/knowledge.js'

const query    = ref('')
const topK     = ref('5')
const searched = ref(false)
const loading  = ref(false)
const results  = ref([])

async function doSearch() {
  if (!query.value.trim()) return
  searched.value = true
  loading.value  = true
  results.value  = []
  try {
    const data = await searchKnowledge(query.value, Number(topK.value))
    results.value = data.map((item) => {
      const lines = item.text.split('\n')
      const q = lines[0]?.replace(/^问：/, '') ?? item.text
      const a = lines[1]?.replace(/^答：/, '') ?? ''
      return { id: item.section, score: item.score, q, a }
    })
  } catch (e) {
    console.error('[Knowledge] 搜索失败:', e)
    results.value = []
  } finally {
    loading.value = false
  }
}

function scoreStyle(score) {
  if (score >= 8) return { class: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: 'check_circle' }
  if (score >= 6) return { class: 'bg-amber-50 text-amber-700 border-amber-200',       icon: 'warning'      }
  return                 { class: 'bg-surface-container-low text-on-surface-variant border-outline-variant/30', icon: 'info'         }
}
</script>
