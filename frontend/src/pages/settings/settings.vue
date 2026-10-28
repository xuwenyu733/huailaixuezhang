<template>
  <view class="page">
    <view class="menu">
      <view class="item" @click="go('/pages/profile/profile')">
        <text>个人资料</text><text class="arrow">›</text>
      </view>
      <view class="item" @click="go('/pages/password/password')">
        <text>修改登录密码</text><text class="arrow">›</text>
      </view>
      <view class="item" @click="go('/pages/notify/notify')">
        <text>消息通知设置</text><text class="arrow">›</text>
      </view>
      <view class="item" @click="go('/pages/privacy/privacy')">
        <text>隐私设置</text><text class="arrow">›</text>
      </view>
    </view>
    <view class="menu">
      <view class="item" @click="clearCache">
        <text>清除缓存</text><text class="sub">不含登录信息</text>
      </view>
      <view class="item" @click="go('/pages/legal/legal?type=agreement')">
        <text>用户协议</text><text class="arrow">›</text>
      </view>
      <view class="item" @click="go('/pages/legal/legal?type=privacy')">
        <text>隐私政策</text><text class="arrow">›</text>
      </view>
      <view class="item">
        <text>版本</text><text class="sub">v1.0.0</text>
      </view>
    </view>
    <button class="logout" @click="onLogout">退出登录</button>
  </view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { logout, requireLogin } from '@/services/auth'

onShow(() => {
  requireLogin()
})

function go(url: string) {
  uni.navigateTo({ url })
}
function clearCache() {
  const info = uni.getStorageInfoSync()
  const keep = new Set(['hlxz_session_user'])
  ;(info.keys || []).forEach((key) => {
    if (key.startsWith('hlxz_') && !keep.has(key)) uni.removeStorageSync(key)
  })
  uni.showToast({ title: '缓存已清理', icon: 'success' })
}
function onLogout() {
  uni.showModal({
    title: '退出登录',
    content: '确认退出当前账号？',
    success: (res) => {
      if (res.confirm) logout()
    },
  })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.menu { background: #fff; border-radius: 20rpx; margin-bottom: 20rpx; overflow: hidden; }
.item {
  display: flex; justify-content: space-between; padding: 32rpx 28rpx;
  border-bottom: 2rpx solid #f3f4f6; font-size: 28rpx;
}
.item:last-child { border-bottom: none; }
.arrow { color: #d1d5db; }
.sub { color: #9ca3af; font-size: 24rpx; }
.logout {
  background: #fff; color: #ef4444; border-radius: 16rpx; height: 88rpx; line-height: 88rpx;
}
.logout::after { border: none; }
</style>
