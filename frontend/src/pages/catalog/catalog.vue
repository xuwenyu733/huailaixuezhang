<template>
  <view class="page">
    <view class="note">商品统一在官网销售。点击任意商品将跳转官网，小程序内不承接下单与支付。</view>
    <view class="goods" v-for="g in list" :key="g.name" @click="open(g)">
      <view class="img" :style="{ background: g.bg }">{{ g.tag }}</view>
      <view class="meta">
        <text class="name">{{ g.name }}</text>
        <text class="sub">{{ g.sub }}</text>
        <view class="row">
          <text class="price">¥{{ g.price }}</text>
          <text class="go">去官网 ›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { INCENTIVE_GOODS, SHOP_GOODS, officialUrlOf, type ShopGoods } from '@/constants/goods'
import { openOfficial } from '@/utils/official'

const kind = ref('shop')
const list = computed(() => (kind.value === 'incentive' ? INCENTIVE_GOODS : SHOP_GOODS))

onLoad((q) => {
  kind.value = String(q?.kind || 'shop')
  uni.setNavigationBarTitle({
    title: kind.value === 'incentive' ? '激励商品' : '周边商品',
  })
})

function open(g: ShopGoods) {
  openOfficial(officialUrlOf(g))
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
.row { display: flex; align-items: center; justify-content: space-between; margin-top: 12rpx; }
.price { color: #ef4444; font-weight: 700; }
.go { font-size: 22rpx; color: #2563eb; }
.note {
  background: #eff6ff; color: #1d4ed8; font-size: 22rpx; line-height: 1.7;
  padding: 18rpx 20rpx; border-radius: 12rpx; margin-bottom: 16rpx;
}
</style>
