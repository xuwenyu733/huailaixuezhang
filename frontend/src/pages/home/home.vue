<template>
  <view class="page">
    <view class="header">
      <view class="user">
        <view class="avatar">{{ profile.avatar }}</view>
        <view>
          <text class="name">{{ profile.name }}</text>
          <text class="sub">{{ profile.sub }}</text>
        </view>
      </view>
      <view class="bell" @click="go('/pages/message/message')">
        <text class="bell-icon">🔔</text>
        <view class="badge" v-if="unread > 0">{{ unread > 99 ? '99+' : unread }}</view>
      </view>
    </view>

    <view class="stats card">
      <view class="stat">
        <text class="num">{{ stats.zze }}</text>
        <text class="lab">知章当量 ZZE</text>
      </view>
      <view class="split" />
      <view class="stat">
        <text class="num">{{ stats.know }}</text>
        <text class="lab">知章次数</text>
      </view>
      <view class="split" />
      <view class="stat">
        <text class="num">{{ stats.combo }}</text>
        <text class="lab">知行对章</text>
      </view>
    </view>

    <view class="card">
      <text class="section-title">阶位进阶进度</text>
      <view class="level" v-for="item in levels" :key="item.name">
        <view class="level-top">
          <text>{{ item.name }} · {{ item.desc }}</text>
          <text class="lv">{{ item.lv }}</text>
        </view>
        <view class="bar">
          <view class="fill" :style="{ width: item.pct + '%', background: item.color }" />
        </view>
      </view>
      <text class="tip">换算规则：Vn = V₁ × K^(n-1)，当前K=10</text>
    </view>

    <view class="quick">
      <view class="q" @click="switchTab('/pages/scan/scan')">
        <view class="q-icon blue">拍</view>
        <text>拍照采集</text>
      </view>
      <view class="q" @click="switchTab('/pages/report/report')">
        <view class="q-icon purple">报</view>
        <text>成长报告</text>
      </view>
      <view class="q" @click="go('/pages/code/code')">
        <view class="q-icon green">码</view>
        <text>编码表</text>
      </view>
    </view>

    <view class="card">
      <view class="row-between">
        <text class="section-title mb0">最近评价记录</text>
        <text class="link" @click="go('/pages/stamp/stamp')">虚拟盖章</text>
      </view>
      <view v-if="!records.length" class="empty">暂无盖章记录，去采集或虚拟盖章试试</view>
      <view class="record" v-for="(r, i) in records" :key="i">
        <view class="stamp-wrap">
          <view v-if="r.type === 'know'" class="stamp-square" />
          <view v-else-if="r.type === 'do'" class="stamp-round" />
          <view v-else class="stamp-combo"><view class="sq" /><view class="rd" /></view>
        </view>
        <view class="meta">
          <text class="t">{{ r.title }}</text>
          <text class="s">{{ r.sub }}</text>
        </view>
        <text class="pts" :style="{ color: r.color }">{{ r.pts }}</text>
      </view>
    </view>

    <AppTabBar />
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { DEMO_STAMPS, getDemoStampStats, isDemoId } from '@/constants/demoData'
import { dimNameOf } from '@/constants/dimensions'
import { formatStampValue } from '@/constants/sealMethods'
import { refreshCurrentUser, requireLogin } from '@/services/auth'
import { countUnreadMessages } from '@/services/messageRepo'
import { listStampsByOwner } from '@/services/stampRepo'
import { useDemoStore } from '@/stores/demo'

const store = useDemoStore()
const profile = computed(() => store.profile)

const levels = [
  { name: '知章', desc: '过程积累', lv: 'Lv.1', pct: 20, color: '#2563eb' },
  { name: '行章', desc: '阶段成果', lv: 'Lv.1', pct: 10, color: '#f59e0b' },
  { name: '知行对章', desc: '深度融合', lv: 'Lv.1', pct: 5, color: '#10b981' },
]

const stats = reactive({ zze: 0, know: 0, combo: 0 })
const unread = ref(0)
const records = ref<
  { type: string; title: string; sub: string; pts: string; color: string }[]
>([])

function applyStampRows(
  rows: typeof DEMO_STAMPS,
  unreadCount: number,
) {
  let zze = 0
  let know = 0
  let combo = 0
  let physical = 0
  rows.forEach((r) => {
    zze += Number(r.value_num) || 0
    if (r.stamp_type === 'combo') combo += 1
    else know += 1
    if (r.source === 'physical') physical += 1
  })
  unread.value = unreadCount
  stats.zze = zze
  stats.know = know
  stats.combo = combo
  const lvOf = (n: number) => Math.min(9, Math.floor(n / 10) + 1)
  levels[0].pct = Math.min(100, know * 10)
  levels[0].lv = `Lv.${lvOf(know)}`
  levels[1].pct = Math.min(100, physical * 12)
  levels[1].lv = `Lv.${lvOf(physical)}`
  levels[2].pct = Math.min(100, combo * 20)
  levels[2].lv = `Lv.${lvOf(combo)}`
  records.value = rows.slice(0, 8).map((r) => {
    // 当量单位跟图标一致：知行对章 DE、实体/行章 XE、知章 ZE
    const unitType =
      r.stamp_type === 'combo'
        ? 'combo'
        : r.stamp_type === 'do' || r.source === 'physical'
          ? 'do'
          : 'know'
    return {
      type:
        r.stamp_type === 'combo' ? 'combo' : r.source === 'physical' ? 'do' : 'know',
      title: `${r.source === 'physical' ? '实体' : '虚拟'} · ${dimNameOf(String(r.code_text || '').charAt(0)) || r.stamp_type}`,
      sub: `${r.subject || '-'} · ${r.child_name || ''} · 编码${r.code_text}`,
      pts: formatStampValue(r.value_num, unitType),
      color: r.stamp_type === 'combo' ? '#10b981' : r.source === 'physical' ? '#f59e0b' : '#2563eb',
    }
  })
}

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  await refreshCurrentUser()
  if (isDemoId(user.id)) {
    if (user.id === 'demo_family') {
      const s = getDemoStampStats()
      applyStampRows(DEMO_STAMPS, s.unread)
    }
    return
  }
  try {
    const unreadCount = await countUnreadMessages(user.id).catch(() => 0)
    const rows = await listStampsByOwner(user.id, 50)
    applyStampRows(rows as typeof DEMO_STAMPS, unreadCount)
  } catch {
    /* ignore */
  }
})

function go(url: string) {
  uni.navigateTo({ url })
}
function switchTab(url: string) {
  uni.switchTab({ url })
}
</script>

<style scoped>
.empty {
  padding: 32rpx 0;
  text-align: center;
  color: #9ca3af;
  font-size: 24rpx;
}
.page {
  min-height: 100vh;
  background: #f9fafb;
  padding-bottom: 30rpx;
}
.header {
  background: #2563eb;
  padding: 32rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
}
.user {
  display: flex;
  align-items: center;
}
.avatar {
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  font-weight: 700;
  margin-right: 20rpx;
}
.name {
  display: block;
  font-size: 34rpx;
  font-weight: 600;
}
.sub {
  display: block;
  margin-top: 6rpx;
  font-size: 24rpx;
  opacity: 0.85;
}
.bell {
  position: relative;
  padding: 12rpx;
}
.bell-icon {
  font-size: 40rpx;
}
.badge {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 32rpx;
  height: 32rpx;
  background: #ef4444;
  border-radius: 999rpx;
  font-size: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8rpx;
}
.card {
  margin: 24rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 28rpx;
}
.stats {
  margin-top: -20rpx;
  display: flex;
  box-shadow: 0 8rpx 24rpx rgba(37, 99, 235, 0.08);
}
.stat {
  flex: 1;
  text-align: center;
}
.num {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #111827;
}
.lab {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #6b7280;
}
.split {
  width: 2rpx;
  background: #f3f4f6;
}
.section-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 20rpx;
}
.mb0 {
  margin-bottom: 0;
}
.level {
  margin-bottom: 20rpx;
}
.level-top {
  display: flex;
  justify-content: space-between;
  font-size: 24rpx;
  color: #374151;
  margin-bottom: 10rpx;
}
.lv {
  color: #6b7280;
}
.bar {
  height: 14rpx;
  background: #f3f4f6;
  border-radius: 999rpx;
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 999rpx;
}
.tip {
  display: block;
  font-size: 22rpx;
  color: #9ca3af;
}
.quick {
  display: flex;
  margin: 0 24rpx 24rpx;
  gap: 16rpx;
}
.q {
  flex: 1;
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx 12rpx;
  text-align: center;
  font-size: 24rpx;
  color: #374151;
}
.q-icon {
  width: 72rpx;
  height: 72rpx;
  border-radius: 20rpx;
  color: #fff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12rpx;
}
.q-icon.blue {
  background: #2563eb;
}
.q-icon.purple {
  background: #7c3aed;
}
.q-icon.green {
  background: #10b981;
}
.row-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}
.link {
  font-size: 24rpx;
  color: #2563eb;
}
.record {
  display: flex;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.record:last-child {
  border-bottom: none;
}
.stamp-wrap {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16rpx;
}
.meta {
  flex: 1;
}
.t {
  display: block;
  font-size: 28rpx;
  color: #111827;
}
.s {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #9ca3af;
}
.pts {
  font-size: 26rpx;
  font-weight: 600;
}
</style>
