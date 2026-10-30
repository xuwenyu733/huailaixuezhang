<template>
  <view class="page">
    <view class="nav-extra">
      <text class="link" @click="onAlbum">相册</text>
      <text class="link strong" @click="goStamp">虚拟章</text>
    </view>

    <view class="camera">
      <view class="frame">
        <image v-if="preview" :src="preview" mode="aspectFit" class="preview-img" />
        <template v-else>
          <view class="scan-line" />
          <view class="ghost know" />
          <view class="ghost do" />
          <text class="hint">将印章与记录卡置于框内</text>
        </template>
      </view>
      <view class="controls">
        <view class="ctrl" @click="onAlbum">相册</view>
        <view class="shutter" :class="{ busy: recognizing }" @click="onShutter" />
        <view class="ctrl" @click="clearPreview">清除</view>
      </view>
      <view v-if="recognizing" class="ocr-busy">
        <text class="ocr-busy-txt">正在识别印章…</text>
      </view>
      <view v-if="isTeacher" class="card-lookup">
        <input class="card-inp" v-model="cardInput" placeholder="教师采集：输入学生记录卡编号" />
        <text class="card-btn" @click="lookupCard">查找</text>
      </view>
      <text class="foot">{{ ocrHint }}</text>
    </view>

    <view class="mask" v-if="showResult" @click="showResult = false" />
    <view class="modal" v-if="showResult">
      <text class="modal-title">识别结果</text>
      <view class="result-head">
        <view class="stamp-square" />
        <view>
          <text class="rt">{{ result.methodName || '知章' }} · {{ dimName || '未识别维度' }}</text>
          <text class="rs">编码 {{ codeLine }} · 个性化 {{ codePersonal }}</text>
        </view>
      </view>
      <view class="kv" v-if="!editing">
        <text>中心溯源区：{{ result.subject }}</text>
        <text>主线编码（维度-指标-行为）：{{ codeLine }}</text>
        <text>个性化编码（右下）：{{ codePersonal }}</text>
        <text>场景因子α：1.0</text>
        <text v-if="result.methodName">盖法：{{ result.methodName }}</text>
        <text v-if="result.methodName">知章×{{ result.zhiCount || 0 }} · 行章×{{ result.xingCount || 0 }}</text>
        <text class="blue">本次当量：{{ result.valueText }}（{{ engineLabel }}）</text>
      </view>
      <view v-if="result.notices.length" class="tips">
        <text v-for="(t, i) in result.notices" :key="i" class="tip">· {{ t }}</text>
      </view>
      <view class="edit" v-else>
        <input class="inp" v-model="result.subject" placeholder="学科" />
        <input class="inp" v-model="result.codeText" placeholder="4 位编码，如 1120" />
        <input class="inp" v-model="result.valueText" placeholder="当量文案" />
        <input class="inp" v-model="result.note" placeholder="备注" />
      </view>
      <view class="student">
        <view class="av">{{ childAvatar }}</view>
        <view>
          <text class="sn">{{ childName }}</text>
          <text class="ss">记录卡编号：{{ childCard }}</text>
        </view>
      </view>
      <text class="meta">采集时间：{{ result.time }}</text>
      <text class="meta">操作教师：{{ result.teacherName }}（印章编号：{{ result.teacherStampNo }}）</text>
      <text class="warn">
        确认上传后数据将进入成长评价报告。若未绑定孩子，将阻止上传。
      </text>
      <view class="actions">
        <button class="ghost" @click="showResult = false">重新识别</button>
        <button class="ghost" @click="editing = !editing">{{ editing ? '完成修改' : '修改数据' }}</button>
        <button class="primary" :loading="uploading" @click="onConfirm">确认上传</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getCurrentUser, requireLogin } from '@/services/auth'
import { findChildByCardNo, getCurrentChild } from '@/services/childRepo'
import { bumpActiveGoals } from '@/services/goalRepo'
import { pushMessage } from '@/services/messageRepo'
import { DEEPSEEK_OCR } from '@/config/deepseek'
import { SEAL_API } from '@/config/sealApi'
import { hasTencentOcrConfig, recognizeStampImage } from '@/services/ocr'
import { checkSealApiHealth, hasSealApiConfig } from '@/services/sealRecognize'
import { saveStamp } from '@/services/stampRepo'
import { dimNameOf, splitCode } from '@/constants/dimensions'
import type { ChildRow } from '@/types/user'

const showResult = ref(false)
const editing = ref(false)
const uploading = ref(false)
const preview = ref('')
const child = ref<ChildRow | null>(null)
const ownerId = ref('')
const role = ref('parent')
const cardInput = ref('')
const recognizing = ref(false)
const serviceStatus = ref<'unknown' | 'ok' | 'down'>('unknown')
const serviceDetail = ref('')

const isTeacher = computed(() => role.value === 'teacher')
const ocrHint = computed(() => {
  if (SEAL_API.baseUrl) {
    if (serviceStatus.value === 'ok') return serviceDetail.value
    if (serviceStatus.value === 'down') return `${serviceDetail.value}`
    return '正在检测印章识别服务…'
  }
  if (DEEPSEEK_OCR.secretKey) {
    return '已配置 DeepSeek 视觉识别（11 种盖法），相册/快门将走真实识别'
  }
  if (hasTencentOcrConfig()) {
    return '已配置腾讯云印章识别，相册/快门将走真实识别'
  }
  return '未配置 DeepSeek Key，当前为模拟识别。请在 .env 填写 VITE_DEEPSEEK_API_KEY'
})
const engineLabel = computed(() => {
  if (result.mode === 'deepseek') return 'DeepSeek'
  if (result.mode === 'seal-api') return '印章识别服务'
  if (result.mode === 'tencent') return '腾讯云'
  return '模拟'
})

const result = reactive({
  subject: '语文',
  primaryDim: '智育',
  secondaryDim: '课堂参与',
  codeText: '1234',
  valueText: '+1 XE',
  valueNum: 100,
  note: '',
  teacherName: '李老师',
  teacherStampNo: 'T0203',
  time: '',
  mode: 'mock' as 'mock' | 'tencent' | 'seal-api' | 'deepseek',
  sealBody: '',
  methodName: '',
  methodId: 0,
  zhiCount: 0,
  xingCount: 0,
  stampType: 'know' as 'know' | 'do' | 'combo',
  notices: [] as string[],
})

/** 编码固定 4 位：前 3 位主线（维度-指标-行为），第 4 位个性化 */
const codeParts = computed(() => splitCode(result.codeText))
const codeLine = computed(() => codeParts.value.line)
const codePersonal = computed(() => codeParts.value.personal)
const dimName = computed(() => dimNameOf(codeParts.value.tl))

const childAvatar = computed(
  () => child.value?.avatar_text || child.value?.name?.slice(0, 1) || '学',
)
const childName = computed(() =>
  child.value ? `${child.value.name} · ${child.value.class_name || ''}` : '未绑定孩子',
)
const childCard = computed(() => child.value?.card_no || '—')

onShow(async () => {
  probeService()
  const user = requireLogin()
  if (!user) return
  ownerId.value = user.id
  role.value = user.role
  if (user.role === 'teacher') {
    result.teacherName = user.name
    result.teacherStampNo = user.stampNo || user.inviteCode
  }
  if (String(user.id).startsWith('demo_')) {
    const { getDemoCurrentChild } = await import('@/constants/demoData')
    child.value = getDemoCurrentChild()
  } else if (user.role !== 'teacher') {
    try {
      child.value = await getCurrentChild(user.id)
    } catch {
      child.value = null
    }
  }
})

async function probeService() {
  if (!hasSealApiConfig()) return
  const r = await checkSealApiHealth()
  serviceStatus.value = r.ok ? 'ok' : 'down'
  serviceDetail.value = r.detail
}

function stampNow() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  result.time = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

async function applyOcr(filePath: string) {
  recognizing.value = true
  try {
    const ocr = await recognizeStampImage(filePath)
    result.subject = ocr.subject
    result.primaryDim = ocr.primaryDim
    result.secondaryDim = ocr.secondaryDim
    result.codeText = ocr.codeText
    result.valueText = ocr.valueText
    result.valueNum = ocr.valueNum
    result.teacherStampNo = isTeacher.value
      ? getCurrentUser()?.stampNo || ocr.teacherStampNo
      : ocr.teacherStampNo
    result.mode = ocr.mode
    result.sealBody = ocr.sealBody
    result.methodName = ocr.methodName || ''
    result.methodId = ocr.methodId || 0
    result.zhiCount = ocr.zhiCount || 0
    result.xingCount = ocr.xingCount || 0
    result.stampType = ocr.stampType || 'know'
    result.notices = ocr.notices || []
    result.note = ''
    editing.value = false
    stampNow()
    showResult.value = true
  } catch (e: any) {
    const msg = String(e?.message || '识别失败')
    // 上游余额/密钥问题给一句人话，别把英文原文糊到教师脸上
    const friendly = /402|Insufficient Balance|401|403|余额/i.test(msg)
      ? '识别服务额度不足或密钥失效，请联系管理员'
      : msg
    uni.showToast({ title: friendly, icon: 'none' })
  } finally {
    recognizing.value = false
  }
}

async function lookupCard() {
  const card = cardInput.value.trim()
  if (!card) {
    uni.showToast({ title: '请输入记录卡编号', icon: 'none' })
    return
  }
  try {
    const row = await findChildByCardNo(card)
    if (!row) {
      uni.showToast({ title: '未找到该记录卡', icon: 'none' })
      child.value = null
      return
    }
    child.value = row
    uni.showToast({ title: `已匹配 ${row.name}`, icon: 'none' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '查找失败', icon: 'none' })
  }
}

function onShutter() {
  if (recognizing.value) return
  applyOcr(preview.value || `mock-${Date.now()}`)
}
function clearPreview() {
  if (recognizing.value) return
  preview.value = ''
}
function goStamp() {
  uni.navigateTo({ url: '/pages/stamp/stamp' })
}
function onAlbum() {
  if (recognizing.value) return
  uni.chooseImage({
    count: 1,
    success: (res) => {
      preview.value = res.tempFilePaths[0]
      applyOcr(preview.value)
    },
  })
}

async function onConfirm() {
  const user = requireLogin()
  if (!user) return
  if (String(user.id).startsWith('demo_')) {
    uni.showToast({ title: '演示账号请用正式账号上传', icon: 'none' })
    return
  }
  if (!child.value) {
    uni.showModal({
      title: '未绑定孩子',
      content: '请先在「我的孩子」中添加孩子',
      confirmText: '去添加',
      success: (res) => {
        if (res.confirm) uni.navigateTo({ url: '/pages/children/children' })
      },
    })
    return
  }

  uploading.value = true
  try {
    const code = result.codeText.replace(/\D/g, '').padStart(4, '0').slice(0, 4)
    await saveStamp({
      ownerId: user.id,
      ownerRole: user.role === 'teacher' ? 'teacher' : 'parent',
      childId: child.value.Id,
      childName: child.value.name,
      cardNo: child.value.card_no,
      source: 'physical',
      stampType: result.stampType || 'know',
      knowKind: result.methodName || '实体章',
      stackKind:
        (result.zhiCount || 0) + (result.xingCount || 0) > 1 ? '叠章' : '无',
      subject: result.subject,
      // 维度由编码推导，不再手填
      primaryDim: dimNameOf(code[0]),
      secondaryDim: `${Number(code[0])}-${Number(code[1])}`,
      codeTl: Number(code[0] || 0),
      codeTr: Number(code[1] || 0),
      codeBl: Number(code[2] || 0),
      codeBr: Number(code[3] || 0),
      codeText: code,
      valueText: result.valueText,
      valueNum: result.valueNum,
      teacherName: result.teacherName,
      teacherStampNo: result.teacherStampNo,
      imageUrl: preview.value || '',
      note: result.note,
      status: 'confirmed',
    })
    if (child.value.parent_id) {
      await bumpActiveGoals(child.value.parent_id, child.value.Id, result.valueNum)
      await pushMessage({
        ownerId: child.value.parent_id,
        title: '盖章已记录',
        content: `${child.value.name} 获得实体章 ${result.valueText}`,
        category: 'stamp',
      })
    }
    showResult.value = false
    preview.value = ''
    uni.showToast({ title: '上传成功', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '上传失败', icon: 'none' })
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #111827;
  padding-bottom: 40rpx;
}
.nav-extra {
  display: flex;
  justify-content: flex-end;
  gap: 32rpx;
  padding: 16rpx 32rpx;
}
.link { color: rgba(255,255,255,.75); font-size: 26rpx; }
.link.strong { color: #93c5fd; font-weight: 600; }
.camera { padding: 0 24rpx; }
.frame {
  height: 720rpx; border-radius: 24rpx; border: 2rpx dashed rgba(255,255,255,.35);
  position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center;
  background: #1f2937;
}
.preview-img { width: 100%; height: 100%; }
.scan-line {
  position: absolute; left: 10%; right: 10%; height: 4rpx; background: #60a5fa;
  animation: scan 2.4s linear infinite;
}
@keyframes scan {
  0% { top: 12%; }
  100% { top: 88%; }
}
.ghost {
  position: absolute; opacity: .25; border: 4rpx solid #93c5fd;
}
.ghost.know { width: 120rpx; height: 120rpx; left: 28%; top: 38%; }
.ghost.do { width: 120rpx; height: 120rpx; border-radius: 50%; right: 28%; top: 42%; }
.hint { color: rgba(255,255,255,.7); font-size: 24rpx; z-index: 2; }
.controls {
  margin-top: 40rpx; display: flex; justify-content: space-around; align-items: center; color: #fff;
}
.ctrl { font-size: 26rpx; opacity: .85; }
.shutter {
  width: 120rpx; height: 120rpx; border-radius: 50%;
  border: 8rpx solid #fff; background: #2563eb;
}
.shutter.busy {
  opacity: 0.45;
}
.ocr-busy {
  margin-top: 24rpx;
  text-align: center;
}
.ocr-busy-txt {
  display: inline-block;
  padding: 12rpx 28rpx;
  border-radius: 999rpx;
  background: rgba(37, 99, 235, 0.35);
  color: #dbeafe;
  font-size: 24rpx;
}
.foot {
  display: block; text-align: center; margin-top: 28rpx;
  color: rgba(255,255,255,.55); font-size: 22rpx; padding: 0 24rpx; line-height: 1.5;
}
.card-lookup {
  margin: 20rpx 24rpx 0; display: flex; gap: 12rpx; align-items: center;
}
.card-inp {
  flex: 1; height: 72rpx; background: #1f2937; color: #fff;
  border-radius: 12rpx; padding: 0 20rpx; font-size: 24rpx;
}
.card-btn { color: #93c5fd; font-size: 26rpx; }
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.5); z-index: 90; }
.modal {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 100;
  background: #fff; border-radius: 28rpx 28rpx 0 0; padding: 36rpx 28rpx 48rpx;
  max-height: 85vh; overflow-y: auto;
}
.modal-title { display: block; font-size: 32rpx; font-weight: 700; margin-bottom: 24rpx; }
.result-head { display: flex; gap: 16rpx; align-items: center; margin-bottom: 16rpx; }
.stamp-square { width: 72rpx; height: 72rpx; background: #2563eb; border-radius: 12rpx; }
.rt { display: block; font-size: 28rpx; font-weight: 600; }
.rs { display: block; margin-top: 6rpx; font-size: 22rpx; color: #6b7280; }
.kv text { display: block; font-size: 24rpx; color: #374151; line-height: 1.8; }
.kv .blue { color: #2563eb; font-weight: 600; }
.tips {
  margin-top: 14rpx; padding: 14rpx 16rpx; background: #fffbeb;
  border-radius: 12rpx; border-left: 4rpx solid #f59e0b;
}
.tip {
  display: block; font-size: 22rpx; color: #92400e; line-height: 1.6;
}
.edit .inp {
  height: 76rpx; background: #f9fafb; border: 2rpx solid #e5e7eb; border-radius: 12rpx;
  padding: 0 20rpx; margin-bottom: 12rpx; font-size: 26rpx;
}
.student {
  margin-top: 20rpx; padding: 20rpx; background: #f9fafb; border-radius: 16rpx;
  display: flex; gap: 16rpx; align-items: center;
}
.av {
  width: 64rpx; height: 64rpx; border-radius: 50%; background: #dbeafe; color: #2563eb;
  display: flex; align-items: center; justify-content: center; font-weight: 700;
}
.sn { display: block; font-size: 26rpx; font-weight: 600; }
.ss { display: block; margin-top: 4rpx; font-size: 22rpx; color: #9ca3af; }
.meta { display: block; margin-top: 10rpx; font-size: 22rpx; color: #6b7280; }
.warn {
  display: block; margin-top: 16rpx; padding: 16rpx; background: #fff7ed;
  color: #c2410c; font-size: 22rpx; line-height: 1.6; border-radius: 12rpx;
}
.actions { display: flex; gap: 12rpx; margin-top: 24rpx; }
.actions button { flex: 1; font-size: 24rpx; height: 76rpx; line-height: 76rpx; border-radius: 12rpx; }
.actions .ghost { background: #f3f4f6; color: #374151; }
.actions .primary { background: #2563eb; color: #fff; }
.actions button::after { border: none; }
</style>
