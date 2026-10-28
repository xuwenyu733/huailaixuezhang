<template>
  <view class="page">
    <view class="brand">
      <view class="logo" />
      <text class="name">淮安学长</text>
      <text class="ver">v1.0.0</text>
    </view>
    <view class="card">
      <text class="title">产品介绍</text>
      <text class="p">
        「淮安学长」是基于多模态实体标识技术的伴随式学生成长评价系统，通过「知章 - 行章 - 知行对章」三阶评价体系，实现教育评价数据的无感采集、智能分析与增值评价。
      </text>
    </view>
    <view class="card">
      <text class="title">专利信息</text>
      <text class="p">发明专利：《一种基于多模态实体标识的伴随式数据采集与增值评价方法及系统》</text>
      <text class="p">专利申请号：20261083365.5</text>
      <text class="p">专利权人：淮安市淮来学长文教科技发展有限公司</text>
    </view>
    <view class="card">
      <text class="li">官方公众号：淮来学长</text>
      <text class="li link" @click="call">客服电话：{{ phoneLabel }}</text>
      <text class="li">公司地址：江苏省淮安市</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SERVICE_PHONE } from '@/constants/goods'

const phoneLabel = computed(() => {
  const p = SERVICE_PHONE
  if (p.length === 10) return `${p.slice(0, 3)}-${p.slice(3, 6)}-${p.slice(6)}`
  if (p.length === 11) return `${p.slice(0, 3)}-${p.slice(3, 7)}-${p.slice(7)}`
  return p
})

function call() {
  uni.makePhoneCall({ phoneNumber: SERVICE_PHONE })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.brand { align-items: center; display: flex; flex-direction: column; padding: 48rpx 0; }
.logo {
  width: 120rpx; height: 120rpx; border: 10rpx solid #2563eb; transform: rotate(45deg);
  border-radius: 16rpx; margin-bottom: 36rpx;
}
.name { font-size: 40rpx; font-weight: 700; color: #111827; }
.ver { margin-top: 8rpx; font-size: 24rpx; color: #9ca3af; }
.card { background: #fff; border-radius: 20rpx; padding: 28rpx; margin-bottom: 16rpx; }
.title { display: block; font-size: 30rpx; font-weight: 600; margin-bottom: 12rpx; }
.p { display: block; font-size: 24rpx; color: #6b7280; line-height: 1.7; margin-bottom: 8rpx; }
.li { display: block; font-size: 26rpx; color: #374151; line-height: 1.9; }
.li.link { color: #2563eb; }
</style>
