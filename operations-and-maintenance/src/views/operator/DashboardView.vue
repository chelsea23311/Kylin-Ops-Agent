<template>
  <div class="h-full flex flex-col overflow-hidden bg-background text-on-surface">

    <!-- Main Content -->
    <main class="flex-1 flex flex-col p-lg gap-lg overflow-auto">

      <!-- Page Header Card -->
      <section class="bg-surface-container-lowest rounded-xl shadow-card p-lg flex flex-col gap-md border border-outline-variant/20 mb-lg shrink-0">
        <!-- Row 1: Title -->
        <div class="flex flex-col gap-xs pt-1">
          <h1 class="text-h2 font-semibold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px;">资源监视器</h1>
        </div>

        <!-- Row 2: Action Buttons (left) + Resource Tabs (right) -->
        <div class="flex justify-between items-center">
          <div class="flex gap-2">
            <button
              class="flex items-center gap-2 px-4 py-2 bg-secondary/10 border border-secondary/30 rounded-lg text-secondary text-body-sm hover:bg-secondary/20 transition-colors"
              @click="openReportDialog"
            >
              <span class="material-symbols-outlined text-[18px]" :class="reportLoading ? 'animate-spin' : ''">analytics</span>
              {{ reportLoading ? '生成中...' : '资源检测报告' }}
            </button>
            <button
              class="flex items-center gap-2 px-4 py-2 bg-primary/10 border border-primary/30 rounded-lg text-primary text-body-sm hover:bg-primary/20 transition-colors"
              @click="openAgentDrawer"
            >
              <span class="material-symbols-outlined text-[18px]">smart_toy</span>
              Agent
            </button>
          </div>

          <!-- Resource Tabs -->
          <div class="flex bg-surface-container-high rounded-lg p-1 border border-outline-variant/20 shadow-sm">
            <button
              v-for="t in resourceTabs"
              :key="t.key"
              :class="[
                'px-4 py-1.5 text-body-sm rounded-md transition-colors',
                activeTab === t.key
                  ? 'bg-surface-container-lowest text-primary font-medium border border-primary/40 shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
              ]"
              @click="activeTab = t.key"
            >{{ t.label }}</button>
          </div>
        </div>
      </section>

      <!-- ════════════════════════════════════════════════ -->
      <!-- 总览 Tab：监控总览                                    -->
      <!-- ════════════════════════════════════════════════ -->
      <template v-if="activeTab === 'overview'">
        <!-- Auto Rules Triggered Banner -->
        <div v-if="triggeredRules.length > 0" class="flex flex-col gap-2">
          <div
            v-for="rule in triggeredRules"
            :key="rule.rule_key"
            :class="[
              'flex items-center gap-3 px-4 py-3 rounded-lg border text-body-sm',
              rule.severity === 'critical'
                ? 'bg-error/10 border-error/30 text-error'
                : 'bg-tertiary/10 border-tertiary/30 text-tertiary'
            ]"
          >
            <span class="material-symbols-outlined text-[20px]">{{ rule.severity === 'critical' ? 'error' : 'warning' }}</span>
            <span class="font-medium">{{ rule.message }}</span>
            <span :class="rule.severity === 'critical' ? 'bg-error/20 text-error' : 'bg-tertiary/20 text-tertiary'" class="px-2 py-0.5 rounded text-[11px] uppercase font-semibold ml-auto">{{ rule.severity === 'critical' ? '严重' : '警告' }}</span>
          </div>
        </div>

        <!-- Gauges Row -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-lg">
          <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg flex flex-col items-center">
            <span class="text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider mb-3">CPU 使用率</span>
            <div class="relative w-32 h-32">
              <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#dee3e9" stroke-width="3"/>
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" :stroke="gaugeColor(overview.gauges.cpu_percent, 90, 70)" stroke-width="3" stroke-linecap="round" :stroke-dasharray="`${overview.gauges.cpu_percent}, 100`"/>
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-h3 font-bold" style="font-family: 'Space Grotesk', sans-serif;">{{ overview.gauges.cpu_percent ?? '—' }}</span>
                <span class="text-[11px] text-on-surface-variant">%</span>
              </div>
            </div>
            <p class="text-body-sm text-on-surface-variant mt-2" :class="overview.gauges.cpu_percent >= 90 ? 'text-error font-semibold' : ''">{{ overview.gauges.cpu_percent >= 90 ? '⚠ 超过阈值 90%' : '阈值 90%' }}</p>
          </div>
          <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg flex flex-col items-center">
            <span class="text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider mb-3">内存使用率</span>
            <div class="relative w-32 h-32">
              <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#dee3e9" stroke-width="3"/>
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" :stroke="gaugeColor(overview.gauges.memory_percent, 85, 70)" stroke-width="3" stroke-linecap="round" :stroke-dasharray="`${overview.gauges.memory_percent}, 100`"/>
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-h3 font-bold" style="font-family: 'Space Grotesk', sans-serif;">{{ overview.gauges.memory_percent ?? '—' }}</span>
                <span class="text-[11px] text-on-surface-variant">%</span>
              </div>
            </div>
            <p class="text-body-sm text-on-surface-variant mt-2">阈值 85%</p>
          </div>
          <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg flex flex-col items-center">
            <span class="text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider mb-3">磁盘使用率</span>
            <div class="relative w-32 h-32">
              <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#dee3e9" stroke-width="3"/>
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" :stroke="gaugeColor(overview.gauges.disk_percent, 85, 70)" stroke-width="3" stroke-linecap="round" :stroke-dasharray="`${overview.gauges.disk_percent}, 100`"/>
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-h3 font-bold" style="font-family: 'Space Grotesk', sans-serif;">{{ overview.gauges.disk_percent ?? '—' }}</span>
                <span class="text-[11px] text-on-surface-variant">%</span>
              </div>
            </div>
            <p class="text-body-sm text-on-surface-variant mt-2" :class="overview.gauges.disk_percent >= 85 ? 'text-error font-semibold' : ''">{{ overview.gauges.disk_percent >= 85 ? '⚠ 超过阈值 85%' : '阈值 85%' }}</p>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 text-body-sm text-on-surface-variant">
          <span>图表时间范围</span>
          <select v-model="overviewTimeRange" class="bg-surface-container-low border border-outline-variant/30 rounded-lg px-3 py-1.5" aria-label="图表时间范围">
            <option value="samples">适配已有数据</option>
            <option value="24h">完整 24 小时</option>
          </select>
        </div>
        <!-- Fit observed timestamps across the chart; missing samples remain gaps. -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-lg">
          <div v-for="chart in overviewCharts" :key="chart.key" class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg">
            <div class="flex items-center justify-between mb-1">
              <h2 class="text-body-md font-semibold text-on-surface">{{ chart.title }}</h2>
              <span class="text-body-sm text-on-surface-variant">{{ chart.unit }}</span>
            </div>
            <p class="text-[11px] text-on-surface-variant mb-3">{{ chart.data.coverage }}</p>
            <div class="relative" style="height: 200px;">
              <div class="absolute text-[10px] text-on-surface-variant flex flex-col justify-between items-end pointer-events-none" style="left: 0; width: 40px; top: 8px; bottom: 8px;">
                <span>{{ chart.data.yTop }}</span>
                <span>{{ chart.data.yMid }}</span>
                <span>0</span>
              </div>
              <div class="absolute" style="left: 48px; right: 12px; top: 8px; bottom: 8px;">
                <svg class="w-full h-full" viewBox="0 0 300 100" preserveAspectRatio="none" aria-hidden="true">
                  <defs>
                    <linearGradient :id="`${chart.key}Grad`" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" :stop-color="chart.color" stop-opacity="0.25"/>
                      <stop offset="100%" :stop-color="chart.color" stop-opacity="0"/>
                    </linearGradient>
                  </defs>
                  <path d="M0,0 H300 M0,50 H300 M0,100 H300" fill="none" stroke="currentColor" opacity="0.12" vector-effect="non-scaling-stroke"/>
                  <path v-if="chart.data.area" :d="chart.data.area" :fill="`url(#${chart.key}Grad)`"/>
                  <FlowingChartLine v-if="chart.data.line" :d="chart.data.line" :color="chart.color" />
                </svg>
                <button
                  v-for="(point, pointIndex) in chart.data.points"
                  :key="point.key"
                  class="chart-data-point overview-chart-point"
                  :class="{ 'is-single': point.isolated, 'is-latest': pointIndex === chart.data.points.length - 1 }"
                  :style="{ left: `${point.xPercent}%`, top: `${point.yPercent}%`, '--point-color': chart.color }"
                  :title="point.tooltip"
                  :aria-label="point.tooltip"
                  type="button"
                >
                  <span class="chart-data-dot"></span>
                  <span class="chart-data-tooltip" :class="point.tooltipSide">
                    <span class="block text-[10px] text-on-surface-variant mb-1">{{ point.time }}</span>
                    <span class="block text-[13px] font-semibold text-on-surface">{{ point.label }}</span>
                    <span class="block text-[11px] text-on-surface-variant leading-snug mt-1">{{ point.explanation }}</span>
                  </span>
                </button>
                <div v-if="!chart.data.points.length" class="absolute inset-0 flex items-center justify-center text-body-sm text-on-surface-variant text-center px-4">
                  {{ chart.key === 'qps' ? '等待有效采样；若持续无数据，请检查 Nginx 访问日志路径和读取权限' : '等待网络速率采样，首次采样需要建立计数基线' }}
                </div>
              </div>
            </div>
            <div class="flex justify-between text-[10px] text-on-surface-variant mt-1" style="margin-left: 48px; margin-right: 12px;">
              <span>{{ chart.data.xFirst }}</span>
              <span>{{ chart.data.xMid }}</span>
              <span>{{ chart.data.xLast }}</span>
            </div>
          </div>
        </div>

        <!-- Service Status -->
        <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg">
          <h2 class="text-body-md font-semibold text-on-surface mb-4">服务状态</h2>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div v-for="svc in overview.service_status" :key="svc.name" class="flex items-center gap-3 bg-surface-container-high rounded-lg p-4 border border-outline-variant/10">
              <span class="w-3 h-3 rounded-full shrink-0" :class="svc.status === 'UP' ? 'bg-success' : 'bg-error'"></span>
              <div class="flex flex-col">
                <span class="text-body-sm font-semibold text-on-surface">{{ svc.name }}</span>
                <span :class="svc.status === 'UP' ? 'text-success' : 'text-error'" class="text-[12px] font-medium">{{ svc.status === 'UP' ? '运行中' : '已停止' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Loading / Error -->
        <div v-if="overviewLoading" class="text-center py-8 text-on-surface-variant">
          <span class="material-symbols-outlined animate-spin text-[24px] mb-2 block">sync</span>
          <p class="text-body-sm">加载监控数据中...</p>
        </div>
        <div v-if="overviewError" class="text-center py-8 text-error bg-error/5 rounded-xl border border-error/20">
          <span class="material-symbols-outlined text-[32px] mb-2 block">error</span>
          <p class="text-body-sm">{{ overviewError }}</p>
        </div>
      </template>

      <!-- ════════════════════════════════════════════════ -->
      <!-- 资源 Tab：CPU / 内存 / 网络 / 磁盘                      -->
      <!-- ════════════════════════════════════════════════ -->
      <template v-if="activeTab !== 'overview'">
        <!-- Summary Bar -->
        <div class="bg-surface-container-lowest glass-panel rounded-xl p-md border border-outline-variant/20 shadow-panel flex gap-lg items-center shrink-0 relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-[3px] bg-primary-container/60"></div>
          <div class="flex-1 border-r border-outline-variant/20 pr-lg">
            <div class="text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider mb-sm">{{ (summaryMeta[activeTab] || {}).title }}</div>
            <div class="flex items-end gap-2">
              <span class="text-h2 font-bold text-primary-container" style="font-family: 'Space Grotesk', sans-serif;">{{ (summaryMeta[activeTab] || {}).value }}</span>
              <span class="text-body-md text-on-surface-variant pb-1">{{ (summaryMeta[activeTab] || {}).unit }}</span>
            </div>
          </div>
          <div class="flex-1 border-r border-outline-variant/20 px-lg">
            <div class="text-label-caps font-semibold text-primary-container uppercase tracking-wider mb-sm">{{ activeSummary.extraLabel }}</div>
            <div class="flex items-end gap-2">
              <span class="text-h3 font-bold text-primary-container" style="font-family: 'Space Grotesk', sans-serif;">{{ activeSummary.extraValue }}</span>
            </div>
          </div>
          <div class="flex-1 border-r border-outline-variant/20 px-lg">
            <div class="text-label-caps font-semibold text-primary-container uppercase tracking-wider mb-sm">{{ col3Meta.label }}</div>
            <div class="flex items-end gap-2">
              <span class="text-h3 font-bold text-primary-container" style="font-family: 'Space Grotesk', sans-serif;">{{ col3Meta.value }}</span>
            </div>
          </div>
          <!-- Uptime -->
          <div class="flex-1">
            <div class="text-label-caps font-semibold text-on-surface-variant uppercase tracking-wider mb-sm">系统运行时长</div>
            <div class="flex items-end gap-1">
              <span class="font-bold text-primary-container neon-text-glow" style="font-family: 'Space Grotesk', sans-serif; font-size: 28px; line-height: 1; letter-spacing: -0.5px;">{{ uptimeDays }}</span>
              <span class="text-body-md text-on-surface-variant pb-1">天</span>
            </div>
          </div>
        </div>

      <!-- Main Grid -->
      <div class="flex-1 grid grid-cols-12 gap-lg min-h-0">

        <!-- Process Table (Left 8 cols) -->
        <div class="col-span-12 lg:col-span-8 bg-surface-container-lowest glass-panel rounded-xl border border-outline-variant/20 shadow-panel flex flex-col overflow-hidden relative">
          <div class="p-md border-b border-outline-variant/30 flex justify-between items-center bg-surface-container-highest/50">
            <h2 class="text-body-md font-semibold text-on-surface">活动进程</h2>
            <button class="p-1.5 text-on-surface-variant hover:text-primary hover:bg-surface-variant/50 rounded transition-colors">
              <span class="material-symbols-outlined text-sm">filter_list</span>
            </button>
          </div>
          <div class="flex-1 overflow-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr>
                  <th v-for="(col, ci) in currentCols" :key="col"
                    class="text-label-caps font-semibold text-on-surface-variant py-2 px-3 border-b border-outline-variant/20 sticky top-0 bg-surface-container"
                    :class="ci > 1 ? 'text-right' : ''"
                  >{{ col }}</th>
                </tr>
              </thead>
              <tbody class="text-body-sm text-on-surface">
                <tr v-if="!currentRows.length">
                  <td :colspan="Math.max(currentCols.length, 1)" class="py-6 text-center text-on-surface-variant">暂无活动进程数据（实时更新中）</td>
                </tr>
                <tr
                  v-for="(row, ri) in currentRows"
                  :key="row[1] ?? `${row[0] ?? 'row'}-${ri}`"
                  class="hover:bg-surface-variant/50 transition-colors cursor-pointer border-b border-outline-variant/20 last:border-0"
                >
                  <!-- Col 0: 进程名 + 图标 -->
                  <td class="py-2.5 px-3">
                    <div class="flex items-center gap-2">
                      <span :class="['material-symbols-outlined text-sm', getIconColor(row)]">{{ getIcon(row[0]) }}</span>
                      {{ row[0] }}
                    </div>
                  </td>
                  <!-- Col 1: PID -->
                  <td class="py-2.5 px-3 text-right text-primary/80" style="font-family: 'Inter', monospace; font-size: 13px;">{{ row[1] }}</td>
                  <!-- Col 2+: 动态列 -->
                  <td
                    v-for="(cell, ci) in safeSlice(row, 2)"
                    :key="ci"
                    :class="['py-2.5 px-3 text-right', getCellClass(currentCols[ci + 2], cell)]"
                  >{{ formatCellValue(cell) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Chart Area (Right 4 cols) -->
        <div class="col-span-12 lg:col-span-4 flex flex-col gap-lg min-h-0">
          <!-- Total Chart -->
          <div class="flex-1 min-h-[220px] bg-surface-container-lowest glass-panel rounded-xl border border-outline-variant/20 shadow-panel p-md flex flex-col overflow-hidden relative">
            <div class="flex justify-between items-center mb-2 shrink-0">
              <h2 class="text-body-md font-semibold text-on-surface">{{ currentChartMeta.title }}</h2>
              <span class="text-label-caps font-semibold text-primary border border-primary/40 bg-surface px-2 py-1 rounded">60帧窗口</span>
            </div>
            <!-- Dynamic chart with axes -->
            <div class="flex-1 flex flex-col min-h-[140px]">
              <!-- Y-axis labels + chart body -->
              <div class="flex-1 flex gap-1 min-h-0">
                <!-- Y labels -->
                <div class="flex flex-col justify-between text-right py-0.5 shrink-0 w-9">
                  <span class="text-[9px] text-on-surface-variant/50 leading-none">{{ chartPathData.yTop }}</span>
                  <span class="text-[9px] text-on-surface-variant/50 leading-none">{{ chartPathData.yMid }}</span>
                  <span class="text-[9px] text-on-surface-variant/50 leading-none">{{ chartPathData.yBot }}</span>
                </div>
                <!-- SVG chart -->
                <div class="flex-1 relative border-l border-b border-outline-variant/20 overflow-visible">
                  <svg class="w-full h-full" viewBox="0 0 300 80" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="monitorChartGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" :stop-color="chartStrokeColor" stop-opacity="0.3"/>
                        <stop offset="100%" :stop-color="chartStrokeColor" stop-opacity="0"/>
                      </linearGradient>
                    </defs>
                    <path v-if="chartPathData.area" :d="chartPathData.area" fill="url(#monitorChartGrad)"/>
                    <FlowingChartLine v-if="chartPathData.line" :d="chartPathData.line" :color="chartStrokeColor" />
                    <text v-if="!chartPathData.line" x="150" y="45" text-anchor="middle" fill="rgba(23,28,32,0.25)" font-size="10" font-family="sans-serif">暂无图表数据</text>
                  </svg>
                  <button
                    v-for="(point, pointIndex) in chartPathData.points"
                    :key="point.key"
                    class="chart-data-point group"
                    :class="{ 'is-latest': pointIndex === chartPathData.points.length - 1 }"
                    :style="{ left: `${point.xPercent}%`, top: `${point.yPercent}%`, '--point-color': chartStrokeColor }"
                    :title="point.tooltip"
                    type="button"
                  >
                    <span class="chart-data-dot"></span>
                    <span class="chart-data-tooltip" :class="point.tooltipSide">
                      <span class="block text-[10px] text-on-surface-variant mb-1">{{ point.time }}</span>
                      <span class="block text-[13px] font-semibold text-on-surface">{{ point.label }}</span>
                      <span class="block text-[11px] text-on-surface-variant leading-snug mt-1">{{ point.explanation }}</span>
                    </span>
                  </button>
                  <!-- Grid lines -->
                  <div class="absolute inset-0 flex flex-col justify-between pointer-events-none">
                    <div class="border-t border-outline-variant/10 w-full"></div>
                    <div class="border-t border-outline-variant/10 w-full"></div>
                    <div class="border-t border-outline-variant/10 w-full"></div>
                    <div class="border-t border-outline-variant/10 w-full"></div>
                  </div>
                </div>
              </div>
              <!-- X-axis labels -->
              <div class="flex justify-between pl-10 pt-0.5 shrink-0">
                <span class="text-[9px] text-on-surface-variant/50 font-mono">{{ chartPathData.xFirst }}</span>
                <span class="text-[9px] text-on-surface-variant/50 font-mono">{{ chartPathData.xMid }}</span>
                <span class="text-[9px] text-on-surface-variant/50 font-mono">{{ chartPathData.xLast }}</span>
              </div>
            </div>
          </div>

          <!-- Stats Panel -->
          <div class="bg-surface-container-lowest glass-panel rounded-xl border border-outline-variant/20 shadow-panel p-md relative">
            <h2 class="text-body-md font-semibold text-on-surface mb-3">进程统计</h2>
            <div class="space-y-2">
              <div class="flex justify-between items-center text-body-sm">
                <span class="text-on-surface-variant">运行中</span>
                <span class="text-success font-medium">{{ processStats.running }}</span>
              </div>
              <div class="flex justify-between items-center text-body-sm">
                <span class="text-on-surface-variant">已挂起</span>
                <span class="text-on-surface-variant font-medium">{{ processStats.suspended }}</span>
              </div>
              <div class="flex justify-between items-center text-body-sm">
                <span class="text-on-surface-variant">异常</span>
                <span class="text-error font-medium">{{ processStats.error }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

        <!-- WS Status Bar -->
        <div class="shrink-0 flex items-center gap-2 py-1 text-[11px] text-on-surface-variant border-t border-outline-variant/10">
          <span :class="['w-1.5 h-1.5 rounded-full inline-block flex-shrink-0 transition-colors duration-500', wsStatusDotClass]"></span>
          <span>{{ wsStatusText }}</span>
          <span class="ml-auto text-on-surface-variant/40">{{ currentChartMeta.unit }}</span>
        </div>
      </template>
    </main>

    <!-- ── Resource Report Dialog ───────────────────────── -->
    <el-dialog
      v-model="reportDialog"
      :show-close="false"
      width="680px"
      top="5vh"
      class="report-dialog"
    >
      <template #header="{ close }">
        <div class="flex items-center justify-between w-full pr-2">
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-secondary text-[22px]">analytics</span>
            <h2 class="text-h2 font-semibold text-on-surface tracking-tight" style="font-family: 'Space Grotesk', sans-serif; font-size: 20px;">资源检测报告</h2>
          </div>
          <button class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors" @click="close">
            <span class="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      </template>

      <div class="flex flex-col gap-lg">
        <!-- Controls -->
        <div class="flex items-center gap-3 bg-surface-container-low rounded-xl p-md border border-outline-variant/20">
          <span class="text-body-sm font-medium text-on-surface-variant shrink-0">分析目录</span>
          <input
            v-model="reportDirectory"
            type="text"
            placeholder="/var/log"
            class="flex-1 h-9 bg-surface-container-lowest border border-outline-variant rounded-lg px-3 text-body-sm text-on-surface outline-none focus:border-secondary/50 transition-colors placeholder:text-outline-variant"
          />
          <button
            class="flex items-center gap-1.5 h-9 px-4 rounded-lg bg-secondary text-on-secondary text-body-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            :disabled="reportLoading"
            @click="generateResourceReport"
          >
            <span class="material-symbols-outlined text-[16px]" :class="reportLoading ? 'animate-spin' : ''">{{ reportLoading ? 'sync' : 'play_arrow' }}</span>
            {{ reportLoading ? '分析中...' : '开始分析' }}
          </button>
        </div>

        <div v-if="reportError" class="bg-error/5 border border-error/20 rounded-xl p-lg text-center">
          <span class="material-symbols-outlined text-error text-[32px] mb-2 block">error</span>
          <p class="text-body-sm text-error">{{ reportError }}</p>
        </div>

        <div v-else-if="reportData" class="flex flex-col gap-lg">
          <!-- Health Score -->
          <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-label-caps text-on-surface-variant uppercase tracking-wider mb-1">系统健康评分</p>
                <p class="text-[11px] text-on-surface-variant/70">目录: {{ reportBaseDir || reportDirectory }}</p>
              </div>
              <div class="flex items-center gap-3">
                <div class="relative w-16 h-16">
                  <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
                    <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#dee3e9" stroke-width="3"/>
                    <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" :stroke="reportScoreColor" stroke-width="3" stroke-linecap="round" :stroke-dasharray="`${reportData.health_score ?? 0}, 100`"/>
                  </svg>
                  <span class="absolute inset-0 flex items-center justify-center font-bold text-on-surface" style="font-family: 'Space Grotesk', sans-serif; font-size: 16px;">{{ reportData.health_score ?? '—' }}</span>
                </div>
                <span :class="['text-body-sm font-semibold', reportScoreLabel.class]">{{ reportScoreLabel.text }}</span>
              </div>
            </div>
          </div>

          <!-- Summary -->
          <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg">
            <h3 class="flex items-center gap-2 text-body-md font-semibold text-on-surface mb-3">
              <span class="material-symbols-outlined text-secondary text-[18px]">description</span>
              总体结论
            </h3>
            <p class="text-body-sm text-on-surface-variant leading-relaxed">{{ reportData.summary || '暂无' }}</p>
          </div>

          <!-- Predictions -->
          <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg">
            <h3 class="flex items-center gap-2 text-body-md font-semibold text-on-surface mb-4">
              <span class="material-symbols-outlined text-tertiary-container text-[18px]">trending_up</span>
              未来可能问题预测
            </h3>
            <div v-if="(reportData.future_predictions || []).length" class="space-y-3">
              <div
                v-for="(item, i) in reportData.future_predictions"
                :key="`rep-future-${i}`"
                class="bg-surface-container-high rounded-lg p-md border border-outline-variant/10"
              >
                <div class="flex items-start justify-between gap-3 mb-2">
                  <span class="text-body-sm font-semibold text-on-surface">{{ item.issue }}</span>
                  <span class="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase shrink-0" :class="reportPriorityClass(item.probability)">{{ item.probability || 'low' }}</span>
                </div>
                <div class="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-on-surface-variant">
                  <span v-if="item.horizon" class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">schedule</span> {{ item.horizon }}</span>
                  <span v-if="item.signal" class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">info</span> {{ item.signal }}</span>
                </div>
                <div v-if="item.mitigation" class="mt-2 flex items-start gap-1.5 text-[12px] text-secondary bg-secondary/5 rounded-lg p-2">
                  <span class="material-symbols-outlined text-[14px] shrink-0 mt-0.5">lightbulb</span>
                  <span>{{ item.mitigation }}</span>
                </div>
              </div>
            </div>
            <div v-else class="flex items-center gap-2 text-body-sm text-tertiary">
              <span class="material-symbols-outlined text-[18px]">check_circle</span>
              暂无未来风险预测
            </div>
          </div>

          <!-- Recommended Tasks -->
          <div class="bg-surface-container-low rounded-xl border border-outline-variant/20 p-lg">
            <h3 class="flex items-center gap-2 text-body-md font-semibold text-on-surface mb-4">
              <span class="material-symbols-outlined text-primary text-[18px]">assignment</span>
              建议任务
            </h3>
            <div v-if="(reportData.recommended_tasks || []).length" class="space-y-3">
              <div
                v-for="(task, i) in reportData.recommended_tasks"
                :key="`rep-task-${i}`"
                class="bg-surface-container-high rounded-lg p-md border border-outline-variant/10"
              >
                <div class="flex items-start justify-between gap-3 mb-2">
                  <span class="text-body-sm font-semibold text-on-surface">{{ task.title }}</span>
                  <span class="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase shrink-0" :class="reportPriorityClass(task.priority)">{{ task.priority || 'low' }}</span>
                </div>
                <p class="text-[12px] text-on-surface-variant mb-2">{{ task.reason }}</p>
                <div v-if="task.suggested_command" class="bg-surface-container-lowest rounded-lg border border-outline-variant/20 p-2 text-[11px] text-on-surface break-all mb-2">{{ task.suggested_command }}</div>
                <div v-if="task.risk_note" class="flex items-start gap-1.5 text-[11px] text-tertiary-container">
                  <span class="material-symbols-outlined text-[14px] shrink-0 mt-0.5">warning</span>
                  <span>{{ task.risk_note }}</span>
                </div>
              </div>
            </div>
            <div v-else class="flex items-center gap-2 text-body-sm text-tertiary">
              <span class="material-symbols-outlined text-[18px]">check_circle</span>
              暂无建议任务
            </div>
          </div>
        </div>
        <div v-else class="flex flex-col items-center gap-3 py-12 text-on-surface-variant">
          <span class="material-symbols-outlined text-[48px] text-outline-variant">analytics</span>
          <p class="text-body-md">点击"开始分析"生成 AI 资源检测报告</p>
        </div>
      </div>
    </el-dialog>

    <!-- ── Agent Drawer ─────────────────────────────────── -->
    <el-drawer
      v-model="agentDrawer"
      title=""
      direction="rtl"
      size="780px"
      :show-close="false"
    >
      <template #header>
        <div class="flex justify-between items-center w-full">
          <div class="flex items-center gap-2 min-w-0">
            <h2 class="font-bold text-on-surface tracking-tight shrink-0" style="font-family: 'Space Grotesk', sans-serif; font-size: 20px;">麒翼智能助手</h2>
            <div v-if="currentSceneTags.length" class="flex items-center gap-1.5 min-w-0 flex-wrap justify-end">
              <span
                v-for="tag in currentSceneTags"
                :key="tag"
                class="text-[10px] px-2 py-0.5 rounded border border-primary/25 bg-primary/10 text-primary font-medium whitespace-nowrap"
              >{{ tag }}</span>
            </div>
          </div>
          <button class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors" @click="closeAgentDrawer">
            <span class="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
      </template>

      <!-- Agent chat area -->
      <div class="h-full flex flex-col" style="background:#fafafa;">

        <!-- 步骤进度条（有任务时显示） -->
        <div v-if="agentStatus" ref="progressBarRef" class="px-4 py-2 border-b border-outline-variant/50 bg-surface-container-highest/30 overflow-x-auto whitespace-nowrap scrollbar-hide">
          <div class="flex items-center gap-2 px-1">
            <template v-for="(step, i) in agentStepProgress" :key="step.key">
              <div v-if="i > 0" class="w-4 h-px shrink-0" :class="step.blocked ? 'bg-error/40' : step.done ? 'bg-primary/50' : 'bg-outline-variant/40'"></div>
              <div class="flex items-center gap-1 shrink-0 text-[11px] tracking-wider px-1 rounded transition-colors duration-300 cursor-pointer hover:bg-surface-container-high"
                   v-bind="(step.active || step.blocked) ? { 'data-step-active': '' } : {}"
                   @click="scrollToCard(step.key)"
                   :class="step.done
                     ? 'opacity-60 text-on-surface-variant'
                     : step.blocked
                       ? 'text-error border border-error/30 bg-error/5'
                       : step.active
                         ? 'text-primary border border-primary/30 bg-primary/5'
                         : 'text-outline'">
                <span class="material-symbols-outlined text-[14px]" :class="{ 'animate-pulse': step.active }">
                  {{ step.done ? 'check_circle' : step.icon }}
                </span>
                {{ step.label }}
              </div>
            </template>
          </div>
        </div>

        <!-- 消息列表 -->
        <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 flex flex-col gap-3">

          <!-- 固定欢迎语 -->
          <div class="flex gap-3">
            <div class="w-8 h-8 rounded-full bg-tertiary/20 border border-tertiary/30 flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-tertiary text-[14px]">smart_toy</span>
            </div>
            <div class="bg-surface-container rounded-xl rounded-tl-sm p-3 border border-outline-variant/20 text-[13px] text-on-surface max-w-[85%]">
              你好，我是麒翼智能运维助手。请描述你需要执行的运维任务。
            </div>
          </div>

          <!-- 动态消息 -->
          <div v-for="(msg, idx) in agentMessages" :key="idx" class="agent-msg-enter">

            <!-- 用户气泡 -->
            <div v-if="msg.type === 'user'" class="flex gap-3 justify-end">
              <div class="bg-primary/20 border border-primary/30 rounded-xl rounded-tr-sm p-3 text-[13px] text-on-surface max-w-[80%]">{{ msg.text }}</div>
              <div class="w-8 h-8 rounded-full bg-surface-variant border border-outline-variant/30 flex items-center justify-center shrink-0 text-primary font-bold text-sm">U</div>
            </div>

            <!-- Agent 历史气泡 -->
            <div v-else-if="msg.type === 'bubble'" class="flex gap-3">
              <div class="w-8 h-8 rounded-full bg-tertiary/20 border border-tertiary/30 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-tertiary text-[14px]">smart_toy</span>
              </div>
              <div class="rounded-xl rounded-tl-sm px-3 py-2 text-[13px] max-w-[85%]" :class="[msg.colorClass, msg.tiny ? 'opacity-60' : '']">
                {{ displayAgentText(msg.text) }}
              </div>
            </div>

            <!-- ── 单气泡指令响应 ── -->
            <div v-else-if="msg.type === 'instruction_response'" class="flex gap-3 instruction-response-bubble">
              <div class="w-8 h-8 rounded-full bg-tertiary/20 border border-tertiary/30 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-tertiary text-[14px]">smart_toy</span>
              </div>
              <div class="flex-1 bg-surface-container rounded-xl rounded-tl-sm border border-outline-variant/20 overflow-hidden max-w-[92%]" style="background:#ffffff;">
                <div class="divide-y divide-outline-variant/10">
                  <div v-for="(sec,si) in msg.sections" :key="si" :data-step-key="sec.key" class="px-3 py-2.5">
                    <div class="font-bold text-[15px] mb-1 section-title-color" style="color:#1544ad;">{{ sec.title }}<span v-if="sec.streaming" class="typing-cursor"></span></div>
                    <div class="text-[13px] text-on-surface leading-relaxed mb-2 whitespace-pre-wrap">{{ displayAgentText(sec.text) }}<span v-if="sec.streaming" class="typing-cursor"></span></div>
                    <!-- 组件加载中 -->
                    <div v-if="!sec.streaming && !sec.componentReady && sec.key && sec.key !== 'step9_approval_payload' && sec.key !== 'step13_execution_report'" class="flex items-center gap-2 text-[11px] text-on-surface-variant/60 py-1">
                      <span class="w-3 h-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></span>加载中...
                    </div>
                    <!-- 组件：折叠/展开 -->
                    <div v-if="sec.componentReady">
                      <!-- 折叠摘要条 -->
                      <div v-if="sec.collapsed" class="flex items-center justify-between cursor-pointer bg-surface-container-low rounded-lg px-3 py-2 border border-outline-variant/15 hover:border-primary/30 transition-colors group" @click="sec.collapsed = false">
                        <span class="text-[11px] text-on-surface-variant/70 flex items-center gap-1.5"><span class="material-symbols-outlined text-[14px] text-outline">info</span>{{ getSectionSummary(sec) }}</span>
                        <span class="text-[11px] text-primary flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">点击详情<span class="material-symbols-outlined text-[12px]">expand_more</span></span>
                      </div>
                      <!-- 展开详情 -->
                      <div v-else>
                        <div class="flex justify-end mb-1">
                          <button class="flex items-center gap-1 text-[10px] text-on-surface-variant/60 hover:text-primary transition-colors px-2 py-0.5 rounded hover:bg-surface-container-high" @click="sec.collapsed = true">
                            <span class="material-symbols-outlined text-[12px]">expand_less</span>收起详情
                          </button>
                        </div>
                        <!-- perception -->
                        <div v-if="sec.key==='step3_perception'" class="bg-surface-container-low rounded-lg border border-outline-variant/20 p-2.5 text-[11px]">
                          <div v-if="stagePlanTasks(sec.data, 'perception').length" class="bg-surface-container p-3 rounded border border-outline-variant/20 mb-2">
                            <div class="text-outline mb-2 text-[13px] font-semibold">感知层 Plan 任务</div>
                            <div class="flex flex-col gap-2">
                              <div v-for="(task, pi) in stagePlanTasks(sec.data, 'perception')" :key="`perception-plan-${pi}`" class="flex items-start gap-2 text-[14px] leading-relaxed text-on-surface-variant">
                                <span class="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 text-[11px] font-semibold mt-0.5">{{ pi + 1 }}</span>
                                <span>{{ task }}</span>
                              </div>
                            </div>
                          </div>
                          <div class="text-outline mb-1.5 text-[10px]">感知层计划/执行明细</div>
                          <div v-for="(tr,i) in (sec.data.tool_results||[])" :key="i" class="p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/40 mb-1 last:mb-0">
                            <div class="flex"><span class="text-outline w-12">工具:</span><span class="text-primary-fixed-dim">{{ tr.tool }}</span></div>
                            <div class="flex"><span class="text-outline w-12">路径:</span><span class="text-on-surface">{{ tr.target||'-' }}</span></div>
                            <div class="flex items-start"><span class="text-outline w-12 shrink-0">命令:</span><span class="break-all" style="font-family:'Courier New',monospace;font-size:11px;background:#3d3d3d;color:#4ade80;padding:4px 8px;border-radius:6px;display:inline-block;max-width:100%;">{{ tr.command }}</span></div>
                            <div class="flex items-start"><span class="text-outline w-12 shrink-0">输出:</span><span class="text-outline-variant whitespace-pre-wrap break-all text-[10px]">{{ displayAgentText(tr.observation) }}</span></div>
                          </div>
                        </div>
                        <!-- context -->
                        <div v-else-if="sec.key==='step4_context_bundle'" class="bg-surface-container-low rounded-lg border border-outline-variant/20 p-2.5">
                          <div class="flex gap-1.5 flex-wrap">
                            <span v-for="m in (sec.data.manual_memory||[])" :key="m.section" class="text-[10px] px-2 py-0.5 bg-secondary/10 rounded border border-secondary/20 text-secondary">{{ m.section }}</span>
                            <span v-for="r in (sec.data.raw_log_memory||[])" :key="r.description" class="text-[10px] px-2 py-0.5 bg-surface-container rounded border border-outline-variant/30 text-outline">{{ r.task }}</span>
                            <span v-for="rf in (sec.data.reflection_memory||[])" :key="rf.reflection_reason" class="text-[10px] px-2 py-0.5 bg-primary/10 rounded border border-primary/20 text-primary/70">反思:{{ rf.original_tool }}→{{ rf.revised_tool }}</span>
                          </div>
                        </div>
                        <!-- decision -->
                        <div v-else-if="sec.key==='step5_decision_draft'" class="bg-surface-container-low rounded-lg border border-outline-variant/20 p-2.5 text-[11px]">
                          <div v-if="stagePlanTasks(sec.data, 'decision').length" class="bg-surface-container p-3 rounded border border-outline-variant/20 mb-2">
                            <div class="text-outline mb-2 text-[13px] font-semibold">初步决策 Plan 任务</div>
                            <div class="flex flex-col gap-2">
                              <div v-for="(task, pi) in stagePlanTasks(sec.data, 'decision')" :key="`decision-plan-${pi}`" class="flex items-start gap-2 text-[14px] leading-relaxed text-on-surface-variant">
                                <span class="w-5 h-5 rounded-full bg-secondary/10 text-secondary flex items-center justify-center shrink-0 text-[11px] font-semibold mt-0.5">{{ pi + 1 }}</span>
                                <span>{{ task }}</span>
                              </div>
                            </div>
                          </div>
                          <div class="text-[12px] text-on-surface-variant italic mb-2">"记忆回溯：{{ sec.data.memory_flashback?.message }}"</div>
                          <div class="flex gap-1.5 flex-wrap mb-2">
                            <span v-for="m in (sec.data.reference_decision?.referenced_fields?.manual_items||[])" :key="m.section" class="text-[10px] px-2 py-0.5 bg-surface-container rounded border border-outline-variant/30 text-outline">{{ m.section }}</span>
                            <span v-for="r in (sec.data.reference_decision?.referenced_fields?.raw_log_items||[])" :key="r.task" class="text-[10px] px-2 py-0.5 bg-surface-container rounded border border-outline-variant/30 text-outline">{{ r.task||r.description }}</span>
                          </div>
                          <div v-if="sec.data.conflict_state?.conflict_detected" class="text-[10px] text-tertiary-container bg-tertiary/5 border border-tertiary/20 rounded p-1.5 mb-2">⚠ {{ sec.data.conflict_state?.conflict_reason }}</div>
                          <div class="bg-surface-container p-2 rounded border border-outline-variant/20"><div class="text-outline mb-1 text-[10px]">命令计划</div><div class="break-all" style="font-family:'Courier New',monospace;font-size:11px;background:#3d3d3d;color:#4ade80;padding:6px 10px;border-radius:6px;">{{ sec.data.command||'—' }}</div></div>
                          <div v-if="stageCommandDetails(sec.data, 'decision').length" class="mt-2 bg-surface-container p-2 rounded border border-outline-variant/20">
                            <div class="text-outline mb-1.5 text-[10px]">初步决策计划/执行明细</div>
                            <div v-for="(run,ri) in stageCommandDetails(sec.data, 'decision')" :key="`decision-${run.id || ri}-${run.tool}`" class="p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/40 mb-1 last:mb-0">
                              <div class="flex items-center justify-between gap-2"><div class="flex"><span class="text-outline w-12">工具:</span><span class="text-primary-fixed-dim">{{ run.tool || '-' }}</span></div><span class="text-[10px] px-1.5 py-0.5 rounded border" :class="commandStatusBadge(run.status)">{{ commandStatusText(run.status) }}</span></div>
                              <div class="flex"><span class="text-outline w-12">路径:</span><span class="text-on-surface break-all">{{ run.target || '-' }}</span></div>
                              <div class="flex items-start"><span class="text-outline w-12 shrink-0">命令:</span><span class="break-all" style="font-family:'Courier New',monospace;font-size:11px;background:#3d3d3d;color:#4ade80;padding:4px 8px;border-radius:6px;display:inline-block;max-width:100%;">{{ run.command || '—' }}</span></div>
                              <div v-if="run.note" class="flex items-start"><span class="text-outline w-12 shrink-0">说明:</span><span class="text-outline-variant whitespace-pre-wrap break-all text-[10px]">{{ run.note }}</span></div>
                              <div v-if="run.stdout" class="flex items-start"><span class="text-outline w-12 shrink-0">输出:</span><span class="text-outline-variant whitespace-pre-wrap break-all text-[10px]">{{ limitOutputLines(displayAgentText(run.stdout)) }}</span></div>
                              <div v-if="run.stderr" class="flex items-start"><span class="text-outline w-12 shrink-0">错误:</span><span class="text-error whitespace-pre-wrap break-all text-[10px]">{{ limitOutputLines(displayAgentText(run.stderr)) }}</span></div>
                            </div>
                          </div>
                        </div>
                        <!-- reflection -->
                        <div v-else-if="sec.key==='step6_reflection'" class="bg-surface-container-low rounded-lg border border-outline-variant/20 p-2.5">
                          <div v-if="stagePlanTasks(sec.data, 'reflection').length" class="bg-surface-container p-3 rounded border border-outline-variant/20 mb-2">
                            <div class="text-outline mb-2 text-[13px] font-semibold">反思层 Plan 任务</div>
                            <div class="flex flex-col gap-2">
                              <div v-for="(task, pi) in stagePlanTasks(sec.data, 'reflection')" :key="`reflection-plan-${pi}`" class="flex items-start gap-2 text-[14px] leading-relaxed text-on-surface-variant">
                                <span class="w-5 h-5 rounded-full bg-tertiary/10 text-tertiary flex items-center justify-center shrink-0 text-[11px] font-semibold mt-0.5">{{ pi + 1 }}</span>
                                <span>{{ task }}</span>
                              </div>
                            </div>
                          </div>
                          <div class="grid grid-cols-2 gap-1.5 mb-2">
                            <div v-for="(check,key) in (sec.data.security_scan?.checks||{})" :key="key" class="px-2 py-1.5 rounded text-[11px]" style="background:#ffffff;">
                              <div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[12px]" :class="check.passed?'text-tertiary':'text-error'">{{ check.passed?'check_circle':'cancel' }}</span><span style="color:#1544ad;font-weight:600;">{{ {reversibility:'可逆性',continuity:'业务连续',least_cost:'最小代价',injection_resistance:'注入防护'}[key]||key }}</span></div>
                              <div v-if="check.note" class="mt-1 pl-5 text-[10px] leading-relaxed text-on-surface-variant/70">{{ check.note }}</div>
                            </div>
                          </div>
                          <div class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20"><span class="text-outline">反思结果: </span><span :class="sec.data.status==='revised'?'text-primary':sec.data.status==='blocked'?'text-error':'text-tertiary'">{{ {revised:'已修订',no_change:'无需修订',blocked:'已拦截'}[sec.data.status]||sec.data.status }}</span></div>
                          <div v-if="stageCommandDetails(sec.data, 'reflection').length" class="mt-2 bg-surface-container p-2 rounded border border-outline-variant/20 text-[11px]">
                            <div class="text-outline mb-1.5 text-[10px]">反思修正计划/执行/React 调整明细</div>
                            <div v-for="(run,ri) in stageCommandDetails(sec.data, 'reflection')" :key="`reflection-${run.id || ri}-${run.tool}`" class="p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/40 mb-1 last:mb-0">
                              <div class="flex items-center justify-between gap-2"><div class="flex"><span class="text-outline w-12">工具:</span><span class="text-primary-fixed-dim">{{ run.tool || '-' }}</span></div><span class="text-[10px] px-1.5 py-0.5 rounded border" :class="commandStatusBadge(run.status)">{{ commandStatusText(run.status) }}</span></div>
                              <div class="flex"><span class="text-outline w-12">路径:</span><span class="text-on-surface break-all">{{ run.target || '-' }}</span></div>
                              <div class="flex items-start"><span class="text-outline w-12 shrink-0">命令:</span><span class="break-all" style="font-family:'Courier New',monospace;font-size:11px;background:#3d3d3d;color:#4ade80;padding:4px 8px;border-radius:6px;display:inline-block;max-width:100%;">{{ run.command || '—' }}</span></div>
                              <div v-if="run.note" class="flex items-start"><span class="text-outline w-12 shrink-0">说明:</span><span class="text-outline-variant whitespace-pre-wrap break-all text-[10px]">{{ run.note }}</span></div>
                              <div v-if="run.stdout" class="flex items-start"><span class="text-outline w-12 shrink-0">输出:</span><span class="text-outline-variant whitespace-pre-wrap break-all text-[10px]">{{ limitOutputLines(displayAgentText(run.stdout)) }}</span></div>
                              <div v-if="run.stderr" class="flex items-start"><span class="text-outline w-12 shrink-0">错误:</span><span class="text-error whitespace-pre-wrap break-all text-[10px]">{{ limitOutputLines(displayAgentText(run.stderr)) }}</span></div>
                            </div>
                          </div>
                        </div>
                        <!-- risk -->
                        <div v-else-if="sec.key==='step7_risk_audit'" class="bg-surface-container-low rounded-lg border border-outline-variant/20 p-2.5">
                          <div class="flex justify-between items-center mb-2.5"><span class="text-[11px] text-primary">安全护栏风险评估</span><span class="font-semibold text-[18px]" style="font-family:'Space Grotesk',sans-serif" :class="sec.data.total_risk>=0.7?'text-error':sec.data.total_risk>=0.4?'text-tertiary-container':'text-primary'">{{ sec.data.total_risk }}<span class="text-[10px] text-outline ml-0.5">综合风险</span></span></div>
                          <div class="grid grid-cols-2 gap-2 mb-2">
                            <div v-for="s in [{label:'操作影响',v:sec.data.action_energy,c:'#0ea5e9',name:'只读/低影响'},{label:'资产敏感度',v:sec.data.asset_sensitivity,c:'#de8712',name:'普通服务'}]" :key="s.label" class="bg-surface-container p-2 rounded border border-outline-variant/20 flex items-center gap-2">
                              <div class="relative w-10 h-10 shrink-0"><svg class="w-full h-full -rotate-90" viewBox="0 0 36 36"><path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#dee3e9" stroke-width="3.5"/><path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" :stroke="s.c" :stroke-dasharray="`${((Number.isFinite(s.v)?s.v:0)*100).toFixed(0)},100`" stroke-width="3.5" stroke-linecap="round"/></svg><span class="absolute inset-0 flex items-center justify-center text-[9px]" :style="`color:${s.c}`">{{ Number.isFinite(s.v)?s.v.toFixed(2):'--' }}</span></div>
                              <div class="flex flex-col gap-0.5"><span class="text-[10px] text-outline">{{ s.label }}</span><span class="text-[10px]" :style="`color:${s.c}`">{{ s.name }}</span></div>
                            </div>
                          </div>
                          <div v-if="sec.data.token_attributions?.length" class="text-[10px] bg-surface-container p-2 rounded border border-outline-variant/20"><span class="text-outline mr-1">关键词:</span><span v-for="t in (sec.data.token_attributions||[])" :key="t.token" class="text-[9px] px-1 border mx-0.5 rounded" :class="t.highlight?'text-error bg-error/10 border-error/20':'text-outline bg-surface-container border-outline-variant/20'">{{ t.token }}</span></div>
                        </div>
                        <!-- guardrail -->
                        <div v-else-if="sec.key==='step8_guardrail_tree'" class="bg-surface-container-low rounded-lg border border-outline-variant/20 p-2.5">
                          <div class="flex flex-col items-center text-[10px]">
                            <div class="w-full border rounded-md px-3 py-2 flex items-center justify-between" :class="sec.data.root?.status==='pass'?'border-blue-400/40 bg-blue-50/30 text-[#1544ad]':sec.data.root?.status==='warning'?'border-yellow-400/50 bg-yellow-400/10 text-yellow-300':'border-error/40 bg-error/5 text-error'">
                              <span class="flex items-center gap-2"><span class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[9px] font-semibold" :class="sec.data.root?.status==='pass'?'bg-blue-100 text-[#1544ad]':sec.data.root?.status==='warning'?'bg-yellow-400/20 text-yellow-300':'bg-error/20 text-error'">{{ sec.data.root?.status==='pass'?'✓':sec.data.root?.status==='warning'?'⚠':'✕' }}</span>安全护栏总流程</span><span class="text-[9px] opacity-50">ROOT</span>
                            </div>
                            <template v-for="(node,ni) in (sec.data.root?.children||[])" :key="node.node_id">
                              <div v-if="(sec._guardrailCount||0)>ni" class="w-full flex flex-col items-center guardrail-layer-enter">
                                <div class="flex flex-col items-center py-0.5"><div class="w-px h-3 border-l border-dashed" :class="node.status==='blocked'?'border-error/60':'border-outline-variant/40'"></div><div class="w-2 h-2 rounded-full" :class="node.status==='pass'?'bg-[#1544ad]':node.status==='blocked'?'bg-error':node.status==='warning'?'bg-yellow-300':'bg-outline-variant'"></div></div>
                                <div class="w-full border rounded-md px-3 py-2" :class="node.status==='pass'?'border-blue-400/50 bg-blue-50/20':node.status==='blocked'?'border-error/50 bg-error/5 guardrail-blocked-glow':node.status==='warning'?'border-yellow-400/50 bg-yellow-400/10':'border-outline-variant/30 bg-surface-container'">
                                  <div class="flex items-center justify-between mb-1">
                                    <div class="flex items-center gap-2"><span class="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold" :class="node.status==='pass'?'bg-blue-100 text-[#1544ad]':node.status==='blocked'?'bg-error/20 text-error':node.status==='warning'?'bg-yellow-400/20 text-yellow-300':'bg-outline-variant/20 text-outline'">{{ ['❶','❷','❸'][ni]||ni+1 }}</span><span :class="node.status==='pass'?'text-[#1544ad]':node.status==='blocked'?'text-error':node.status==='warning'?'text-yellow-300':'text-outline'">{{ node.label }}</span></div>
                                    <span class="text-[9px] px-1.5 py-0.5 rounded-full font-semibold" :class="node.status==='pass'?'text-[#1544ad] bg-blue-50':node.status==='blocked'?'text-error bg-error/15 animate-pulse':node.status==='warning'?'text-yellow-300 bg-yellow-400/15 animate-pulse':'text-outline bg-outline-variant/15'">{{ {pass:'✓ 通过',blocked:'✕ 拦截',warning:'⚠ 警告',skipped:'→ 跳过'}[node.status]||node.status }}</span>
                                  </div>
                                  <div v-if="node.reason" class="text-[10px] pl-8 leading-relaxed" :class="node.status==='blocked'?'text-error/80':'text-on-surface-variant/60'">{{ node.reason }}</div>
                                  <div v-if="node.children?.length" class="mt-2 ml-7 flex flex-col gap-1 border-l-2 border-outline-variant/20 pl-2.5"><div v-for="child in node.children" :key="child.node_id" class="flex items-center gap-1.5 text-[10px]"><span class="w-1.5 h-1.5 rounded-full" :class="child.status==='pass'?'bg-[#1544ad]':child.status==='pending'?'bg-yellow-300 animate-pulse':'bg-outline'"></span><span :class="child.status==='pass'?'text-[#1544ad]':child.status==='pending'?'text-yellow-300':'text-outline'">{{ child.label }}: {{ {pass:'通过',pending:'等待审批中',blocked:'已拦截'}[child.status]||child.status }}</span></div></div>
                                </div>
                              </div>
                            </template>
                          </div>
                        </div>
                        <!-- approval -->
                        <div v-else-if="sec.key==='step9_approval_payload'" class="bg-tertiary/10 border border-tertiary/30 rounded-lg p-2.5">
                          <div class="flex items-center gap-2 mb-1.5"><span class="material-symbols-outlined text-tertiary text-[14px] animate-pulse">pending_actions</span><span class="text-[11px] text-tertiary">等待审计人员审批</span><span class="text-[9px] ml-auto text-tertiary/60 border border-tertiary/20 px-1 rounded">风险评分 {{ sec.data.risk_score }}</span></div>
                          <div class="text-[10px] text-tertiary/70 mb-1">{{ sec.data.command_preview }}</div>
                          <div class="text-[10px] text-tertiary font-semibold mb-1">必须审计人员审批后才能执行</div>
                          <div class="text-[9px] text-tertiary/50 border-t border-tertiary/20 pt-1.5">→ 请前往「审批管理」页面操作</div>
                        </div>
                        <!-- execution -->
                        <div v-else-if="sec.key==='step10_execution_result'" class="bg-surface-container-low rounded-lg border border-outline-variant/20 p-2.5 text-[11px]">
                          <div class="flex justify-between items-center mb-1.5"><span :class="sec.data.status==='success'?'text-tertiary':'text-error'" class="font-semibold">{{ executionSummary(sec.data).label }}</span><span class="text-[10px] px-1.5 border rounded" :class="sec.data.status==='success'?'text-tertiary border-tertiary/30 bg-tertiary/10':'text-error border-error/30 bg-error/10'">退出码 {{ executionSummary(sec.data).exit_code }}</span></div>
                          <div class="bg-surface-container p-2 rounded border border-outline-variant/20 flex flex-col gap-1">
                            <div class="flex"><span class="text-outline w-14">工具:</span><span class="text-primary-fixed-dim">{{ executionSummary(sec.data).tool }}</span></div>
                            <div class="flex"><span class="text-outline w-14">命令:</span><span class="text-on-surface break-all">{{ executionSummary(sec.data).command }}</span></div>
                            <div v-if="executionSummary(sec.data).stdout" class="flex items-start"><span class="text-outline w-14 shrink-0">输出:</span><span class="text-on-surface-variant whitespace-pre-wrap break-all">{{ limitOutputLines(displayAgentText(executionSummary(sec.data).stdout)) }}</span></div>
                            <div v-if="executionSummary(sec.data).stderr" class="flex items-start"><span class="text-outline w-14 shrink-0">错误:</span><span class="text-error whitespace-pre-wrap break-all">{{ limitOutputLines(displayAgentText(executionSummary(sec.data).stderr)) }}</span></div>
                            <div v-if="sec.data.command_runs?.length" class="mt-1 pt-1 border-t border-outline-variant/20">
                              <div class="text-outline mb-1 text-[10px]">执行明细（{{ sec.data.command_runs.length }} 条）</div>
                              <div v-for="(run,ri) in sec.data.command_runs" :key="'run'+ri" class="mb-1 p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/30">
                                <div class="flex items-center justify-between"><span class="text-primary-fixed-dim">{{ run.tool }}</span><span :class="run.status==='success'?'text-tertiary':'text-error'">{{ run.status }}</span></div>
                                <div class="text-on-surface break-all">{{ run.command }}</div>
                                <div v-if="run.rollback_supported" class="text-[10px] mt-0.5" :class="run.rollback_available?'text-tertiary':'text-tertiary-container'">回滚: {{ run.rollback_available?'可回滚':'已禁用' }}</div>
                                <div v-if="run.stdout" class="text-[10px] text-on-surface-variant whitespace-pre-wrap break-all mt-0.5">{{ limitOutputLines(displayAgentText(run.stdout)) }}</div>
                                <div v-if="run.stderr" class="text-[10px] text-error whitespace-pre-wrap break-all mt-0.5">{{ limitOutputLines(displayAgentText(run.stderr)) }}</div>
                              </div>
                            </div>
                            <div v-if="sec.data.execution_attribution" class="mt-2 pt-2 border-t border-outline-variant/20">
                              <div class="text-outline mb-1.5 text-[10px]">执行阶段可视化归因</div>
                              <div v-if="sec.data.execution_attribution.chains?.length" class="bg-surface-container-high/30 rounded border border-outline-variant/20 p-2 mb-2">
                                <div class="text-[10px] text-primary mb-1.5">命令责任链</div>
                                <div class="flex flex-col gap-2">
                                  <div v-for="chain in sec.data.execution_attribution.chains" :key="chain.command_id" class="rounded border border-outline-variant/20 bg-white/70 p-2">
                                    <div class="text-[10px] text-primary-fixed-dim break-all mb-1">{{ chain.command }}</div>
                                    <div class="grid grid-cols-1 sm:grid-cols-5 gap-1 text-[10px]">
                                      <div class="rounded bg-primary/5 border border-primary/10 p-1"><div class="text-outline">Plan</div><div class="text-on-surface-variant">{{ chain.plan_task }}</div></div>
                                      <div class="rounded bg-tertiary/5 border border-tertiary/10 p-1"><div class="text-outline">反思</div><div class="text-on-surface-variant">{{ chain.reflection }}</div></div>
                                      <div class="rounded bg-secondary/5 border border-secondary/10 p-1"><div class="text-outline">审批</div><div class="text-on-surface-variant">{{ chain.approval_basis }}</div></div>
                                      <div class="rounded bg-surface-container border border-outline-variant/20 p-1"><div class="text-outline">命令</div><div class="text-on-surface-variant break-all">{{ chain.command_id }}</div></div>
                                      <div class="rounded bg-tertiary/5 border border-tertiary/10 p-1"><div class="text-outline">结果</div><div class="text-on-surface-variant">{{ chain.result }}</div></div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <div v-if="sec.data.execution_attribution.heatmap?.length" class="bg-surface-container-high/30 rounded border border-outline-variant/20 p-2">
                                <div class="text-[10px] text-primary mb-1.5">风险热力图</div>
                                <div class="grid grid-cols-[minmax(86px,1.2fr)_repeat(4,minmax(42px,1fr))] gap-1 text-[10px] items-stretch">
                                  <div class="text-outline">动作</div>
                                  <div v-for="metric in attributionMetrics" :key="metric.key" class="text-outline text-center">{{ metric.label }}</div>
                                  <template v-for="row in sec.data.execution_attribution.heatmap" :key="row.label">
                                    <div class="text-on-surface-variant rounded bg-surface-container px-1 py-1">{{ row.label }}</div>
                                    <div v-for="metric in attributionMetrics" :key="`${row.label}-${metric.key}`" class="rounded px-1 py-1 text-center border" :class="attributionHeatClass(row[metric.key])">
                                      {{ formatAttributionScore(row[metric.key]) }}
                                    </div>
                                  </template>
                                </div>
                              </div>
                            </div>
                            <div v-if="rollbackCandidates(sec.data).length" class="mt-1.5 pt-1.5 border-t border-outline-variant/20">
                              <div class="text-outline mb-1 text-[10px]">回滚选择（可多选）</div>
                              <label v-for="r in rollbackCandidates(sec.data)" :key="'rb-'+r.id" class="flex items-start gap-2 text-[10px] py-1">
                                <input
                                  type="checkbox"
                                  :checked="isRollbackSelected(sec.data, r.id)"
                                  @change="toggleRollbackSelection(sec.data, r.id, $event.target.checked)"
                                />
                                <span class="text-on-surface break-all">{{ r.command }}</span>
                              </label>
                              <button class="mt-1.5 px-3 py-1.5 rounded border border-tertiary/30 text-tertiary-container hover:bg-tertiary/10 transition-colors text-[11px]" @click="submitRollback(sec.data)">执行回滚</button>
                            </div>
                            <div v-else class="mt-1.5 pt-1.5 border-t border-outline-variant/20 text-[10px] text-outline">暂无可回滚项：{{ rollbackUnavailableReason(sec.data) }}</div>
                          </div>
                        </div>
                        <!-- execution_review -->
                        <div v-else-if="sec.key==='step13_execution_report'" class="bg-surface-container-low rounded-lg border border-outline-variant/20 p-2.5 text-[11px]">
                          <div class="flex items-center gap-2 mb-1.5"><span class="text-secondary font-semibold">结果解读</span><span class="text-[9px] ml-auto px-1.5 border rounded border-secondary/30 text-secondary bg-secondary/10">{{ sec.data.task_completion }}</span></div>
                          <div class="bg-surface-container p-2 rounded border border-outline-variant/20 flex flex-col gap-1.5">
                            <div v-if="sec.data.result_summary"><span class="text-outline">总结: </span><span class="text-on-surface">{{ sec.data.result_summary }}</span></div>
                            <div v-if="sec.data.risk_explanation"><span class="text-outline">风险说明: </span><span class="text-tertiary-container">{{ sec.data.risk_explanation }}</span></div>
                            <div v-if="sec.data.user_facing_answer" class="pt-1 border-t border-outline-variant/20"><div class="text-outline mb-1 text-[10px]">最终答复</div><div class="text-on-surface whitespace-pre-wrap break-all">{{ sec.data.user_facing_answer }}</div></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="msg.status==='running'" class="flex items-center gap-2 px-3 py-2 text-[12px] text-on-surface-variant"><span class="flex gap-1"><span class="w-1.5 h-1.5 rounded-full bg-outline-variant animate-bounce" style="animation-delay:0ms"/><span class="w-1.5 h-1.5 rounded-full bg-outline-variant animate-bounce" style="animation-delay:150ms"/><span class="w-1.5 h-1.5 rounded-full bg-outline-variant animate-bounce" style="animation-delay:300ms"/></span>智能体思考中...</div>
                <div v-else-if="msg.status==='success'" class="text-[12px] text-tertiary font-semibold px-3 py-2">✓ 任务完成</div>
                <div v-else-if="msg.status==='failed'||msg.status==='blocked'" class="text-[12px] text-error font-semibold px-3 py-2">✕ 任务终止</div>
                <div v-else-if="msg.status==='rejected'" class="text-[12px] text-error font-semibold px-3 py-2">✕ 审批已拒绝</div>
              </div>
            </div>

            <!-- 步骤卡片：环境感知 -->
            <div v-else-if="msg.type === 'card_perception'" class="bg-surface-container-high border-t-2 border-t-tertiary border border-outline-variant/30 rounded-lg p-3 shadow-md">
              <div class="flex justify-between items-center mb-2">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-tertiary text-[16px]">visibility</span>
                  <span class="text-[12px] text-on-surface-variant">步骤 03 // 环境感知</span>
                </div>
                <span class="text-[10px] text-tertiary px-1.5 border border-tertiary/30 bg-tertiary/10 rounded">{{ msg.data.tool_results?.[0]?.status || 'done' }}</span>
              </div>
              <div class="bg-surface-container p-2 rounded border border-outline-variant/20 text-[12px] flex flex-col gap-1">
                <div v-if="stagePlanTasks(msg.data, 'perception').length" class="mb-2.5">
                  <div class="text-outline mb-2 text-[13px] font-semibold">感知层 Plan 任务</div>
                  <div v-for="(task, pi) in stagePlanTasks(msg.data, 'perception')" :key="`card-perception-plan-${pi}`" class="flex items-start gap-2 text-[14px] leading-relaxed text-on-surface-variant mb-1">
                    <span class="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 text-[11px] font-semibold mt-0.5">{{ pi + 1 }}</span>
                    <span>{{ task }}</span>
                  </div>
                </div>
                <div class="text-outline mb-1">感知层计划/执行明细</div>
                <div v-for="(tr, i) in (msg.data.tool_results || [])" :key="`${tr.tool}-${i}`" class="p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/40">
                  <div class="flex"><span class="text-outline w-14">工具:</span><span class="text-primary-fixed-dim">{{ tr.tool }}</span></div>
                  <div class="flex"><span class="text-outline w-14">路径:</span><span class="text-on-surface">{{ tr.target || '-' }}</span></div>
                  <div class="flex items-start"><span class="text-outline w-14 shrink-0">命令:</span><span class="text-on-surface break-all">{{ tr.command }}</span></div>
                  <div class="flex items-start"><span class="text-outline w-14 shrink-0">输出:</span><span class="text-outline-variant whitespace-pre-wrap break-all text-[11px]">{{ displayAgentText(tr.observation) }}</span></div>
                </div>
              </div>
              <div v-if="msg.data.summary" class="mt-2 text-[11px] text-on-surface-variant/70 italic">{{ msg.data.summary }}</div>
            </div>

            <!-- 步骤卡片：上下文构建 -->
            <div v-else-if="msg.type === 'card_context'" class="bg-surface-container-high border-t-2 border-t-secondary border border-outline-variant/30 rounded-lg p-3 shadow-md">
              <div class="flex items-center gap-2 mb-2">
                <span class="material-symbols-outlined text-secondary text-[16px]">library_books</span>
                <span class="text-[12px] text-on-surface-variant">步骤 04 // 上下文构建</span>
              </div>
              <div class="flex gap-1.5 flex-wrap">
                <span v-for="m in (msg.data.manual_memory || [])" :key="m.section"
                      class="text-[10px] px-2 py-0.5 bg-secondary/10 rounded border border-secondary/20 text-secondary">{{ m.section }}</span>
                <span v-for="r in (msg.data.raw_log_memory || [])" :key="r.description"
                      class="text-[10px] px-2 py-0.5 bg-surface-container rounded border border-outline-variant/30 text-outline">{{ r.task }}</span>
                <span v-for="rf in (msg.data.reflection_memory || [])" :key="rf.reflection_reason"
                      class="text-[10px] px-2 py-0.5 bg-primary/10 rounded border border-primary/20 text-primary/70">反思: {{ rf.original_tool }}→{{ rf.revised_tool }}</span>
              </div>
              <div v-if="msg.data.allowed_tools?.length" class="mt-2 text-[10px] text-on-surface-variant/50">
                允许工具: {{ msg.data.allowed_tools.join(', ') }}
              </div>
            </div>

            <!-- 步骤卡片：初步决策 -->
            <div v-else-if="msg.type === 'card_decision'" class="bg-surface-container-high border-t-2 border-t-secondary border border-outline-variant/30 rounded-lg p-3 shadow-md">
              <div class="flex items-center gap-2 mb-2">
                <span class="material-symbols-outlined text-secondary text-[16px]">psychology</span>
                <span class="text-[12px] text-on-surface-variant">步骤 05 // 初步决策</span>
              </div>
              <div class="flex gap-2">
                <div class="w-0.5 bg-outline-variant/30 rounded-full shrink-0"></div>
                <div class="flex-1 flex flex-col gap-2">
                  <div v-if="stagePlanTasks(msg.data, 'decision').length" class="bg-surface-container p-3 rounded border border-outline-variant/20">
                    <div class="text-outline mb-2 text-[13px] font-semibold">初步决策 Plan 任务</div>
                    <div v-for="(task, pi) in stagePlanTasks(msg.data, 'decision')" :key="`card-decision-plan-${pi}`" class="flex items-start gap-2 text-[14px] leading-relaxed text-on-surface-variant mb-1">
                      <span class="w-5 h-5 rounded-full bg-secondary/10 text-secondary flex items-center justify-center shrink-0 text-[11px] font-semibold mt-0.5">{{ pi + 1 }}</span>
                      <span>{{ task }}</span>
                    </div>
                  </div>
                  <div class="text-[13px] text-on-surface-variant italic">"记忆回溯：{{ msg.data.memory_flashback?.message }}"</div>
                  <div class="flex gap-1.5 flex-wrap">
                    <span v-for="m in (msg.data.reference_decision?.referenced_fields?.manual_items || [])" :key="m.section"
                          class="text-[10px] px-2 py-0.5 bg-surface-container rounded border border-outline-variant/30 text-outline">{{ m.section }}</span>
                    <span v-for="r in (msg.data.reference_decision?.referenced_fields?.raw_log_items || [])" :key="r.task"
                          class="text-[10px] px-2 py-0.5 bg-surface-container rounded border border-outline-variant/30 text-outline">{{ r.task || r.description }}</span>
                  </div>
                  <div v-if="msg.data.conflict_state?.conflict_detected"
                       class="text-[11px] text-tertiary-container bg-tertiary/5 border border-tertiary/20 rounded p-1.5">
                    ⚠ {{ msg.data.conflict_state?.conflict_reason }}
                  </div>
                  <div class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20">
                    <div class="text-outline mb-1">命令计划（Step5）</div>
                    <div v-if="msg.data.execution_plan?.commands?.length" class="flex flex-col gap-1">
                      <div v-for="(c, ci) in msg.data.execution_plan.commands" :key="`${c.id || ci}-${c.tool}`" class="p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/30">
                        <div class="flex items-center gap-2 mb-0.5">
                          <span class="text-primary-fixed-dim">{{ c.tool }}</span>
                          <span v-if="c.auto_generated" class="text-[10px] px-1 rounded border border-tertiary/30 text-tertiary-container">AUTO</span>
                        </div>
                        <div class="text-on-surface break-all">{{ c.command }}</div>
                      </div>
                    </div>
                    <div v-else>
                      <span class="text-outline">命令: </span><span class="text-primary-fixed-dim">{{ msg.data.command }}</span>
                    </div>
                  </div>
                  <div v-if="stageCommandDetails(msg.data, 'decision').length" class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20">
                    <div class="text-outline mb-1">初步决策计划/执行明细</div>
                    <div v-for="(run, ri) in stageCommandDetails(msg.data, 'decision')" :key="`decision-card-${run.id || ri}-${run.tool}`" class="mb-1 p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/30">
                      <div class="flex items-center justify-between gap-2"><span class="text-primary-fixed-dim">{{ run.tool || '-' }}</span><span class="text-[10px] px-1.5 py-0.5 rounded border" :class="commandStatusBadge(run.status)">{{ commandStatusText(run.status) }}</span></div>
                      <div class="text-[10px] text-outline mt-0.5">路径: {{ run.target || '-' }}</div>
                      <div class="text-on-surface break-all">{{ run.command || '—' }}</div>
                      <div v-if="run.note" class="text-[10px] text-outline mt-0.5 break-all">{{ run.note }}</div>
                      <div v-if="run.stdout" class="text-[10px] text-on-surface-variant whitespace-pre-wrap break-all mt-0.5">{{ limitOutputLines(displayAgentText(run.stdout)) }}</div>
                      <div v-if="run.stderr" class="text-[10px] text-error whitespace-pre-wrap break-all mt-0.5">{{ limitOutputLines(displayAgentText(run.stderr)) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 步骤卡片：反思修正 -->
            <div v-else-if="msg.type === 'card_reflection'" class="bg-surface-container-high border-t-2 border-t-primary border border-outline-variant/30 rounded-lg p-3 shadow-md"
                 :class="msg.data.status === 'blocked' ? 'border-t-error' : ''">
              <div class="flex items-center gap-2 mb-2">
                <span class="material-symbols-outlined text-[16px]" :class="msg.data.status === 'blocked' ? 'text-error' : 'text-primary'">verified_user</span>
                <span class="text-[12px] text-on-surface-variant">步骤 06 // 反思修正</span>
              </div>
              <div class="grid grid-cols-2 gap-1.5 mb-2">
                <div v-for="(check, key) in (msg.data.security_scan?.checks || {})" :key="key"
                     class="px-2 py-1.5 rounded border font-mono"
                     :class="check.passed ? 'bg-tertiary/5 border-tertiary/20 text-tertiary' : 'bg-error/5 border-error/20 text-error'">
                  <div class="flex items-center gap-1.5 text-[11px]">
                    <span class="material-symbols-outlined text-[12px]">{{ check.passed ? 'check_circle' : 'cancel' }}</span>
                    {{ { reversibility: '可逆性', continuity: '业务连续', least_cost: '最小代价', injection_resistance: '注入防护' }[key] || key }}
                  </div>
                  <div v-if="check.note" class="mt-1 pl-5 text-[10px] leading-relaxed text-on-surface-variant/70">
                    {{ check.note }}
                  </div>
                </div>
              </div>
              <div v-if="stagePlanTasks(msg.data, 'reflection').length" class="bg-surface-container p-3 rounded border border-outline-variant/20 mb-2">
                <div class="text-outline mb-2 text-[13px] font-semibold">反思层 Plan 任务</div>
                <div v-for="(task, pi) in stagePlanTasks(msg.data, 'reflection')" :key="`card-reflection-plan-${pi}`" class="flex items-start gap-2 text-[14px] leading-relaxed text-on-surface-variant mb-1">
                  <span class="w-5 h-5 rounded-full bg-tertiary/10 text-tertiary flex items-center justify-center shrink-0 text-[11px] font-semibold mt-0.5">{{ pi + 1 }}</span>
                  <span>{{ task }}</span>
                </div>
              </div>
              <div class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20">
                <span class="text-outline">反思结果: </span>
                <span :class="msg.data.status === 'revised' ? 'text-primary' : msg.data.status === 'blocked' ? 'text-error' : 'text-tertiary'">
                  {{ { revised: '已修订', no_change: '无需修订', blocked: '已拦截' }[msg.data.status] || msg.data.status }}
                </span>
                <span v-if="msg.data.revised_command" class="text-primary-fixed-dim ml-2">{{ msg.data.revised_command }}</span>
              </div>
              <div class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20 mt-2">
                <div class="text-outline mb-1">反思命令计划（Step6）</div>
                <div v-if="msg.data.plan_execute?.commands?.length" class="flex flex-col gap-1">
                  <div v-for="(c, ci) in msg.data.plan_execute.commands" :key="`${c.id || ci}-${c.tool}`" class="p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/30">
                    <div class="flex items-center gap-2 mb-0.5">
                      <span class="text-primary-fixed-dim">{{ c.tool }}</span>
                      <span v-if="c.auto_generated" class="text-[10px] px-1 rounded border border-yellow-500/30 text-yellow-300">AUTO</span>
                    </div>
                    <div class="text-on-surface break-all">{{ c.command }}</div>
                  </div>
                </div>
                <div v-else class="text-outline-variant">（未返回计划命令，显示为单命令模式）</div>
              </div>
              <div v-if="stageCommandDetails(msg.data, 'reflection').length" class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20 mt-2">
                <div class="text-outline mb-1">反思修正计划/执行/React 调整明细</div>
                <div v-for="(run, ri) in stageCommandDetails(msg.data, 'reflection')" :key="`reflection-card-${run.id || ri}-${run.tool}`" class="mb-1 p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/30">
                  <div class="flex items-center justify-between gap-2"><span class="text-primary-fixed-dim">{{ run.tool || '-' }}</span><span class="text-[10px] px-1.5 py-0.5 rounded border" :class="commandStatusBadge(run.status)">{{ commandStatusText(run.status) }}</span></div>
                  <div class="text-[10px] text-outline mt-0.5">路径: {{ run.target || '-' }}</div>
                  <div class="text-on-surface break-all">{{ run.command || '—' }}</div>
                  <div v-if="run.note" class="text-[10px] text-outline mt-0.5 break-all">{{ run.note }}</div>
                  <div v-if="run.stdout" class="text-[10px] text-on-surface-variant whitespace-pre-wrap break-all mt-0.5">{{ limitOutputLines(displayAgentText(run.stdout)) }}</div>
                  <div v-if="run.stderr" class="text-[10px] text-error whitespace-pre-wrap break-all mt-0.5">{{ limitOutputLines(displayAgentText(run.stderr)) }}</div>
                </div>
              </div>
            </div>

            <!-- 步骤卡片：安全护栏风险评估 -->
            <div v-else-if="msg.type === 'card_risk'" class="bg-surface-container-high border-t-2 border-t-primary border border-outline-variant/30 rounded-lg p-3 shadow-md" style="box-shadow: 0 0 12px rgba(14,165,233,0.15)">
              <div class="flex justify-between items-center mb-3">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-primary text-[16px]">security</span>
                  <span class="text-[12px] text-primary">步骤 07 // 安全护栏风险评估</span>
                </div>
                <span class="font-semibold text-[20px]" style="font-family:'Space Grotesk',sans-serif"
                      :class="msg.data.total_risk >= 0.7 ? 'text-error' : msg.data.total_risk >= 0.4 ? 'text-tertiary-container' : 'text-primary'">
                  {{ msg.data.total_risk }}<span class="text-[11px] text-outline ml-1">综合风险</span>
                </span>
              </div>
              <div class="grid grid-cols-2 gap-2 mb-2">
                <div v-for="s in [
                  { label: '操作影响',   value: msg.data.action_energy,     color: '#0ea5e9', name: '只读/低影响' },
                  { label: '资产敏感度', value: msg.data.asset_sensitivity,  color: '#de8712', name: '普通服务' }
                ]" :key="s.label" class="bg-surface-container p-2 rounded border border-outline-variant/20 flex items-center gap-2">
                  <div class="relative w-10 h-10 shrink-0">
                    <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none" stroke="#dee3e9" stroke-width="3.5"/>
                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none" :stroke="s.color" :stroke-dasharray="`${((Number.isFinite(s.value) ? s.value : 0) * 100).toFixed(0)}, 100`" stroke-width="3.5" stroke-linecap="round"/>
                    </svg>
                    <div class="absolute inset-0 flex items-center justify-center text-[9px]" :style="`color: ${s.color}`">{{ Number.isFinite(s.value) ? s.value.toFixed(2) : '--' }}</div>
                  </div>
                  <div class="flex flex-col gap-0.5">
                    <span class="text-[10px] text-outline">{{ s.label }}</span>
                    <span class="text-[11px]" :style="`color: ${s.color}`">{{ s.name }}</span>
                  </div>
                </div>
              </div>
              <div v-if="msg.data.error" class="text-[10px] text-error/70 mb-2">
                审计引擎异常：{{ msg.data.error }}
              </div>
              <div v-if="msg.data.highest_risk_command" class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20 mb-2">
                <div class="text-outline mb-1">最高风险动作</div>
                <div class="text-tertiary-container break-all">{{ msg.data.highest_risk_command.command }}</div>
                <div class="text-[10px] text-outline mt-1">
                  工具 {{ msg.data.highest_risk_command.tool }} · 风险 {{ Number(msg.data.highest_risk_command.risk_level ?? 0).toFixed(2) }}
                </div>
              </div>
              <div class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20">
                <span class="text-outline mr-1">关键词:</span>
                <span v-for="t in (msg.data.token_attributions || [])" :key="t.token"
                      class="text-[10px] px-1 border mx-0.5 rounded"
                      :class="t.highlight ? 'text-error bg-error/10 border-error/20' : 'text-outline bg-surface-container border-outline-variant/20'">{{ t.token }}</span>
              </div>
            </div>

            <!-- 步骤卡片：护栏判定（流程图） -->
            <div v-else-if="msg.type === 'card_guardrail'" class="bg-surface-container-high border-t-2 rounded-lg p-3 shadow-md"
                 :class="msg.data.root?.status === 'pass' ? 'border-t-tertiary border border-outline-variant/30' : msg.data.root?.status === 'warning' ? 'border-t-yellow-400 border border-yellow-400/30' : 'border-t-error border border-error/30'"
                 :style="msg.data.root?.status !== 'pass' ? 'box-shadow: 0 0 12px rgba(250,204,21,0.12)' : ''">
              <div class="flex justify-between items-center mb-3">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-[16px]"
                        :class="msg.data.root?.status === 'pass' ? 'text-tertiary' : msg.data.root?.status === 'warning' ? 'text-yellow-300' : 'text-error'">policy</span>
                  <span class="text-[12px]"
                        :class="msg.data.root?.status === 'pass' ? 'text-on-surface-variant' : msg.data.root?.status === 'warning' ? 'text-yellow-300' : 'text-error'">步骤 08 // 护栏判定</span>
                </div>
                <span class="text-[10px] px-1.5 border rounded"
                      :class="msg.data.root?.status === 'pass' ? 'text-tertiary border-tertiary/30 bg-tertiary/10' : msg.data.root?.status === 'warning' ? 'text-yellow-300 border-yellow-400/30 bg-yellow-400/10 animate-pulse' : 'text-error border-error/30 bg-error/10 animate-pulse'">
                  {{ msg.data.root?.status === 'pass' ? '全部通过' : msg.data.root?.status === 'warning' ? '待审批' : '已拦截' }}
                </span>
              </div>
              <!-- Flowchart -->
              <div class="flex flex-col items-center text-[11px]">
                <!-- Root node -->
                <div class="w-full border rounded-md px-3 py-2 flex items-center justify-between"
                     :class="msg.data.root?.status === 'pass' ? 'border-tertiary/40 bg-tertiary/5 text-tertiary' : msg.data.root?.status === 'warning' ? 'border-yellow-400/40 bg-yellow-400/10 text-yellow-300' : 'border-error/40 bg-error/5 text-error'">
                  <div class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-[14px]">account_tree</span>
                    <span>安全护栏总流程</span>
                  </div>
                  <span class="text-[10px] opacity-60">ROOT</span>
                </div>
                <!-- Layers with progressive reveal -->
                <template v-for="(node, ni) in (msg.data.root?.children || [])" :key="node.node_id">
                  <Transition name="guardrail-node">
                    <div v-if="(guardrailRevealed[idx] ?? 0) > ni" class="w-full flex flex-col items-center">
                      <!-- Arrow connector -->
                      <div class="flex flex-col items-center py-0.5">
                        <div class="w-px h-3 border-l border-dashed border-outline-variant/40"></div>
                        <span class="text-outline-variant/50 text-[8px] leading-none">▼</span>
                      </div>
                      <!-- Layer box -->
                      <div class="w-full border rounded-md px-3 py-2"
                           :class="node.status === 'pass' ? 'border-tertiary/40 bg-tertiary/5' : node.status === 'blocked' ? 'border-error/40 bg-error/5' : node.status === 'warning' ? 'border-yellow-400/40 bg-yellow-400/10' : 'border-outline-variant/30 bg-surface-container'">
                        <div class="flex items-center justify-between mb-1">
                          <div class="flex items-center gap-2">
                            <span class="material-symbols-outlined text-[14px]"
                                  :class="node.status === 'pass' ? 'text-tertiary' : node.status === 'blocked' ? 'text-error' : node.status === 'warning' ? 'text-yellow-300' : 'text-outline'">
                              {{ node.status === 'pass' ? 'check_circle' : node.status === 'blocked' ? 'block' : node.status === 'warning' ? 'warning' : 'radio_button_unchecked' }}
                            </span>
                            <span :class="node.status === 'pass' ? 'text-tertiary' : node.status === 'blocked' ? 'text-error' : node.status === 'warning' ? 'text-yellow-300' : 'text-outline'">
                              {{ node.label }}
                            </span>
                          </div>
                          <span class="text-[10px] px-1 border rounded"
                                :class="node.status === 'pass' ? 'text-tertiary border-tertiary/30' : node.status === 'blocked' ? 'text-error border-error/30' : node.status === 'warning' ? 'text-yellow-300 border-yellow-400/30' : 'text-outline border-outline-variant/30'">
                            {{ { pass: '通过', blocked: '拦截', warning: '警告', skipped: '跳过' }[node.status] || node.status }}
                          </span>
                        </div>
                        <div v-if="node.reason" class="text-[10px] text-on-surface-variant/50 pl-6 leading-relaxed">{{ node.reason }}</div>
                        <!-- Sub-children (semantic layer approval items) -->
                        <div v-if="node.children?.length" class="mt-2 ml-5 flex flex-col gap-1 border-l border-outline-variant/20 pl-2">
                          <div v-for="child in node.children" :key="child.node_id" class="flex items-center gap-1.5 text-[10px]">
                            <span class="material-symbols-outlined text-[11px]"
                                  :class="child.status === 'pass' ? 'text-tertiary' : child.status === 'pending' ? 'text-yellow-300 animate-pulse' : 'text-outline'">
                              {{ child.status === 'pass' ? 'check_circle' : child.status === 'pending' ? 'hourglass_top' : 'radio_button_unchecked' }}
                            </span>
                            <span :class="child.status === 'pass' ? 'text-tertiary' : child.status === 'pending' ? 'text-yellow-300' : 'text-outline'">
                              {{ child.label }}: {{ { pass: '通过', pending: '等待审批中', blocked: '已拦截' }[child.status] || child.status }}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Transition>
                </template>
              </div>
            </div>

            <!-- 步骤卡片：等待审批 -->
            <div v-else-if="msg.type === 'card_approval'" class="bg-tertiary/10 border border-tertiary/30 rounded-lg p-3">
              <div class="flex items-center gap-2 mb-2">
                <span class="material-symbols-outlined text-tertiary text-[16px] animate-pulse">pending_actions</span>
                <span class="text-[12px] text-tertiary">等待审计人员审批</span>
                <span class="text-[10px] ml-auto text-tertiary/60 border border-tertiary/20 px-1 rounded">风险评分 {{ msg.data.risk_score }}</span>
              </div>
              <div class="text-[11px] text-tertiary/70 mb-1">{{ msg.data.command_preview }}</div>
              <div class="flex flex-col gap-1 mb-2">
                <div v-for="reason in msg.data.trigger_reasons" :key="reason"
                     class="text-[11px] text-tertiary/60 flex items-start gap-1">
                  <span class="shrink-0">·</span>{{ reason }}
                </div>
              </div>
              <div class="text-[10px] text-tertiary/50 border-t border-tertiary/20 pt-2">→ 请前往「审批管理」页面操作</div>
            </div>

            <!-- 步骤卡片：执行结果 -->
            <div v-else-if="msg.type === 'card_execution'" class="bg-surface-container-high border-t-2 rounded-lg p-3 shadow-md"
                 :class="msg.data.status === 'success' ? 'border-t-tertiary border border-outline-variant/30' : 'border-t-error border border-error/30'">
              <div class="flex justify-between items-center mb-2">
                <div class="flex items-center gap-2">
                  <span class="material-symbols-outlined text-[16px]"
                        :class="msg.data.status === 'success' ? 'text-tertiary' : 'text-error'">
                    {{ msg.data.status === 'success' ? 'check_circle' : 'error' }}
                  </span>
                  <span class="text-[12px] text-on-surface-variant">{{ executionSummary(msg.data).label }}</span>
                </div>
                <span class="text-[10px] px-1.5 border rounded"
                      :class="msg.data.status === 'success' ? 'text-tertiary border-tertiary/30 bg-tertiary/10' : 'text-error border-error/30 bg-error/10'">
                  退出码 {{ executionSummary(msg.data).exit_code }}
                </span>
              </div>
              <div class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20 flex flex-col gap-1">
                <div class="flex"><span class="text-outline w-16">工具:</span><span class="text-primary-fixed-dim">{{ executionSummary(msg.data).tool }}</span></div>
                <div class="flex"><span class="text-outline w-16">命令:</span><span class="text-on-surface break-all">{{ executionSummary(msg.data).command }}</span></div>
                <div v-if="executionSummary(msg.data).stdout" class="flex items-start"><span class="text-outline w-16 shrink-0">输出:</span><span class="text-on-surface-variant whitespace-pre-wrap break-all">{{ limitOutputLines(displayAgentText(executionSummary(msg.data).stdout)) }}</span></div>
                <div v-if="executionSummary(msg.data).stderr" class="flex items-start"><span class="text-outline w-16 shrink-0">错误:</span><span class="text-error whitespace-pre-wrap break-all">{{ limitOutputLines(displayAgentText(executionSummary(msg.data).stderr)) }}</span></div>
                <div v-if="msg.data.command_runs?.length" class="mt-1 pt-1 border-t border-outline-variant/20">
                  <div class="text-outline mb-1">执行明细（{{ msg.data.command_runs.length }} 条）</div>
                  <div v-for="(run, ri) in msg.data.command_runs" :key="`${run.id || ri}-${run.tool}`" class="mb-1 p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/30">
                    <div class="flex items-center justify-between">
                      <span class="text-primary-fixed-dim">{{ run.tool }}</span>
                      <span :class="run.status === 'success' ? 'text-success' : 'text-error'">{{ run.status }}</span>
                    </div>
                    <div class="text-on-surface break-all">{{ run.command }}</div>
                    <div v-if="run.rollback_supported" class="text-[11px] mt-1" :class="run.rollback_available ? 'text-success' : 'text-tertiary-container'">
                      回滚: {{ run.rollback_available ? '可回滚' : '已禁用（仅成功命令可回滚）' }}
                    </div>
                    <div v-if="run.rollback_reason" class="text-[11px] text-outline mt-1 break-all">{{ run.rollback_reason }}</div>
                    <div v-if="run.rollback_command" class="text-[11px] text-on-surface-variant mt-1 break-all">rollback_cmd: {{ run.rollback_command }}</div>
                    <div v-if="run.stdout" class="text-[11px] text-on-surface-variant whitespace-pre-wrap break-all mt-1">{{ limitOutputLines(displayAgentText(run.stdout)) }}</div>
                    <div v-if="run.stderr" class="text-[11px] text-error whitespace-pre-wrap break-all mt-1">{{ limitOutputLines(displayAgentText(run.stderr)) }}</div>
                  </div>
                </div>
                <div v-if="rollbackCandidates(msg.data).length" class="mt-2 pt-2 border-t border-outline-variant/20">
                  <div class="text-outline mb-1">回滚选择（可多选）</div>
                  <label
                    v-for="r in rollbackCandidates(msg.data)"
                    :key="`rb-${msg.data.request_id}-${r.id}`"
                    class="flex items-start gap-2 text-[11px] py-1"
                  >
                    <input
                      type="checkbox"
                      :checked="isRollbackSelected(msg.data, r.id)"
                      @change="toggleRollbackSelection(msg.data, r.id, $event.target.checked)"
                    />
                    <span class="text-on-surface break-all">{{ r.command }}</span>
                  </label>
                  <button
                    class="mt-2 px-3 py-1.5 rounded border border-tertiary/30 text-tertiary-container hover:bg-tertiary/10 transition-colors"
                    @click="submitRollback(msg.data)"
                  >执行回滚</button>
                </div>
                <div v-else class="mt-2 pt-2 border-t border-outline-variant/20 text-[11px] text-outline">
                  暂无可回滚项：{{ rollbackUnavailableReason(msg.data) }}
                </div>
              </div>
            </div>

            <!-- 步骤卡片：执行结果解读 -->
            <div v-else-if="msg.type === 'card_execution_review'" class="bg-surface-container-high border-t-2 border-t-secondary border border-outline-variant/30 rounded-lg p-3 shadow-md">
              <div class="flex items-center gap-2 mb-2">
                <span class="material-symbols-outlined text-secondary text-[16px]">fact_check</span>
                <span class="text-[12px] text-on-surface-variant">结果解读</span>
                <span class="text-[10px] ml-auto px-1.5 border rounded border-secondary/30 text-secondary bg-secondary/10">{{ msg.data.task_completion }}</span>
              </div>
              <div class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20 flex flex-col gap-2">
                <div v-if="msg.data.result_summary"><span class="text-outline">总结: </span><span class="text-on-surface">{{ msg.data.result_summary }}</span></div>
                <div v-if="msg.data.risk_explanation"><span class="text-outline">风险说明: </span><span class="text-tertiary-container">{{ msg.data.risk_explanation }}</span></div>
                <div v-if="msg.data.user_facing_answer" class="pt-1 border-t border-outline-variant/20">
                  <div class="text-outline mb-1">最终答复</div>
                  <div class="text-on-surface whitespace-pre-wrap break-all">{{ msg.data.user_facing_answer }}</div>
                </div>
              </div>
            </div>

            <!-- 步骤卡片：回滚结果 -->
            <div v-else-if="msg.type === 'card_rollback_result'" class="bg-surface-container-high border-t-2 rounded-lg p-3 shadow-md"
                 :class="msg.data.status === 'success' ? 'border-t-tertiary border border-outline-variant/30' : 'border-t-error border border-error/30'">
              <div class="flex items-center gap-2 mb-2">
                <span class="material-symbols-outlined text-[16px]" :class="msg.data.status === 'success' ? 'text-tertiary' : 'text-error'">restart_alt</span>
                <span class="text-[12px] text-on-surface-variant">回滚结果</span>
                <span class="text-[10px] ml-auto px-1.5 border rounded"
                      :class="msg.data.status === 'success' ? 'text-tertiary border-tertiary/30 bg-tertiary/10' : 'text-error border-error/30 bg-error/10'">
                  {{ msg.data.status }}
                </span>
              </div>
              <div class="text-[11px] bg-surface-container p-2 rounded border border-outline-variant/20">
                <div class="text-outline mb-1">回滚明细（{{ msg.data.runs?.length || 0 }} 条）</div>
                <div v-for="(r, ri) in (msg.data.runs || [])" :key="`${r.id || ri}-${r.tool}`" class="mb-1 p-1.5 rounded border border-outline-variant/20 bg-surface-container-high/30">
                  <div class="flex items-center justify-between">
                    <span class="text-primary-fixed-dim">{{ r.tool }}</span>
                    <span :class="r.status === 'success' ? 'text-tertiary' : 'text-error'">{{ r.status }}</span>
                  </div>
                  <div class="text-on-surface break-all">原命令: {{ r.original_command }}</div>
                  <div class="text-on-surface-variant break-all mt-1">回滚命令: {{ r.rollback_command || '-' }}</div>
                  <div v-if="r.stdout" class="text-[11px] text-on-surface-variant whitespace-pre-wrap break-all mt-1">{{ limitOutputLines(displayAgentText(r.stdout)) }}</div>
                  <div v-if="r.stderr" class="text-[11px] text-error whitespace-pre-wrap break-all mt-1">{{ limitOutputLines(displayAgentText(r.stderr)) }}</div>
                </div>
              </div>
            </div>

          </div>

          <!-- 思考中指示器 -->
          <div v-if="agentThinkingVisible" class="flex gap-3">
            <div class="w-8 h-8 rounded-full bg-tertiary/20 border border-tertiary/30 flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-tertiary text-[14px] animate-spin">autorenew</span>
            </div>
            <div class="bg-surface-container rounded-xl rounded-tl-sm px-3 py-2 border border-outline-variant/20 text-[13px] text-on-surface-variant flex items-center gap-2">
              <span>{{ agentStatus === 'awaiting_approval' ? '等待审计人员审批...' : '思考中...' }}</span>
            </div>
          </div>

          <!-- 完成状态提示 -->
          <div v-if="agentStatus === 'success'" class="flex justify-center">
            <span class="text-[11px] text-tertiary bg-tertiary/10 border border-tertiary/20 px-3 py-1 rounded-full">任务完成</span>
          </div>
          <div v-if="agentStatus === 'failed' || agentStatus === 'blocked'" class="flex justify-center">
            <span class="text-[11px] text-error bg-error/10 border border-error/20 px-3 py-1 rounded-full">任务终止</span>
          </div>
          <div v-if="agentStatus === 'rejected'" class="flex justify-center">
            <span class="text-[11px] text-error bg-error/10 border border-error/20 px-3 py-1 rounded-full">审批已拒绝</span>
          </div>

        </div>

        <!-- 输入区 -->
        <div class="p-4 border-t border-outline-variant/30">
          <div class="flex gap-2">
            <input
              v-model="agentInput"
              type="text"
              placeholder="输入运维指令..."
              class="flex-1 bg-surface-container border border-outline-variant rounded-xl py-2 px-3 text-[13px] text-on-surface focus:border-primary focus:outline-none transition-colors disabled:opacity-40"
              :disabled="agentPolling"
              @keydown.enter="sendAgent"
            />
            <button
              class="px-4 py-2 bg-primary text-on-primary rounded-xl text-[13px] font-medium hover:bg-primary-fixed transition-colors disabled:opacity-40"
              :disabled="agentPolling || !agentInput.trim()"
              @click="sendAgent"
            >发送</button>
          </div>
        </div>
      </div>
    </el-drawer>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import { getSnapshot, getResourceReport } from '@/api/monitor.js'
import { runTask, pollTask, rollbackTask } from '@/api/agent.js'
import { getOverview } from '@/api/aiops.js'
import { buildOverviewChart } from '@/utils/overviewChart.js'
import { executionSummary } from '@/utils/executionSummary.js'
import FlowingChartLine from '@/components/FlowingChartLine.vue'
import { getApiBaseUrl } from '@/api/request.js'

const activeTab   = ref('overview')
const route       = useRoute()
const agentDrawer = ref(false)
const reportDialog = ref(false)
const agentInput  = ref('')
const snapshotLoading = ref(true)
const reportLoading = ref(false)
const reportError = ref('')
const reportData = ref(null)
const reportBaseDir = ref('')
const reportDirectory = ref('/var/log')

// ── Agent 状态 ────────────────────────────────────────────
const agentMessages    = ref([])          // 消息数组
const agentStatus      = ref(null)        // running / success / failed / awaiting_approval / ...
const agentTaskId      = ref(null)
const agentPolling     = ref(false)
const agentContextData  = ref({})          // 最新的 context_data，用于进度条
const rollbackSelectedByTask = ref({})
const messagesContainer = ref(null)        // 滚动容器 ref
const progressBarRef    = ref(null)        // 进度条容器，用于自动滚入当前步骤
const guardrailRevealed = ref({})          // msgIdx → 已展示的护栏节点数

let _pollTimer       = null
let _prevHistoryLen  = 0
let _prevContextKeys = new Set()
let _seenHistoryTexts = new Set()

const AGENT_LAST_TASK_KEY = 'kylin:lastAgentTaskId'
const AGENT_TERMINAL_STATUSES = ['success', 'failed', 'blocked', 'rejected']

const agentThinkingVisible = computed(() =>
  agentDrawer.value
  && !!agentStatus.value
  && !AGENT_TERMINAL_STATUSES.includes(agentStatus.value)
)

function persistLastTaskId(taskId) {
  if (!taskId) return
  try { localStorage.setItem(AGENT_LAST_TASK_KEY, String(taskId)) } catch {}
}

function readLastTaskId() {
  try { return localStorage.getItem(AGENT_LAST_TASK_KEY) || null } catch { return null }
}

function clearLastTaskId() {
  try { localStorage.removeItem(AGENT_LAST_TASK_KEY) } catch {}
}

// 步骤定义（用于进度条）
const STEP_DEFS = [
  { key: 'step3_perception',     label: '[环境感知]',  icon: 'visibility'    },
  { key: 'step4_context_bundle', label: '[上下文构建]', icon: 'library_books' },
  { key: 'step5_decision_draft', label: '[初步决策]',  icon: 'psychology'    },
  { key: 'step6_reflection',     label: '[反思修正]',  icon: 'verified_user' },
  { key: 'step7_risk_audit',     label: '[风险评估]',  icon: 'radar'         },
  { key: 'step8_guardrail_tree', label: '[护栏判定]',  icon: 'gavel'         },
]

const agentStepProgress = computed(() => {
  const cd = agentContextData.value
  const isBlocked = agentStatus.value === 'blocked'
  return STEP_DEFS.map((s, i) => {
    const done   = !!cd[s.key]
    const prevDone = i === 0 || !!cd[STEP_DEFS[i - 1]?.key]
    const active = !done && agentPolling.value && prevDone
    const blocked = !done && isBlocked && prevDone
    return { ...s, done, active, blocked }
  })
})

// 气泡颜色映射
function getBubbleClass(text) {
  if (/^\[(安全拦截|审批拒绝)\]/.test(text))    return 'bg-error/10 border border-error/30 text-error'
  if (/^\[(流程挂起|系统通知)\]/.test(text))    return 'bg-tertiary/10 border border-tertiary/30 text-tertiary'
  if (/^\[(流程复活|审批通过)\]/.test(text))    return 'bg-tertiary/10 border border-tertiary/30 text-tertiary'
  if (/^\[执行阶段\]/.test(text))               return 'bg-primary/10 border border-primary/30 text-primary'
  if (/^\[(审计落库|记忆写回)\]/.test(text))    return 'bg-surface-container-high border border-tertiary/20 text-on-surface-variant'
  return 'bg-surface-container border border-outline-variant/20 text-on-surface'
}

function isTinyBubble(text) {
  return false
}

// ── 流式输出（返回 Promise） ───────────────────────────
function streamText(target, fullText, speed = 15) {
  return new Promise((resolve) => {
    let pos = 0
    const timer = setInterval(() => {
      pos++
      target.text = fullText.slice(0, pos)
      if (pos >= fullText.length) { clearInterval(timer); target.streaming = false; resolve() }
    }, speed)
  })
}

// ── 单气泡段落解析 ────────────────────────────────────
const SECTION_MAP = [
  { prefix: '环境感知',   key: 'step3_perception' },
  { prefix: '上下文构建', key: 'step4_context_bundle' },
  { prefix: '初步决策',   key: 'step5_decision_draft' },
  { prefix: '反思修正',   key: 'step6_reflection' },
  { prefix: '风险评估',   key: 'step7_risk_audit' },
  { prefix: '护栏判定',   key: 'step8_guardrail_tree' },
  { prefix: '系统通知',   key: 'step9_approval_payload' },
  { prefix: '流程挂起',   key: 'step9_approval_payload' },
  { prefix: '审批通过',   key: 'step9_approval_payload' },
  { prefix: '审批拒绝',   key: 'step9_approval_payload' },
  { prefix: '流程复活',   key: 'step9_approval_payload' },
  { prefix: '执行阶段',   key: 'step10_execution_result' },
  { prefix: '审计落库',   key: 'step13_execution_report' },
  { prefix: '记忆写回',   key: null },
  { prefix: '安全拦截',   key: null },
]

function parseSection(text) {
  const m = text.match(/^\[(.+?)\]\s*/)
  if (!m) return { title: '', key: null, text: '', fullText: text, data: null, componentReady: false, collapsed: true, streaming: true }
  const tag = m[1]
  const rest = text.slice(m[0].length)
  const found = SECTION_MAP.find(s => tag.includes(s.prefix))
  return { title: tag, key: found?.key || null, text: '', fullText: rest, data: null, componentReady: false, collapsed: true, streaming: true }
}

function startGuardrailReveal(sec, data) {
  if (!sec || !data?.root?.children?.length) return
  const total = data.root.children.length
  sec._guardrailCount = 0
  const tick = () => {
    if ((sec._guardrailCount || 0) < total) {
      sec._guardrailCount = (sec._guardrailCount || 0) + 1
      setTimeout(tick, 400)
    }
  }
  setTimeout(tick, 200)
}

function scrollToCard(stepKey) {
  const el = document.querySelector(`[data-step-key="${stepKey}"]`)
  if (el) { el.scrollIntoView({ behavior:'smooth', block:'center' }); el.classList.add('card-flash'); setTimeout(()=>el.classList.remove('card-flash'),1200) }
}

function getSectionSummary(sec) {
  if (!sec.data) return '点击查看详情'
  switch (sec.key) {
    case 'step3_perception': return `感知探测完成，使用 ${sec.data.tool_results?.[0]?.tool || '—'} 工具`
    case 'step4_context_bundle': return `上下文构建完成，召回 ${(sec.data.manual_memory?.length||0)+(sec.data.raw_log_memory?.length||0)} 条记忆`
    case 'step5_decision_draft': return sec.data.conflict_state?.conflict_detected ? '⚠ 检测到冲突' : `决策完成，工具 [${sec.data.command?.split(' ')[0] || '—'}]`
    case 'step6_reflection': return sec.data.status === 'blocked' ? '✕ 反思层拦截' : sec.data.status === 'revised' ? '✓ 方案已修订' : '✓ 无需修订'
    case 'step7_risk_audit': return `护栏评分 ${sec.data.total_risk}，判定 ${(sec.data.total_risk||0) >= 0.7 ? '高风险' : (sec.data.total_risk||0) >= 0.4 ? '中风险' : '低风险'}`
    case 'step8_guardrail_tree': { const s = sec.data.root?.status; return `护栏判定：${s==='pass'?'✓ 全部通过':s==='warning'?'⚠ 待审批':s==='blocked'?'✕ 已拦截':s||'--'}` }
    case 'step9_approval_payload': return `等待审计人员审批（风险评分 ${sec.data.risk_score}）`
    case 'step10_execution_result': return sec.data.status === 'success' ? '✓ 执行成功' : '✕ 执行失败'
    case 'step13_execution_report': return sec.data.result_summary?.slice(0, 40) || '结果解读完成'
    default: return '点击查看详情'
  }
}

const currentSceneTags = computed(() => {
  const tags = agentContextData.value?.step3_perception?.tags
  if (!Array.isArray(tags)) return []
  return tags.map(tag => String(tag ?? '').trim()).filter(Boolean)
})

function scrollActiveStepIntoView() {
  nextTick(() => {
    const bar = progressBarRef.value
    if (!bar) return
    const active = bar.querySelector('[data-step-active]')
    if (!active) return
    const targetLeft = active.offsetLeft - (bar.clientWidth - active.clientWidth) / 2
    bar.scrollTo({ left: Math.max(0, targetLeft), behavior: 'smooth' })
  })
}

function revealGuardrailNodes(msgIdx, totalNodes) {
  guardrailRevealed.value[msgIdx] = 0
  const tick = () => {
    if ((guardrailRevealed.value[msgIdx] ?? 0) < totalNodes) {
      guardrailRevealed.value[msgIdx]++
      setTimeout(tick, 500)
    }
  }
  setTimeout(tick, 350)
}

function shouldStickToBottom(el, threshold = 64) {
  if (!el) return false
  return (el.scrollHeight - el.scrollTop - el.clientHeight) <= threshold
}

function rollbackCandidates(executionData) {
  const runs = Array.isArray(executionData?.command_runs) ? executionData.command_runs : []
  return runs.filter((r) => r?.rollback_available)
}

function rollbackUnavailableReason(executionData) {
  const runs = Array.isArray(executionData?.command_runs) ? executionData.command_runs : []
  if (!runs.length) return '未收到执行明细。'

  const successRuns = runs.filter((r) => r?.status === 'success')
  const failedRuns = runs.filter((r) => r?.status !== 'success')
  const readonlyOrNoRollback = successRuns.filter((r) => !r?.rollback_available)

  if (!successRuns.length) return '本次命令均执行失败，仅成功命令可回滚。'
  if (readonlyOrNoRollback.length === successRuns.length) {
    return '成功命令均为只读或未生成回滚命令。'
  }
  return `可回滚条件未满足（成功 ${successRuns.length} 条，失败 ${failedRuns.length} 条）。`
}

function commandStatusText(status) {
  const map = {
    planned: '计划中',
    skipped: '已记录',
    success: '成功',
    failed: '失败',
    warning: '警告',
  }
  return map[status] || status || '计划中'
}

function commandStatusBadge(status) {
  if (status === 'success') return 'text-tertiary border-tertiary/30 bg-tertiary/10'
  if (status === 'failed') return 'text-error border-error/30 bg-error/10'
  if (status === 'warning') return 'text-tertiary-container border-tertiary/30 bg-tertiary/10'
  return 'text-primary border-primary/30 bg-primary/10'
}

const attributionMetrics = [
  { key: 'command', label: '命令' },
  { key: 'path', label: '路径' },
  { key: 'privilege', label: '权限' },
  { key: 'output', label: '输出' },
]

function formatAttributionScore(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(2) : '--'
}

function attributionHeatClass(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return 'text-outline border-outline-variant/20 bg-surface-container'
  if (n >= 0.75) return 'text-error border-error/30 bg-error/15'
  if (n >= 0.55) return 'text-tertiary-container border-tertiary/30 bg-tertiary/15'
  if (n >= 0.35) return 'text-primary border-primary/30 bg-primary/10'
  return 'text-on-surface-variant border-outline-variant/20 bg-surface-container'
}

function commandPlanText(cmd, index, stage) {
  const tool = String(cmd?.tool || '').trim()
  const target = String(cmd?.target || cmd?.args?.path || cmd?.args?.service_name || '').trim()
  const command = String(cmd?.command || '').trim()
  const note = String(cmd?.source_plan || cmd?.plan_task || cmd?.note || '').trim()
  if (note) return note

  const targetText = target ? `，目标 ${target}` : ''
  const commandText = command ? `：${command}` : ''
  const prefix = stage === 'reflection' ? '确认/调整' : stage === 'perception' ? '执行探测' : '生成计划'
  return `${prefix} ${index + 1}：使用 ${tool || '工具'}${targetText}${commandText}`
}

function toolPlanText(result, index) {
  const tool = String(result?.tool || '').trim()
  const target = String(result?.target || '').trim()
  const map = {
    list_dir: '找到目标目录中的 nginx 访问日志、历史归档和候选清理对象',
    read_file: '读取目标文件元信息，确认文件类型和敏感性',
    stat: '读取目标文件元信息，确认文件类型、大小、权限和修改时间',
    list_process: '确认 nginx 相关进程是否运行，判断日志是否可能仍在写入',
    show_system_log: '查看近期系统日志，排除清理前后的服务异常信号',
    show_service_status: '确认目标服务状态，判断执行是否影响业务连续性',
    list_disk: '检查磁盘占用，确认清理收益和紧急程度',
  }
  const base = map[tool] || `执行 ${tool || '探测工具'} 获取环境证据`
  return target ? `${base}（目标：${target}）` : base || `执行感知计划 ${index + 1}`
}

function stagePlanTasks(data, stage) {
  const source = data || {}
  if (Array.isArray(source.plan_tasks) && source.plan_tasks.length) {
    return source.plan_tasks.map((item) => String(item || '').trim()).filter(Boolean)
  }

  const commandSource = stage === 'reflection'
    ? (source.plan_execute?.commands || source.execution_plan?.commands || [])
    : stage === 'perception'
      ? (source.plan_execute?.commands || [])
      : (source.execution_plan?.commands || source.plan_execute?.commands || [])

  if (Array.isArray(commandSource) && commandSource.length) {
    return commandSource.map((cmd, index) => commandPlanText(cmd, index, stage)).filter(Boolean)
  }

  if (stage === 'perception' && Array.isArray(source.tool_results) && source.tool_results.length) {
    return source.tool_results.map((item, index) => toolPlanText(item, index)).filter(Boolean)
  }

  return []
}

function stageCommandDetails(data, stage) {
  const source = data || {}
  const commands = stage === 'reflection'
    ? (source.plan_execute?.commands || [])
    : (source.execution_plan?.commands || [])
  const executions = stage === 'reflection' ? (source.plan_execute?.execution || []) : []
  const executionById = new Map(executions.map((item, index) => [String(item.id || index), item]))
  const defaultNote = stage === 'reflection'
    ? '反思修正阶段完成计划/执行/React 调整确认，实际执行会在执行阶段进行。'
    : '初步决策阶段生成计划/执行明细，实际执行会在执行阶段进行。'

  if (Array.isArray(commands) && commands.length) {
    const rows = commands.map((cmd, index) => {
      const matched = executionById.get(String(cmd.id || index)) || {}
      const args = cmd.args || matched.args || {}
      return {
        ...cmd,
        ...matched,
        id: cmd.id || matched.id || `cmd_${index + 1}`,
        tool: cmd.tool || matched.tool || '',
        target: cmd.target || matched.target || args.path || args.service_name || '-',
        command: cmd.command || matched.command || '',
        status: matched.status || 'planned',
        note: matched.note || defaultNote,
        stdout: matched.stdout || '',
        stderr: matched.stderr || '',
      }
    })
    for (const [index, item] of executions.entries()) {
      const id = String(item.id || index)
      const matchedCommand = commands.some((cmd, ci) => String(cmd.id || ci) === id)
      if (matchedCommand) continue
      const args = item.args || {}
      rows.push({
        ...item,
        id: item.id || `react_${index + 1}`,
        tool: item.tool || '',
        target: item.target || args.path || args.service_name || '-',
        command: item.command || '',
        status: item.status || 'planned',
        note: item.note || 'React 调整记录。',
        stdout: item.stdout || '',
        stderr: item.stderr || '',
      })
    }
    return rows
  }

  const fallbackCommand = stage === 'reflection' ? source.revised_command : source.command
  if (!fallbackCommand) return []
  return [{
    id: 'single',
    tool: stage === 'reflection' ? source.revised_tool : source.tool,
    target: stage === 'reflection' ? source.revised_target : source.target,
    command: fallbackCommand,
    status: 'planned',
    note: defaultNote,
  }]
}

function stripMcpPrefixDeep(value) {
  if (typeof value === 'string') {
    const legacyToolNames = {
      'mcp.fs.list_dir': 'list_dir',
      'mcp.fs.stat': 'list_dir',
      'mcp.service.inspect': 'show_service_status',
      'mcp.fs.mkdir': 'list_dir',
      'mcp.fs.copy': 'copy_file',
      'mcp.archive.gzip': 'archive_backup',
      'mcp.fs.truncate': 'truncate_file',
      'mcp.fs.find_delete': 'delete_file',
      'mcp.fs.move': 'move_rename',
      'mcp.workflow.plan_execute': 'archive_backup',
      'mcp.policy.extract_intent': 'read_file',
      'mcp.fs.patch_file': 'write_file_overwrite',
      'mcp.policy.prompt_scan': 'read_file',
      'mcp.policy.block': 'read_file',
      'fs.list_dir': 'list_dir',
      'fs.stat': 'list_dir',
      'service.inspect': 'show_service_status',
      'fs.mkdir': 'list_dir',
      'fs.copy': 'copy_file',
      'archive.gzip': 'archive_backup',
      'fs.truncate': 'truncate_file',
      'fs.find_delete': 'delete_file',
      'fs.move': 'move_rename',
      'workflow.plan_execute': 'archive_backup',
      'policy.extract_intent': 'read_file',
      'fs.patch_file': 'write_file_overwrite',
      'policy.prompt_scan': 'read_file',
      'policy.block': 'read_file',
    }
    return legacyToolNames[value] || value.replace(/\bmcp\./g, '')
  }
  if (Array.isArray(value)) return value.map(item => stripMcpPrefixDeep(item))
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, stripMcpPrefixDeep(item)]),
    )
  }
  return value
}

function ensureRollbackSelection(executionData) {
  const taskId = executionData?.request_id
  if (!taskId) return
  if (Array.isArray(rollbackSelectedByTask.value[taskId])) return
  rollbackSelectedByTask.value[taskId] = rollbackCandidates(executionData)
    .map((r) => r.id)
    .filter(Boolean)
}

function rollbackSelectionFor(executionData) {
  const taskId = executionData?.request_id
  if (!taskId) return []
  ensureRollbackSelection(executionData)
  return rollbackSelectedByTask.value[taskId] || []
}

function isRollbackSelected(executionData, commandId) {
  return rollbackSelectionFor(executionData).includes(commandId)
}

function toggleRollbackSelection(executionData, commandId, checked) {
  const taskId = executionData?.request_id
  if (!taskId || !commandId) return
  const current = new Set(rollbackSelectionFor(executionData))
  if (checked) current.add(commandId)
  else current.delete(commandId)
  rollbackSelectedByTask.value[taskId] = Array.from(current)
}

async function submitRollback(executionData) {
  const taskId = executionData?.request_id || agentTaskId.value
  if (!taskId) {
    ElMessage({ type: 'warning', message: '缺少任务 ID，无法执行回滚。' })
    return
  }
  const selected = rollbackSelectionFor(executionData)
  if (!selected.length) {
    ElMessage({ type: 'warning', message: '请至少勾选一条可回滚命令。' })
    return
  }
  try {
    const resp = await rollbackTask(taskId, { selected_command_ids: selected })
    if (resp?.rollback_result) {
      agentMessages.value.push({ type: 'card_rollback_result', data: resp.rollback_result })
      agentContextData.value = {
        ...(agentContextData.value || {}),
        step14_rollback_result: resp.rollback_result,
      }
    }
    ElMessage({ type: 'success', message: '回滚命令已执行，请查看回滚结果。' })
  } catch (e) {
    ElMessage({ type: 'error', message: `回滚失败：${e.message || '未知错误'}` })
  }
}

// ── 单气泡轮询 ──────────────────────────────────────
async function doPoll() {
  try {
    const shouldAutoScroll = shouldStickToBottom(messagesContainer.value)
    const d = await pollTask(agentTaskId.value)
    const cd = stripMcpPrefixDeep(d.context_data ?? {})
    agentContextData.value = cd
    const historyList = Array.isArray(d.history) ? d.history : []
    const newItems = historyList
      .slice(_prevHistoryLen)
      .filter((text) => {
        const key = String(text || '').trim()
        if (!key || _seenHistoryTexts.has(key)) return false
        _seenHistoryTexts.add(key)
        return true
      })
    _prevHistoryLen = historyList.length

    const isTerminalStatus = AGENT_TERMINAL_STATUSES.includes(d.status)
    let resp = agentMessages.value.find(m => m.type === 'instruction_response' && m.status === 'running')
    if (!resp && (!isTerminalStatus || newItems.length > 0)) {
      resp = { type: 'instruction_response', sections: [], status: 'running' }
      agentMessages.value.push(resp)
    }
    if (resp) {
      for (const text of newItems) {
        const sec = parseSection(text)
        const dataKey = sec.key
        if (dataKey && cd[dataKey]) {
          sec.data = cd[dataKey]
          sec.componentReady = true
          sec.collapsed = false
          if (dataKey === 'step8_guardrail_tree') startGuardrailReveal(sec, sec.data)
        }
        resp.sections.push(sec)
        await streamText(sec, sec.fullText, 15)
        if (shouldAutoScroll) nextTick(() => { const el = messagesContainer.value; if (el) el.scrollTop = el.scrollHeight })
      }
    }

    scrollActiveStepIntoView()
    if (resp) {
      for (const [key, data] of Object.entries(cd)) {
        if (!data) continue
        const sections = resp.sections.filter(s => s.key === key)
        if (!sections.length) continue

        const firstBindForKey = !_prevContextKeys.has(key)
        _prevContextKeys.add(key)
        for (const sec of sections) {
          if (sec.componentReady) {
            sec.data = data
            if (key === 'step8_guardrail_tree' && data.root?.children?.length && sec._guardrailCount == null) {
              startGuardrailReveal(sec, data)
            }
            continue
          }
          sec.data = data; sec.componentReady = true; sec.collapsed = false
          if (firstBindForKey) {
            for (const sib of resp.sections) { if (sib !== sec && sib.componentReady) sib.collapsed = true }
          }
          if (key === 'step8_guardrail_tree') startGuardrailReveal(sec, data)
          if (key === 'step10_execution_result') ensureRollbackSelection(data)
        }
      }
    }

    agentStatus.value = d.status
    if (shouldAutoScroll) nextTick(() => { const el = messagesContainer.value; if (el) el.scrollTop = el.scrollHeight })
    if (isTerminalStatus) { if (resp) resp.status = d.status; stopPolling(); return }
    _pollTimer = setTimeout(doPoll, d.status === 'awaiting_approval' ? 5000 : 1500)
  } catch (e) {
    console.error('[Agent] 轮询失败:', e)
    const msg = String(e?.message || '')
    if (msg.includes('404') || msg.includes('403') || /无权|权限不足|任务不存在|forbidden|not found|not exist/i.test(msg)) {
      stopPolling(); clearLastTaskId(); agentStatus.value = null
    }
    _pollTimer = setTimeout(doPoll, 3000)
  }
}

function startPolling(taskId) {
  agentPolling.value = true
  _prevHistoryLen = 0
  _prevContextKeys = new Set()
  _seenHistoryTexts = new Set()
  agentTaskId.value = taskId
  persistLastTaskId(taskId)
  loadOverview()
  doPoll()
}

function stopPolling() {
  agentPolling.value = false
  if (_pollTimer) { clearTimeout(_pollTimer); _pollTimer = null }
  loadOverview()
}

function openAgentDrawer() {
  agentDrawer.value = true
  loadOverview()
  loadSnapshot({ replaceSeries: false })
}

function closeAgentDrawer() {
  agentDrawer.value = false
  loadOverview()
  loadSnapshot({ replaceSeries: false })
}

async function sendAgent() {
  const text = agentInput.value.trim()
  if (!text || agentPolling.value) return
  agentInput.value = ''

  // 清旧消息，追加用户气泡
  agentMessages.value = [{ type: 'user', text }]
  agentContextData.value = {}
  agentStatus.value = 'running'
  guardrailRevealed.value = {}

  try {
    const resp = await runTask(text)
    startPolling(resp.task_id)
  } catch (e) {
    console.error('[Agent] 启动任务失败:', e)
    agentStatus.value = null
    agentPolling.value = false
  }
}

function restoreLastAgentTask() {
  const lastTaskId = readLastTaskId()
  if (!lastTaskId || agentPolling.value) return
  agentMessages.value = []
  agentContextData.value = {}
  agentStatus.value = 'running'
  startPolling(lastTaskId)
}

function openAgentTask(taskId) {
  if (!taskId || agentPolling.value) return false
  agentDrawer.value = true
  agentMessages.value = []
  agentContextData.value = {}
  agentStatus.value = 'running'
  startPolling(taskId)
  return true
}

function consumePendingAgentTask() {
  const routeTaskId = typeof route.query.agent_task_id === 'string' ? route.query.agent_task_id : ''
  const sessionTaskId = sessionStorage.getItem('pending_agent_task_id') || ''
  const taskId = routeTaskId || sessionTaskId
  if (!taskId) return false
  sessionStorage.removeItem('pending_agent_task_id')
  return openAgentTask(taskId)
}

const resourceTabs = [
  { key: 'overview', label: '总览'  },
  { key: 'cpu',      label: 'CPU'  },
  { key: 'memory',   label: '内存'  },
  { key: 'net',      label: '网络'  },
  { key: 'disk',     label: '磁盘'  },
]

// ── 响应式数据（由 API 填充） ──────────────────────────────
const summaryMeta = ref({
  cpu:    { title: 'CPU 使用率', value: '—', unit: '%',    extraLabel: '最大频率',   extraValue: '—' },
  memory: { title: '内存使用',   value: '—', unit: 'GB',   extraLabel: '已使用',     extraValue: '—' },
  net:    { title: '网络流量',   value: '—', unit: 'KB/s', extraLabel: '网络接口',   extraValue: '—' },
  disk:   { title: '磁盘使用',   value: '—', unit: 'GB',   extraLabel: '磁盘使用率', extraValue: '—' },
})
const uptimeDays = ref('—')
const tableData  = ref({ cpu: { cols: [], rows: [] }, memory: { cols: [], rows: [] }, net: { cols: [], rows: [] }, disk: { cols: [], rows: [] } })

// 图表序列（每 tab 滑动窗口最多 60 帧）
const chartSeries = ref({ cpu: [], memory: [], net: [], disk: [] })
const chartMeta   = ref({
  cpu:    { title: 'CPU - 总计',    unit: '%'    },
  memory: { title: '内存 - 已使用', unit: 'MB'   },
  net:    { title: '网络 - 吸吐量', unit: 'KB/s' },
  disk:   { title: '磁盘 - I/O',   unit: 'KB/s' },
})

// ── 总览 Tab 状态 ──────────────────────────────────────
const overview = ref({
  generated_at: '',
  gauges: { cpu_percent: null, memory_percent: null, disk_percent: null, network_kbps: null, nginx_qps: null },
  service_status: [],
  network_24h: [],
  nginx_qps_24h: [],
  auto_rules: [],
})
const overviewLoading = ref(false)
const overviewError = ref('')
const overviewTimeRange = ref('samples')
let _overviewTimer = null

const triggeredRules = computed(() =>
  (overview.value.auto_rules || [])
    .filter(r => r.triggered)
)

const overviewCharts = computed(() => {
  const options = { now: overview.value.generated_at || Date.now(), intervalSeconds: overview.value.sample_interval_seconds || 60, timeRange: overviewTimeRange.value }
  return [
    { key: 'net', title: '过去 24 小时网络流量', unit: 'KB/s', color: '#0ea5e9',
      data: buildOverviewChart(overview.value.network_24h, { ...options, kind: 'network', unit: 'KB/s' }) },
    { key: 'qps', title: '过去 24 小时 Nginx QPS', unit: 'QPS', color: '#10b981',
      data: buildOverviewChart(overview.value.nginx_qps_24h, { ...options, kind: 'qps', unit: 'QPS' }) },
  ]
})

function gaugeColor(value, criticalThreshold, warningThreshold) {
  if (value >= criticalThreshold) return '#ba1a1a'
  if (value >= warningThreshold) return '#de8712'
  return '#0ea5e9'
}

async function loadOverview() {
  overviewLoading.value = true
  overviewError.value = ''
  try {
    const data = await getOverview(true)
    overview.value = data
  } catch (err) {
    overviewError.value = err.message || '加载监控总览失败'
    console.error('loadOverview error:', err)
  } finally {
    overviewLoading.value = false
  }
}

// WebSocket 状态
const wsStatus         = ref('disconnected') // 'connected' | 'reconnecting' | 'disconnected'
const wsReconnectCount = ref(0)
let _ws = null
let _wsReconnectTimer = null
let _wsReconnectDelay = 1000
let _snapshotPollTimer = null

function normalizeCols(cols) {
  return Array.isArray(cols) ? cols : []
}

function normalizeRows(rows, cols = []) {
  if (!Array.isArray(rows)) return []
  const colCount = cols.length
  return rows
    .map((row) => {
      if (Array.isArray(row)) return [...row]
      if (row && typeof row === 'object') {
        if (colCount > 0) {
          const mapped = cols.map((c) => row[c])
          if (mapped.some((v) => v !== undefined)) return mapped
        }
        return Object.values(row)
      }
      return [row]
    })
    .map((row) => {
      if (colCount <= 0 || row.length >= colCount) return row
      return [...row, ...Array(colCount - row.length).fill('')]
    })
}

// ── Computed ─────────────────────────────────────────────
const activeSummary  = computed(() => summaryMeta.value[activeTab.value] || {})
const currentCols    = computed(() => normalizeCols(tableData.value[activeTab.value]?.cols))
const currentRows    = computed(() => normalizeRows(tableData.value[activeTab.value]?.rows, currentCols.value))
const chartTitle     = computed(() => ({ cpu: 'CPU', memory: '内存', net: '网络', disk: '磁盘', overview: '' }[activeTab.value] ?? 'CPU'))

const currentChartMeta = computed(() => chartMeta.value[activeTab.value] || { title: '', unit: '' })
const currentSeries    = computed(() => chartSeries.value[activeTab.value] ?? [])
const chartPathData    = computed(() => buildChartPath(currentSeries.value, currentChartMeta.value?.unit ?? ''))
const chartStrokeColor = computed(() => {
  const s = activeSummary.value?.status
  if (s === 'critical') return '#ba1a1a'
  if (s === 'warning')  return '#de8712'
  return '#0ea5e9'
})
const wsStatusDotClass = computed(() => ({
  connected:    'bg-success',
  reconnecting: 'bg-tertiary-container animate-pulse',
  disconnected: 'bg-red-500',
}[wsStatus.value] ?? 'bg-outline'))
const wsStatusText = computed(() => ({
  connected:    '实时更新中',
  reconnecting: `重连中（第 ${wsReconnectCount.value} 次）`,
  disconnected: '已断线 — 等待 WebSocket 连接',
}[wsStatus.value] ?? ''))

const col3Meta = computed(() => {
  const cols = currentCols.value
  const rows = currentRows.value
  const tab  = activeTab.value

  function sumCol(colName) {
    const i = cols.indexOf(colName)
    if (i < 0) return null
    return rows.reduce((s, r) => s + (Number(r[i]) || 0), 0)
  }

  if (tab === 'cpu') {
    const v = sumCol('线程数')
    return { label: '线程数', value: v != null ? v.toLocaleString('zh-CN') : '—' }
  }
  if (tab === 'memory') {
    const v = sumCol('工作集(KB)')
    if (v == null) return { label: '工作集合计', value: '—' }
    const display = v >= 1024 * 1024
      ? `${(v / 1024 / 1024).toFixed(1)} GB`
      : `${(v / 1024).toFixed(0)} MB`
    return { label: '工作集合计', value: display }
  }
  if (tab === 'net') {
    const summaryValue = Number(summaryMeta.value.net?.value)
    if (Number.isFinite(summaryValue)) {
      const unit = summaryMeta.value.net?.unit || 'KB/s'
      return { label: '总带宽', value: `${summaryValue.toFixed(1)} ${unit}` }
    }
    const v = sumCol('总数(字节/秒)')
    if (v == null) return { label: '总带宽', value: '—' }
    const display = v >= 1024 * 1024
      ? `${(v / 1024 / 1024).toFixed(1)} MB/s`
      : `${(v / 1024).toFixed(1)} KB/s`
    return { label: '总带宽', value: display }
  }
  if (tab === 'disk') {
    const v = sumCol('总数(字节/秒)')
    const summaryDiskIo = Number(summaryMeta.value.disk?.extraValue)
    if ((v == null || v <= 0) && Number.isFinite(summaryDiskIo)) {
      return { label: '总 I/O', value: `${summaryDiskIo.toFixed(1)} KB/s` }
    }
    if (v == null) return { label: '总 I/O', value: '—' }
    const display = v >= 1024 * 1024
      ? `${(v / 1024 / 1024).toFixed(1)} MB/s`
      : `${(v / 1024).toFixed(1)} KB/s`
    return { label: '总 I/O', value: display }
  }
  return { label: '—', value: '—' }
})

const processStats = computed(() => {
  const cols = currentCols.value
  const si = cols.indexOf('状态')
  if (si < 0) return { running: currentRows.value.length, suspended: 0, error: 0 }
  let running = 0, suspended = 0, error = 0
  for (const row of currentRows.value) {
    const s = String(row[si] ?? '')
    if (s.includes('挂起')) suspended++
    else if (s.includes('高占用') || s.includes('异常') || s.includes('错误')) error++
    else running++
  }
  return { running, suspended, error }
})

// ── 辅助函数 ─────────────────────────────────────────────
function parseMainValue(label, view) {
  if (!label) return { value: '—', unit: '' }
  const numM = label.match(/(\d+\.?\d*)/)
  const value = numM ? numM[1] : '—'
  if (label.includes('KB/s')) return { value, unit: 'KB/s' }
  if (label.includes('GB'))   return { value, unit: 'GB' }
  if (label.includes('MB'))   return { value, unit: 'MB' }
  if (label.includes('%'))    return { value, unit: '%' }
  return { value, unit: '' }
}

function limitOutputLines(text, maxLines = 30) {
  if (text == null) return ''
  const lines = String(text).replace(/\r\n/g, '\n').split('\n')
  if (lines.length <= maxLines) return lines.join('\n')
  return `${lines.slice(0, maxLines).join('\n')}\n... 已仅展示前 ${maxLines} 行`
}

function displayAgentText(text) {
  return text == null ? '' : String(text)
}

function parseExtraLabel(extra) {
  if (!extra) return { label: '扩展', value: '—' }
  if (extra.startsWith('— ')) return { label: extra.slice(2), value: '—' }
  const m = extra.match(/^(\d+(?:\.\d+)?%)\s+(.+)$/)
  if (m) return { label: m[2], value: m[1] }
  const numericWithUnit = extra.match(/^(\d+(?:\.\d+)?)\s+((?:KB\/s|MB\/s|GB\/s|KB|MB|GB)\s+.+)$/i)
  if (numericWithUnit) return { label: numericWithUnit[2], value: numericWithUnit[1] }
  const numericLabel = extra.match(/^(\d+(?:\.\d+)?)\s+(.+)$/)
  if (numericLabel) return { label: numericLabel[2], value: numericLabel[1] }
  const parts = extra.split(' ')
  return parts.length >= 2
    ? { label: parts[0], value: parts.slice(1).join(' ') }
    : { label: '扩展',  value: extra }
}

const ICON_MAP = [
  [/python|fastapi|flask|django/,  'terminal'],
  [/nginx|apache|httpd|caddy/,     'language'],
  [/postgres|mysql|mongo|redis/,   'storage'],
  [/java|jvm|kotlin/,              'code'],
  [/node|npm|deno/,                'terminal'],
  [/chrome|firefox|browser/,       'open_in_browser'],
  [/svchost|system|host/,          'settings_applications'],
  [/explorer|shell/,               'grid_view'],
]
function getIcon(name) {
  const n = String(name ?? '').toLowerCase()
  for (const [re, icon] of ICON_MAP) {
    if (re.test(n)) return icon
  }
  return 'memory'
}

function getIconColor(row) {
  // 若当前 tab 是 CPU 且 CPU% 高则用 error 色
  if (activeTab.value === 'cpu') {
    const cpuIdx = currentCols.value.indexOf('CPU%')
    if (cpuIdx >= 0 && Number(row[cpuIdx]) >= 15) return 'text-error'
  }
  return 'text-primary'
}

function getCellClass(colName, val) {
  if (colName?.includes('CPU') && Number(val) >= 15) return 'text-error font-medium'
  if (colName?.includes('状态')) {
    const s = String(val ?? '')
    if (s.includes('高占用') || s.includes('异常')) return 'text-error'
    if (s.includes('挂起')) return 'text-on-surface-variant'
    return 'text-tertiary'
  }
  return 'text-on-surface-variant'
}

function formatCellValue(val) {
  if (typeof val === 'number' && val >= 1000) return val.toLocaleString('zh-CN')
  return val
}

function safeSlice(value, start = 0) {
  return Array.isArray(value) ? value.slice(start) : []
}

const reportScoreColor = computed(() => {
  const s = reportData.value?.health_score ?? 0
  if (s >= 80) return '#10b981'
  if (s >= 50) return '#de8712'
  return '#ba1a1a'
})
const reportScoreLabel = computed(() => {
  const s = reportData.value?.health_score ?? 0
  if (s >= 80) return { text: '健康', class: 'text-success' }
  if (s >= 50) return { text: '需关注', class: 'text-tertiary-container' }
  return { text: '严重', class: 'text-error' }
})

function reportPriorityClass(priority) {
  const p = String(priority || '').toLowerCase()
  if (p === 'high') return 'text-error border-error/30 bg-error/10'
  if (p === 'medium') return 'text-tertiary-container border-tertiary/30 bg-tertiary/10'
  return 'text-tertiary border-tertiary/30 bg-tertiary/10'
}

async function generateResourceReport() {
  reportLoading.value = true
  reportError.value = ''
  try {
    const resp = await getResourceReport({
      directory: reportDirectory.value || '/var/log',
      max_depth: 2,
      max_entries: 120,
    })
    reportData.value = resp?.ai_report || null
    reportBaseDir.value = resp?.directory_snapshot?.base_dir || ''
  } catch (e) {
    reportError.value = e?.message || '生成资源检测报告失败'
    reportData.value = null
    console.error('[Monitor] 资源检测报告失败:', e)
  } finally {
    reportLoading.value = false
  }
}

function openReportDialog() {
  reportDialog.value = true
  if (!reportData.value && !reportLoading.value) {
    generateResourceReport()
  }
}

// ── API 加载 ──────────────────────────────────────────────
const VIEW_KEYS = { cpu: 'cpu_view', memory: 'memory_view', net: 'network_view', disk: 'disk_view' }
const SUMMARY_TITLES = { cpu: 'CPU 使用率', memory: '内存使用', net: '网络流量', disk: '磁盘使用' }

function mergeSeriesPoints(existing, incoming, replace = false) {
  const base = Array.isArray(existing)
    ? existing
      .map((p) => ({ timestamp: String(p?.timestamp || ''), value: Number(p?.value) }))
      .filter((p) => p.timestamp && Number.isFinite(p.value))
    : []

  const src = Array.isArray(incoming) ? incoming : []
  const normalized = src
    .map((p) => ({
      timestamp: String(p?.timestamp || ''),
      value: Number(p?.value),
    }))
    .filter((p) => p.timestamp && Number.isFinite(p.value))

  if (replace) return normalized.slice(-60)
  if (!normalized.length) return base.slice(-60)

  const arr = [...base]
  const last = normalized[normalized.length - 1]
  const tail = arr[arr.length - 1]
  if (!tail || tail.timestamp !== last.timestamp) {
    arr.push(last)
  }
  if (arr.length > 60) arr.splice(0, arr.length - 60)
  return arr
}

function applySnapshotData(d, { replaceSeries = false } = {}) {
  const keys = ['cpu', 'memory', 'net', 'disk']
  for (const k of keys) {
    const view = d[VIEW_KEYS[k]]
    if (!view) continue
    const sb = view.summary_bar
    if (!sb) continue
    const parsed = { ...parseMainValue(sb.label, view), status: sb.status ?? 'normal' }
    const { value, unit, status } = parsed
    const { label: extraLabel, value: extraValue } = parseExtraLabel(sb.extra_label)
    summaryMeta.value[k] = { title: SUMMARY_TITLES[k], value, unit, extraLabel, extraValue, status }
    tableData.value[k] = {
      cols: view.process_table?.columns || [],
      rows: view.process_table?.rows || [],
    }
    uptimeDays.value = sb.uptime_days ?? '—'
    if (view.main_chart) {
      chartMeta.value[k] = { title: view.main_chart.title, unit: view.main_chart.unit }
      chartSeries.value[k] = mergeSeriesPoints(
        chartSeries.value[k],
        view.main_chart.series ?? [],
        replaceSeries,
      )
    }
  }
}

async function loadSnapshot({ replaceSeries = false } = {}) {
  try {
    const resp = await getSnapshot()
    const d = resp?.data || resp
    applySnapshotData(d, { replaceSeries })
  } catch (e) {
    console.error('[Monitor] 加载快照失败:', e)
    if (replaceSeries) {
      ElMessage({ type: 'error', message: `监控数据加载失败：${e.message || '未知错误'}` })
    }
  } finally {
  }
}

function startSnapshotPolling() {
  if (_snapshotPollTimer) return
  _snapshotPollTimer = setInterval(async () => {
    await loadSnapshot({ replaceSeries: false })
  }, 2000)
}

function stopSnapshotPolling() {
  if (_snapshotPollTimer) {
    clearInterval(_snapshotPollTimer)
    _snapshotPollTimer = null
  }
}

// ── WebSocket + 图表 ─────────────────────────────────────────────
function formatAxisTime(isoStr) {
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  } catch { return '' }
}

function formatAxisVal(val, unit) {
  if (unit === '%')      return `${val.toFixed(1)}%`
  if (unit === 'MB')     return val >= 1024 ? `${(val / 1024).toFixed(1)}G` : `${val.toFixed(0)}M`
  if (unit === 'KB/s')   return val >= 1024 ? `${(val / 1024).toFixed(1)}M` : `${val.toFixed(0)}K`
  return val.toFixed(1)
}

function formatChartPointValue(value, unit) {
  if (unit === '%') return `${value.toFixed(1)}%`
  if (unit === 'MB') return value >= 1024 ? `${(value / 1024).toFixed(1)} GB` : `${value.toFixed(0)} MB`
  if (unit === 'KB/s') return value >= 1024 ? `${(value / 1024).toFixed(1)} MB/s` : `${value.toFixed(1)} KB/s`
  return value.toFixed(1)
}

function explainChartPoint(tab, value, unit) {
  if (tab === 'cpu') {
    if (value < 60) return `CPU 占比为 ${value.toFixed(1)}%，说明此时计算负载较轻，系统很健康。`
    if (value < 80) return `CPU 占比为 ${value.toFixed(1)}%，说明有一定负载，但仍在可接受范围。`
    if (value < 90) return `CPU 占比为 ${value.toFixed(1)}%，说明负载偏高，建议观察高占用进程。`
    return `CPU 占比为 ${value.toFixed(1)}%，说明负载过高，可能影响响应速度。`
  }
  if (tab === 'memory') {
    if (value < 70) return `内存占比为 ${value.toFixed(1)}%，说明可用内存充足，系统很健康。`
    if (value < 85) return `内存占比为 ${value.toFixed(1)}%，说明内存使用正常偏高，建议持续观察。`
    if (value < 95) return `内存占比为 ${value.toFixed(1)}%，说明内存压力较大，需关注缓存或进程占用。`
    return `内存占比为 ${value.toFixed(1)}%，说明内存压力严重，可能触发换页或服务抖动。`
  }
  if (tab === 'disk') {
    if (unit === '%') {
      if (value < 70) return `磁盘占比为 ${value.toFixed(1)}%，说明空间或活动时间充足，状态健康。`
      if (value < 85) return `磁盘占比为 ${value.toFixed(1)}%，说明使用率偏高，建议关注增长趋势。`
      return `磁盘占比为 ${value.toFixed(1)}%，说明磁盘压力较高，建议排查大文件或高 I/O 进程。`
    }
    if (value < 1024) return `磁盘 I/O 为 ${formatChartPointValue(value, unit)}，说明读写压力较低。`
    if (value < 10240) return `磁盘 I/O 为 ${formatChartPointValue(value, unit)}，说明有持续读写活动，整体可控。`
    return `磁盘 I/O 为 ${formatChartPointValue(value, unit)}，说明读写压力较高，建议查看磁盘活动进程。`
  }
  if (tab === 'net') {
    if (value < 128) return `网络吞吐为 ${formatChartPointValue(value, unit)}，说明当前网络负载很低。`
    if (value < 1024) return `网络吞吐为 ${formatChartPointValue(value, unit)}，说明网络使用平稳。`
    if (value < 10240) return `网络吞吐为 ${formatChartPointValue(value, unit)}，说明网络较活跃但仍可控。`
    return `网络吞吐为 ${formatChartPointValue(value, unit)}，说明网络流量较高，建议关注连接来源。`
  }
  return `当前值为 ${formatChartPointValue(value, unit)}，可用于判断该时刻资源负载变化。`
}

function buildChartPath(series, unit = '') {
  const EMPTY = { line: '', area: '', points: [], yTop: '', yMid: '', yBot: '', xFirst: '', xMid: '', xLast: '' }
  const normalized = (Array.isArray(series) ? series : [])
    .map((p) => ({
      timestamp: String(p?.timestamp || ''),
      value: Number(p?.value),
    }))
    .filter((p) => p.timestamp && Number.isFinite(p.value))

  if (normalized.length < 2) return EMPTY

  const W = 300, H = 80
  const vals = normalized.map((p) => p.value)
  const dataMin = Math.min(...vals)
  const dataMax = Math.max(...vals)
  if (!Number.isFinite(dataMin) || !Number.isFinite(dataMax)) return EMPTY
  const pad   = Math.max((dataMax - dataMin) * 0.2, dataMax * 0.1, 1)
  const yMin  = Math.max(0, dataMin - pad)
  const yMax  = dataMax + pad
  const range = yMax - yMin || 1
  const pointModels = normalized.map((p, i) => {
    const x = (i / (normalized.length - 1)) * W
    const y = H - ((p.value - yMin) / range) * H
    const xPercent = (x / W) * 100
    const yPercent = (y / H) * 100
    const time = formatAxisTime(p.timestamp)
    const valueText = formatChartPointValue(p.value, unit)
    const metricName = chartTitle.value || '指标'
    const label = `${metricName}：${valueText}`
    const explanation = explainChartPoint(activeTab.value, p.value, unit)
    return {
      key: `${p.timestamp}-${i}`,
      coord: `${x.toFixed(1)},${y.toFixed(1)}`,
      xPercent,
      yPercent,
      time,
      label,
      explanation,
      tooltip: `${time}\n${label}\n${explanation}`,
      tooltipSide: xPercent > 76 ? 'is-left' : xPercent < 24 ? 'is-right' : '',
    }
  })
  const pts = pointModels.map((p) => p.coord)
  if (pts.some((p) => p.includes('NaN'))) return EMPTY
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ')
  const midIdx = Math.floor(normalized.length / 2)
  return {
    line,
    area:    `${line} L${W},${H} L0,${H} Z`,
    points:  pointModels,
    yTop:    formatAxisVal(yMax, unit),
    yMid:    formatAxisVal((yMax + yMin) / 2, unit),
    yBot:    formatAxisVal(yMin, unit),
    xFirst:  formatAxisTime(normalized[0].timestamp),
    xMid:    formatAxisTime(normalized[midIdx].timestamp),
    xLast:   formatAxisTime(normalized[normalized.length - 1].timestamp),
  }
}

function handleWsFrame(msg) {
  const d = msg.data
  const tabMap = { cpu: 'cpu_view', memory: 'memory_view', net: 'network_view', disk: 'disk_view' }
  for (const [k, viewKey] of Object.entries(tabMap)) {
    const view = d[viewKey]
    if (!view) continue
    const sb = view.summary_bar
    if (sb) {
        const parsed = { ...parseMainValue(sb.label), status: sb.status ?? 'normal' }
      const { value, unit, status } = parsed
      const { label: extraLabel, value: extraValue } = parseExtraLabel(sb.extra_label ?? '')
      summaryMeta.value[k] = { ...summaryMeta.value[k], value, unit, extraLabel, extraValue, status }
      if (k === 'cpu' && sb.uptime_days != null) uptimeDays.value = sb.uptime_days
    }
    if (view.process_table) {
      tableData.value[k] = {
        cols: view.process_table.columns || [],
        rows: view.process_table.rows || [],
      }
    }
    chartSeries.value[k] = mergeSeriesPoints(
      chartSeries.value[k],
      view.main_chart?.series ?? [],
      false,
    )
  }
}

function connectWS() {
  let token = ''
  try { token = JSON.parse(localStorage.getItem('auth') || '{}').token ?? '' } catch {}
  const base = getApiBaseUrl().replace(/^http/, 'ws')
  const url = `${base}/system/monitor/ws?token=${encodeURIComponent(token)}&interval=1`
  _ws = new WebSocket(url)
  wsStatus.value = 'reconnecting'
  _ws.onopen = () => {
    wsStatus.value = 'connected'
    _wsReconnectDelay = 1000
    wsReconnectCount.value = 0
  }
  _ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.type === 'monitor_frame') handleWsFrame(msg)
    } catch {}
  }
  _ws.onerror = () => {}
  _ws.onclose = () => {
    _ws = null
    if (wsStatus.value !== 'disconnected') wsStatus.value = 'reconnecting'
    wsReconnectCount.value++
    _wsReconnectTimer = setTimeout(() => {
      _wsReconnectDelay = Math.min(_wsReconnectDelay * 2, 30000)
      connectWS()
    }, _wsReconnectDelay)
  }
}

function closeWS() {
  if (_wsReconnectTimer) { clearTimeout(_wsReconnectTimer); _wsReconnectTimer = null }
  if (_ws) { _ws.onclose = null; _ws.close(); _ws = null }
  wsStatus.value = 'disconnected'
}

onMounted(async () => {
  await loadOverview()
  _overviewTimer = setInterval(loadOverview, 12_000)
  await loadSnapshot({ replaceSeries: true })
  startSnapshotPolling()
  connectWS()
  if (!consumePendingAgentTask()) restoreLastAgentTask()
})

onUnmounted(() => {
  if (_overviewTimer) { clearInterval(_overviewTimer); _overviewTimer = null }
  stopSnapshotPolling()
  closeWS()
  stopPolling()
})
</script>

<style scoped>
@keyframes agentFadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* 每条新消息入场动画 */
.agent-msg-enter {
  animation: agentFadeIn 0.32s ease-out both;
}

/* 护栏节点逐层出现 */
.guardrail-node-enter-active {
  animation: agentFadeIn 0.4s ease-out both;
}
.guardrail-node-leave-active {
  display: none;
}

/* ── Report Dialog Overrides ────────────────────────── */
:deep(.report-dialog) {
  border-radius: 16px;
  overflow: hidden;
}
:deep(.report-dialog .el-dialog__header) {
  padding: 20px 24px 0;
  margin: 0;
  border-bottom: none;
}
:deep(.report-dialog .el-dialog__body) {
  padding: 16px 24px 24px;
}
:deep(.report-dialog .el-dialog) {
  background: var(--color-surface-container-lowest, #faf9fb);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
}
@keyframes cardFlash { 0%,100%{box-shadow:0 0 0 0 rgba(14,165,233,0)} 50%{box-shadow:0 0 0 4px rgba(14,165,233,0.3)} }
.card-flash { animation:cardFlash .6s ease-in-out 2; }
.typing-cursor { display:inline-block;width:1.5px;height:1em;background:#1544ad;margin-left:1px;vertical-align:text-bottom;animation:cursorBlink .8s infinite; }
@keyframes cursorBlink { 0%,50%{opacity:1} 51%,100%{opacity:0} }
.guardrail-blocked-glow { box-shadow:0 0 8px rgba(186,26,26,0.15); }
@keyframes guardrailLayerIn { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }
.guardrail-layer-enter { animation:guardrailLayerIn .35s ease-out both; }
.chart-data-point {
  position: absolute;
  width: 18px;
  height: 18px;
  transform: translate(-50%, -50%);
  z-index: 12;
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
}
.chart-data-dot {
  position: absolute;
  inset: 5px;
  border-radius: 999px;
  background: #fff;
  border: 2px solid var(--point-color);
  box-shadow: 0 0 0 2px rgba(255,255,255,0.95), 0 2px 6px rgba(15,23,42,0.18);
  transition: transform .16s ease, box-shadow .16s ease;
}
.chart-data-point:hover .chart-data-dot,
.chart-data-point:focus-visible .chart-data-dot {
  transform: scale(1.35);
  box-shadow: 0 0 0 3px rgba(14,165,233,0.16), 0 4px 10px rgba(15,23,42,0.22);
}
.overview-chart-point {
  width: 8px;
  height: 14px;
}
.overview-chart-point .chart-data-dot {
  inset: 4px 1px;
  opacity: 0;
}
.overview-chart-point.is-single .chart-data-dot,
.overview-chart-point.is-latest .chart-data-dot,
.overview-chart-point:hover .chart-data-dot,
.overview-chart-point:focus-visible .chart-data-dot {
  opacity: 1;
}
.chart-data-point.is-latest::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  border: 1.5px solid var(--point-color);
  border-radius: 50%;
  pointer-events: none;
  animation: chartPointPulse 2s ease-out infinite;
}
@keyframes chartPointPulse {
  from { transform: translate(-50%, -50%) scale(0.6); opacity: 0.8; }
  to { transform: translate(-50%, -50%) scale(2); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .chart-data-point.is-latest::before { animation: none; opacity: 0; }
}
.chart-data-tooltip {
  position: absolute;
  left: 50%;
  bottom: 20px;
  width: 220px;
  transform: translateX(-50%) translateY(4px);
  opacity: 0;
  pointer-events: none;
  border-radius: 8px;
  border: 1px solid rgba(110,120,129,0.24);
  background: rgba(255,255,255,0.98);
  box-shadow: 0 10px 24px rgba(15,23,42,0.14);
  padding: 9px 10px;
  text-align: left;
  white-space: normal;
  transition: opacity .16s ease, transform .16s ease;
}
.chart-data-tooltip.is-left {
  left: auto;
  right: 0;
  transform: translateX(0) translateY(4px);
}
.chart-data-tooltip.is-right {
  left: 0;
  transform: translateX(0) translateY(4px);
}
.chart-data-point:hover .chart-data-tooltip,
.chart-data-point:focus-visible .chart-data-tooltip {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
.chart-data-point:hover .chart-data-tooltip.is-left,
.chart-data-point:focus-visible .chart-data-tooltip.is-left,
.chart-data-point:hover .chart-data-tooltip.is-right,
.chart-data-point:focus-visible .chart-data-tooltip.is-right {
  transform: translateX(0) translateY(0);
}
</style>
