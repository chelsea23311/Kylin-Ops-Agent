import assert from 'node:assert/strict'
import test from 'node:test'
import { executionSummary } from '../src/utils/executionSummary.js'

test('a later permission failure is shown instead of the successful df command', () => {
  const success = { tool: 'disk_usage', command: 'df -h', status: 'success', exit_code: 0, stdout: '95% /' }
  const failed = { tool: 'directory_usage', command: 'du /', status: 'failed', exit_code: 1, stdout: 'partial totals', stderr: 'Permission denied' }
  const data = { ...success, status: 'failed', exit_code: 1, command_runs: [success, failed, { ...failed, tool: 'find_large_files' }] }
  const summary = executionSummary(data)
  assert.equal(summary.label, '部分失败（1/3 条成功）')
  assert.equal(summary.tool, 'directory_usage')
  assert.equal(summary.command, 'du /')
  assert.equal(summary.stdout, 'partial totals')
  assert.equal(summary.stderr, 'Permission denied')
  assert.equal(summary.exit_code, 1)
  assert.equal(data.tool, 'disk_usage') // Historical records remain intact.
})

test('fully successful, fully failed, and legacy records retain accurate summaries', () => {
  const success = { status: 'success', tool: 'disk_usage', exit_code: 0 }
  const failed = { status: 'failed', tool: 'directory_usage', exit_code: 1 }
  assert.equal(executionSummary({ command_runs: [success, success] }).label, '执行成功')
  assert.equal(executionSummary({ command_runs: [failed, failed] }).label, '执行失败')
  assert.equal(executionSummary({ ...failed, stderr: 'Permission denied' }).stderr, 'Permission denied')
  assert.equal(executionSummary({ ...success, command_runs: [] }).tool, 'disk_usage')
})
