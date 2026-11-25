const DAY_MS = 24 * 60 * 60 * 1000

export function formatMetric(value) {
  return Number(value).toLocaleString('zh-CN', { maximumSignificantDigits: 4 })
}

function timeLabel(timestamp) {
  return new Date(timestamp).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

export function buildOverviewChart(series, { now = Date.now(), intervalSeconds = 60, kind = 'network', unit = 'KB/s', timeRange = 'samples' } = {}) {
  const parsed = typeof now === 'number' ? now : Date.parse(now)
  const end = Number.isFinite(parsed) ? parsed : Date.now()
  const start = end - DAY_MS
  const metric = kind === 'network' ? '网络收发总速率' : 'Nginx QPS'
  const samples = [...new Map((Array.isArray(series) ? series : []).map(s => {
    const ts = Date.parse(s?.timestamp)
    const value = s?.value == null || s?.value === '' ? null : Number(s.value)
    return [ts, { ts, value: Number.isFinite(value) && value >= 0 ? value : null }]
  })).values()].filter(s => Number.isFinite(s.ts) && s.ts >= start && s.ts <= end).sort((a, b) => a.ts - b.ts)
  const valid = samples.filter(s => s.value !== null)
  // Keep the last 24 hours of evidence, but fit the axis to observed data by default.
  let axisStart = start
  let axisEnd = end
  if (timeRange === 'samples' && valid.length) {
    axisStart = valid[0].ts
    axisEnd = valid.at(-1).ts
    if (axisStart === axisEnd) {
      const padding = Math.max(Number(intervalSeconds) || 60, 1) * 500
      axisStart = Math.max(start, axisStart - padding)
      axisEnd = Math.min(end, axisEnd + padding)
    }
  }
  const axisDuration = axisEnd - axisStart
  const max = Math.max(...valid.map(s => s.value), 0) || 1
  const magnitude = 10 ** Math.floor(Math.log10(max))
  const scale = [1, 2, 5, 10].find(n => n * magnitude >= max) * magnitude
  const points = []
  const segments = []
  let segment = []
  let previous = null
  for (const sample of samples) {
    if (sample.value === null || (previous !== null && sample.ts - previous > intervalSeconds * 2500)) {
      if (segment.length) segments.push(segment)
      segment = []
    }
    previous = sample.ts
    if (sample.value === null) continue
    const xPercent = (sample.ts - axisStart) / axisDuration * 100
    const yPercent = 100 * (1 - sample.value / scale)
    const time = timeLabel(sample.ts)
    const label = `${metric}：${formatMetric(sample.value)} ${unit}`
    const explanation = kind === 'network'
      ? '该采样周期内系统发送与接收字节的平均速率。'
      : '该采样周期内访问日志新增请求数除以实际采样秒数。'
    const point = {
      key: `${kind}-${sample.ts}`, xPercent, yPercent, time, label, explanation,
      coord: `${(xPercent * 3).toFixed(4)},${yPercent.toFixed(4)}`,
      tooltip: `${time}\n${label}\n${explanation}`,
      tooltipSide: xPercent > 76 ? 'is-left' : xPercent < 24 ? 'is-right' : '',
    }
    points.push(point)
    segment.push(point)
  }
  if (segment.length) segments.push(segment)
  for (const s of segments) {
    if (s.length === 1) s[0].isolated = true
  }
  const drawable = segments.filter(s => s.length > 1)
  return {
    line: drawable.map(s => `M${s.map(p => p.coord).join(' L')}`).join(' ') || null,
    area: drawable.map(s => `M${s.map(p => p.coord).join(' L')} L${(s.at(-1).xPercent * 3).toFixed(4)},100 L${(s[0].xPercent * 3).toFixed(4)},100 Z`).join(' ') || null,
    points, yTop: formatMetric(scale), yMid: formatMetric(scale / 2),
    xFirst: timeLabel(axisStart), xMid: timeLabel(axisStart + axisDuration / 2), xLast: timeLabel(axisEnd),
    coverage: points.length ? `有效采样 ${points.length} 个 · ${points[0].time} 至 ${points.at(-1).time}` : '尚无有效采样',
  }
}
