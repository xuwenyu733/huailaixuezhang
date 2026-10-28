<template>
  <view class="page">
    <view class="top">
      <view class="tabs">
        <text
          v-for="t in tabs"
          :key="t"
          class="tab"
          :class="{ on: tab === t }"
          @click="switchTab(t)"
        >{{ t }}</text>
      </view>
      <view class="top-actions">
        <text
          v-if="canSeed"
          class="seed"
          :class="{ disabled: seeding }"
          @click="onSeedFake"
        >{{ seeding ? '写入中…' : '写入演示数据' }}</text>
        <text class="export" @click="onExport">导出</text>
      </view>
    </view>

    <view class="card">
      <text class="title">阴阳双螺旋成长模型</text>
      <view class="legend">
        <view class="leg">
          <view class="leg-line yang" />
          <text>显性成长曲线(阳)</text>
        </view>
        <view class="leg">
          <view class="leg-line yin" />
          <text>隐性增值速率(阴)</text>
        </view>
      </view>
      <canvas
        canvas-id="growthCanvas"
        id="growthCanvas"
        class="chart-box"
        :style="{ width: chartCssW + 'px', height: growthCssH + 'px' }"
      />
      <view class="helix-stats">
        <view class="stat">
          <text class="stat-k">累计显性</text>
          <text class="stat-v yang-c">{{ latestYang }}</text>
        </view>
        <view class="stat">
          <text class="stat-k">近期增值</text>
          <text class="stat-v yin-c">{{ latestYin }}</text>
        </view>
        <view class="stat">
          <text class="stat-k">总当量</text>
          <text class="stat-v">{{ totalZze }}</text>
        </view>
      </view>
    </view>

    <view class="card">
      <text class="title">知行融合分析</text>
      <view class="fusion">
        <view class="f f-know">
          <text class="fn">{{ fusion.knowStrong }}%</text>
          <text class="fl">知强于行</text>
        </view>
        <view class="f f-do">
          <text class="fn">{{ fusion.doStrong }}%</text>
          <text class="fl">行强于知</text>
        </view>
        <view class="f f-bal">
          <text class="fn">{{ fusion.balance }}%</text>
          <text class="fl">知行合一</text>
        </view>
      </view>
      <text class="advice">{{ advice }}</text>
    </view>

    <view class="card">
      <text class="title">多维度能力画像</text>
      <canvas
        canvas-id="radarCanvas"
        id="radarCanvas"
        class="chart-box radar-box"
        :style="{ width: chartCssW + 'px', height: radarCssH + 'px' }"
      />
      <view class="radar-legend">
        <view class="leg"><view class="dot me" /><text>个人</text></view>
        <view class="leg"><view class="dot norm" /><text>年级常模</text></view>
      </view>
      <text class="tip">已通过区域难度系数β归一化处理，支持全国对标</text>
    </view>

    <view class="card">
      <text class="title">班级对标排名</text>
      <view
        v-for="(r, i) in ranks"
        :key="r.name + i"
        class="rank"
        :class="{ me: r.me }"
      >
        <text class="ri">{{ i + 1 }}</text>
        <view class="rav">{{ r.av }}</view>
        <text class="rn">{{ r.name }}</text>
        <text class="rz">{{ r.zze }} ZZE</text>
      </view>
    </view>

    <AppTabBar />
  </view>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, reactive, ref } from 'vue'
import { onReady, onShow } from '@dcloudio/uni-app'
import { getDemoCurrentChild, getDemoReport, isDemoId } from '@/constants/demoData'
import { getCurrentUser, requireLogin } from '@/services/auth'
import { getCurrentChild } from '@/services/childRepo'
import { pushMessage } from '@/services/messageRepo'
import {
  buildParentReport,
  seedFakeReportData,
  type ReportMode,
} from '@/services/reportRepo'

const tabs = ['月度报告', '学期报告', '维度专项'] as const
const tab = ref<(typeof tabs)[number]>('月度报告')
const months = ref<string[]>(['本月'])
const growth = ref<number[]>([0])
const rate = ref<number[]>([0])
const dims = ref<{ name: string; me: number; norm?: number }[]>([])
const ranks = ref<{ av: string; name: string; zze: string; me: boolean }[]>([])
const advice = ref('加载中…')
const fusion = reactive({ knowStrong: 0, doStrong: 0, balance: 0 })
const totalZze = ref(0)
const childLabel = ref('')
const seeding = ref(false)
const canSeed = ref(false)
let cachedChildName = ''
let cachedOwnerId = ''
let emptyPrompted = false

const instance = getCurrentInstance()
const sys = uni.getSystemInfoSync()
const chartCssW = Math.min(Math.floor((sys.windowWidth || 375) - 48), 400)
const growthCssH = Math.round(chartCssW * 0.52)
const radarCssH = Math.round(chartCssW * 0.72)

const latestYang = computed(() => growth.value[growth.value.length - 1] || 0)
const latestYin = computed(() => rate.value[rate.value.length - 1] || 0)

function tabToMode(t: string): ReportMode {
  if (t === '学期报告') return 'term'
  if (t === '维度专项') return 'dim'
  return 'month'
}

function withNorm(
  list: { name: string; me: number; norm?: number }[],
) {
  return list.map((d) => ({
    ...d,
    norm:
      d.norm != null
        ? d.norm
        : Math.max(40, Math.min(95, Math.round(d.me * 0.82 + 8))),
  }))
}

function applyBundle(bundle: ReturnType<typeof getDemoReport>) {
  months.value = bundle.months
  growth.value = bundle.growth
  rate.value = bundle.rate
  dims.value = withNorm(bundle.dims)
  ranks.value = bundle.ranks
  advice.value = bundle.advice
  totalZze.value = bundle.totalZze
  fusion.knowStrong = bundle.fusion.knowStrong
  fusion.doStrong = bundle.fusion.doStrong
  fusion.balance = bundle.fusion.balance
  scheduleDraw()
}

function scheduleDraw() {
  nextTick(() => {
    setTimeout(() => {
      drawGrowthChart()
      drawRadarChart()
    }, 40)
  })
}

function niceMax(v: number) {
  if (v <= 0) return 100
  const p = Math.pow(10, Math.floor(Math.log10(v)))
  return Math.ceil(v / p) * p
}

function drawGrowthChart() {
  const labels = months.value.length ? months.value : ['—']
  const yang = growth.value.length ? growth.value : [0]
  const yin = rate.value.length ? rate.value : [0]
  const n = Math.max(labels.length, yang.length, yin.length)
  const L = Array.from({ length: n }, (_, i) => labels[i] || `${i + 1}`)
  const Y = Array.from({ length: n }, (_, i) => Number(yang[i]) || 0)
  const N = Array.from({ length: n }, (_, i) => Number(yin[i]) || 0)

  const w = chartCssW
  const h = growthCssH
  const pad = { l: 36, r: 36, t: 16, b: 28 }
  const plotW = w - pad.l - pad.r
  const plotH = h - pad.t - pad.b
  const maxY = niceMax(Math.max(...Y, 1) * 1.1)
  const maxN = niceMax(Math.max(...N, 1) * 1.15)

  const ctx = uni.createCanvasContext('growthCanvas', instance?.proxy as any)
  ctx.clearRect(0, 0, w, h)
  ctx.setFillStyle('#ffffff')
  ctx.fillRect(0, 0, w, h)

  // grid
  ctx.setStrokeStyle('#e5e7eb')
  ctx.setLineWidth(1)
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (plotH * i) / 4
    ctx.beginPath()
    ctx.moveTo(pad.l, y)
    ctx.lineTo(pad.l + plotW, y)
    ctx.stroke()
  }

  const xAt = (i: number) =>
    pad.l + (n <= 1 ? plotW / 2 : (plotW * i) / (n - 1))
  const yYang = (v: number) => pad.t + plotH * (1 - v / maxY)
  const yYin = (v: number) => pad.t + plotH * (1 - v / maxN)

  // yang fill
  ctx.beginPath()
  ctx.moveTo(xAt(0), pad.t + plotH)
  Y.forEach((v, i) => ctx.lineTo(xAt(i), yYang(v)))
  ctx.lineTo(xAt(n - 1), pad.t + plotH)
  ctx.closePath()
  ctx.setFillStyle('rgba(37, 99, 235, 0.12)')
  ctx.fill()

  // yang line
  ctx.beginPath()
  Y.forEach((v, i) => {
    const x = xAt(i)
    const y = yYang(v)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.setStrokeStyle('#2563eb')
  ctx.setLineWidth(2.5)
  ctx.setLineJoin('round')
  ctx.stroke()
  Y.forEach((v, i) => {
    ctx.beginPath()
    ctx.arc(xAt(i), yYang(v), 3.5, 0, Math.PI * 2)
    ctx.setFillStyle('#2563eb')
    ctx.fill()
  })

  // yin dashed
  ctx.beginPath()
  N.forEach((v, i) => {
    const x = xAt(i)
    const y = yYin(v)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.setStrokeStyle('#7c3aed')
  ctx.setLineWidth(2)
  // @ts-expect-error 小程序 canvas 支持虚线
  ctx.setLineDash([6, 4])
  ctx.stroke()
  // @ts-expect-error
  ctx.setLineDash([])
  N.forEach((v, i) => {
    ctx.beginPath()
    ctx.arc(xAt(i), yYin(v), 3.5, 0, Math.PI * 2)
    ctx.setFillStyle('#7c3aed')
    ctx.fill()
  })

  // labels
  ctx.setFillStyle('#9ca3af')
  ctx.setFontSize(10)
  ctx.setTextAlign('center')
  L.forEach((lab, i) => {
    ctx.fillText(lab, xAt(i), h - 8)
  })
  ctx.setTextAlign('right')
  ctx.fillText(String(maxY), pad.l - 4, pad.t + 10)
  ctx.setTextAlign('left')
  ctx.fillText(String(maxN), pad.l + plotW + 4, pad.t + 10)

  ctx.draw()
}

function drawRadarChart() {
  const list = dims.value.length
    ? dims.value
    : [{ name: '—', me: 0, norm: 0 }]
  const w = chartCssW
  const h = radarCssH
  const cx = w / 2
  const cy = h / 2 - 8
  const r = Math.min(w, h) * 0.32
  const count = list.length
  const step = (Math.PI * 2) / count

  const ctx = uni.createCanvasContext('radarCanvas', instance?.proxy as any)
  ctx.clearRect(0, 0, w, h)
  ctx.setFillStyle('#ffffff')
  ctx.fillRect(0, 0, w, h)

  const pt = (i: number, ratio: number) => {
    const ang = -Math.PI / 2 + step * i
    return {
      x: cx + Math.cos(ang) * r * ratio,
      y: cy + Math.sin(ang) * r * ratio,
    }
  }

  // rings
  for (let ring = 1; ring <= 4; ring++) {
    ctx.beginPath()
    for (let i = 0; i < count; i++) {
      const p = pt(i, ring / 4)
      if (i === 0) ctx.moveTo(p.x, p.y)
      else ctx.lineTo(p.x, p.y)
    }
    ctx.closePath()
    ctx.setStrokeStyle('#e5e7eb')
    ctx.setLineWidth(1)
    ctx.stroke()
  }

  // axes + labels
  ctx.setFillStyle('#6b7280')
  ctx.setFontSize(11)
  ctx.setTextAlign('center')
  for (let i = 0; i < count; i++) {
    const tip = pt(i, 1)
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.lineTo(tip.x, tip.y)
    ctx.setStrokeStyle('#e5e7eb')
    ctx.stroke()
    const lab = pt(i, 1.22)
    ctx.fillText(list[i].name, lab.x, lab.y + 4)
  }

  const drawPoly = (
    values: number[],
    stroke: string,
    fill: string,
    pointColor: string,
  ) => {
    ctx.beginPath()
    values.forEach((v, i) => {
      const p = pt(i, Math.max(0, Math.min(100, v)) / 100)
      if (i === 0) ctx.moveTo(p.x, p.y)
      else ctx.lineTo(p.x, p.y)
    })
    ctx.closePath()
    ctx.setFillStyle(fill)
    ctx.fill()
    ctx.setStrokeStyle(stroke)
    ctx.setLineWidth(2)
    ctx.stroke()
    values.forEach((v, i) => {
      const p = pt(i, Math.max(0, Math.min(100, v)) / 100)
      ctx.beginPath()
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2)
      ctx.setFillStyle(pointColor)
      ctx.fill()
    })
  }

  drawPoly(
    list.map((d) => d.norm || 70),
    '#9ca3af',
    'rgba(156, 163, 175, 0.12)',
    '#9ca3af',
  )
  drawPoly(
    list.map((d) => d.me),
    '#2563eb',
    'rgba(37, 99, 235, 0.2)',
    '#2563eb',
  )

  ctx.draw()
}

async function loadReport() {
  if (!cachedOwnerId) return
  if (isDemoId(cachedOwnerId)) {
    applyBundle(getDemoReport())
    return
  }
  try {
    const bundle = await buildParentReport(
      cachedOwnerId,
      cachedChildName || undefined,
      tabToMode(tab.value),
    )
    applyBundle(bundle)
    // 正式账号且无数据：自动提示写入演示数据
    if (canSeed.value && bundle.totalZze <= 0 && !emptyPrompted && !seeding.value) {
      emptyPrompted = true
      setTimeout(() => {
        uni.showModal({
          title: '报告暂无数据',
          content:
            '当前账号还没有盖章记录。是否写入近 6 个月虚假演示数据到数据库？写入后报告会立刻出图。',
          confirmText: '写入数据',
          success: (res) => {
            if (res.confirm) onSeedFake(true)
          },
        })
      }, 300)
    }
  } catch (e: any) {
    advice.value = e.message || '报告加载失败'
  }
}

async function switchTab(t: (typeof tabs)[number]) {
  if (tab.value === t) return
  tab.value = t
  await loadReport()
}

onReady(() => {
  scheduleDraw()
})

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  cachedOwnerId = user.id
  canSeed.value = !isDemoId(user.id) && user.role === 'parent'
  if (isDemoId(user.id)) {
    const child = getDemoCurrentChild()
    childLabel.value = child.name
    cachedChildName = child.name
    await loadReport()
    return
  }
  try {
    const child =
      user.role === 'teacher' ? null : await getCurrentChild(user.id)
    childLabel.value = child?.name || user.name
    cachedChildName = child?.name || ''
    await loadReport()
  } catch (e: any) {
    advice.value = e.message || '报告加载失败'
  }
})

async function runSeed() {
  if (!canSeed.value || seeding.value || !cachedOwnerId) return
  seeding.value = true
  try {
    const r = await seedFakeReportData(cachedOwnerId)
    cachedChildName = r.childName
    childLabel.value = r.childName
    emptyPrompted = true
    await loadReport()
    uni.showToast({
      title: `已写入 ${r.count} 条`,
      icon: 'success',
    })
  } catch (e: any) {
    uni.showToast({ title: e.message || '写入失败', icon: 'none', duration: 3000 })
  } finally {
    seeding.value = false
  }
}

async function onSeedFake(skipConfirm = false) {
  if (!canSeed.value || seeding.value || !cachedOwnerId) return
  if (skipConfirm) {
    await runSeed()
    return
  }
  uni.showModal({
    title: '写入演示数据',
    content:
      '将向数据库写入近 6 个月虚假盖章记录（若无孩子会自动创建「测试同学」）。确认继续？',
    success: async (res) => {
      if (!res.confirm) return
      await runSeed()
    },
  })
}

function onExport() {
  const user = getCurrentUser()
  const text = [
    `淮来学长成长报告`,
    `学生：${childLabel.value}`,
    `累计当量：${totalZze.value}`,
    `知强于行 ${fusion.knowStrong}% / 行强于知 ${fusion.doStrong}% / 知行合一 ${fusion.balance}%`,
    `月份：${months.value.join('、')}`,
    `分析：${advice.value}`,
  ].join('\n')
  uni.setClipboardData({
    data: text,
    success: async () => {
      uni.showToast({ title: '报告摘要已复制', icon: 'success' })
      if (user && !String(user.id).startsWith('demo_')) {
        await pushMessage({
          ownerId: user.id,
          title: '报告已导出',
          content: `${childLabel.value} 累计当量 ${totalZze.value}，摘要已复制`,
          category: 'report',
        }).catch(() => undefined)
      }
    },
  })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f9fafb;
  padding: 24rpx;
  padding-bottom: 40rpx;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}
.tabs {
  display: flex;
  background: #fff;
  border-radius: 14rpx;
  padding: 6rpx;
}
.tab {
  padding: 12rpx 20rpx;
  font-size: 24rpx;
  color: #6b7280;
  border-radius: 10rpx;
}
.tab.on {
  background: #2563eb;
  color: #fff;
}
.top-actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 20rpx;
}
.seed {
  color: #d97706;
  font-size: 24rpx;
}
.seed.disabled {
  opacity: 0.5;
}
.export {
  color: #2563eb;
  font-size: 26rpx;
}
.card {
  background: #fff;
  border-radius: 24rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
}
.title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 16rpx;
  color: #1f2937;
}
.legend {
  display: flex;
  gap: 28rpx;
  font-size: 22rpx;
  color: #6b7280;
  margin-bottom: 12rpx;
}
.leg {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10rpx;
}
.leg-line {
  width: 36rpx;
  height: 6rpx;
  border-radius: 6rpx;
}
.leg-line.yang {
  background: #2563eb;
}
.leg-line.yin {
  background: repeating-linear-gradient(
    90deg,
    #7c3aed 0,
    #7c3aed 8rpx,
    transparent 8rpx,
    transparent 14rpx
  );
  height: 4rpx;
}
.chart-box {
  width: 100%;
  display: block;
  margin: 0 auto;
}
.radar-box {
  margin-top: 4rpx;
}
.helix-stats {
  display: flex;
  flex-direction: row;
  margin-top: 16rpx;
  gap: 12rpx;
}
.stat {
  flex: 1;
  background: #f8fafc;
  border-radius: 14rpx;
  padding: 16rpx 12rpx;
  text-align: center;
}
.stat-k {
  display: block;
  font-size: 20rpx;
  color: #94a3b8;
  margin-bottom: 6rpx;
}
.stat-v {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: #0f172a;
}
.stat-v.yang-c {
  color: #2563eb;
}
.stat-v.yin-c {
  color: #7c3aed;
}
.fusion {
  display: flex;
  gap: 12rpx;
  margin-bottom: 16rpx;
}
.f {
  flex: 1;
  text-align: center;
  border-radius: 16rpx;
  padding: 20rpx 8rpx;
}
.f-know {
  background: #eff6ff;
}
.f-do {
  background: #fffbeb;
}
.f-bal {
  background: #ecfdf5;
}
.fn {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  margin-bottom: 6rpx;
}
.f-know .fn {
  color: #2563eb;
}
.f-do .fn {
  color: #d97706;
}
.f-bal .fn {
  color: #059669;
}
.fl {
  color: #64748b;
  font-size: 22rpx;
}
.advice {
  font-size: 24rpx;
  color: #6b7280;
  line-height: 1.7;
}
.radar-legend {
  display: flex;
  justify-content: center;
  gap: 32rpx;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #6b7280;
}
.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
}
.dot.me {
  background: #2563eb;
}
.dot.norm {
  background: #9ca3af;
}
.tip {
  display: block;
  margin-top: 12rpx;
  font-size: 22rpx;
  color: #9ca3af;
  text-align: center;
}
.rank {
  display: flex;
  align-items: center;
  padding: 20rpx 12rpx;
  border-radius: 14rpx;
}
.rank.me {
  background: #eff6ff;
}
.ri {
  width: 40rpx;
  font-weight: 700;
  color: #9ca3af;
}
.rav {
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  background: #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16rpx;
  font-weight: 600;
}
.rank.me .rav {
  background: #2563eb;
  color: #fff;
}
.rn {
  flex: 1;
  font-size: 28rpx;
}
.rz {
  font-size: 26rpx;
  font-weight: 600;
  color: #2563eb;
}
</style>
