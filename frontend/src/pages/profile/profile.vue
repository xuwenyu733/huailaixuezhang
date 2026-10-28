<template>
  <view class="page">
    <view class="card">
      <view class="avatar">{{ form.avatar }}</view>
      <view class="field">
        <text class="label">姓名</text>
        <input v-model="form.name" class="input" maxlength="20" placeholder="家长姓名" />
      </view>
      <view class="field">
        <text class="label">手机号</text>
        <text class="readonly">{{ maskedPhone }}</text>
        <text class="hint">手机号暂不支持自行修改</text>
      </view>
      <view class="field">
        <text class="label">推荐码</text>
        <text class="readonly">{{ form.inviteCode || '-' }}</text>
      </view>
      <button class="btn" :loading="loading" @click="onSave">保存修改</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { requireLogin, updateParentProfile } from '@/services/auth'
import { displayPhone } from '@/utils/security'

const loading = ref(false)
const form = reactive({
  name: '',
  avatar: '',
  inviteCode: '',
  phone: '',
})

const maskedPhone = computed(() => displayPhone(form.phone))

onShow(() => {
  const user = requireLogin()
  if (!user) return
  form.name = user.name
  form.avatar = user.avatarText || user.name.slice(0, 1)
  form.inviteCode = user.inviteCode
  form.phone = user.phone
})

async function onSave() {
  loading.value = true
  try {
    const user = await updateParentProfile({ name: form.name })
    form.avatar = user.avatarText
    uni.showToast({ title: '已保存', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '保存失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.card {
  background: #fff; border-radius: 20rpx; padding: 40rpx 32rpx;
  display: flex; flex-direction: column; align-items: stretch;
}
.avatar {
  width: 120rpx; height: 120rpx; border-radius: 50%; margin: 0 auto 36rpx;
  background: #2563eb; color: #fff; display: flex; align-items: center;
  justify-content: center; font-size: 48rpx; font-weight: 700;
}
.field { margin-bottom: 28rpx; }
.label { display: block; font-size: 26rpx; color: #6b7280; margin-bottom: 12rpx; }
.input {
  height: 88rpx; padding: 0 24rpx; background: #f9fafb;
  border: 2rpx solid #e5e7eb; border-radius: 16rpx; font-size: 28rpx;
}
.readonly { display: block; font-size: 30rpx; color: #111827; }
.hint { display: block; margin-top: 8rpx; font-size: 22rpx; color: #9ca3af; }
.btn {
  margin-top: 12rpx; height: 88rpx; line-height: 88rpx;
  background: #2563eb; color: #fff; border-radius: 16rpx; font-size: 30rpx;
}
.btn::after { border: none; }
</style>
