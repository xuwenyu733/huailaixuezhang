<template>
  <view class="page">
    <view class="top">
      <text class="link" @click="readAll">全部已读</text>
    </view>
    <view v-if="!list.length" class="empty">暂无消息。盖章、开通会员后会收到通知。</view>
    <view class="item" v-for="m in list" :key="String(m.Id)" @click="open(m)">
      <view class="left">
        <text class="t">{{ m.title }}</text>
        <text class="d">{{ m.content }}</text>
        <text class="time">{{ m.created_at }}</text>
      </view>
      <view class="badge" v-if="Number(m.is_read) !== 1" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { DEMO_MESSAGES, isDemoId } from '@/constants/demoData'
import { requireLogin } from '@/services/auth'
import {
  listMessages,
  markAllMessagesRead,
  markMessageRead,
  type MessageRow,
} from '@/services/messageRepo'

const list = ref<MessageRow[]>([])
const ownerId = ref('')

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  ownerId.value = user.id
  if (isDemoId(user.id)) {
    list.value = DEMO_MESSAGES.map((m) => ({ ...m }))
    return
  }
  list.value = await listMessages(user.id).catch(() => [])
})

async function open(m: MessageRow) {
  if (Number(m.is_read) === 1) return
  if (!isDemoId(ownerId.value)) await markMessageRead(m.Id)
  m.is_read = 1
}

async function readAll() {
  if (!ownerId.value) return
  if (!isDemoId(ownerId.value)) await markAllMessagesRead(ownerId.value)
  list.value.forEach((m) => {
    m.is_read = 1
  })
  uni.showToast({ title: '已全部已读', icon: 'success' })
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.top { display: flex; justify-content: flex-end; margin-bottom: 12rpx; }
.link { color: #2563eb; font-size: 26rpx; }
.empty { color: #9ca3af; font-size: 26rpx; padding: 80rpx 20rpx; text-align: center; }
.item {
  background: #fff; border-radius: 16rpx; padding: 28rpx; margin-bottom: 16rpx;
  display: flex; justify-content: space-between; align-items: flex-start;
}
.t { display: block; font-size: 28rpx; font-weight: 600; }
.d { display: block; margin-top: 8rpx; font-size: 24rpx; color: #6b7280; }
.time { display: block; margin-top: 8rpx; font-size: 22rpx; color: #9ca3af; }
.badge {
  width: 16rpx; height: 16rpx; background: #ef4444; border-radius: 50%; margin-top: 8rpx;
}
</style>
