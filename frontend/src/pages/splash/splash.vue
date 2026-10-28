<template>
  <view class="splash">
    <view class="logo-wrap">
      <view class="logo" />
    </view>
    <text class="name">淮安学长</text>
    <text class="slogan">多模态伴随式成长评价系统</text>
    <text class="patent">专利号：20261083365.5</text>
  </view>
</template>

<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { getCurrentUser } from '@/services/auth'

onLoad(() => {
  setTimeout(() => {
    try {
      if (getCurrentUser()) {
        uni.switchTab({ url: '/pages/home/home' })
        return
      }
    } catch (e) {
      console.warn('[splash] session', e)
    }
    uni.reLaunch({ url: '/pages/login/login' })
  }, 1600)
})
</script>

<style scoped>
.splash {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
}
.logo-wrap {
  width: 140rpx;
  height: 140rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 32rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 40rpx;
}
.logo {
  width: 72rpx;
  height: 72rpx;
  border: 8rpx solid #fff;
  transform: rotate(45deg);
  border-radius: 8rpx;
}
.name {
  color: #fff;
  font-size: 52rpx;
  font-weight: 700;
  letter-spacing: 6rpx;
}
.slogan {
  margin-top: 16rpx;
  color: rgba(255, 255, 255, 0.85);
  font-size: 26rpx;
}
.patent {
  position: absolute;
  bottom: 80rpx;
  color: rgba(255, 255, 255, 0.55);
  font-size: 22rpx;
}
</style>
