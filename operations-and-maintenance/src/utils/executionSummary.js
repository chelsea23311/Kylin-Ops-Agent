export function executionSummary(data = {}) {
  const runs = Array.isArray(data.command_runs) ? data.command_runs : []
  const failed = runs.find(run => run.status !== 'success')
  const selected = failed || runs[0] || data
  const succeeded = runs.filter(run => run.status === 'success').length
  const label = failed
    ? succeeded ? `部分失败（${succeeded}/${runs.length} 条成功）` : '执行失败'
    : (runs.length || data.status === 'success') ? '执行成功' : '执行失败'
  return { ...selected, exit_code: selected.exit_code ?? data.exit_code, label }
}
