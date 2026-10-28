<template>
  <view class="page">
    <input class="search" placeholder="搜索问题" v-model="kw" />
    <view class="card">
      <text class="title">常见问题</text>
      <view class="faq" v-for="f in filtered" :key="f.q" @click="f.open = !f.open">
        <view class="qrow">
          <text class="q">{{ f.q }}</text>
          <text>{{ f.open ? '−' : '+' }}</text>
        </view>
        <text class="a" v-if="f.open">{{ f.a }}</text>
      </view>
    </view>
    <view class="card">
      <text class="title">联系客服</text>
      <button class="btn" @click="showForm = !showForm">在线客服</button>
      <view v-if="showForm" class="form">
        <textarea v-model="question" class="area" placeholder="请输入你的问题" />
        <button class="btn" @click="send">发送给客服</button>
      </view>
      <button class="btn ghost" @click="call">电话咨询 {{ phone }}</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { SERVICE_PHONE } from '@/constants/goods'
import { getCurrentUser } from '@/services/auth'
import { pushMessage } from '@/services/messageRepo'

const kw = ref('')
const phone = SERVICE_PHONE
const showForm = ref(false)
const question = ref('')
const faqs = reactive([
  { q: '如何使用拍照采集？', a: '进入采集页，将印章与记录卡置于框内，点击快门即可识别上传。也可使用虚拟盖章。', open: false },
  { q: '知章和行章有什么区别？', a: '知章记录日常过程积累；行章确认阶段性成果；知行对章确认完整成长周期。', open: false },
  { q: '识别失败怎么办？', a: '可尝试调整角度、光线，或改用虚拟盖章；仍失败请联系客服人工复核。', open: false },
  { q: '如何导出成长报告？', a: '在报告页点击右上角「导出」，会员可导出完整 PDF。', open: false },
])
const filtered = computed(() =>
  faqs.filter((f) => !kw.value || f.q.includes(kw.value)),
)
function call() {
  uni.makePhoneCall({ phoneNumber: phone })
}
async function send() {
  const user = getCurrentUser()
  const text = question.value.trim()
  if (!text) {
    uni.showToast({ title: '请填写问题', icon: 'none' })
    return
  }
  if (!user || String(user.id).startsWith('demo_')) {
    uni.showToast({ title: '请用手机号登录后再留言', icon: 'none' })
    return
  }
  await pushMessage({
    ownerId: user.id,
    title: '客服已收到',
    content: text.slice(0, 180),
    category: 'system',
  })
  question.value = ''
  showForm.value = false
  uni.showToast({ title: '已发送，请到消息里查看', icon: 'none' })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.search {
  height: 80rpx; background: #fff; border-radius: 14rpx; padding: 0 24rpx; margin-bottom: 20rpx;
}
.card { background: #fff; border-radius: 20rpx; padding: 28rpx; margin-bottom: 16rpx; }
.title { display: block; font-size: 30rpx; font-weight: 600; margin-bottom: 16rpx; }
.faq { padding: 20rpx 0; border-bottom: 2rpx solid #f3f4f6; }
.qrow { display: flex; justify-content: space-between; }
.q { font-size: 28rpx; color: #111827; }
.a { display: block; margin-top: 12rpx; font-size: 24rpx; color: #6b7280; line-height: 1.7; }
.btn {
  background: #2563eb; color: #fff; border-radius: 14rpx; height: 80rpx; line-height: 80rpx; margin-bottom: 16rpx;
}
.btn.ghost { background: #eff6ff; color: #2563eb; }
.btn::after { border: none; }
.area {
  width: 100%; min-height: 160rpx; background: #f9fafb; border-radius: 12rpx;
  padding: 16rpx; box-sizing: border-box; margin-bottom: 12rpx; font-size: 26rpx;
}
</style>
