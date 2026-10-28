<template>
  <view class="page">
    <view class="card tip">
      请上传支付成功截图。选择「年度会员费」并提交后即时开通会员（正式环境可改为后台审核）。客服：{{ phoneLabel }}
    </view>
    <view class="card">
      <text class="title">支付凭证</text>
      <view class="upload" @click="pick">
        <image v-if="img" :src="img" mode="aspectFit" class="preview" />
        <text v-else>+ 上传图片</text>
      </view>
    </view>
    <view class="card">
      <text class="title">支付信息</text>
      <input class="inp" v-model="form.amount" placeholder="支付金额" type="digit" />
      <input class="inp" v-model="form.time" placeholder="支付时间，如 2026-10-19" />
      <picker :range="types" @change="onType">
        <view class="inp picker">{{ form.type || '选择支付类型' }}</view>
      </picker>
      <textarea class="area" v-model="form.note" placeholder="备注（选填）" />
    </view>
    <button class="btn ghost" @click="call">电话咨询客服</button>
    <button class="btn" :loading="loading" @click="submit">提交审核</button>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { SERVICE_PHONE } from '@/constants/goods'
import { requireLogin } from '@/services/auth'
import { pushMessage } from '@/services/messageRepo'
import { createOrder } from '@/services/orderRepo'
import { markInviteePaidAndReward } from '@/services/referral'

const img = ref('')
const loading = ref(false)
const types = ['年度会员费', '成长记录册', '光敏印油', '定制印章', '其他']
const form = reactive({ amount: '', time: '', type: '', note: '' })
let userId = ''

const phoneLabel = computed(() => {
  const p = SERVICE_PHONE
  if (p.length === 10) return `${p.slice(0, 3)}-${p.slice(3, 6)}-${p.slice(6)}`
  return p
})

onShow(() => {
  const user = requireLogin()
  if (user) userId = user.id
})

function onType(e: any) {
  form.type = types[e.detail.value]
}
function pick() {
  uni.chooseImage({
    count: 1,
    success: (res) => {
      img.value = res.tempFilePaths[0]
    },
  })
}
function call() {
  uni.makePhoneCall({ phoneNumber: SERVICE_PHONE })
}
async function submit() {
  if (!img.value) {
    uni.showToast({ title: '请先上传支付凭证', icon: 'none' })
    return
  }
  if (!form.type) {
    uni.showToast({ title: '请选择支付类型', icon: 'none' })
    return
  }
  if (!form.amount) {
    uni.showToast({ title: '请填写支付金额', icon: 'none' })
    return
  }

  loading.value = true
  try {
    if (userId && !String(userId).startsWith('demo_')) {
      await createOrder({
        ownerId: userId,
        title: form.type,
        amount: form.amount,
        payType: form.type,
        payTime: form.time,
        note: form.note,
        voucherUrl: img.value,
        status: form.type === '年度会员费' ? 'paid' : 'pending',
      })
      await pushMessage({
        ownerId: userId,
        title: form.type === '年度会员费' ? '会员已开通' : '凭证已提交',
        content: `${form.type} ¥${form.amount} 已记录（含凭证）`,
        category: 'order',
      })
    }
    if (form.type === '年度会员费' && userId && !String(userId).startsWith('demo_')) {
      const result = await markInviteePaidAndReward(userId)
      uni.showModal({
        title: '会员已开通',
        content: result.rewarded
          ? `推荐人已获得 ${result.pointsAwarded} 积分`
          : '权益已生效（无待发推荐奖励）',
        showCancel: false,
        success: () => uni.navigateBack(),
      })
      return
    }
    uni.showToast({ title: '提交成功，1个工作日内审核', icon: 'none' })
    setTimeout(() => uni.navigateBack(), 800)
  } catch (e: any) {
    uni.showToast({ title: e.message || '提交失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.card { background: #fff; border-radius: 20rpx; padding: 28rpx; margin-bottom: 16rpx; }
.tip { font-size: 24rpx; line-height: 1.7; background: #eff6ff; color: #1d4ed8; }
.title { display: block; font-size: 28rpx; font-weight: 600; margin-bottom: 16rpx; }
.upload {
  height: 280rpx; background: #f9fafb; border: 2rpx dashed #d1d5db; border-radius: 16rpx;
  display: flex; align-items: center; justify-content: center; color: #9ca3af;
}
.preview { width: 100%; height: 100%; }
.inp {
  height: 84rpx; background: #f9fafb; border: 2rpx solid #e5e7eb; border-radius: 14rpx;
  padding: 0 24rpx; margin-bottom: 16rpx; display: flex; align-items: center;
}
.picker { color: #374151; }
.area {
  width: 100%; min-height: 140rpx; background: #f9fafb; border: 2rpx solid #e5e7eb;
  border-radius: 14rpx; padding: 20rpx; box-sizing: border-box;
}
.btn { background: #2563eb; color: #fff; border-radius: 14rpx; height: 88rpx; line-height: 88rpx; margin-bottom: 16rpx; }
.btn.ghost { background: #eff6ff; color: #2563eb; }
.btn::after { border: none; }
</style>
