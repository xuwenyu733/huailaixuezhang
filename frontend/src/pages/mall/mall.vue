<template>
  <view class="page">
    <view class="note">
      教师端初期不收费，家长端有 3 个月试用期。本模块不对学生开放。
    </view>

    <view class="vip card">
      <view class="vip-top">
        <text class="vip-title">小程序年度会员</text>
        <text class="vip-tag">{{ vipTag }}</text>
      </view>
      <text class="vip-sub">{{ vipSub }}</text>
      <text class="vip-desc">支持完整报告导出 · 无限次识别 · 定制化维度 · 专属客服</text>
      <view class="vip-actions" v-if="!isDemo">
        <button class="vip-btn" size="mini" :loading="busy" @click="onSimulatePay">
          模拟开通会员
        </button>
        <button
          class="vip-btn ghost"
          size="mini"
          :disabled="points < rewardPoints"
          :loading="busy"
          @click="onRedeem"
        >
          {{ rewardPoints }} 积分抵扣年费
        </button>
      </view>
    </view>

    <view class="card points">
      <view>
        <text class="p-num">{{ points }}</text>
        <text class="p-lab">我的积分</text>
      </view>
      <view class="p-right">
        <text class="code">{{ inviteCode || '—' }}</text>
        <text class="p-lab">我的推荐码</text>
        <text class="link" @click="goReferral">去邀请</text>
      </view>
    </view>
    <text class="tip">被推荐人注册并缴费后，您可获得 {{ rewardPoints }} 积分，可抵扣年费</text>

    <view class="card">
      <view class="row-between">
        <text class="title">热门商品</text>
        <text class="link" @click="goCatalog('shop')">查看全部</text>
      </view>
      <text class="tip mb">商品统一在官网销售，点击即跳转官网，小程序内不承接下单</text>
      <view class="grid">
        <view class="goods" v-for="g in goods" :key="g.name" @click="onGoods(g)">
          <view class="g-img" :style="{ background: g.bg }">{{ g.tag }}</view>
          <text class="g-name">{{ g.name }}</text>
          <text class="g-sub">{{ g.sub }}</text>
          <text class="g-price">¥{{ g.price }}</text>
        </view>
      </view>
    </view>

    <view class="card" v-if="role === 'family'">
      <view class="row-between">
        <text class="title">激励商城</text>
        <text class="link" @click="goCatalog('incentive')">查看全部</text>
      </view>
      <text class="tip mb">仅对家长端开放 · 完成任务后作为奖励下单</text>
      <view class="grid">
        <view class="goods" v-for="g in incentives" :key="g.name" @click="onGoods(g)">
          <view class="g-img" :style="{ background: g.bg }">{{ g.tag }}</view>
          <text class="g-name">{{ g.name }}</text>
          <text class="g-sub">{{ g.sub }}</text>
          <text class="g-price">¥{{ g.price }}</text>
        </view>
      </view>
      <text class="link center" @click="onIncentive">查看已制定的激励</text>
    </view>

    <view class="card pay">
      <text class="title">线下支付通道</text>
      <view class="qr">收款二维码</view>
      <text class="tip">扫码支付后上传凭证，后台审核开通</text>
      <button class="btn" @click="goPayment">上传支付凭证</button>
    </view>

    <AppTabBar />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import {
  REFERRAL_REWARD_POINTS,
  refreshCurrentUser,
  requireLogin,
} from '@/services/auth'
import { requireMallAccess } from '@/services/mallGate'
import {
  markInviteePaidAndReward,
  redeemPointsForMembership,
} from '@/services/referral'
import { useDemoStore } from '@/stores/demo'
import { INCENTIVE_GOODS, SHOP_GOODS, officialUrlOf } from '@/constants/goods'
import { openOfficial } from '@/utils/official'
import { formatShortDate } from '@/utils/security'
import type { SessionUser } from '@/types/user'

const store = useDemoStore()
const role = computed(() => store.role)
const rewardPoints = REFERRAL_REWARD_POINTS
const busy = ref(false)
const session = ref<SessionUser | null>(null)

const isDemo = computed(() => String(session.value?.id || '').startsWith('demo_'))
const points = computed(() => Number(session.value?.points) || 0)
const inviteCode = computed(() => session.value?.inviteCode || '')
const vipTag = computed(() => {
  const s = session.value?.membershipStatus
  if (s === 'active') return '已开通'
  if (s === 'trial') return '试用中'
  if (s === 'expired') return '已过期'
  return '未开通'
})
const vipSub = computed(() => {
  const u = session.value
  if (!u) return '登录后查看会员状态'
  if (u.membershipStatus === 'active') {
    return `有效期至 ${formatShortDate(u.membershipExpireAt)}`
  }
  if (u.membershipStatus === 'trial') {
    return `试用期至 ${formatShortDate(u.membershipExpireAt)}（注册起 90 天）`
  }
  if (u.membershipStatus === 'expired') {
    return `已于 ${formatShortDate(u.membershipExpireAt)} 到期`
  }
  return '开通后可使用完整报告与无限次识别'
})

// 商品统一取 constants/goods.ts，官网链接也只在那里维护一份
const goods = SHOP_GOODS
const incentives = INCENTIVE_GOODS

onShow(async () => {
  if (!requireLogin()) return
  if (!requireMallAccess()) return
  session.value = await refreshCurrentUser()
})

async function reload() {
  session.value = await refreshCurrentUser()
}

function onSimulatePay() {
  const user = session.value
  if (!user || isDemo.value) {
    uni.showToast({ title: '演示账号请用正式账号测试', icon: 'none' })
    return
  }
  uni.showModal({
    title: '模拟开通会员',
    content: '将标记本账号已缴费一年，并向推荐人发放积分（若有待发奖励）',
    success: async (res) => {
      if (!res.confirm) return
      busy.value = true
      try {
        const result = await markInviteePaidAndReward(user.id)
        await reload()
        uni.showToast({
          title: result.rewarded
            ? `已开通，推荐人 +${result.pointsAwarded}`
            : '会员已开通',
          icon: 'none',
        })
      } catch (e: any) {
        uni.showToast({ title: e.message || '开通失败', icon: 'none' })
      } finally {
        busy.value = false
      }
    },
  })
}

function onRedeem() {
  const user = session.value
  if (!user || isDemo.value) return
  uni.showModal({
    title: '积分抵扣年费',
    content: `将消耗 ${rewardPoints} 积分开通一年会员`,
    success: async (res) => {
      if (!res.confirm) return
      busy.value = true
      try {
        await redeemPointsForMembership(user.id)
        await reload()
        uni.showToast({ title: '已用积分开通会员', icon: 'success' })
      } catch (e: any) {
        uni.showToast({ title: e.message || '抵扣失败', icon: 'none' })
      } finally {
        busy.value = false
      }
    },
  })
}

function onGoods(g: { name: string; url?: string }) {
  openOfficial(officialUrlOf(g))
}
function goCatalog(kind: string) {
  uni.navigateTo({ url: `/pages/catalog/catalog?kind=${kind}` })
}
function goReferral() {
  uni.navigateTo({ url: '/pages/referral/referral' })
}
function goPayment() {
  uni.navigateTo({ url: '/pages/payment/payment' })
}
function onIncentive() {
  uni.navigateTo({ url: '/pages/goals/goals' })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f9fafb;
  padding: 24rpx;
  padding-bottom: 40rpx;
}
.note {
  font-size: 22rpx;
  color: #9ca3af;
  margin-bottom: 16rpx;
  line-height: 1.5;
}
.card {
  background: #fff;
  border-radius: 24rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
}
.vip {
  background: linear-gradient(135deg, #1d4ed8, #60a5fa);
  color: #fff;
}
.vip-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.vip-title {
  font-size: 32rpx;
  font-weight: 700;
}
.vip-tag {
  background: rgba(255, 255, 255, 0.2);
  padding: 6rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}
.vip-sub {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  opacity: 0.9;
}
.vip-desc {
  display: block;
  margin-top: 16rpx;
  font-size: 22rpx;
  opacity: 0.85;
}
.vip-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  margin-top: 24rpx;
}
.vip-btn {
  background: #fff;
  color: #2563eb;
  border: none;
  font-size: 22rpx;
}
.vip-btn.ghost {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}
.vip-btn::after {
  border: none;
}
.points {
  display: flex;
  justify-content: space-between;
}
.p-num {
  display: block;
  font-size: 48rpx;
  font-weight: 700;
  color: #2563eb;
}
.p-lab {
  display: block;
  font-size: 22rpx;
  color: #9ca3af;
  margin-top: 6rpx;
}
.p-right {
  text-align: right;
}
.code {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: #111827;
}
.link {
  color: #2563eb;
  font-size: 24rpx;
}
.tip {
  display: block;
  font-size: 22rpx;
  color: #9ca3af;
  margin: -8rpx 0 20rpx;
  padding: 0 8rpx;
}
.tip.mb {
  margin: 0 0 16rpx;
}
.title {
  font-size: 30rpx;
  font-weight: 600;
}
.row-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}
.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.goods {
  width: calc(50% - 8rpx);
  background: #f9fafb;
  border-radius: 16rpx;
  padding: 16rpx;
  box-sizing: border-box;
}
.g-img {
  height: 140rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #374151;
  font-weight: 600;
  margin-bottom: 12rpx;
}
.g-name {
  display: block;
  font-size: 26rpx;
  font-weight: 600;
}
.g-sub {
  display: block;
  font-size: 20rpx;
  color: #9ca3af;
  margin: 6rpx 0;
}
.g-price {
  color: #ef4444;
  font-size: 28rpx;
  font-weight: 700;
}
.center {
  display: block;
  text-align: center;
  margin-top: 20rpx;
}
.pay .qr {
  height: 240rpx;
  margin: 20rpx 0;
  background: #f3f4f6;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}
.btn {
  margin-top: 16rpx;
  background: #2563eb;
  color: #fff;
  border-radius: 14rpx;
  height: 80rpx;
  line-height: 80rpx;
  font-size: 28rpx;
}
.btn::after {
  border: none;
}
</style>
