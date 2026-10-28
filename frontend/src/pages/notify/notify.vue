<template>
  <view class="page">
    <view class="menu">
      <view class="item">
        <text>盖章通知</text>
        <switch :checked="form.stamp" color="#2563eb" @change="onSwitch('stamp', $event)" />
      </view>
      <view class="item">
        <text>报告更新</text>
        <switch :checked="form.report" color="#2563eb" @change="onSwitch('report', $event)" />
      </view>
      <view class="item">
        <text>会员与订单</text>
        <switch :checked="form.order" color="#2563eb" @change="onSwitch('order', $event)" />
      </view>
      <view class="item">
        <text>推荐积分</text>
        <switch :checked="form.referral" color="#2563eb" @change="onSwitch('referral', $event)" />
      </view>
    </view>
    <button class="btn" :loading="saving" @click="save">保存</button>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { requireLogin } from '@/services/auth'
import { getUserPrefs, saveUserPrefs } from '@/services/prefsRepo'

const saving = ref(false)
const form = reactive({ stamp: true, report: true, order: true, referral: true })
let ownerId = ''

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  ownerId = user.id
  const prefs = await getUserPrefs(user.id)
  form.stamp = prefs.notifyStamp
  form.report = prefs.notifyReport
  form.order = prefs.notifyOrder
  form.referral = prefs.notifyReferral
})

function onSwitch(key: 'stamp' | 'report' | 'order' | 'referral', e: any) {
  form[key] = !!(e?.detail?.value)
}

async function save() {
  if (!ownerId) return
  saving.value = true
  try {
    await saveUserPrefs(ownerId, {
      ...(await getUserPrefs(ownerId)),
      notifyStamp: form.stamp,
      notifyReport: form.report,
      notifyOrder: form.order,
      notifyReferral: form.referral,
    })
    uni.showToast({ title: '通知设置已保存', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '保存失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.menu { background: #fff; border-radius: 20rpx; overflow: hidden; }
.item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 28rpx; border-bottom: 2rpx solid #f3f4f6; font-size: 28rpx;
}
.item:last-child { border-bottom: none; }
.btn {
  margin-top: 32rpx; background: #2563eb; color: #fff; border-radius: 16rpx;
  height: 88rpx; line-height: 88rpx;
}
.btn::after { border: none; }
</style>
