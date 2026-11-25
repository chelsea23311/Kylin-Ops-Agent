import assert from 'node:assert/strict'
import test from 'node:test'
import { buildOverviewChart } from '../src/utils/overviewChart.js'

const now = '2026-11-25T12:00:00Z'
const point = (timestamp, value) => ({ timestamp, value })

test('full-day mode keeps a single point at its real time without fabricated area', () => {
  const chart = buildOverviewChart([point('2026-11-25T11:00:00Z', 4)], { now, timeRange: '24h' })
  assert.ok(Math.abs(chart.points[0].xPercent - 23 / 24 * 100) < 1e-8)
  assert.equal(chart.line, null)
  assert.equal(chart.area, null)
  assert.equal(chart.points[0].isolated, true)
})

test('irregular timestamps are spaced by elapsed time', () => {
  const chart = buildOverviewChart([
    point('2026-11-25T00:00:00Z', 4), point('2026-11-25T11:00:00Z', 2), point(now, 3),
  ], { now, timeRange: '24h' })
  assert.deepEqual(chart.points.map(p => Math.round(p.xPercent)), [50, 96, 100])
  assert.equal(chart.line, null) // Hours without samples are gaps.
})

test('recent samples fill the chart width by default, preserving elapsed time', () => {
  const chart = buildOverviewChart([
    point('2026-11-25T10:00:00Z', 4), point('2026-11-25T10:30:00Z', 2),
    point('2026-11-25T11:00:00Z', 3), point('2026-11-25T11:59:00Z', null),
  ], { now })
  assert.deepEqual(chart.points.map(p => p.xPercent), [0, 50, 100])
  assert.equal(chart.xFirst, chart.points[0].time)
  assert.equal(chart.xLast, chart.points.at(-1).time)
  assert.equal(chart.line, null) // Fitting the axis must not bridge missing samples.
})

test('a single sample has a finite axis and no fabricated line or area', () => {
  for (const timestamp of ['2026-11-25T11:00:00Z', now, '2026-11-24T12:00:00Z']) {
    const chart = buildOverviewChart([point(timestamp, 0)], { now })
    assert.ok(Number.isFinite(chart.points[0].xPercent))
    assert.ok(chart.points[0].xPercent >= 0 && chart.points[0].xPercent <= 100)
    assert.equal(chart.line, null)
    assert.equal(chart.area, null)
    assert.equal(chart.points[0].isolated, true)
  }
})

test('nulls and long gaps split lines; actual zero remains on baseline', () => {
  const chart = buildOverviewChart([
    point('2026-11-25T11:54:00Z', 1), point('2026-11-25T11:55:00Z', 2),
    point('2026-11-25T11:56:00Z', null), point('2026-11-25T11:57:00Z', 0),
    point('2026-11-25T11:58:00Z', 2), point(now, null),
  ], { now })
  assert.equal(chart.points.length, 4)
  assert.equal(chart.line.match(/M/g).length, 2)
  assert.equal(chart.area.match(/Z/g).length, 2)
  assert.equal(chart.points[2].yPercent, 100)
})

test('small QPS stays visible with distinct fractional axis labels', () => {
  const chart = buildOverviewChart([point(now, 0.0167)], { now, kind: 'qps', unit: 'QPS' })
  assert.equal(chart.yTop, '0.02')
  assert.equal(chart.yMid, '0.01')
  assert.ok(chart.points[0].label.includes('0.0167'))
})

test('invalid, future, expired samples do not create zero points', () => {
  const chart = buildOverviewChart([
    point('2026-11-24T11:59:00Z', 1), point('2026-11-25T12:01:00Z', 1),
    point(now, null), point('invalid', 4), point('2026-11-25T11:59:00Z', -2),
  ], { now })
  assert.deepEqual(chart.points, [])
  assert.ok(chart.xFirst)
  assert.ok(chart.xLast)
})
