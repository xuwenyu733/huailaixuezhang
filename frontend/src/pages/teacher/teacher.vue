<template>
  <view class="page">
    <view class="top"><text class="add" @click="openAdd">+ 添加</text></view>
    <view v-if="!list.length" class="empty">暂无教师子账号，点击右上角添加</view>
    <view class="card" v-for="t in list" :key="String(t.Id)">
      <view class="av">{{ t.name.slice(0, 1) }}</view>
      <view class="meta">
        <text class="n">{{ t.name }}</text>
        <text class="s">{{ t.job_desc || '未填科目' }}</text>
        <text class="s">印章编号 {{ t.stamp_no }} · 工号 {{ t.job_no || '-' }}</text>
      </view>
    </view>

    <view class="mask" v-if="show" @click="show = false" />
    <view class="modal" v-if="show">
      <text class="mt">添加教师</text>
      <input class="inp" v-model="form.name" placeholder="教师姓名" />
      <input class="inp" v-model="form.jobNo" placeholder="工号" />
      <input class="inp" v-model="form.job" placeholder="所教班级 / 科目" />
      <input class="inp" v-model="form.stamp" placeholder="印章编号（必填）" />
      <input class="inp" v-model="form.phone" placeholder="联系电话" />
      <button class="btn" :loading="loading" @click="submit">确认添加</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { DEMO_TEACHERS, isDemoId } from '@/constants/demoData'
import { requireLogin } from '@/services/auth'
import { addTeacher, listTeachersBySchool } from '@/services/teacherRepo'
import type { TeacherRow } from '@/types/user'

const show = ref(false)
const loading = ref(false)
const list = ref<TeacherRow[]>([])
const schoolId = ref('')
const form = reactive({ name: '', jobNo: '', job: '', stamp: '', phone: '' })

onShow(async () => {
  const user = requireLogin()
  if (!user) return
  schoolId.value = user.id
  await reload()
})

async function reload() {
  if (!schoolId.value) {
    list.value = []
    return
  }
  if (isDemoId(schoolId.value)) {
    list.value = DEMO_TEACHERS.map((t) => ({ ...t }))
    return
  }
  try {
    list.value = await listTeachersBySchool(schoolId.value)
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  }
}

function openAdd() {
  if (String(schoolId.value).startsWith('demo_')) {
    uni.showToast({ title: '演示账号请用正式学校账号', icon: 'none' })
    return
  }
  show.value = true
}

async function submit() {
  loading.value = true
  try {
    await addTeacher({
      schoolId: schoolId.value,
      name: form.name,
      jobNo: form.jobNo,
      jobDesc: form.job,
      stampNo: form.stamp,
      phone: form.phone,
    })
    form.name = ''
    form.jobNo = ''
    form.job = ''
    form.stamp = ''
    form.phone = ''
    show.value = false
    await reload()
    uni.showToast({ title: '教师添加成功，印章编号已绑定', icon: 'none' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '添加失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.top { display: flex; justify-content: flex-end; margin-bottom: 12rpx; }
.add { color: #2563eb; font-weight: 600; }
.empty { text-align: center; color: #9ca3af; padding: 80rpx 0; }
.card {
  background: #fff; border-radius: 20rpx; padding: 28rpx; margin-bottom: 16rpx;
  display: flex; align-items: center;
}
.av {
  width: 80rpx; height: 80rpx; border-radius: 50%; background: #dbeafe; color: #2563eb;
  font-weight: 700; display: flex; align-items: center; justify-content: center; margin-right: 16rpx;
}
.n { display: block; font-size: 30rpx; font-weight: 600; }
.s { display: block; margin-top: 6rpx; font-size: 22rpx; color: #9ca3af; }
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 90; }
.modal {
  position: fixed; left: 0; right: 0; bottom: 0; background: #fff; z-index: 100;
  border-radius: 28rpx 28rpx 0 0; padding: 36rpx;
}
.mt { display: block; font-size: 32rpx; font-weight: 700; margin-bottom: 20rpx; }
.inp {
  height: 84rpx; background: #f9fafb; border: 2rpx solid #e5e7eb; border-radius: 14rpx;
  padding: 0 24rpx; margin-bottom: 16rpx;
}
.btn { background: #2563eb; color: #fff; height: 88rpx; line-height: 88rpx; border-radius: 14rpx; }
.btn::after { border: none; }
</style>
