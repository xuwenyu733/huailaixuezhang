<template>
  <view class="page">
    <text class="tip">正在进入商城…</text>
  </view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { requireLogin } from '@/services/auth'
import { canAccessMall } from '@/services/mallGate'

/** 已取消独立密码：旧入口直接跳转商城 Tab */
onShow(() => {
  if (!requireLogin()) return
  if (!canAccessMall()) {
    uni.showToast({ title: '周边商城仅家长端可使用', icon: 'none' })
    setTimeout(() => uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/home/home' }) }), 400)
    return
  }
  uni.switchTab({ url: '/pages/mall/mall' })
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
}
.tip {
  font-size: 28rpx;
  color: #94a3b8;
}
</style>
