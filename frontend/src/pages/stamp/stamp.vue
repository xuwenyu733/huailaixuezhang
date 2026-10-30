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
      <text class="block-title">印章编码</text>
      <view class="preview-wrap">
        <view class="big-stamp" :class="stampClass">
          <view class="center" :class="{ locked: !isTeacher }" @click="onCenterTap">{{ centerText }}</view>
          <view class="corner tl" @click="openPicker('tl')">{{ codes.tl }}</view>
          <view class="corner tr" @click="openPicker('tr')">{{ codes.tr }}</view>
          <view class="corner bl" @click="openPicker('bl')">{{ codes.bl }}</view>
          <view class="corner br" @click="openPicker('br')">{{ codes.br }}</view>
        </view>
        <text class="tip">{{ centerTip }}</text>
        <text class="tip soft">左上 一级维度(1–7) · 右上 二级指标 · 左下 三级行为 · 右下 个性化</text>
        <text class="tip soft">始终 4 位编码；叠章只加枚数，不改编码</text>
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

    <!-- 行章说明（可手动盖） -->
    <view class="block" v-if="stampType === 'do'">
      <text class="block-title">行章（手动可盖）</text>
      <text class="hint">黄色圆章，1 枚基础 1XE；下方选叠数，按枚数累计，最高三叠</text>
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
      <text class="hint">{{ stackHint }}</text>
    </view>

    <!-- AI 识别编码：对话 / 记录 / 语音 -->
    <view class="block">
      <view class="row-between">
        <text class="block-title">AI 识别编码</text>
        <text class="soft">描述孩子做了什么，自动匹配编码</text>
      </view>
      <textarea
        v-model="aiText"
        class="textarea"
        placeholder="例：孩子今天回家后不用提醒，自己把作业写完还检查了一遍"
        maxlength="300"
      />
      <view class="ai-actions">
        <button class="mini-btn" :loading="aiBusy" @click="suggestByAi">识别编码</button>
        <button class="mini-btn ghost" @click="startVoice">语音输入</button>
        <text class="link" @click="toggleRecords">{{ showRecords ? '收起记录' : '从记录选' }}</text>
      </view>
      <view v-if="showRecords" class="rec-pick">
        <text v-if="!records.length" class="soft">暂无记录可复用</text>
        <text v-for="(r, i) in records" :key="i" class="rec-item" @click="useRecord(r)">
          {{ r.title }} · {{ r.sub }}
        </text>
      </view>
      <view v-if="aiResult" class="ai-result">
        <text class="ai-code" v-if="aiResult.matched">
          {{ aiResult.code }} · {{ aiResult.dim_name }} · {{ aiResult.method }}
        </text>
        <text class="ai-code warn" v-else>未匹配到编码</text>
        <text class="ai-meta" v-if="aiResult.matched">
          置信度 {{ Math.round((aiResult.confidence || 0) * 100) }}% · 个性化位 {{ aiResult.personal }}
        </text>
        <text v-if="aiResult.quote" class="ai-quote">原文：{{ aiResult.quote }}</text>
        <text v-if="aiResult.advice" class="ai-advice">建议：{{ aiResult.advice }}</text>
        <text v-if="aiResult.reason" class="ai-hint">{{ aiResult.reason }}</text>
        <view class="ai-actions">
          <button v-if="aiResult.matched" class="mini-btn" @click="applyAiResult">采用该编码</button>
          <text class="link" @click="aiResult = null">清除</text>
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
          v-for="num in pickerNums"
          :key="num"
          class="num"
          :class="{ active: codes[currentCorner] === num }"
          @click="selectNum(num)"
        >
          {{ num }}
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
import { dimNameOf } from '@/constants/dimensions'
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
const note = ref('')
const pickerShow = ref(false)
const currentCorner = ref<Corner>('tl')
const records = ref<{ title: string; sub: string }[]>([])
const saving = ref(false)
const ownerId = ref('')
const child = ref<ChildRow | null>(null)
const role = ref<'parent' | 'teacher' | 'family'>('parent')
const aiText = ref('')
const aiBusy = ref(false)
const aiResult = ref<any>(null)
const showRecords = ref(false)

const isTeacher = computed(() => role.value === 'teacher')
const centerTip = computed(() => {
  if (isTeacher.value) return '点击中心切换学科'
  return '家长端不选学科，编码即为定位'
})

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

const stackHint = computed(() => {
  if (stampType.value === 'know' && knowKind.value !== '正向章') {
    return `${knowKind.value}不可叠章；换回正向章才能叠加`
  }
  return '二叠 = 2 枚、三叠 = 3 枚，按枚数累计当量'
})

const canStack = computed(() => {
  if (stampType.value === 'combo' || stampType.value === 'do') return true
  return knowKind.value === '正向章'
})

const valuePreview = computed(() => {
  const mul = stackKind.value === '三叠章' ? 3 : stackKind.value === '二叠章' ? 2 : 1
  // 统一成「+N 单位」：DE=知行对章、XE=行章、ZE=知章，不再写“XX当量”中文注解
  if (stampType.value === 'combo') return `+${mul} DE`
  if (stampType.value === 'do') return `+${mul} XE`
  if (knowKind.value === '引导章') return '不计当量（引导章）'
  if (knowKind.value === '改进章') return `+${2 * mul} ZE`
  return `+${mul} ZE`
})

const pickerTitle = computed(() => {
  const map = {
    tl: '左上 · 一级维度（1–7）',
    tr: '右上 · 二级指标',
    bl: '左下 · 三级行为',
    br: '右下 · 个性化编码',
  }
  return map[currentCorner.value]
})

/** 一级维度只有 1–7，其余角位 0–9 */
const pickerNums = computed(() => {
  if (currentCorner.value === 'tl') return [1, 2, 3, 4, 5, 6, 7]
  return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
})

onLoad(async () => {
  const user = requireLogin()
  if (!user) return
  ownerId.value = user.id
  role.value = (user.role as 'parent' | 'teacher' | 'family') || 'parent'
  // 家长端不选学科，中心只作体系标识
  if (role.value !== 'teacher') centerText.value = 'ZZE'
  try {
    if (String(user.id).startsWith('demo_')) {
      const { DEMO_STAMPS, getDemoCurrentChild } = await import('@/constants/demoData')
      child.value = getDemoCurrentChild()
      records.value = DEMO_STAMPS.slice(0, 10).map((r) => ({
        title: `${r.source === 'physical' ? '实体' : '虚拟'} · ${dimNameOf(String(r.code_text || '').charAt(0)) || '未归类'}`,
        sub: `${r.subject || '-'} · ${r.child_name || ''} · 编码${r.code_text}`,
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
    sub: `${dimNameOf(String(r.code_text || '').charAt(0)) || '未归类'} · 编码${r.code_text} · ${r.subject}${
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

/** 只有教师端保留中心选科；家长端不选科 */
function onCenterTap() {
  if (!isTeacher.value) {
    uni.showToast({ title: '家长端不用选学科，编码即定位', icon: 'none' })
    return
  }
  const idx = subjects.indexOf(centerText.value)
  centerText.value = subjects[(idx + 1) % subjects.length]
}

function toggleRecords() {
  showRecords.value = !showRecords.value
}

/** 复用历史记录里的 4 位编码，不再调模型 */
function useRecord(r: { title: string; sub: string }) {
  const m = /编码\s*(\d)(\d)(\d)(\d)/.exec(r.sub)
  if (!m) {
    uni.showToast({ title: '该记录没有可用编码', icon: 'none' })
    return
  }
  codeStore[stampType.value] = {
    tl: Number(m[1]),
    tr: Number(m[2]),
    bl: Number(m[3]),
    br: Number(m[4]),
  }
  showRecords.value = false
  uni.showToast({ title: `已复用编码 ${m[1]}${m[2]}${m[3]}${m[4]}`, icon: 'none' })
}

async function suggestByAi() {
  const text = aiText.value.trim()
  if (text.length < 4) {
    uni.showToast({ title: '先描述一下孩子做了什么', icon: 'none' })
    return
  }
  aiBusy.value = true
  try {
    const { suggestCode } = await import('@/services/aiCode')
    const r = await suggestCode(text, { role: role.value === 'teacher' ? 'teacher' : 'parent' })
    aiResult.value = r
    if (!r.matched) {
      uni.showToast({ title: r.reason || '信息不足，补一句具体行为', icon: 'none' })
    }
  } catch (e: any) {
    uni.showToast({ title: e.message || '识别失败', icon: 'none' })
  } finally {
    aiBusy.value = false
  }
}

/** 把 AI 结果填进四角与章型，仍可手动改 */
function applyAiResult() {
  const r = aiResult.value
  if (!r || !r.matched) return
  // 先切章型，再写该章型的编码，否则会写到上一个章型的缓存里
  stampType.value = r.stamp_type as StampType
  if (r.stamp_type === 'know' && r.know_kind) knowKind.value = r.know_kind
  if (r.stamp_type === 'know' && r.know_kind !== '正向章') stackKind.value = '无'
  codeStore[stampType.value] = {
    tl: r.level1,
    tr: r.level2,
    bl: r.level3,
    br: r.personal,
  }
  aiText.value = ''
  uni.showToast({ title: `已填入编码 ${r.code}`, icon: 'none' })
}

/** 语音输入：H5 用浏览器识别，不可用时提示通道待定 */
function startVoice() {
  const w = window as any
  const Rec = w.SpeechRecognition || w.webkitSpeechRecognition
  if (!Rec) {
    uni.showModal({
      title: '语音通道待接入',
      content: '当前环境不支持浏览器语音识别。可以先手动输入，或在 docs/待确认清单.md 里选定语音通道。',
      showCancel: false,
    })
    return
  }
  const rec = new Rec()
  rec.lang = 'zh-CN'
  rec.interimResults = false
  rec.maxAlternatives = 1
  rec.onresult = (e: any) => {
    const text = e.results?.[0]?.[0]?.transcript || ''
    if (text) aiText.value = text
  }
  rec.onerror = () => uni.showToast({ title: '语音识别失败，请手动输入', icon: 'none' })
  try {
    rec.start()
    uni.showToast({ title: '请说话…', icon: 'none' })
  } catch {
    uni.showToast({ title: '无法启动语音识别', icon: 'none' })
  }
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
      subject: isTeacher.value ? centerText.value : '',
      // 评价维度不再手选，改由编码推导：第 1 位即一级维度
      primaryDim: dimNameOf(c.tl),
      secondaryDim: `${c.tl}-${c.tr}`,
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

/* AI 识别编码 */
.center.locked {
  background: rgba(107, 114, 128, 0.08);
  color: #9ca3af;
  font-size: 24rpx;
}
.ai-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 16rpx;
}
.mini-btn {
  margin: 0;
  padding: 0 24rpx;
  height: 60rpx;
  line-height: 60rpx;
  font-size: 24rpx;
  color: #fff;
  background: #2563eb;
  border-radius: 12rpx;
}
.mini-btn::after {
  border: none;
}
.mini-btn.ghost {
  color: #2563eb;
  background: #eff6ff;
}
.link {
  font-size: 24rpx;
  color: #2563eb;
  margin-left: auto;
}
.rec-pick {
  margin-top: 12rpx;
  max-height: 300rpx;
  overflow-y: auto;
  background: #f9fafb;
  border-radius: 12rpx;
  padding: 8rpx 16rpx;
}
.rec-item {
  display: block;
  padding: 14rpx 0;
  font-size: 22rpx;
  color: #374151;
  border-bottom: 2rpx solid #eef2f7;
}
.rec-item:last-child {
  border-bottom: none;
}
.ai-result {
  margin-top: 16rpx;
  padding: 20rpx;
  background: #f0f9ff;
  border-radius: 12rpx;
}
.ai-code {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: #0369a1;
}
.ai-code.warn {
  color: #b45309;
  font-size: 26rpx;
}
.ai-meta {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #6b7280;
}
.ai-quote,
.ai-advice,
.ai-hint {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  line-height: 1.6;
  color: #374151;
}
.ai-hint {
  color: #6b7280;
}
</style>
