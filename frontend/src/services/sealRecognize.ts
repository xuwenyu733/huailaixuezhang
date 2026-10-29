/**
 * 对接桌面「印章识别」Flask API（/api/recognize）
 * 返回结构与 DeepSeek / 本地 OpenCV 一致的 stamps[]
 */
import { SEAL_API } from '@/config/sealApi'
import {
  formatSealValue,
  sealMethodById,
  type SealMethodDef,
} from '@/constants/sealMethods'
import type { OcrStampResult } from './ocr'
import { readImageBase64 } from './ocr'

export interface SealApiStamp {
  row?: number
  col?: number
  method_id?: number
  method_name?: string
  zhi?: number
  xing?: number
  orientation_deg?: number
  corner_digits?: Record<string, number | null>
  confidence?: number
  bbox?: number[]
}

export interface SealApiDegraded {
  stage?: string
  reason?: string
  action?: string
}

export interface SealApiIntegrity {
  cells_detected?: number
  cells_cropped?: number
  cells_recognized?: number
  groups_returned?: number
  groups_dropped?: number
  cells_failed?: number
  coverage?: number
}

export interface SealApiResponse {
  ok: boolean
  error?: string
  engine?: string
  mode?: string
  layout?: string
  page_note?: string
  stamps?: SealApiStamp[]
  summary?: Record<string, unknown>
  warning?: string | null
  degraded?: SealApiDegraded[]
  integrity?: SealApiIntegrity
  failed_cells?: unknown[]
  dropped_groups?: unknown[]
  result_image?: string
  preview_base64?: string
}

const STAGE_LABEL: Record<string, string> = {
  upstream: '上游服务',
  recognize: '整组识别',
  crop: '裁切',
  count: '枚数复核',
  orient: '朝向判定',
  digit_refine: '四角数字复核',
}

/** 把服务端的降级账本翻成人话，供采集页直接展示 */
function buildNotices(data: SealApiResponse): string[] {
  const notices: string[] = []
  if (data.warning) notices.push(data.warning)

  for (const d of data.degraded || []) {
    const stage = STAGE_LABEL[String(d.stage || '')] || String(d.stage || '识别')
    const reason = String(d.reason || '').trim()
    const action = String(d.action || '').trim()
    if (reason) notices.push(`${stage}降级：${reason}${action ? `（${action}）` : ''}`)
  }

  const dropped = data.dropped_groups?.length || 0
  if (dropped) notices.push(`有 ${dropped} 组定位到但未识别出枚数，已跳过，请人工核对`)
  const failed = data.failed_cells?.length || 0
  if (failed) notices.push(`${failed} 组识别请求失败，结果可能不完整`)
  if (data.layout === 'illustration') {
    notices.push('本页按盖法说明页版式识别，四角数字已忽略')
  }

  const groups = data.stamps?.length || 0
  if (groups > 1) notices.push(`本页共识别到 ${groups} 组盖章，已取置信度最高的一组`)
  return notices
}

export function hasSealApiConfig(): boolean {
  return !!String(SEAL_API.baseUrl || '').trim()
}

function cornerToCode(digits?: Record<string, number | null>): {
  tl: number
  tr: number
  bl: number
  br: number
  codeText: string
} {
  const tl = Number(digits?.['左上'] ?? digits?.tl ?? 0) || 0
  const tr = Number(digits?.['右上'] ?? digits?.tr ?? 0) || 0
  const bl = Number(digits?.['左下'] ?? digits?.bl ?? 0) || 0
  const br = Number(digits?.['右下'] ?? digits?.br ?? 0) || 0
  return {
    tl,
    tr,
    bl,
    br,
    codeText: `${tl}${tr}${bl}${br}`,
  }
}

function dimFromCode(tl: number, tr: number): { primary: string; secondary: string } {
  const primaryMap = ['综合', '德育', '智育', '体育', '美育', '劳育', '品格', '致远', '诚正', '其它']
  const secondaryMap = [
    '综合表现',
    '课堂参与',
    '作业完成',
    '测试达标',
    '志愿服务',
    '习惯养成',
    '合作交流',
    '创新实践',
    '体能达标',
    '艺术表现',
  ]
  return {
    primary: primaryMap[tl] || '智育',
    secondary: secondaryMap[tr] || '课堂参与',
  }
}

export function mapSealStampToOcr(
  stamp: SealApiStamp,
  engine: string,
): OcrStampResult {
  const methodId = Number(stamp.method_id) || 1
  const def: SealMethodDef | undefined = sealMethodById(methodId)
  const corners = cornerToCode(stamp.corner_digits)
  const dims = dimFromCode(corners.tl, corners.tr)
  const valueNum = def?.valueNum ?? 10
  const name = def?.name || stamp.method_name || `盖法${methodId}`
  const stampType = def?.stampType || 'know'

  return {
    mode: 'seal-api',
    sealBody: name,
    sealShape: stampType === 'do' ? '0' : stampType === 'combo' ? '1' : '2',
    otherTexts: [
      name,
      `知${stamp.zhi ?? def?.zhi ?? 0}`,
      `行${stamp.xing ?? def?.xing ?? 0}`,
      engine,
    ],
    subject: stampType === 'do' ? '行章' : stampType === 'combo' ? '知行对章' : '知章',
    primaryDim: dims.primary,
    secondaryDim: dims.secondary,
    codeText: corners.codeText,
    valueText: def ? formatSealValue(def) : `+${valueNum} ZZE`,
    valueNum,
    teacherStampNo: '',
    methodId,
    methodName: name,
    zhiCount: Number(stamp.zhi ?? def?.zhi ?? 0) || 0,
    xingCount: Number(stamp.xing ?? def?.xing ?? 0) || 0,
    cornerDigits: stamp.corner_digits || {},
    confidence: Number(stamp.confidence) || 0,
    stampType,
    raw: stamp,
  }
}

function pickBest(list: SealApiStamp[]): SealApiStamp {
  return [...list].sort(
    (a, b) => Number(b.confidence || 0) - Number(a.confidence || 0),
  )[0]
}

async function postRecognizeH5(filePath: string, url: string): Promise<SealApiResponse> {
  const b64 = await readImageBase64(filePath)
  const byteChars = atob(b64)
  const byteNums = new Array(byteChars.length)
  for (let i = 0; i < byteChars.length; i++) byteNums[i] = byteChars.charCodeAt(i)
  const blob = new Blob([new Uint8Array(byteNums)], { type: 'image/jpeg' })
  const form = new FormData()
  form.append('file', blob, 'stamp.jpg')
  if (SEAL_API.engine) form.append('engine', SEAL_API.engine)
  const resp = await fetch(url, { method: 'POST', body: form })
  return (await resp.json()) as SealApiResponse
}

function postRecognizeUpload(filePath: string, url: string): Promise<SealApiResponse> {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url,
      filePath,
      name: 'file',
      formData: SEAL_API.engine ? { engine: SEAL_API.engine } : {},
      timeout: SEAL_API.timeoutMs || 60000,
      success: (res) => {
        try {
          resolve(JSON.parse(String(res.data || '')) as SealApiResponse)
        } catch (e: any) {
          reject(new Error(e?.message || '解析识别结果失败'))
        }
      },
      fail: (e) => reject(new Error(e.errMsg || '上传识别失败')),
    })
  })
}

/** 探测印章识别服务是否在线，供采集页显示状态 */
export async function checkSealApiHealth(): Promise<{
  ok: boolean
  engine?: string
  detail: string
}> {
  const base = String(SEAL_API.baseUrl || '').replace(/\/$/, '')
  if (!base) return { ok: false, detail: '未配置识别服务地址' }
  try {
    const resp = await fetch(`${base}/api/health`)
    const data: any = await resp.json()
    const failed = (data?.checks || []).filter((c: any) => !c.ok)
    return {
      ok: !!data?.ok,
      engine: data?.engine,
      detail: data?.ok
        ? `识别服务在线 · ${data?.engine || 'deepseek+cv'}`
        : failed.map((c: any) => `${c.name} ${c.detail || ''}`).join('；') || '识别服务未就绪',
    }
  } catch (e: any) {
    return { ok: false, detail: '识别服务未启动（backend: python app.py）' }
  }
}

/** 上传本地图片到印章识别服务，取置信度最高的一枚 */
export async function recognizeViaSealApi(
  filePath: string,
): Promise<OcrStampResult> {
  const base = String(SEAL_API.baseUrl || '').replace(/\/$/, '')
  if (!base) throw new Error('未配置印章识别服务地址')

  const url = `${base}/api/recognize${SEAL_API.engine ? `?engine=${SEAL_API.engine}` : ''}`

  let data: SealApiResponse
  // #ifdef H5
  data = await postRecognizeH5(filePath, url)
  // #endif
  // #ifndef H5
  data = await postRecognizeUpload(filePath, url)
  // #endif

  if (!data.ok) {
    const reason = data.error || '印章识别失败'
    const detail = (data.degraded || [])
      .map((d) => String(d.reason || '').trim())
      .filter(Boolean)[0]
    throw new Error(detail ? `${reason}：${detail}` : reason)
  }
  const list = data.stamps || []
  if (!list.length) throw new Error('未识别到印章，请重拍或改用虚拟盖章')
  const best = mapSealStampToOcr(pickBest(list), data.engine || 'seal-api')
  return {
    ...best,
    notices: buildNotices(data),
    groupCount: list.length,
    layout: data.layout,
    resultImage: data.result_image,
    integrity: data.integrity,
  }
}
