<template>
  <view class="page">
    <!-- 当前学生 -->
    <view class="student">
      <view class="avatar">{{ childAvatar }}</view>
      <view class="info">
        <text class="name">{{ childName }}</text>
        <text class="sub">{{ childSub }}</text>
      </view>
    </view>

    <!-- 章型 -->
    <view class="block">
      <text class="block-title">选择章型</text>
      <view class="stamp-types">
        <view
          class="type-card"
          :class="{ active: stampType === 'know' }"
          @click="selectStamp('know')"
        >
          <view class="mini-square" />
          <text class="type-name">知章</text>
          <text class="type-desc">过程积累</text>
        </view>
        <view
          class="type-card"
          :class="{ active: stampType === 'do' }"
          @click="selectStamp('do')"
        >
          <view class="mini-round-solo" />
          <text class="type-name">行章</text>
          <text class="type-desc">实践成果</text>
        </view>
        <view
          class="type-card"
          :class="{ active: stampType === 'combo' }"
          @click="selectStamp('combo')"
        >
          <view class="mini-combo">
            <view class="mini-square green" />
            <view class="mini-round green" />
          </view>
          <text class="type-name">知行对章</text>
          <text class="type-desc">深度融合</text>
        </view>
      </view>
    </view>

    <!-- 印章编码预览 -->
    <view class="block">
      <text class="block-title">印章编码设置</text>
      <view class="preview-wrap">
        <view class="big-stamp" :class="stampClass">
          <view class="center" @click="cycleCenter">{{ centerText }}</view>
          <view class="corner tl" @click="openPicker('tl')">{{ codes.tl }}</view>
          <view class="corner tr" @click="openPicker('tr')">{{ codes.tr }}</view>
          <view class="corner bl" @click="openPicker('bl')">{{ codes.bl }}</view>
          <view class="corner br" @click="openPicker('br')">{{ codes.br }}</view>
        </view>
        <text class="tip">点击中心切换学科；点击四角选择 0–9 编码</text>
        <text class="tip soft">左上一级维度 · 右上二级 · 左下场景 · 右下校验</text>
      </view>
    </view>

    <!-- 盖章类型（仅知章） -->
    <view class="block" v-if="stampType === 'know'">
      <text class="block-title">选择盖章类型</text>
      <view class="tags">
        <view
          v-for="item in knowKinds"
          :key="item"
          class="tag"
          :class="{ active: knowKind === item }"
          @click="selectKnowKind(item)"
        >
          {{ item }}
        </view>
      </view>
      <text class="hint">正章=1ZE；引导章=1Y 不计分；改进章=1G+2ZE</text>
    </view>

    <!-- 行章叠章说明 -->
    <view class="block" v-if="stampType === 'do'">
      <text class="block-title">行章说明</text>
      <text class="hint">黄色圆章，基础 1XE；可与叠章叠加计分</text>
    </view>

    <!-- 叠章 -->
    <view class="block" v-if="canStack">
      <text class="block-title">叠章</text>
      <view class="tags">
        <view
          v-for="item in stackOptions"
          :key="item"
          class="tag"
          :class="{ active: stackKind === item }"
          @click="stackKind = item"
        >
          {{ item }}
        </view>
      </view>
      <text class="hint">未选正向章时不可叠章；最高三叠</text>
    </view>

    <!-- 维度 -->
    <view class="block">
      <text class="block-title">选择评价维度</text>
      <view class="tags">
        <view
          v-for="item in primaryDims"
          :key="item"
          class="tag"
          :class="{ active: primaryDim === item }"
          @click="selectPrimary(item)"
        >
          {{ item }}
        </view>
      </view>
      <view class="tags mt">
        <view
          v-for="item in secondaryDims"
          :key="item"
          class="tag"
          :class="{ active: secondaryDim === item }"
          @click="selectSecondary(item)"
        >
          {{ item }}
        </view>
      </view>
    </view>

    <!-- 补充说明 -->
    <view class="block">
      <text class="block-title">补充说明（选填）</text>
      <textarea
        v-model="note"
        class="textarea"
        placeholder="记录具体表现"
        maxlength="200"
      />
    </view>

    <!-- 当量预览 -->
    <view class="value-card">
      <text class="value-label">当量预览</text>
      <text class="value-text">{{ valuePreview }}</text>
    </view>

    <button class="submit" :loading="saving" @click="confirmStamp">确认盖章</button>

    <view class="block" v-if="records.length">
      <view class="row-between">
        <text class="block-title">最近记录</text>
        <text class="soft">云端同步</text>
      </view>
      <view v-for="(r, i) in records" :key="i" class="record">
        <text class="r-title">{{ r.title }}</text>
        <text class="r-sub">{{ r.sub }}</text>
      </view>
    </view>

    <!-- 数字选择弹层 -->
    <view class="mask" v-if="pickerShow" @click="closePicker" />
    <view class="picker" :class="{ show: pickerShow }">
      <view class="picker-head">
        <text class="picker-title">选择编码数字</text>
        <text class="picker-close" @click="closePicker">关闭</text>
      </view>
      <text class="picker-sub">{{ pickerTitle }}</text>
      <view class="num-grid">
        <view
          v-for="num in 10"
          :key="num - 1"
          class="num"
          :class="{ active: codes[currentCorner] === num - 1 }"
          @click="selectNum(num - 1)"
        >
          {{ num - 1 }}
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireLogin } from '@/services/auth'
import { getCurrentChild } from '@/services/childRepo'
import { bumpActiveGoals } from '@/services/goalRepo'
import { pushMessage } from '@/services/messageRepo'
import { listStampsByOwner, saveStamp } from '@/services/stampRepo'
import type { ChildRow } from '@/types/user'

type StampType = 'know' | 'do' | 'combo'
type Corner = 'tl' | 'tr' | 'bl' | 'br'
type KnowKind = '正向章' | '引导章' | '改进章'
type StackKind = '无' | '二叠章' | '三叠章'

const stampType = ref<StampType>('know')
const centerText = ref('语文')
const subjects = ['语文', '数学', '英语', '科学', '德育', '综合']
const knowKind = ref<KnowKind>('正向章')
const stackKind = ref<StackKind>('无')
const primaryDim = ref('智育')
const secondaryDim = ref('课堂发言')
const note = ref('')
const pickerShow = ref(false)
const currentCorner = ref<Corner>('tl')
const records = ref<{ title: string; sub: string }[]>([])
const saving = ref(false)
const ownerId = ref('')
const child = ref<ChildRow | null>(null)

const childAvatar = computed(
  () => child.value?.avatar_text || child.value?.name?.slice(0, 1) || '学',
)
const childName = computed(() => child.value?.name || '未绑定孩子')
const childSub = computed(() => {
  if (!child.value) return '请先在「我的孩子」中添加并选择当前孩子'
  return `${child.value.class_name || '未填班级'} · 记录卡 ${child.value.card_no}`
})

const codeStore = reactive<Record<StampType, Record<Corner, number>>>({
  know: { tl: 1, tr: 2, bl: 3, br: 4 },
  do: { tl: 1, tr: 2, bl: 3, br: 4 },
  combo: { tl: 1, tr: 2, bl: 3, br: 4 },
})

const codes = computed(() => codeStore[stampType.value])
const stampClass = computed(() => {
  if (stampType.value === 'combo') return 'combo'
  if (stampType.value === 'do') return 'do'
  return ''
})
const knowKinds: KnowKind[] = ['正向章', '引导章', '改进章']
const stackOptions: StackKind[] = ['无', '二叠章', '三叠章']
const primaryDims = ['智育', '德育', '体育', '美育', '劳育', '品格']
const secondaryDims = ['课堂发言', '作业完成', '测试达标', '志愿服务']

const dimCodeMap: Record<string, number> = {
  智育: 1,
  德育: 2,
  体育: 3,
  美育: 4,
  劳育: 5,
  品格: 6,
  课堂发言: 1,
  作业完成: 2,
  测试达标: 3,
  志愿服务: 4,
}

const canStack = computed(() => {
  if (stampType.value === 'combo' || stampType.value === 'do') return true
  return knowKind.value === '正向章'
})

const valuePreview = computed(() => {
  if (stampType.value === 'combo') {
    const mul = stackKind.value === '三叠章' ? 3 : stackKind.value === '二叠章' ? 2 : 1
    return `+${mul} 知行对章当量（DE）`
  }
  if (stampType.value === 'do') {
    const mul = stackKind.value === '三叠章' ? 3 : stackKind.value === '二叠章' ? 2 : 1
    return `+${mul} 行章当量（XE）`
  }
  if (knowKind.value === '引导章') return '+1 引导章（Y，不计当量）'
  if (knowKind.value === '改进章') return '+2 知章当量（ZE，改进章）'
  const mul = stackKind.value === '三叠章' ? 3 : stackKind.value === '二叠章' ? 2 : 1
  return `+${mul} 知章当量（ZE）`
})

const pickerTitle = computed(() => {
  const map = { tl: '左上角', tr: '右上角', bl: '左下角', br: '右下角' }
  return `${map[currentCorner.value]}编码`
})

onLoad(async () => {
  const user = requireLogin()
  if (!user) return
  ownerId.value = user.id
  try {
    if (String(user.id).startsWith('demo_')) {
      const { DEMO_STAMPS, getDemoCurrentChild } = await import('@/constants/demoData')
      child.value = getDemoCurrentChild()
      records.value = DEMO_STAMPS.slice(0, 10).map((r) => ({
        title: `${r.source === 'physical' ? '实体' : '虚拟'} · ${r.value_text || r.stamp_type}`,
        sub: `${r.primary_dim}/${r.secondary_dim} · 编码${r.code_text} · ${r.subject}${
          r.child_name ? ' · ' + r.child_name : ''
        }`,
      }))
      return
    }
    child.value = await getCurrentChild(user.id)
    await reloadRecords()
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  }
})

async function reloadRecords() {
  if (!ownerId.value || String(ownerId.value).startsWith('demo_')) return
  const rows = await listStampsByOwner(ownerId.value, 10)
  records.value = rows.map((r) => ({
    title: `${r.source === 'physical' ? '实体' : '虚拟'} · ${r.value_text || r.stamp_type}`,
    sub: `${r.primary_dim}/${r.secondary_dim} · 编码${r.code_text} · ${r.subject}${
      r.child_name ? ' · ' + r.child_name : ''
    }`,
  }))
}

function valueNumOf(): number {
  if (stampType.value === 'combo') {
    return stackKind.value === '三叠章' ? 3 : stackKind.value === '二叠章' ? 2 : 1
  }
  if (stampType.value === 'do') {
    return stackKind.value === '三叠章' ? 3 : stackKind.value === '二叠章' ? 2 : 1
  }
  if (knowKind.value === '引导章') return 0
  if (knowKind.value === '改进章') return 2
  return stackKind.value === '三叠章' ? 3 : stackKind.value === '二叠章' ? 2 : 1
}

function selectStamp(type: StampType) {
  stampType.value = type
  if (type === 'combo' || type === 'do') {
    knowKind.value = '正向章'
  }
  if (!canStack.value) stackKind.value = '无'
}

function selectKnowKind(kind: KnowKind) {
  knowKind.value = kind
  if (kind !== '正向章') stackKind.value = '无'
}

function selectPrimary(dim: string) {
  primaryDim.value = dim
  if (dimCodeMap[dim] !== undefined) {
    codeStore[stampType.value].tl = dimCodeMap[dim]
  }
}

function selectSecondary(dim: string) {
  secondaryDim.value = dim
  if (dimCodeMap[dim] !== undefined) {
    codeStore[stampType.value].tr = dimCodeMap[dim]
  }
}

function cycleCenter() {
  const idx = subjects.indexOf(centerText.value)
  centerText.value = subjects[(idx + 1) % subjects.length]
}

function openPicker(corner: Corner) {
  currentCorner.value = corner
  pickerShow.value = true
}

function closePicker() {
  pickerShow.value = false
}

function selectNum(num: number) {
  codeStore[stampType.value][currentCorner.value] = num
  closePicker()
}

async function confirmStamp() {
  const user = requireLogin()
  if (!user) return
  if (String(user.id).startsWith('demo_')) {
    uni.showToast({ title: '演示账号请用正式账号盖章', icon: 'none' })
    return
  }
  if (!child.value) {
    uni.showModal({
      title: '未绑定孩子',
      content: '请先添加孩子后再盖章',
      confirmText: '去添加',
      success: (res) => {
        if (res.confirm) uni.navigateTo({ url: '/pages/children/children' })
      },
    })
    return
  }

  const c = codes.value
  const code = `${c.tl}${c.tr}${c.bl}${c.br}`
  saving.value = true
  try {
    await saveStamp({
      ownerId: user.id,
      ownerRole: 'parent',
      childId: child.value.Id,
      childName: child.value.name,
      cardNo: child.value.card_no,
      source: 'virtual',
      stampType: stampType.value,
      knowKind: stampType.value === 'know' ? knowKind.value : '',
      stackKind: stackKind.value,
      subject: centerText.value,
      primaryDim: primaryDim.value,
      secondaryDim: secondaryDim.value,
      codeTl: c.tl,
      codeTr: c.tr,
      codeBl: c.bl,
      codeBr: c.br,
      codeText: code,
      valueText: valuePreview.value,
      valueNum: valueNumOf(),
      note: note.value,
      status: 'confirmed',
    })
    note.value = ''
    if (child.value?.parent_id) {
      await bumpActiveGoals(child.value.parent_id, child.value.Id, valueNumOf())
      await pushMessage({
        ownerId: child.value.parent_id,
        title: '虚拟盖章成功',
        content: `${child.value.name} ${valuePreview.value}`,
        category: 'stamp',
      })
    }
    await reloadRecords()
    uni.showToast({ title: `盖章成功 编码${code}`, icon: 'none' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '盖章失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 24rpx 24rpx 80rpx;
  box-sizing: border-box;
}
.student {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}
.avatar {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: #dbeafe;
  color: #2563eb;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16rpx;
}
.name {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: #111827;
}
.sub {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #6b7280;
}
.block {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
}
.block-title {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: #111827;
  margin-bottom: 20rpx;
}
.stamp-types {
  display: flex;
  gap: 16rpx;
}
.type-card {
  flex: 1;
  text-align: center;
  padding: 24rpx 12rpx;
  border: 2rpx solid #e5e7eb;
  border-radius: 16rpx;
  background: #fff;
}
.type-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}
.mini-square {
  width: 48rpx;
  height: 48rpx;
  border: 4rpx solid #2563eb;
  margin: 0 auto 12rpx;
}
.mini-square.green {
  border-color: #10b981;
}
.mini-combo {
  height: 56rpx;
  position: relative;
  margin-bottom: 8rpx;
}
.mini-combo .mini-square {
  position: absolute;
  left: 50%;
  top: 4rpx;
  transform: translateX(-50%);
  margin: 0;
}
.mini-round {
  width: 40rpx;
  height: 40rpx;
  border: 4rpx solid #10b981;
  border-radius: 50%;
  position: absolute;
  left: 50%;
  top: 8rpx;
  transform: translateX(-50%);
}
.mini-round-solo {
  width: 48rpx;
  height: 48rpx;
  border: 4rpx solid #f59e0b;
  border-radius: 50%;
  margin: 0 auto 12rpx;
  box-sizing: border-box;
}
.type-name {
  display: block;
  font-size: 26rpx;
  font-weight: 600;
  color: #111827;
}
.type-desc {
  display: block;
  margin-top: 4rpx;
  font-size: 22rpx;
  color: #9ca3af;
}
.preview-wrap {
  text-align: center;
  padding: 16rpx 0 8rpx;
}
.big-stamp {
  width: 360rpx;
  height: 360rpx;
  margin: 0 auto;
  position: relative;
  border: 6rpx solid #2563eb;
  background: rgba(255, 255, 255, 0.7);
}
.big-stamp.do {
  border-color: #f59e0b;
  border-radius: 50%;
}
.big-stamp.combo {
  border-color: #10b981;
}
.big-stamp.combo::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 85%;
  height: 85%;
  border-radius: 50%;
  border: 6rpx solid #10b981;
  pointer-events: none;
}
.center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 140rpx;
  height: 140rpx;
  border-radius: 16rpx;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-size: 32rpx;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}
.big-stamp.do .center {
  color: #d97706;
  background: rgba(245, 158, 11, 0.12);
  border-radius: 50%;
}
.big-stamp.combo .center {
  color: #10b981;
  background: rgba(16, 185, 129, 0.08);
}
.corner {
  position: absolute;
  width: 64rpx;
  height: 64rpx;
  border-radius: 12rpx;
  border: 4rpx solid #2563eb;
  background: #fff;
  color: #2563eb;
  font-size: 28rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3;
}
.big-stamp.do .corner {
  border-color: #f59e0b;
  color: #d97706;
  border-radius: 50%;
}
.big-stamp.combo .corner {
  border-color: #10b981;
  color: #10b981;
}
.corner.tl {
  top: -20rpx;
  left: -20rpx;
}
.corner.tr {
  top: -20rpx;
  right: -20rpx;
}
.corner.bl {
  bottom: -20rpx;
  left: -20rpx;
}
.corner.br {
  bottom: -20rpx;
  right: -20rpx;
}
.tip {
  display: block;
  margin-top: 28rpx;
  font-size: 24rpx;
  color: #6b7280;
  line-height: 1.5;
}
.tip.soft,
.soft {
  color: #9ca3af;
  font-size: 22rpx;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.tags.mt {
  margin-top: 16rpx;
}
.tag {
  padding: 14rpx 28rpx;
  border-radius: 999rpx;
  border: 2rpx solid #e5e7eb;
  background: #fff;
  font-size: 26rpx;
  color: #374151;
}
.tag.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 500;
}
.hint {
  display: block;
  margin-top: 16rpx;
  font-size: 22rpx;
  color: #9ca3af;
  line-height: 1.5;
}
.textarea {
  width: 100%;
  min-height: 140rpx;
  padding: 20rpx;
  box-sizing: border-box;
  background: #f9fafb;
  border: 2rpx solid #e5e7eb;
  border-radius: 16rpx;
  font-size: 26rpx;
}
.value-card {
  background: #eff6ff;
  border-radius: 20rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.value-label {
  font-size: 26rpx;
  color: #1d4ed8;
}
.value-text {
  font-size: 30rpx;
  font-weight: 700;
  color: #2563eb;
}
.submit {
  height: 88rpx;
  line-height: 88rpx;
  background: #2563eb;
  color: #fff;
  border-radius: 16rpx;
  font-size: 30rpx;
  margin-bottom: 20rpx;
}
.submit::after {
  border: none;
}
.row-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.record {
  padding: 20rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.record:last-child {
  border-bottom: none;
}
.r-title {
  display: block;
  font-size: 26rpx;
  color: #111827;
  font-weight: 500;
}
.r-sub {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #9ca3af;
}
.mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 90;
}
.picker {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: #fff;
  border-radius: 24rpx 24rpx 0 0;
  padding: 32rpx;
  z-index: 100;
  transform: translateY(110%);
  transition: transform 0.25s ease;
}
.picker.show {
  transform: translateY(0);
}
.picker-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.picker-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #111827;
}
.picker-close {
  font-size: 26rpx;
  color: #9ca3af;
}
.picker-sub {
  display: block;
  margin: 12rpx 0 20rpx;
  font-size: 24rpx;
  color: #6b7280;
}
.num-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16rpx;
}
.num {
  height: 80rpx;
  border-radius: 14rpx;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  font-weight: 600;
  color: #374151;
}
.num.active {
  background: #2563eb;
  color: #fff;
}
</style>
