<template>
  <view class="page">
    <view class="card head">
      <text class="h">{{ title }}</text>
      <text class="s">共 {{ filtered.length }} 人{{ classCode ? ` · 班级码 ${classCode}` : '' }}</text>
      <input
        class="search"
        placeholder="搜索学生姓名 / 记录卡"
        v-model="kw"
      />
      <view v-if="needClassFilter" class="filter">
        <input
          class="search grow"
          v-model="classCode"
          placeholder="班级码筛选（可选）"
        />
        <text class="btn-mini" @click="reload">查询</text>
      </view>
      <view class="seg">
        <text
          class="seg-item"
          :class="{ on: filterType === 'all' }"
          @click="filterType = 'all'"
          >全部</text
        >
        <text
          class="seg-item"
          :class="{ on: filterType === 'active' }"
          @click="filterType = 'active'"
          >有数据</text
        >
        <text
          class="seg-item"
          :class="{ on: filterType === 'hidden' }"
          @click="filterType = 'hidden'"
          >未授权</text
        >
      </view>
    </view>

    <view v-if="!filtered.length" class="empty">
      <text class="empty-title">暂无学生数据</text>
      <text class="empty-desc"
        >家长添加孩子并完成盖章后会出现在这里。可让家长填写班级码。</text
      >
      <text
        v-if="classCode"
        class="copy"
        @click="copyClassCode"
        >复制班级码 {{ classCode }}</text
      >
    </view>

    <view
      class="card row"
      v-for="s in filtered"
      :key="s.id"
      @click="goDetail(s)"
    >
      <view class="av" :class="{ muted: s.hidden }">{{ s.av }}</view>
      <view class="meta">
        <text class="n">{{ s.name }}</text>
        <text class="sub" v-if="s.hidden"
          >家长未授权查看当量 · {{ s.card || '-' }}</text
        >
        <text class="sub" v-else
          >知章 {{ s.know }} · 对章 {{ s.combo }} · {{ s.card || '-' }}</text
        >
      </view>
      <text class="zze" :class="{ hid: s.hidden }">{{
        s.hidden ? '—' : s.zze
      }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
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

interface Row {
  id: string
  av: string
  name: string
  know: number | string
  combo: number | string
  card: string
  zze: number | string
  hidden?: boolean
}

const kw = ref('')
const classCode = ref('')
const title = ref('学生管理')
const needClassFilter = ref(false)
const list = ref<Row[]>([])
const filterType = ref<'all' | 'active' | 'hidden'>('all')

const filtered = computed(() =>
  list.value.filter((s) => {
    const hitKw =
      !kw.value ||
      s.name.includes(kw.value) ||
      String(s.card || '').includes(kw.value)
    if (!hitKw) return false
    if (filterType.value === 'hidden') return !!s.hidden
    if (filterType.value === 'active') return !s.hidden
    return true
  }),
)

onLoad((query) => {
  if (query?.classCode) classCode.value = String(query.classCode)
})

onShow(() => {
  reload()
})

async function reload() {
  const user = requireLogin()
  if (!user) return
  if (String(user.id).startsWith('demo_')) {
    const { DEMO_CLASS_STUDENTS } = await import('@/constants/demoData')
    title.value =
      user.id === 'demo_school' ? '全校学生（演示）' : '学生管理（演示）'
    needClassFilter.value = true
    classCode.value = classCode.value || 'HA-G3-02'
    list.value = [
      ...DEMO_CLASS_STUDENTS.map((s) => ({ ...s, hidden: false as boolean })),
      {
        id: 'demo_hidden',
        av: '陈',
        name: '陈思雨',
        know: '—',
        combo: '—',
        card: 'CARD-022',
        zze: '—',
        hidden: true,
      },
    ]
    return
  }

  try {
    let children: ChildRow[] = []
    if (user.role === 'teacher') {
      title.value = `${user.name} · 学生`
      needClassFilter.value = true
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
    } else if (user.role === 'school' || user.id === 'demo_school') {
      title.value = '全校学生'
      needClassFilter.value = true
      children = classCode.value.trim()
        ? await listChildrenByClassCode(classCode.value)
        : await listAllChildren()
    } else {
      title.value = '我的孩子概览'
      needClassFilter.value = false
      const { listChildrenByParent } = await import('@/services/childRepo')
      children = await listChildrenByParent(user.id)
    }

    const isStaff = user.role === 'teacher' || user.role === 'school'
    const hiddenParents = isStaff
      ? await listHiddenParentIds(children.map((c) => c.parent_id))
      : new Set<string>()

    const rows: Row[] = []
    for (const c of children) {
      const hidden = isStaff && hiddenParents.has(String(c.parent_id))
      if (hidden) {
        rows.push({
          id: String(c.Id),
          av: c.avatar_text || c.name.slice(0, 1),
          name: c.name,
          know: '—',
          combo: '—',
          card: c.card_no,
          zze: '—',
          hidden: true,
        })
        continue
      }
      const stamps = await listStampsByChild(c.Id, 200)
      const know = stamps.filter((s) => s.stamp_type !== 'combo').length
      const combo = stamps.filter((s) => s.stamp_type === 'combo').length
      const zze = stamps.reduce((sum, s) => sum + (Number(s.value_num) || 0), 0)
      rows.push({
        id: String(c.Id),
        av: c.avatar_text || c.name.slice(0, 1),
        name: c.name,
        know,
        combo,
        card: c.card_no,
        zze,
      })
    }
    rows.sort((a, b) => {
      const az = typeof a.zze === 'number' ? a.zze : -1
      const bz = typeof b.zze === 'number' ? b.zze : -1
      return bz - az
    })
    list.value = rows
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  }
}

function goDetail(s: Row) {
  uni.navigateTo({
    url: `/pages/studentDetail/studentDetail?id=${s.id}&name=${encodeURIComponent(
      s.name,
    )}&hidden=${s.hidden ? '1' : '0'}&card=${encodeURIComponent(s.card || '')}`,
  })
}

function copyClassCode() {
  if (!classCode.value) return
  uni.setClipboardData({
    data: classCode.value,
    success: () => uni.showToast({ title: '已复制班级码', icon: 'success' }),
  })
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
.h {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
}
.s {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #6b7280;
}
.search {
  margin-top: 20rpx;
  height: 72rpx;
  background: #f3f4f6;
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 26rpx;
}
.filter {
  display: flex;
  gap: 12rpx;
  align-items: center;
  margin-top: 4rpx;
}
.filter .grow {
  flex: 1;
  margin-top: 12rpx;
}
.btn-mini {
  color: #2563eb;
  font-size: 26rpx;
  font-weight: 600;
  padding-top: 12rpx;
}
.seg {
  display: flex;
  gap: 12rpx;
  margin-top: 20rpx;
}
.seg-item {
  flex: 1;
  text-align: center;
  font-size: 24rpx;
  color: #6b7280;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12rpx;
  padding: 14rpx 0;
}
.seg-item.on {
  color: #2563eb;
  background: #eff6ff;
  border-color: #bfdbfe;
  font-weight: 600;
}
.empty {
  text-align: center;
  padding: 80rpx 32rpx;
}
.empty-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  color: #111827;
}
.empty-desc {
  display: block;
  margin-top: 12rpx;
  font-size: 26rpx;
  color: #9ca3af;
  line-height: 1.5;
}
.copy {
  display: inline-block;
  margin-top: 28rpx;
  color: #2563eb;
  font-size: 26rpx;
  font-weight: 600;
}
.row {
  display: flex;
  align-items: center;
}
.av {
  width: 84rpx;
  height: 84rpx;
  border-radius: 20rpx;
  background: linear-gradient(145deg, #3b82f6, #1d4ed8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  margin-right: 20rpx;
  font-size: 30rpx;
}
.av.muted {
  background: #9ca3af;
}
.meta {
  flex: 1;
  min-width: 0;
}
.n {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
}
.sub {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #9ca3af;
}
.zze {
  font-size: 28rpx;
  font-weight: 700;
  color: #2563eb;
}
.zze.hid {
  color: #9ca3af;
}
</style>
