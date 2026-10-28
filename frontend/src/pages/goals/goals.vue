<template>
  <view class="page">
    <view class="top"><text class="add" @click="show = true">+ 制定目标</text></view>
    <view v-if="!list.length" class="empty">还没有激励目标。为孩子设一个当量目标，盖章后自动累加。</view>
    <view class="card" v-for="g in list" :key="String(g.Id)">
      <view class="row">
        <text class="title">{{ g.title }}</text>
        <text :class="['st', g.status]">{{ statusText(g.status) }}</text>
      </view>
      <text class="sub">{{ g.child_name || '未指定孩子' }} · 奖励 {{ g.reward_name }} {{ g.reward_price ? '¥' + g.reward_price : '' }}</text>
      <view class="bar">
        <view class="fill" :style="{ width: pct(g) + '%' }" />
      </view>
      <view class="row">
        <text class="sub">{{ g.current_points }} / {{ g.target_points }}</text>
        <text v-if="g.status === 'active'" class="cancel" @click="onCancel(g)">取消</text>
      </view>
    </view>

    <view class="mask" v-if="show" @click="show = false" />
    <view class="modal" v-if="show">
      <text class="mt">制定激励目标</text>
      <input class="inp" v-model="form.title" placeholder="目标标题，如 本月课堂积极" />
      <input class="inp" v-model="form.rewardName" placeholder="奖励商品" />
      <input class="inp" v-model="form.rewardPrice" placeholder="参考价格（选填）" />
      <input class="inp" v-model="form.target" type="number" placeholder="目标当量，如 30" />
      <button class="btn" :loading="loading" @click="submit">保存目标</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { DEMO_GOALS, getDemoCurrentChild, isDemoId } from '@/constants/demoData'
import { requireLogin } from '@/services/auth'
import { getCurrentChild } from '@/services/childRepo'
import { cancelGoal, createGoal, listGoalsByParent, type GoalRow } from '@/services/goalRepo'

const list = ref<GoalRow[]>([])
const show = ref(false)
const loading = ref(false)
const parentId = ref('')
const childId = ref<string | number>(0)
const childName = ref('')
const form = reactive({ title: '', rewardName: '', rewardPrice: '', target: '' })

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  if (user.role === 'teacher') {
    uni.showToast({ title: '激励目标由家长制定', icon: 'none' })
    return
  }
  parentId.value = user.id
  if (isDemoId(user.id)) {
    const child = getDemoCurrentChild()
    childId.value = child.Id
    childName.value = child.name
    list.value = DEMO_GOALS.map((g) => ({ ...g }))
    return
  }
  const child = await getCurrentChild(user.id).catch(() => null)
  childId.value = child?.Id || 0
  childName.value = child?.name || ''
  list.value = await listGoalsByParent(user.id)
})

function pct(g: GoalRow) {
  const t = Number(g.target_points) || 1
  return Math.min(100, Math.round((Number(g.current_points) / t) * 100))
}
function statusText(s: string) {
  if (s === 'done') return '已达成'
  if (s === 'cancel') return '已取消'
  return '进行中'
}

async function submit() {
  loading.value = true
  try {
    await createGoal({
      parentId: parentId.value,
      childId: childId.value,
      childName: childName.value,
      title: form.title,
      rewardName: form.rewardName,
      rewardPrice: form.rewardPrice,
      targetPoints: Number(form.target),
    })
    form.title = ''
    form.rewardName = ''
    form.rewardPrice = ''
    form.target = ''
    show.value = false
    list.value = await listGoalsByParent(parentId.value)
    uni.showToast({ title: '已创建', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '创建失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function onCancel(g: GoalRow) {
  await cancelGoal(g.Id)
  list.value = await listGoalsByParent(parentId.value)
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.top { display: flex; justify-content: flex-end; margin-bottom: 12rpx; }
.add { color: #2563eb; font-weight: 600; }
.empty { color: #9ca3af; font-size: 26rpx; padding: 48rpx 12rpx; line-height: 1.6; }
.card { background: #fff; border-radius: 20rpx; padding: 28rpx; margin-bottom: 16rpx; }
.row { display: flex; justify-content: space-between; align-items: center; }
.title { font-size: 30rpx; font-weight: 600; }
.sub { display: block; margin: 10rpx 0; font-size: 22rpx; color: #9ca3af; }
.st { font-size: 22rpx; }
.st.active { color: #2563eb; }
.st.done { color: #10b981; }
.st.cancel { color: #9ca3af; }
.bar { height: 12rpx; background: #f3f4f6; border-radius: 999rpx; overflow: hidden; }
.fill { height: 100%; background: #2563eb; }
.cancel { color: #ef4444; font-size: 24rpx; }
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 90; }
.modal {
  position: fixed; left: 0; right: 0; bottom: 0; background: #fff; z-index: 100;
  border-radius: 28rpx 28rpx 0 0; padding: 36rpx;
}
.mt { display: block; font-size: 32rpx; font-weight: 700; margin-bottom: 20rpx; }
.inp {
  height: 84rpx; background: #f9fafb; border: 2rpx solid #e5e7eb; border-radius: 14rpx;
  padding: 0 24rpx; margin-bottom: 16rpx;
}
.btn { background: #2563eb; color: #fff; height: 88rpx; line-height: 88rpx; border-radius: 14rpx; }
.btn::after { border: none; }
</style>
