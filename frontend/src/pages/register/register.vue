<template>
  <view class="page">
    <view class="hero">
      <view class="mark"><view class="diamond" /></view>
      <text class="title">创建家长账号</text>
      <text class="sub">注册即得专属推荐码，邀请好友开通会员可获积分</text>
    </view>

    <view class="panel">
      <view class="field">
        <text class="label">姓名</text>
        <input v-model="name" class="input" placeholder="请输入家长姓名" />
      </view>
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
        <text class="label">设置密码</text>
        <view class="pwd-box">
          <input
            v-model="password"
            class="input pwd-input"
            :password="!showPwd"
            placeholder="字母+数字，至少 6 位"
          />
          <view class="eye" @click.stop="showPwd = !showPwd">
            <view class="eye-outer" :class="{ off: !showPwd }">
              <view class="eye-dot" />
              <view v-if="!showPwd" class="eye-slash" />
            </view>
          </view>
        </view>
      </view>
      <view class="field">
        <text class="label">确认密码</text>
        <view class="pwd-box">
          <input
            v-model="password2"
            class="input pwd-input"
            :password="!showPwd2"
            placeholder="再次输入密码"
          />
          <view class="eye" @click.stop="showPwd2 = !showPwd2">
            <view class="eye-outer" :class="{ off: !showPwd2 }">
              <view class="eye-dot" />
              <view v-if="!showPwd2" class="eye-slash" />
            </view>
          </view>
        </view>
      </view>
      <view class="field">
        <view class="label-row">
          <text class="label">推荐码</text>
          <text class="opt">选填</text>
        </view>
        <input v-model="inviteCode" class="input" placeholder="如 HAXXXXXX" />
      </view>

      <view class="agree" @click="agreed = !agreed">
        <view class="check" :class="{ on: agreed }">
          <text v-if="agreed" class="check-tick">✓</text>
        </view>
        <view class="agree-txt">
          我已阅读并同意
          <text class="link" @click.stop="openLegal('agreement')">《用户协议》</text>
          与
          <text class="link" @click.stop="openLegal('privacy')">《隐私政策》</text>
        </view>
      </view>

      <button class="submit" :loading="loading" @click="onRegister">注册并登录</button>
      <view class="back" @click="goLogin">
        <text>已有账号？去登录</text>
      </view>
    </view>

    <view class="rules">
      <text class="rules-h">推荐规则</text>
      <text class="rules-p">1. 注册后获得唯一推荐码</text>
      <text class="rules-p">2. 好友填写推荐码完成注册，建立推荐关系</text>
      <text class="rules-p">3. 好友缴费开通会员后，你获得 50 积分</text>
      <text class="rules-p">4. 积分可用于抵扣年费</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { registerParent } from '@/services/auth'
import { normalizeInviteCode } from '@/utils/invite'
import { validatePassword } from '@/utils/security'

const name = ref('')
const phone = ref('')
const password = ref('')
const password2 = ref('')
const inviteCode = ref('')
const agreed = ref(false)
const loading = ref(false)
const showPwd = ref(false)
const showPwd2 = ref(false)

function openLegal(type: string) {
  uni.navigateTo({ url: `/pages/legal/legal?type=${type}` })
}

function goLogin() {
  uni.navigateBack({
    fail: () => uni.reLaunch({ url: '/pages/login/login' }),
  })
}

onLoad((query) => {
  try {
    const fromQuery = query?.invite ? String(query.invite) : ''
    const pending = uni.getStorageSync('hlxz_pending_invite')
    const code = fromQuery || (pending ? String(pending) : '')
    if (code) inviteCode.value = normalizeInviteCode(code)
    const wxName = uni.getStorageSync('hlxz_wx_nickname')
    if (wxName && !name.value) name.value = String(wxName)
  } catch (e) {
    console.warn('register onLoad', e)
  }
})

async function onRegister() {
  if (!agreed.value) {
    uni.showToast({ title: '请先同意用户协议与隐私政策', icon: 'none' })
    return
  }
  if (password.value !== password2.value) {
    uni.showToast({ title: '两次密码不一致', icon: 'none' })
    return
  }
  const pwdErr = validatePassword(password.value)
  if (pwdErr) {
    uni.showToast({ title: pwdErr, icon: 'none' })
    return
  }

  loading.value = true
  try {
    const user = await registerParent({
      name: name.value,
      phone: phone.value,
      password: password.value,
      inviteCode: inviteCode.value || undefined,
    })
    uni.removeStorageSync('hlxz_pending_invite')
    uni.setStorageSync('hlxz_wx_bound_phone', user.phone)
    uni.showModal({
      title: '注册成功',
      content: `您的专属推荐码：${user.inviteCode}${
        user.referredByCode ? `\n已绑定推荐人：${user.referredByCode}` : ''
      }`,
      showCancel: false,
      success: () => uni.switchTab({ url: '/pages/home/home' }),
    })
  } catch (e: any) {
    uni.showToast({ title: e.message || '注册失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24rpx 40rpx 64rpx;
  box-sizing: border-box;
  background-color: #eef2f7;
}
.hero {
  padding: 12rpx 8rpx 28rpx;
}
.mark {
  width: 72rpx;
  height: 72rpx;
  border-radius: 18rpx;
  background-color: #1e4fd6;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20rpx;
}
.diamond {
  width: 28rpx;
  height: 28rpx;
  border: 5rpx solid #ffffff;
  transform: rotate(45deg);
  border-radius: 4rpx;
}
.title {
  display: block;
  font-size: 44rpx;
  font-weight: 700;
  color: #0f172a;
}
.sub {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #64748b;
  line-height: 1.55;
}
.panel {
  background-color: #ffffff;
  border-radius: 24rpx;
  padding: 32rpx 28rpx 36rpx;
}
.field {
  margin-bottom: 22rpx;
}
.label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10rpx;
}
.label {
  display: block;
  font-size: 24rpx;
  color: #64748b;
  margin-bottom: 10rpx;
}
.label-row .label {
  margin-bottom: 0;
}
.opt {
  font-size: 22rpx;
  color: #94a3b8;
}
.input {
  height: 92rpx;
  padding: 0 28rpx;
  background-color: #f8fafc;
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
.agree {
  display: flex;
  align-items: flex-start;
  margin: 8rpx 0 28rpx;
}
.check {
  width: 36rpx;
  height: 36rpx;
  border-radius: 8rpx;
  background-color: #ffffff;
  border: 2rpx solid #94a3b8;
  margin-right: 14rpx;
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
  font-size: 24rpx;
  color: #64748b;
  line-height: 1.55;
}
.link {
  color: #1e4fd6;
}
.submit {
  height: 96rpx;
  line-height: 96rpx;
  background-color: #1e4fd6;
  color: #ffffff;
  border-radius: 18rpx;
  font-size: 32rpx;
  font-weight: 600;
}
.submit::after {
  border: none;
}
.back {
  margin-top: 28rpx;
  text-align: center;
  font-size: 26rpx;
  color: #1e4fd6;
}
.rules {
  margin-top: 28rpx;
  padding: 28rpx;
  border-radius: 20rpx;
  background-color: #e0eaff;
}
.rules-h {
  display: block;
  font-size: 26rpx;
  font-weight: 600;
  color: #1e4fd6;
  margin-bottom: 12rpx;
}
.rules-p {
  display: block;
  font-size: 24rpx;
  color: #475569;
  line-height: 1.7;
}
</style>
