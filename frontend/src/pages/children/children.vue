<template>
  <view class="page">
    <view class="top">
      <text class="add" @click="openAdd">+ 添加</text>
    </view>
    <view v-if="!kids.length" class="empty">暂无孩子，请先添加（最多 2 个）</view>
    <view
      class="card"
      v-for="c in kids"
      :key="String(c.Id)"
      @click="onSelect(c)"
      @longpress="setCurrent(c)"
    >
      <view class="av">{{ c.avatar_text || c.name.slice(0, 1) }}</view>
      <view class="meta">
        <view class="row">
          <text class="name">{{ c.name }}</text>
          <text class="tag" v-if="Number(c.is_current) === 1">当前</text>
        </view>
        <text class="sub">{{ c.class_name || '未填班级' }} · {{ c.card_no }}</text>
        <text class="sub">标签 {{ c.tag || '-' }} · {{ c.school || '未填学校' }}</text>
      </view>
      <text class="del" @click.stop="onDelete(c)">删除</text>
    </view>
    <view class="tips">
      <text>• 记录卡编号全局唯一</text>
      <text>• 通过班级码绑定班级</text>
      <text>• 每个账号最多绑定 2 个孩子</text>
      <text>• 长按可设为当前孩子（盖章默认使用）</text>
    </view>

    <view class="mask" v-if="showAdd" @click="showAdd = false" />
    <view class="modal" v-if="showAdd">
      <text class="mt">添加孩子</text>
      <input v-model="form.name" class="inp" placeholder="学生姓名" />
      <input v-model="form.no" class="inp" placeholder="学号" />
      <input v-model="form.school" class="inp" placeholder="所在学校" />
      <input v-model="form.className" class="inp" placeholder="班级，如 三年级(2)班" />
      <input v-model="form.classCode" class="inp" placeholder="班级码" />
      <input v-model="form.card" class="inp" placeholder="记录卡编号" />
      <button class="btn" :loading="loading" @click="submit">确认添加</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { DEMO_CHILDREN, isDemoId } from '@/constants/demoData'
import { requireLogin } from '@/services/auth'
import {
  addChild,
  listChildrenByParent,
  setCurrentChild,
  softDeleteChild,
} from '@/services/childRepo'
import type { ChildRow } from '@/types/user'

const showAdd = ref(false)
const loading = ref(false)
const kids = ref<ChildRow[]>([])
const parentId = ref('')
const form = reactive({
  name: '',
  no: '',
  school: '',
  className: '',
  classCode: '',
  card: '',
})

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  parentId.value = user.id
  await reload()
})

async function reload() {
  if (!parentId.value) {
    kids.value = []
    return
  }
  if (isDemoId(parentId.value)) {
    kids.value = DEMO_CHILDREN.map((c) => ({ ...c }))
    return
  }
  try {
    kids.value = await listChildrenByParent(parentId.value)
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  }
}

function openAdd() {
  if (String(parentId.value).startsWith('demo_')) {
    uni.showToast({ title: '演示账号请用正式账号', icon: 'none' })
    return
  }
  showAdd.value = true
}

async function submit() {
  loading.value = true
  try {
    await addChild({
      parentId: parentId.value,
      name: form.name,
      studentNo: form.no,
      school: form.school,
      className: form.className,
      classCode: form.classCode,
      cardNo: form.card,
    })
    form.name = ''
    form.no = ''
    form.school = ''
    form.className = ''
    form.classCode = ''
    form.card = ''
    showAdd.value = false
    await reload()
    uni.showToast({ title: '添加成功', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '添加失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function setCurrent(c: ChildRow) {
  try {
    await setCurrentChild(parentId.value, c.Id)
    await reload()
    uni.showToast({ title: `已切换为 ${c.name}`, icon: 'none' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '切换失败', icon: 'none' })
  }
}

function onSelect(c: ChildRow) {
  uni.navigateTo({
    url: `/pages/studentDetail/studentDetail?id=${c.Id}&name=${encodeURIComponent(c.name)}`,
  })
}

function onDelete(c: ChildRow) {
  uni.showModal({
    title: '删除孩子',
    content: `确认删除 ${c.name}？历史盖章仍保留。`,
    success: async (res) => {
      if (!res.confirm) return
      try {
        await softDeleteChild(parentId.value, c.Id)
        await reload()
        uni.showToast({ title: '已删除', icon: 'none' })
      } catch (e: any) {
        uni.showToast({ title: e.message || '删除失败', icon: 'none' })
      }
    },
  })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.top { display: flex; justify-content: flex-end; margin-bottom: 12rpx; }
.add { color: #2563eb; font-size: 28rpx; font-weight: 600; }
.empty { text-align: center; color: #9ca3af; padding: 80rpx 0; font-size: 26rpx; }
.card {
  background: #fff; border-radius: 20rpx; padding: 28rpx; margin-bottom: 16rpx;
  display: flex; align-items: center;
}
.av {
  width: 88rpx; height: 88rpx; border-radius: 50%; background: #dbeafe; color: #2563eb;
  font-weight: 700; display: flex; align-items: center; justify-content: center; margin-right: 20rpx;
}
.row { display: flex; align-items: center; gap: 12rpx; }
.name { font-size: 30rpx; font-weight: 600; }
.tag { background: #eff6ff; color: #2563eb; font-size: 20rpx; padding: 4rpx 12rpx; border-radius: 999rpx; }
.sub { display: block; margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }
.del { color: #ef4444; font-size: 24rpx; padding: 12rpx; }
.tips text { display: block; font-size: 22rpx; color: #9ca3af; line-height: 1.8; margin-top: 8rpx; }
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 90; }
.modal {
  position: fixed; left: 0; right: 0; bottom: 0; background: #fff; z-index: 100;
  border-radius: 28rpx 28rpx 0 0; padding: 36rpx;
}
.mt { display: block; font-size: 32rpx; font-weight: 700; margin-bottom: 24rpx; }
.inp {
  height: 84rpx; background: #f9fafb; border: 2rpx solid #e5e7eb; border-radius: 14rpx;
  padding: 0 24rpx; margin-bottom: 16rpx; font-size: 28rpx;
}
.btn { background: #2563eb; color: #fff; border-radius: 14rpx; height: 88rpx; line-height: 88rpx; }
.btn::after { border: none; }
</style>
