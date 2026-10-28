<template>
  <view class="page">
    <view class="banner">
      <text class="title">邀请好友，各有收获</text>
      <text class="desc">好友注册并缴费开通会员后，你获得 50 积分，可抵扣年费</text>
      <view class="code-box">
        <text class="code">{{ inviteCode || '—' }}</text>
        <button class="copy" size="mini" @click="copy">复制推荐码</button>
      </view>
    </view>
    <view class="summary">
      <view class="cell"><text class="n">{{ summary.total }}</text><text class="l">累计邀请</text></view>
      <view class="cell"><text class="n">{{ summary.pending }}</text><text class="l">待缴费</text></view>
      <view class="cell"><text class="n">{{ summary.rewarded }}</text><text class="l">已奖励</text></view>
      <view class="cell"><text class="n">{{ summary.earnedPoints }}</text><text class="l">累计积分</text></view>
    </view>
    <view class="card">
      <text class="ct">推荐关系明细</text>
      <view v-if="!list.length" class="empty">暂无推荐记录，把推荐码发给好友吧</view>
      <view class="row" v-for="r in list" :key="String(r.Id)">
        <view>
          <text class="name">{{ r.invitee_name }}</text>
          <text class="sub">{{ mask(r.invitee_phone) }} · {{ shortDate(r.created_at) }}</text>
        </view>
        <text :class="['st', r.status]">{{ statusLabel(r) }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getDemoReferralSummary, isDemoId } from '@/constants/demoData'
import { REFERRAL_REWARD_POINTS, requireLogin } from '@/services/auth'
import { getReferralSummary } from '@/services/referral'
import type { ReferralRow } from '@/types/user'
import { displayPhone, formatShortDate } from '@/utils/security'

const inviteCode = ref('')
const list = ref<ReferralRow[]>([])
const summary = reactive({
  total: 0,
  pending: 0,
  rewarded: 0,
  earnedPoints: 0,
})

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  inviteCode.value = user.inviteCode
  if (isDemoId(user.id)) {
    const data = getDemoReferralSummary()
    list.value = data.list
    summary.total = data.total
    summary.pending = data.pending
    summary.rewarded = data.rewarded
    summary.earnedPoints = data.earnedPoints
    return
  }
  try {
    const data = await getReferralSummary(user.id)
    list.value = data.list
    summary.total = data.total
    summary.pending = data.pending
    summary.rewarded = data.rewarded
    summary.earnedPoints = data.earnedPoints
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  }
})

function mask(phone: string) {
  return displayPhone(phone)
}
function shortDate(iso: string) {
  return formatShortDate(iso)
}
function statusLabel(r: ReferralRow) {
  if (r.status === 'rewarded') {
    return `已奖励 +${Number(r.reward_points) || REFERRAL_REWARD_POINTS}`
  }
  if (r.status === 'invalid') return '已失效'
  return '待缴费'
}
function copy() {
  if (!inviteCode.value) {
    uni.showToast({ title: '暂无推荐码', icon: 'none' })
    return
  }
  uni.setClipboardData({ data: inviteCode.value })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding-bottom: 40rpx; }
.banner {
  margin: 24rpx; padding: 36rpx 28rpx; border-radius: 20rpx;
  background: linear-gradient(135deg, #1d4ed8, #60a5fa); color: #fff;
}
.title { display: block; font-size: 34rpx; font-weight: 700; }
.desc { display: block; margin-top: 12rpx; font-size: 24rpx; opacity: .9; line-height: 1.6; }
.code-box {
  margin-top: 28rpx; padding: 20rpx 24rpx; background: rgba(255,255,255,.16);
  border-radius: 16rpx; display: flex; justify-content: space-between; align-items: center;
}
.code { font-size: 36rpx; font-weight: 700; }
.copy { background: #fff; color: #2563eb; border: none; }
.copy::after { border: none; }
.summary {
  margin: 0 24rpx 20rpx; background: #fff; border-radius: 20rpx; padding: 28rpx 0; display: flex;
}
.cell { flex: 1; text-align: center; }
.n { display: block; font-size: 32rpx; font-weight: 700; }
.l { display: block; margin-top: 8rpx; font-size: 22rpx; color: #9ca3af; }
.card { margin: 0 24rpx; background: #fff; border-radius: 20rpx; padding: 28rpx; }
.ct { display: block; font-size: 28rpx; font-weight: 600; margin-bottom: 16rpx; }
.empty { padding: 40rpx 0; text-align: center; color: #9ca3af; font-size: 26rpx; }
.row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20rpx 0; border-bottom: 2rpx solid #f3f4f6;
}
.row:last-child { border-bottom: none; }
.name { display: block; font-size: 28rpx; }
.sub { display: block; margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }
.st.rewarded { color: #10b981; font-size: 24rpx; }
.st.pending { color: #f59e0b; font-size: 24rpx; }
.st.invalid { color: #9ca3af; font-size: 24rpx; }
</style>
