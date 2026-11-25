<template>
  <g fill="none" stroke-linecap="round" stroke-linejoin="round" pointer-events="none">
    <path :d="d" :stroke="color" stroke-width="1.8" vector-effect="non-scaling-stroke" />
    <!-- Follow the real path, including its gaps, without changing sample values. -->
    <path
      class="chart-line-flow"
      :d="d"
      stroke="#fff"
      stroke-width="1.2"
      stroke-opacity="0.85"
      pathLength="100"
      stroke-dasharray="4 16"
      vector-effect="non-scaling-stroke"
    />
  </g>
</template>

<script setup>
defineProps({
  d: { type: String, required: true },
  color: { type: String, required: true },
})
</script>

<style scoped>
.chart-line-flow {
  animation: chartLineFlow 2s linear infinite;
}
@keyframes chartLineFlow {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: -20; }
}
@media (prefers-reduced-motion: reduce) {
  .chart-line-flow { display: none; }
}
</style>
