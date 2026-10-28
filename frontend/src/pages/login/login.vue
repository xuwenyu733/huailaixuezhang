<template>
  <view class="page">
    <view class="bg">
      <view class="orb orb-a" />
      <view class="orb orb-b" />
      <view class="grid" />
    </view>

    <view class="brand">
      <view class="mark">
        <view class="diamond" />
      </view>
      <text class="name">淮安学长</text>
      <text class="slogan">知章 · 行章 · 知行对章</text>
    </view>

    <view class="panel">
      <view class="tabs">
        <view
          class="tab"
          :class="{ on: mode === 'parent' }"
          @click="mode = 'parent'"
        >
          家长登录
        </view>
        <view
          class="tab"
          :class="{ on: mode === 'teacher' }"
          @click="mode = 'teacher'"
        >
          教师登录
        </view>
      </view>

      <view v-if="mode === 'parent'" class="form">
        <view class="field">
          <text class="label">手机号</text>
          <input
            v-model="phone"
            class="input"
            type="number"
            maxlength="11"
            placeholder="请输入手机号"
          />
        </view>
        <view class="field">
          <text class="label">密码</text>
          <view class="pwd-box">
            <input
              v-model="password"
              class="input pwd-input"
              :password="!showParentPwd"
              placeholder="字母+数字，至少 6 位"
            />
            <view class="eye" @click.stop="showParentPwd = !showParentPwd">
              <view class="eye-outer" :class="{ off: !showParentPwd }">
                <view class="eye-dot" />
                <view v-if="!showParentPwd" class="eye-slash" />
              </view>
            </view>
          </view>
        </view>
        <button class="submit" :loading="loading" @click="onPhoneLogin">
          登录
        </button>
        <view class="row">
          <text class="ghost" @click="goRegister">没有账号？去注册</text>
        </view>
      </view>

      <view v-else class="form">
        <view class="field">
          <text class="label">印章编号</text>
          <input
            v-model="stampNo"
            class="input"
            placeholder="如 T9901"
          />
        </view>
        <view class="field">
          <text class="label">密码</text>
          <view class="pwd-box">
            <input
              v-model="teacherPwd"
              class="input pwd-input"
              :password="!showTeacherPwd"
              placeholder="默认 123456a"
            />
            <view class="eye" @click.stop="showTeacherPwd = !showTeacherPwd">
              <view class="eye-outer" :class="{ off: !showTeacherPwd }">
                <view class="eye-dot" />
                <view v-if="!showTeacherPwd" class="eye-slash" />
              </view>
            </view>
          </view>
        </view>
        <button class="submit" :loading="loading" @click="onTeacherLogin">
          登录
        </button>
        <text class="hint">教师账号由学校在「教师管理」中分配，无法自行注册</text>
      </view>

      <view class="agree" @click="agreed = !agreed">
        <view class="check" :class="{ on: agreed }">
          <text v-if="agreed" class="check-tick">✓</text>
        </view>
        <view class="agree-txt">
          登录即表示同意
          <text class="link" @click.stop="openLegal('agreement')">《用户协议》</text>
          与
          <text class="link" @click.stop="openLegal('privacy')">《隐私政策》</text>
        </view>
      </view>
    </view>

    <view class="demo">
      <text class="demo-lab">快速体验</text>
      <view class="demo-row">
        <text class="demo-btn" @click="onLogin('family')">家长演示</text>
        <text class="sep">|</text>
        <text class="demo-btn" @click="onLogin('school')">学校演示</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { loginAs, type AppRole } from '@/stores/demo'
import { loginParent, loginTeacher } from '@/services/auth'

const mode = ref<'parent' | 'teacher'>('parent')
const phone = ref('')
const password = ref('')
const stampNo = ref('')
const teacherPwd = ref('')
const loading = ref(false)
const agreed = ref(false)
const showParentPwd = ref(false)
const showTeacherPwd = ref(false)

function ensureAgreed() {
  if (!agreed.value) {
    uni.showToast({ title: '请先勾选同意用户协议与隐私政策', icon: 'none' })
    return false
  }
  return true
}

async function onPhoneLogin() {
  if (!ensureAgreed()) return
  loading.value = true
  try {
    await loginParent({ phone: phone.value, password: password.value })
    uni.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(() => uni.switchTab({ url: '/pages/home/home' }), 400)
  } catch (e: any) {
    uni.showToast({ title: e.message || '登录失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function onTeacherLogin() {
  if (!ensureAgreed()) return
  loading.value = true
  try {
    await loginTeacher({ stampNo: stampNo.value, password: teacherPwd.value })
    uni.showToast({ title: '教师登录成功', icon: 'success' })
    setTimeout(() => uni.switchTab({ url: '/pages/scan/scan' }), 400)
  } catch (e: any) {
    uni.showToast({ title: e.message || '登录失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function onLogin(role: AppRole) {
  if (!ensureAgreed()) return
  loginAs(role)
  uni.switchTab({ url: '/pages/home/home' })
}

function goRegister() {
  uni.navigateTo({ url: '/pages/register/register' })
}
function openLegal(type: string) {
  uni.navigateTo({ url: `/pages/legal/legal?type=${type}` })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  position: relative;
  padding: 0 40rpx 48rpx;
  box-sizing: border-box;
  overflow: hidden;
  background: #e8eef8;
}

.bg {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 520rpx;
  background: linear-gradient(165deg, #1e4fd6 0%, #3b82f6 48%, #93c5fd 100%);
  overflow: hidden;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(2rpx);
}
.orb-a {
  width: 280rpx;
  height: 280rpx;
  right: -60rpx;
  top: -40rpx;
  background: rgba(255, 255, 255, 0.16);
  animation: float 7s ease-in-out infinite;
}
.orb-b {
  width: 180rpx;
  height: 180rpx;
  left: -40rpx;
  top: 220rpx;
  background: rgba(255, 255, 255, 0.1);
  animation: float 9s ease-in-out infinite reverse;
}
.grid {
  position: absolute;
  inset: 0;
  opacity: 0.12;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.35) 1rpx, transparent 1rpx),
    linear-gradient(90deg, rgba(255, 255, 255, 0.35) 1rpx, transparent 1rpx);
  background-size: 48rpx 48rpx;
}

.brand {
  position: relative;
  z-index: 1;
  padding: 120rpx 8rpx 56rpx;
  color: #fff;
}
.mark {
  width: 96rpx;
  height: 96rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 28rpx;
}
.diamond {
  width: 44rpx;
  height: 44rpx;
  border: 6rpx solid #fff;
  transform: rotate(45deg);
  border-radius: 6rpx;
}
.name {
  display: block;
  font-size: 56rpx;
  font-weight: 700;
  letter-spacing: 8rpx;
  font-family: "Songti SC", "STSong", "PingFang SC", serif;
}
.slogan {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  letter-spacing: 4rpx;
  opacity: 0.88;
}

.panel {
  position: relative;
  z-index: 1;
  margin-top: -24rpx;
  background: #fff;
  border-radius: 28rpx 28rpx 24rpx 24rpx;
  padding: 28rpx 28rpx 32rpx;
  box-shadow: 0 18rpx 48rpx rgba(30, 79, 214, 0.12);
}

.tabs {
  display: flex;
  background: #f1f5f9;
  border-radius: 16rpx;
  padding: 6rpx;
  margin-bottom: 28rpx;
}
.tab {
  flex: 1;
  text-align: center;
  height: 72rpx;
  line-height: 72rpx;
  font-size: 28rpx;
  color: #64748b;
  border-radius: 12rpx;
}
.tab.on {
  background: #fff;
  color: #1e4fd6;
  font-weight: 600;
  box-shadow: 0 4rpx 12rpx rgba(15, 23, 42, 0.06);
}

.field { margin-bottom: 22rpx; }
.label {
  display: block;
  margin-bottom: 10rpx;
  font-size: 24rpx;
  color: #64748b;
}
.input {
  height: 92rpx;
  padding: 0 28rpx;
  background: #f8fafc;
  border: 2rpx solid #e2e8f0;
  border-radius: 16rpx;
  font-size: 30rpx;
  color: #0f172a;
}
.pwd-box {
  position: relative;
}
.pwd-input {
  padding-right: 88rpx;
}
.eye {
  position: absolute;
  right: 8rpx;
  top: 0;
  bottom: 0;
  width: 80rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.eye-outer {
  width: 36rpx;
  height: 22rpx;
  border: 3rpx solid #64748b;
  border-radius: 50%;
  position: relative;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
}
.eye-outer.off {
  opacity: 0.55;
}
.eye-dot {
  width: 10rpx;
  height: 10rpx;
  background: #64748b;
  border-radius: 50%;
}
.eye-slash {
  position: absolute;
  left: -4rpx;
  top: 8rpx;
  width: 40rpx;
  height: 3rpx;
  background: #94a3b8;
  transform: rotate(-28deg);
}
.submit {
  margin-top: 8rpx;
  height: 96rpx;
  line-height: 96rpx;
  background: linear-gradient(135deg, #1e4fd6, #3b82f6);
  color: #fff;
  border-radius: 18rpx;
  font-size: 32rpx;
  font-weight: 600;
  letter-spacing: 4rpx;
}
.submit::after { border: none; }
.row {
  margin-top: 24rpx;
  text-align: center;
}
.ghost {
  font-size: 26rpx;
  color: #1e4fd6;
}
.hint {
  display: block;
  margin-top: 20rpx;
  font-size: 22rpx;
  color: #94a3b8;
  line-height: 1.6;
  text-align: center;
}

.agree {
  margin-top: 28rpx;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  justify-content: center;
}
.check {
  width: 36rpx;
  height: 36rpx;
  border-radius: 8rpx;
  background-color: #ffffff;
  border: 2rpx solid #94a3b8;
  margin-right: 12rpx;
  margin-top: 2rpx;
  flex-shrink: 0;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
}
.check.on {
  background-color: #1e4fd6;
  border-color: #1e4fd6;
}
.check-tick {
  color: #ffffff;
  font-size: 24rpx;
  font-weight: 700;
  line-height: 1;
}
.agree-txt {
  flex: 1;
  font-size: 22rpx;
  color: #94a3b8;
  line-height: 1.55;
}
.link { color: #1e4fd6; }

.demo {
  position: relative;
  z-index: 1;
  margin-top: 40rpx;
  text-align: center;
}
.demo-lab {
  display: block;
  font-size: 22rpx;
  color: #94a3b8;
  margin-bottom: 12rpx;
}
.demo-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20rpx;
}
.demo-btn {
  font-size: 26rpx;
  color: #475569;
}
.sep { color: #cbd5e1; font-size: 24rpx; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(18rpx); }
}
</style>
