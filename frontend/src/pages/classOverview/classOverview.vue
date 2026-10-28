<template>
  <view class="page">
    <view class="hero">
      <text class="hero-title">班级概览</text>
      <text class="hero-sub">{{ schoolLabel }}</text>
    </view>

    <view class="body">
      <view class="card">
        <view class="stats">
          <view class="stat">
            <text class="n">{{ stats.count }}</text>
            <text class="l">本班学生</text>
          </view>
          <view class="stat">
            <text class="n">{{ stats.weekStamps }}</text>
            <text class="l">本周盖章</text>
          </view>
          <view class="stat">
            <text class="n">{{ stats.attention }}</text>
            <text class="l">待关注</text>
          </view>
        </view>
      </view>

      <view class="card">
        <text class="h">待关注</text>
        <view v-if="!attentionList.length" class="empty-sm">暂无待关注项</view>
        <view
          v-for="item in attentionList"
          :key="item.id"
          class="attn"
          @click="goDetail(item)"
        >
          <view class="dot" />
          <view class="attn-meta">
            <text class="t">{{ item.title }}</text>
            <text class="d">{{ item.desc }}</text>
          </view>
        </view>
      </view>

      <button class="btn" @click="goList">进入学生列表</button>
      <button class="btn ghost" @click="goScan">去采集盖章</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { requireLogin } from '@/services/auth'
import {
  listAllChildren,
  listChildrenByClassCode,
} from '@/services/childRepo'
import { listHiddenParentIds } from '@/services/prefsRepo'
import {
  listStampsByChild,
  listStampsByTeacherStamp,
} from '@/services/stampRepo'
import type { ChildRow } from '@/types/user'

interface Attn {
  id: string
  title: string
  desc: string
  card?: string
}

const classCode = ref('HA-G3-02')
const schoolLabel = ref('淮安实验小学')
const stats = ref({ count: 0, weekStamps: 0, attention: 0 })
const attentionList = ref<Attn[]>([])

const defaultClass = computed(() => classCode.value || 'HA-G3-02')

onShow(() => {
  reload()
})

function withinDays(iso: string, days: number) {
  if (!iso) return false
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return false
  return Date.now() - t <= days * 86400000
}

async function reload() {
  const user = requireLogin()
  if (!user) return

  if (String(user.id).startsWith('demo_')) {
    const { DEMO_CLASS_STUDENTS } = await import('@/constants/demoData')
    schoolLabel.value =
      user.id === 'demo_school'
        ? '全校 · 演示'
        : `演示班级 · ${defaultClass.value}`
    classCode.value = classCode.value || 'HA-G3-02'
    const list = DEMO_CLASS_STUDENTS
    stats.value = {
      count: list.length,
      weekStamps: 86,
      attention: 3,
    }
    attentionList.value = [
      {
        id: list[3]?.id || 'a1',
        title: `${list[3]?.name || '学生'} · 近 7 日盖章偏少`,
        desc: `记录卡 ${list[3]?.card || '-'}`,
        card: list[3]?.card,
      },
      {
        id: 'hidden_demo',
        title: '陈思雨 · 家长未授权当量',
        desc: '仅可查看档案，不可看 ZZE',
      },
      {
        id: list[0]?.id || 'a2',
        title: `${list[0]?.name || '学生'} · 行章偏少`,
        desc: `知章 ${list[0]?.know || 0} · 对章 ${list[0]?.combo || 0}`,
        card: list[0]?.card,
      },
    ]
    return
  }

  try {
    let children: ChildRow[] = []
    if (user.role === 'teacher') {
      schoolLabel.value = `${user.name} · ${defaultClass.value}`
      if (classCode.value.trim()) {
        children = await listChildrenByClassCode(classCode.value)
      } else {
        const stamps = await listStampsByTeacherStamp(
          user.stampNo || user.inviteCode,
          300,
        )
        const map = new Map<string, ChildRow>()
        stamps.forEach((s) => {
          if (!s.child_id) return
          const id = String(s.child_id)
          if (!map.has(id)) {
            map.set(id, {
              Id: s.child_id,
              parent_id: 0,
              name: s.child_name,
              avatar_text: (s.child_name || '学').slice(0, 1),
              student_no: '',
              school: '',
              class_name: '',
              class_code: '',
              card_no: s.card_no,
              tag: '',
              is_current: 0,
              created_at: '',
            })
          }
        })
        children = [...map.values()]
      }
    } else {
      schoolLabel.value = `全校 · ${classCode.value || '未筛选'}`
      children = classCode.value.trim()
        ? await listChildrenByClassCode(classCode.value)
        : await listAllChildren()
    }

    const hiddenParents = await listHiddenParentIds(
      children.map((c) => c.parent_id),
    )
    const attn: Attn[] = []
    let week = 0

    for (const c of children) {
      const hidden = hiddenParents.has(String(c.parent_id))
      if (hidden) {
        attn.push({
          id: String(c.Id),
          title: `${c.name} · 家长未授权当量`,
          desc: `记录卡 ${c.card_no || '-'}`,
          card: c.card_no,
        })
        continue
      }
      const stamps = await listStampsByChild(c.Id, 200)
      week += stamps.filter((s) => withinDays(String(s.created_at || ''), 7)).length
      const recent = stamps.filter((s) =>
        withinDays(String(s.created_at || ''), 7),
      )
      const know = stamps.filter((s) => s.stamp_type !== 'combo').length
      const combo = stamps.filter((s) => s.stamp_type === 'combo').length
      if (recent.length === 0) {
        attn.push({
          id: String(c.Id),
          title: `${c.name} · 近 7 日无盖章`,
          desc: `记录卡 ${c.card_no || '-'}`,
          card: c.card_no,
        })
      } else if (know >= 8 && combo <= 1) {
        attn.push({
          id: String(c.Id),
          title: `${c.name} · 行章偏少`,
          desc: `知章 ${know} · 对章 ${combo}`,
          card: c.card_no,
        })
      }
    }

    stats.value = {
      count: children.length,
      weekStamps: week,
      attention: attn.length,
    }
    attentionList.value = attn.slice(0, 8)
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  }
}

function goList() {
  const q = classCode.value
    ? `?classCode=${encodeURIComponent(classCode.value)}`
    : ''
  uni.navigateTo({ url: `/pages/studentManage/studentManage${q}` })
}
function goScan() {
  uni.switchTab({ url: '/pages/scan/scan' })
}
function goDetail(item: Attn) {
  if (item.id === 'hidden_demo') {
    uni.navigateTo({
      url: `/pages/studentDetail/studentDetail?name=${encodeURIComponent('陈思雨')}&hidden=1`,
    })
    return
  }
  uni.navigateTo({
    url: `/pages/studentDetail/studentDetail?id=${item.id}&name=${encodeURIComponent(
      item.title.split(' · ')[0] || '学生',
    )}`,
  })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f3f4f6;
}
.hero {
  background: #2563eb;
  padding: 28rpx 32rpx 40rpx;
  color: #fff;
}
.hero-title {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
}
.hero-sub {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  opacity: 0.88;
}
.body {
  padding: 24rpx;
  margin-top: -12rpx;
}
.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
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
  font-size: 40rpx;
  font-weight: 700;
  color: #2563eb;
}
.l {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #6b7280;
}
.h {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  margin-bottom: 16rpx;
}
.attn {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 18rpx 0;
  border-bottom: 1px solid #f3f4f6;
}
.attn:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  background: #f59e0b;
  margin-top: 12rpx;
  flex-shrink: 0;
}
.attn-meta {
  flex: 1;
}
.t {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
}
.d {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #9ca3af;
}
.empty-sm {
  color: #9ca3af;
  font-size: 26rpx;
  padding: 12rpx 0;
}
.btn {
  background: #2563eb;
  color: #fff;
  border-radius: 16rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 30rpx;
  margin-bottom: 16rpx;
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
