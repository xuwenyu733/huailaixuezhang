<template>
  <view class="page">
    <view class="menu">
      <view class="item">
        <view>
          <text class="t">手机号脱敏展示</text>
          <text class="d">我的页、推荐列表只显示部分号码</text>
        </view>
        <switch :checked="form.maskPhone" color="#2563eb" @change="onSwitch('maskPhone', $event)" />
      </view>
      <view class="item">
        <view>
          <text class="t">允许教师查看孩子盖章</text>
          <text class="d">关闭后教师端学生列表不展示当量明细</text>
        </view>
        <switch :checked="form.shareTeacher" color="#2563eb" @change="onSwitch('shareTeacher', $event)" />
      </view>
    </view>
    <button class="btn" :loading="saving" @click="save">保存</button>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { requireLogin } from '@/services/auth'
import { getUserPrefs, saveUserPrefs } from '@/services/prefsRepo'
import { syncDemoFromSession } from '@/stores/demo'
import { getLocalSession } from '@/services/session'

const saving = ref(false)
const form = reactive({ maskPhone: true, shareTeacher: true })
let ownerId = ''

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  ownerId = user.id
  const prefs = await getUserPrefs(user.id)
  form.maskPhone = prefs.maskPhone
  form.shareTeacher = prefs.shareTeacher
})

function onSwitch(key: 'maskPhone' | 'shareTeacher', e: any) {
  form[key] = !!(e?.detail?.value)
}

async function save() {
  if (!ownerId) return
  saving.value = true
  try {
    await saveUserPrefs(ownerId, {
      ...(await getUserPrefs(ownerId)),
      maskPhone: form.maskPhone,
      shareTeacher: form.shareTeacher,
    })
    const session = getLocalSession()
    if (session) syncDemoFromSession(session)
    uni.showToast({ title: '隐私设置已保存', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '保存失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.menu { background: #fff; border-radius: 20rpx; overflow: hidden; }
.item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 28rpx; border-bottom: 2rpx solid #f3f4f6; gap: 20rpx;
}
.item:last-child { border-bottom: none; }
.t { display: block; font-size: 28rpx; }
.d { display: block; margin-top: 8rpx; font-size: 22rpx; color: #9ca3af; line-height: 1.5; }
.btn {
  margin-top: 32rpx; background: #2563eb; color: #fff; border-radius: 16rpx;
  height: 88rpx; line-height: 88rpx;
}
.btn::after { border: none; }
</style>
