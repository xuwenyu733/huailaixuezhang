<template>
  <view class="page">
    <view class="head card">
      <view class="av">{{ avatar }}</view>
      <view class="head-meta">
        <text class="name">{{ child?.name || displayName || '学生' }}</text>
        <text class="sub"
          >{{ child?.class_name || '未填班级' }} ·
          {{ child?.school || '未填学校' }}</text
        >
      </view>
    </view>

    <view class="card">
      <text class="title">基本信息</text>
      <text class="li">学号：{{ child?.student_no || '-' }}</text>
      <text class="li">学校：{{ child?.school || '-' }}</text>
      <text class="li">班级：{{ child?.class_name || '-' }}</text>
      <text class="li">班级码：{{ child?.class_code || '-' }}</text>
      <text class="li">记录卡：{{ child?.card_no || cardHint || '-' }}</text>
      <text class="li"
        >家长授权当量：{{ hiddenStats ? '未授权' : '已授权' }}</text
      >
    </view>

    <view class="card">
      <text class="title">成长数据概览</text>
      <text v-if="hiddenStats" class="tip"
        >家长未授权教师查看当量明细。你仍可查看档案与记录卡号。</text
      >
      <view v-else class="stats">
        <view class="stat">
          <text class="n">{{ know }}</text>
          <text class="l">知章</text>
        </view>
        <view class="stat">
          <text class="n">{{ combo }}</text>
          <text class="l">对章</text>
        </view>
        <view class="stat">
          <text class="n">{{ total }}</text>
          <text class="l">当量 ZZE</text>
        </view>
      </view>
    </view>

    <view class="card" v-if="!hiddenStats && recent.length">
      <text class="title">近 7 日盖章</text>
      <view class="stamp" v-for="(r, i) in recent" :key="i">
        <view class="stamp-l">
          <text class="stamp-t"
            >{{ r.subject || '综合' }} · {{ r.kindLabel }}</text
          >
          <text class="badge" :class="r.badgeClass">{{ r.badge }}</text>
        </view>
        <text class="stamp-d">{{ r.day }}</text>
      </view>
    </view>

    <button class="btn" @click="goReport">查看完整报告</button>
    <button v-if="isTeacher" class="btn ghost" @click="goScan"
      >为该生补盖章</button
    >
    <button v-if="isParent" class="btn ghost" @click="setCurrent"
      >设为当前查看</button
    >
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireLogin } from '@/services/auth'
import {
  findChildByCardNo,
  listAllChildren,
  listChildrenByParent,
  setCurrentChild,
} from '@/services/childRepo'
import { getUserPrefs } from '@/services/prefsRepo'
import { listStampsByChild } from '@/services/stampRepo'
import type { ChildRow } from '@/types/user'

interface RecentRow {
  subject: string
  kindLabel: string
  badge: string
  badgeClass: string
  day: string
}

const child = ref<ChildRow | null>(null)
const know = ref(0)
const combo = ref(0)
const total = ref(0)
const parentId = ref('')
const isParent = ref(true)
const isTeacher = ref(false)
const hiddenStats = ref(false)
const displayName = ref('')
const cardHint = ref('')
const recent = ref<RecentRow[]>([])

const avatar = computed(
  () =>
    child.value?.avatar_text ||
    child.value?.name?.slice(0, 1) ||
    displayName.value.slice(0, 1) ||
    '学',
)

function withinDays(iso: string, days: number) {
  if (!iso) return false
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return false
  return Date.now() - t <= days * 86400000
}

function formatDay(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const m = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${m}-${day}`
}

onLoad(async (query) => {
  const user = requireLogin()
  if (!user) return
  parentId.value = user.id
  isParent.value = user.role === 'parent'
  isTeacher.value = user.role === 'teacher'
  displayName.value = decodeURIComponent(String(query?.name || ''))
  cardHint.value = decodeURIComponent(String(query?.card || ''))
  if (String(query?.hidden) === '1') hiddenStats.value = true

  const id = String(query?.id || '')
  if (String(user.id).startsWith('demo_') || id === 'demo_hidden') {
    if (hiddenStats.value || id === 'demo_hidden') {
      child.value = {
        Id: 0,
        parent_id: 0,
        name: displayName.value || '陈思雨',
        avatar_text: (displayName.value || '陈').slice(0, 1),
        student_no: '-',
        school: '淮安实验小学',
        class_name: '三年级 2 班',
        class_code: 'HA-G3-02',
        card_no: cardHint.value || 'CARD-022',
        tag: '',
        is_current: 0,
        created_at: '',
      }
      hiddenStats.value = true
      return
    }
    const { DEMO_CLASS_STUDENTS, DEMO_STAMPS } = await import(
      '@/constants/demoData'
    )
    const demo = DEMO_CLASS_STUDENTS.find((s) => s.id === id)
    child.value = {
      Id: 0,
      parent_id: 0,
      name: demo?.name || displayName.value || '演示学生',
      avatar_text: demo?.av || '学',
      student_no: '20261001',
      school: '淮安实验小学',
      class_name: '三年级 2 班',
      class_code: 'HA-G3-02',
      card_no: demo?.card || cardHint.value || '-',
      tag: '',
      is_current: 0,
      created_at: '',
    }
    know.value = Number(demo?.know) || 0
    combo.value = Number(demo?.combo) || 0
    total.value = Number(demo?.zze) || 0
    recent.value = DEMO_STAMPS.slice(0, 3).map((s) => {
      const type = String(s.stamp_type)
      return {
        subject: String(s.subject || '综合'),
        kindLabel:
          type === 'combo' ? '知行对章' : type === 'do' ? '行章' : '正向章',
        badge: type === 'combo' ? '对' : type === 'do' ? '行' : '知',
        badgeClass: type === 'combo' ? 'combo' : type === 'do' ? 'do' : '',
        day: formatDay(String(s.created_at || '')),
      }
    })
    return
  }

  if (!id) return

  let found: ChildRow | null = null
  if (user.role === 'parent') {
    const kids = await listChildrenByParent(user.id)
    found = kids.find((c) => String(c.Id) === id) || null
  } else {
    const all = await listAllChildren(300)
    found = all.find((c) => String(c.Id) === id) || null
    if (!found && query?.card) {
      found = await findChildByCardNo(String(query.card))
    }
  }
  child.value = found
  if (!found) return

  if (!isParent.value && found.parent_id) {
    const prefs = await getUserPrefs(found.parent_id)
    if (!prefs.shareTeacher) {
      hiddenStats.value = true
      return
    }
  }

  const stamps = await listStampsByChild(found.Id)
  know.value = stamps.filter((s) => s.stamp_type !== 'combo').length
  combo.value = stamps.filter((s) => s.stamp_type === 'combo').length
  total.value = stamps.reduce((sum, s) => sum + (Number(s.value_num) || 0), 0)
  recent.value = stamps
    .filter((s) => withinDays(String(s.created_at || ''), 7))
    .slice(0, 8)
    .map((s) => {
      const type = String(s.stamp_type)
      return {
        subject: String(s.subject || '综合'),
        kindLabel:
          type === 'combo' ? '知行对章' : type === 'do' ? '行章' : '正向章',
        badge: type === 'combo' ? '对' : type === 'do' ? '行' : '知',
        badgeClass: type === 'combo' ? 'combo' : type === 'do' ? 'do' : '',
        day: formatDay(String(s.created_at || '')),
      }
    })
})

function goReport() {
  uni.switchTab({ url: '/pages/report/report' })
}
function goScan() {
  uni.switchTab({ url: '/pages/scan/scan' })
}
async function setCurrent() {
  if (!child.value || !child.value.Id) return
  await setCurrentChild(parentId.value, child.value.Id)
  uni.showToast({ title: '已设为当前查看', icon: 'success' })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f3f4f6;
  padding: 24rpx;
}
.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  margin-bottom: 16rpx;
}
.head {
  display: flex;
  align-items: center;
}
.av {
  width: 96rpx;
  height: 96rpx;
  border-radius: 24rpx;
  background: linear-gradient(145deg, #3b82f6, #1d4ed8);
  color: #fff;
  font-size: 40rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
}
.head-meta {
  flex: 1;
}
.name {
  display: block;
  font-size: 34rpx;
  font-weight: 700;
}
.sub {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #6b7280;
}
.title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 16rpx;
}
.li {
  display: block;
  font-size: 26rpx;
  color: #374151;
  line-height: 1.9;
}
.tip {
  display: block;
  font-size: 26rpx;
  color: #9ca3af;
  line-height: 1.55;
  padding: 8rpx 0;
}
.stats {
  display: flex;
  gap: 12rpx;
}
.stat {
  flex: 1;
  text-align: center;
  background: #eff6ff;
  border-radius: 16rpx;
  padding: 20rpx 8rpx;
}
.n {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: #2563eb;
}
.l {
  display: block;
  font-size: 22rpx;
  color: #9ca3af;
  margin-top: 6rpx;
}
.stamp {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18rpx 0;
  border-bottom: 1px solid #f3f4f6;
}
.stamp:last-child {
  border-bottom: none;
}
.stamp-l {
  display: flex;
  align-items: center;
  gap: 12rpx;
  flex: 1;
  min-width: 0;
}
.stamp-t {
  font-size: 26rpx;
  color: #111827;
}
.badge {
  font-size: 20rpx;
  padding: 2rpx 12rpx;
  border-radius: 999rpx;
  background: #dbeafe;
  color: #1d4ed8;
  font-weight: 600;
}
.badge.do {
  background: #fef3c7;
  color: #b45309;
}
.badge.combo {
  background: #d1fae5;
  color: #047857;
}
.stamp-d {
  font-size: 24rpx;
  color: #9ca3af;
}
.btn {
  background: #2563eb;
  color: #fff;
  border-radius: 14rpx;
  height: 88rpx;
  line-height: 88rpx;
  margin-bottom: 16rpx;
  font-size: 28rpx;
}
.btn.ghost {
  background: #fff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
}
.btn::after {
  border: none;
}
</style>
