<template>
  <view class="page">
    <view class="goods" v-for="g in list" :key="g.name" @click="open(g.name)">
      <view class="img" :style="{ background: g.bg }">{{ g.tag }}</view>
      <view class="meta">
        <text class="name">{{ g.name }}</text>
        <text class="sub">{{ g.sub }}</text>
        <text class="price">¥{{ g.price }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { INCENTIVE_GOODS, SHOP_GOODS } from '@/constants/goods'

const kind = ref('shop')
const list = computed(() => (kind.value === 'incentive' ? INCENTIVE_GOODS : SHOP_GOODS))

onLoad((q) => {
  kind.value = String(q?.kind || 'shop')
  uni.setNavigationBarTitle({
    title: kind.value === 'incentive' ? '激励商品' : '周边商品',
  })
})

function open(name: string) {
  uni.navigateTo({ url: `/pages/shop/shop?name=${encodeURIComponent(name)}` })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.goods {
  display: flex; background: #fff; border-radius: 16rpx; padding: 20rpx; margin-bottom: 16rpx;
}
.img {
  width: 140rpx; height: 140rpx; border-radius: 12rpx; display: flex;
  align-items: center; justify-content: center; font-weight: 600; margin-right: 20rpx;
}
.meta { flex: 1; }
.name { display: block; font-size: 28rpx; font-weight: 600; }
.sub { display: block; margin-top: 8rpx; font-size: 22rpx; color: #9ca3af; }
.price { display: block; margin-top: 12rpx; color: #ef4444; font-weight: 700; }
</style>
