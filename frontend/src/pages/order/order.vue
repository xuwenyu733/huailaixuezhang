<template>
  <view class="page">
    <view class="empty" v-if="!orders.length">
      <text class="t">暂无订单</text>
      <text class="d">上传支付凭证后，订单会显示在这里</text>
      <button class="btn" @click="goPay">去上传支付凭证</button>
    </view>
    <view class="card" v-for="o in orders" :key="String(o.Id)">
      <view class="row">
        <text class="name">{{ o.title }}</text>
        <text class="st">{{ statusText(o.status) }}</text>
      </view>
      <text class="sub">{{ o.pay_time || o.created_at }} · ¥{{ o.amount }}</text>
      <text class="sub" v-if="o.note">{{ o.note }}</text>
      <image
        v-if="o.voucher_url"
        class="voucher"
        :src="o.voucher_url"
        mode="aspectFit"
        @click="preview(o.voucher_url)"
      />
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { DEMO_ORDERS, isDemoId } from '@/constants/demoData'
import { requireLogin } from '@/services/auth'
import { listOrders, type OrderRow } from '@/services/orderRepo'

const orders = ref<OrderRow[]>([])

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  if (isDemoId(user.id)) {
    orders.value = DEMO_ORDERS.map((o) => ({ ...o }))
    return
  }
  try {
    orders.value = await listOrders(user.id)
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  }
})

function statusText(s: string) {
  if (s === 'paid') return '已开通'
  if (s === 'pending') return '待审核'
  return s || '已提交'
}
function goPay() {
  uni.navigateTo({ url: '/pages/payment/payment' })
}
function preview(url: string) {
  uni.previewImage({ urls: [url] })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.empty { padding: 120rpx 40rpx; text-align: center; }
.t { display: block; font-size: 32rpx; font-weight: 600; }
.d { display: block; margin: 16rpx 0 40rpx; font-size: 24rpx; color: #9ca3af; line-height: 1.6; }
.btn { background: #2563eb; color: #fff; border-radius: 14rpx; }
.btn::after { border: none; }
.card { background: #fff; border-radius: 16rpx; padding: 28rpx; margin-bottom: 16rpx; }
.row { display: flex; justify-content: space-between; }
.name { font-size: 28rpx; font-weight: 600; }
.st { color: #10b981; font-size: 24rpx; }
.sub { display: block; margin-top: 10rpx; font-size: 22rpx; color: #9ca3af; }
.voucher {
  margin-top: 16rpx; width: 100%; height: 220rpx; border-radius: 12rpx; background: #f3f4f6;
}
</style>
