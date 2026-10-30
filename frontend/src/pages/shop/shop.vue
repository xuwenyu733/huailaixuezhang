<template>
  <view class="page">
    <view class="hero" :style="{ background: goods.bg }">{{ goods.tag }}</view>
    <view class="card">
      <text class="name">{{ goods.name }}</text>
      <text class="sub">{{ goods.sub }}</text>
      <text class="price">¥{{ goods.price }}</text>
      <text class="desc">
        {{
          goods.kind === 'incentive'
            ? '激励商品：达成目标后到官网下单领取，官网负责发货与售后。'
            : '周边商品：统一在官网销售，价格与库存以官网为准。'
        }}
      </text>
      <view class="code-box">
        <text class="lab">购买编号</text>
        <text class="code">{{ buyCode }}</text>
      </view>
      <button class="btn" @click="goOfficial">到官网购买</button>
      <button class="btn ghost" :loading="loading" @click="buy">
        仅在程序内登记意向（不付款）
      </button>
      <text class="foot">小程序不收款、不发货，登记只用于家长自己核对清单</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { INCENTIVE_GOODS, SHOP_GOODS, officialUrlOf, type ShopGoods } from '@/constants/goods'
import { openOfficial } from '@/utils/official'
import { requireLogin } from '@/services/auth'
import { pushMessage } from '@/services/messageRepo'
import { createOrder } from '@/services/orderRepo'

const goods = ref<ShopGoods>(SHOP_GOODS[0])
const buyCode = ref('')
const loading = ref(false)

onLoad((q) => {
  const name = decodeURIComponent(String(q?.name || ''))
  const found = [...SHOP_GOODS, ...INCENTIVE_GOODS].find((g) => g.name === name)
  if (found) goods.value = found
  buyCode.value = `HL${Date.now().toString().slice(-8)}`
})

/** 官网购买：小程序不收款，统一跳官网 */
function goOfficial() {
  openOfficial(officialUrlOf(goods.value))
}

async function buy() {
  const user = requireLogin()
  if (!user) return
  if (String(user.id).startsWith('demo_')) {
    uni.showModal({
      title: '请使用正式账号',
      content: '当前是演示登录，订单不会写入数据库。请退出后用手机号登录再购买。',
      showCancel: false,
    })
    return
  }
  loading.value = true
  try {
    await createOrder({
      ownerId: user.id,
      title: goods.value.name,
      amount: goods.value.price,
      payType: goods.value.kind === 'incentive' ? '激励领取' : '周边购买',
      note: `购买编号 ${buyCode.value}`,
      status: 'pending',
    })
    await pushMessage({
      ownerId: user.id,
      title: '订单已登记',
      content: `${goods.value.name} ¥${goods.value.price}，编号 ${buyCode.value}`,
      category: 'order',
    })
    uni.showModal({
      title: '已记入订单',
      content: '可在「我的 - 我的订单」查看。如已线下付款，请上传支付凭证。',
      confirmText: '去看订单',
      success: (res) => {
        if (res.confirm) uni.navigateTo({ url: '/pages/order/order' })
        else uni.navigateBack()
      },
    })
  } catch (e: any) {
    uni.showToast({ title: e.message || '下单失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.hero {
  height: 280rpx; border-radius: 24rpx; display: flex; align-items: center;
  justify-content: center; font-size: 40rpx; font-weight: 700; color: #1f2937;
}
.card { margin-top: 20rpx; background: #fff; border-radius: 24rpx; padding: 32rpx; }
.name { display: block; font-size: 34rpx; font-weight: 700; }
.sub { display: block; margin-top: 8rpx; color: #6b7280; font-size: 24rpx; }
.price { display: block; margin-top: 16rpx; color: #ef4444; font-size: 40rpx; font-weight: 700; }
.desc { display: block; margin-top: 16rpx; font-size: 24rpx; color: #6b7280; line-height: 1.6; }
.code-box {
  margin-top: 24rpx; padding: 20rpx; background: #f9fafb; border-radius: 12rpx;
}
.lab { display: block; font-size: 22rpx; color: #9ca3af; }
.code { display: block; margin-top: 6rpx; font-size: 32rpx; font-weight: 700; letter-spacing: 2rpx; }
.btn {
  margin-top: 28rpx; background: #2563eb; color: #fff; border-radius: 14rpx;
  height: 88rpx; line-height: 88rpx;
}
.btn::after { border: none; }
.btn.ghost {
  margin-top: 16rpx; background: #eff6ff; color: #2563eb;
}
.foot {
  display: block; margin-top: 16rpx; font-size: 22rpx; color: #9ca3af; text-align: center;
}
</style>
