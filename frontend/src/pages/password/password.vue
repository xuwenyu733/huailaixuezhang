<template>
  <view class="page">
    <view class="card">
      <text class="tip">密码需同时包含字母和数字，长度 6–32 位。修改后请妥善保管，不要告知他人。</text>
      <view class="field">
        <text class="label">当前密码</text>
        <input v-model="oldPassword" class="input" password placeholder="请输入当前密码" />
      </view>
      <view class="field">
        <text class="label">新密码</text>
        <input v-model="newPassword" class="input" password placeholder="字母+数字，至少 6 位" />
      </view>
      <view class="field">
        <text class="label">确认新密码</text>
        <input v-model="newPassword2" class="input" password placeholder="再次输入新密码" />
      </view>
      <button class="btn" :loading="loading" @click="onSubmit">确认修改</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { changeParentPassword, logout, requireLogin } from '@/services/auth'

const oldPassword = ref('')
const newPassword = ref('')
const newPassword2 = ref('')
const loading = ref(false)

onShow(() => {
  requireLogin()
})

async function onSubmit() {
  if (newPassword.value !== newPassword2.value) {
    uni.showToast({ title: '两次新密码不一致', icon: 'none' })
    return
  }
  loading.value = true
  try {
    await changeParentPassword({
      oldPassword: oldPassword.value,
      newPassword: newPassword.value,
    })
    uni.showModal({
      title: '修改成功',
      content: '请使用新密码重新登录',
      showCancel: false,
      success: () => logout(),
    })
  } catch (e: any) {
    uni.showToast({ title: e.message || '修改失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.card { background: #fff; border-radius: 20rpx; padding: 36rpx 32rpx; }
.tip {
  display: block; font-size: 24rpx; color: #6b7280; line-height: 1.6;
  margin-bottom: 28rpx; padding: 20rpx; background: #eff6ff; border-radius: 12rpx;
}
.field { margin-bottom: 24rpx; }
.label { display: block; font-size: 26rpx; color: #374151; margin-bottom: 12rpx; }
.input {
  height: 88rpx; padding: 0 24rpx; background: #f9fafb;
  border: 2rpx solid #e5e7eb; border-radius: 16rpx; font-size: 28rpx;
}
.btn {
  margin-top: 8rpx; height: 88rpx; line-height: 88rpx;
  background: #2563eb; color: #fff; border-radius: 16rpx; font-size: 30rpx;
}
.btn::after { border: none; }
</style>
