<template>
  <view class="page">
    <view class="header">
      <view class="user" @click="go('/pages/profile/profile')">
        <view class="avatar">{{ avatarText }}</view>
        <view class="meta">
          <text class="name">{{ displayName }}</text>
          <text class="id">ID: {{ displayId }}</text>
        </view>
      </view>
      <view class="gear" @click="go('/pages/settings/settings')">
        <view class="gear-ring" />
        <view class="gear-dot" />
      </view>
    </view>

    <view class="body">
      <view class="card">
        <view class="item" @click="openFirst">
          <view class="ico ico-blue"><text class="ico-txt">孩</text></view>
          <text class="label">{{ firstEntry }}</text>
          <text class="arrow">›</text>
        </view>

        <view
          v-if="sessionRole === 'school'"
          class="item"
          @click="go('/pages/teacher/teacher')"
        >
          <view class="ico ico-teal"><text class="ico-txt">师</text></view>
          <text class="label">教师管理</text>
          <text class="arrow">›</text>
        </view>

        <view
          v-if="sessionRole === 'teacher'"
          class="item"
          @click="switchTab('/pages/scan/scan')"
        >
          <view class="ico ico-amber"><text class="ico-txt">采</text></view>
          <text class="label">去采集盖章</text>
          <text class="arrow">›</text>
        </view>

        <view
          v-if="sessionRole !== 'teacher'"
          class="item"
          @click="switchTab('/pages/report/report')"
        >
          <view class="ico ico-green"><text class="ico-txt">报</text></view>
          <text class="label">我的报告</text>
          <text class="arrow">›</text>
        </view>

        <view
          v-if="sessionRole === 'parent'"
          class="item item-desc"
          @click="go('/pages/order/order')"
        >
          <view class="ico ico-orange"><text class="ico-txt">订</text></view>
          <view class="item-main">
            <text class="label">我的订单</text>
            <text class="desc">
              点击查看已经支付的订单，上传支付凭证后，「我的订单」页面就会显示对应的订单信息，方便用户查看订单状态和历史记录
            </text>
          </view>
          <text class="arrow">›</text>
        </view>

        <view
          v-if="sessionRole === 'parent'"
          class="item"
          @click="go('/pages/referral/referral')"
        >
          <view class="ico ico-pink">
            <text class="ico-txt">荐</text>
          </view>
          <text class="label">我的推荐 · {{ points }} 积分</text>
          <text class="arrow">›</text>
        </view>

        <view
          v-if="sessionRole === 'parent'"
          class="item"
          @click="go('/pages/goals/goals')"
        >
          <view class="ico ico-indigo">
            <text class="ico-txt">标</text>
          </view>
          <text class="label">目标管理</text>
          <text class="arrow">›</text>
        </view>
      </view>

      <view class="card">
        <view class="item" @click="go('/pages/help/help')">
          <view class="ico ico-purple">
            <text class="ico-txt">?</text>
          </view>
          <text class="label">帮助中心</text>
          <text class="arrow">›</text>
        </view>
        <view class="item" @click="go('/pages/about/about')">
          <view class="ico ico-gray">
            <text class="ico-txt">i</text>
          </view>
          <text class="label">关于我们</text>
          <text class="arrow">›</text>
        </view>
      </view>

      <view class="logout" @click="onLogout">
        <text class="logout-txt">退出登录</text>
      </view>
    </view>

    <AppTabBar />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import {
  getCurrentUser,
  logout,
  refreshCurrentUser,
  requireLogin,
} from '@/services/auth'
import { useDemoStore } from '@/stores/demo'
import type { UserRole } from '@/types/user'

const store = useDemoStore()
const profile = computed(() => store.profile)
const sessionRole = ref<UserRole>('parent')
const points = ref(0)
const sessionId = ref('')

const firstEntry = computed(() => {
  if (sessionRole.value === 'parent') return '我的孩子'
  if (sessionRole.value === 'teacher') return '班级概览'
  return '学生管理'
})

const avatarText = computed(
  () => profile.value.avatar || profile.value.name?.slice(0, 1) || '用',
)

const displayName = computed(() => {
  const n = profile.value.name || '用户'
  if (sessionRole.value === 'parent' && !n.includes('同学') && !n.includes('家长')) {
    return `${n}`
  }
  return n
})

const displayId = computed(() => {
  const code = profile.value.inviteCode || profile.value.userId || sessionId.value
  return code || '—'
})

function resolveRole(user: { id: string; role: UserRole } | null): UserRole {
  if (!user) return 'parent'
  if (user.id === 'demo_school' || user.role === 'school') return 'school'
  return user.role
}

onShow(async () => {
  if (!requireLogin()) return
  const user = (await refreshCurrentUser()) || getCurrentUser()
  sessionRole.value = resolveRole(user)
  points.value = Number(user?.points) || 0
  sessionId.value = user?.id || ''
})

function openFirst() {
  if (sessionRole.value === 'parent') go('/pages/children/children')
  else if (sessionRole.value === 'teacher') go('/pages/classOverview/classOverview')
  else go('/pages/classOverview/classOverview')
}
function go(url: string) {
  uni.navigateTo({ url })
}
function switchTab(url: string) {
  uni.switchTab({ url })
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
.page {
  min-height: 100vh;
  background: #f3f4f6;
  padding-bottom: 48rpx;
}
.header {
  background: #2563eb;
  padding: 36rpx 40rpx 88rpx;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-radius: 0 0 32rpx 32rpx;
}
.user {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.avatar {
  width: 112rpx;
  height: 112rpx;
  border-radius: 50%;
  background: #fff;
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
  font-weight: 700;
  margin-right: 24rpx;
  flex-shrink: 0;
}
.meta {
  flex: 1;
  min-width: 0;
}
.name {
  display: block;
  font-size: 36rpx;
  font-weight: 600;
  color: #fff;
}
.id {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.85);
}
.gear {
  width: 56rpx;
  height: 56rpx;
  margin-top: 8rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gear-ring {
  width: 36rpx;
  height: 36rpx;
  border: 4rpx solid rgba(255, 255, 255, 0.92);
  border-radius: 50%;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gear-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
}

.body {
  margin-top: -48rpx;
  padding: 0 28rpx;
  position: relative;
  z-index: 2;
}
.card {
  background: #fff;
  border-radius: 24rpx;
  margin-bottom: 24rpx;
  overflow: hidden;
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.04);
}
.item {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 28rpx 28rpx;
  border-bottom: 2rpx solid #f3f4f6;
}
.item:last-child {
  border-bottom: none;
}
.item-desc {
  align-items: flex-start;
}
.ico {
  width: 72rpx;
  height: 72rpx;
  border-radius: 18rpx;
  margin-right: 20rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ico-blue {
  background: #dbeafe;
}
.ico-green {
  background: #d1fae5;
}
.ico-orange {
  background: #ffedd5;
}
.ico-purple {
  background: #ede9fe;
}
.ico-gray {
  background: #e5e7eb;
}
.ico-teal {
  background: #ccfbf1;
}
.ico-amber {
  background: #fef3c7;
}
.ico-pink {
  background: #fce7f3;
}
.ico-indigo {
  background: #e0e7ff;
}
.ico-txt {
  font-size: 28rpx;
  font-weight: 700;
  color: #4b5563;
  line-height: 1;
}
.ico-blue .ico-txt {
  color: #2563eb;
}
.ico-green .ico-txt {
  color: #059669;
}
.ico-orange .ico-txt {
  color: #ea580c;
}
.ico-purple .ico-txt {
  color: #7c3aed;
}
.ico-teal .ico-txt {
  color: #0d9488;
}
.ico-amber .ico-txt {
  color: #d97706;
}
.ico-pink .ico-txt {
  color: #db2777;
}
.ico-indigo .ico-txt {
  color: #4f46e5;
}
.item-main {
  flex: 1;
  min-width: 0;
  padding-right: 8rpx;
}
.label {
  flex: 1;
  font-size: 30rpx;
  color: #1f2937;
}
.item-desc .label {
  flex: none;
  display: block;
  margin-bottom: 8rpx;
}
.desc {
  display: block;
  font-size: 22rpx;
  color: #6b7280;
  line-height: 1.55;
}
.arrow {
  color: #d1d5db;
  font-size: 36rpx;
  flex-shrink: 0;
  margin-top: 0;
}
.item-desc .arrow {
  margin-top: 4rpx;
}
.logout {
  background: #fff;
  border-radius: 24rpx;
  height: 96rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.04);
}
.logout-txt {
  color: #ef4444;
  font-size: 30rpx;
}
</style>
