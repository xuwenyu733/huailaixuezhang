/**
 * 印章 OCR：优先 DeepSeek → 桌面 seal-api → 腾讯云 → 模拟。
 */
import { DEEPSEEK_OCR } from '@/config/deepseek'
import { TENCENT_OCR } from '@/config/ocr'

export interface OcrStampResult {
  mode: 'tencent' | 'mock' | 'seal-api' | 'deepseek'
  sealBody: string
  sealShape: string
  otherTexts: string[]
  /** 映射到业务字段 */
  subject: string
  primaryDim: string
  secondaryDim: string
  codeText: string
  valueText: string
  valueNum: number
  teacherStampNo: string
  /** 桌面印章识别扩展字段 */
  methodId?: number
  methodName?: string
  zhiCount?: number
  xingCount?: number
  cornerDigits?: Record<string, number | null>
  confidence?: number
  stampType?: 'know' | 'do' | 'combo'
  raw?: any
}

const SUBJECTS = ['语文', '数学', '英语', '科学', '德育', '综合']
const PRIMARY = ['智育', '德育', '体育', '美育', '劳育', '品格']
const SECONDARY = ['课堂参与', '作业完成', '测试达标', '志愿服务', '课堂发言']

function sha256Hex(message: string): Promise<ArrayBuffer> {
  // uni-app / 浏览器 SubtleCrypto
  const enc = new TextEncoder()
  return crypto.subtle.digest('SHA-256', enc.encode(message))
}

async function hmacSha256(key: ArrayBuffer | string, message: string): Promise<ArrayBuffer> {
  const enc = new TextEncoder()
  const keyData =
    typeof key === 'string' ? enc.encode(key) : new Uint8Array(key)
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  return crypto.subtle.sign('HMAC', cryptoKey, enc.encode(message))
}

function bufToHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

function getDateUTC(): string {
  return new Date().toISOString().slice(0, 10)
}

/** TC3 签名调用 SealOCR（依赖运行环境支持 SubtleCrypto） */
async function callTencentSealOcr(imageBase64: string): Promise<any> {
  const secretId = TENCENT_OCR.secretId
  const secretKey = TENCENT_OCR.secretKey
  if (!secretId || !secretKey) throw new Error('未配置腾讯云 OCR 密钥')
  if (!globalThis.crypto?.subtle) {
    throw new Error('当前环境不支持加密签名，请用 H5 或配置服务端代理')
  }

  const host = 'ocr.tencentcloudapi.com'
  const service = 'ocr'
  const action = 'SealOCR'
  const version = '2018-11-19'
  const region = TENCENT_OCR.region || 'ap-guangzhou'
  const timestamp = Math.floor(Date.now() / 1000).toString()
  const date = getDateUTC()
  const payload = JSON.stringify({
    ImageBase64: imageBase64.replace(/^data:image\/\w+;base64,/, ''),
    EnablePdf: false,
  })

  const hashedRequestPayload = bufToHex(await sha256Hex(payload))
  const canonicalHeaders =
    `content-type:application/json; charset=utf-8\nhost:${host}\nx-tc-action:${action.toLowerCase()}\n`
  const signedHeaders = 'content-type;host;x-tc-action'
  const canonicalRequest = [
    'POST',
    '/',
    '',
    canonicalHeaders,
    signedHeaders,
    hashedRequestPayload,
  ].join('\n')

  const credentialScope = `${date}/${service}/tc3_request`
  const stringToSign = [
    'TC3-HMAC-SHA256',
    timestamp,
    credentialScope,
    bufToHex(await sha256Hex(canonicalRequest)),
  ].join('\n')

  const secretDate = await hmacSha256(`TC3${secretKey}`, date)
  const secretService = await hmacSha256(secretDate, service)
  const secretSigning = await hmacSha256(secretService, 'tc3_request')
  const signature = bufToHex(await hmacSha256(secretSigning, stringToSign))

  const authorization =
    `TC3-HMAC-SHA256 Credential=${secretId}/${credentialScope}, ` +
    `SignedHeaders=${signedHeaders}, Signature=${signature}`

  const res: any = await new Promise((resolve, reject) => {
    uni.request({
      url: `https://${host}`,
      method: 'POST',
      header: {
        'Content-Type': 'application/json; charset=utf-8',
        Host: host,
        'X-TC-Action': action,
        'X-TC-Timestamp': timestamp,
        'X-TC-Version': version,
        'X-TC-Region': region,
        Authorization: authorization,
      },
      data: payload,
      success: (r) => resolve(r.data),
      fail: (e) => reject(e),
    })
  })

  if (res?.Response?.Error) {
    throw new Error(res.Response.Error.Message || '腾讯云 OCR 失败')
  }
  return res?.Response
}

function mapTencentToBiz(resp: any): OcrStampResult {
  const sealBody = String(resp?.SealBody || '')
  const otherTexts: string[] = Array.isArray(resp?.OtherTexts) ? resp.OtherTexts : []
  const digits = [...otherTexts, sealBody]
    .join(' ')
    .replace(/\D/g, '')
  const codeText = (digits.slice(0, 4) || '1234').padEnd(4, '0').slice(0, 4)

  let subject = SUBJECTS.find((s) => sealBody.includes(s)) || SUBJECTS[0]
  let primaryDim = PRIMARY.find((s) => sealBody.includes(s.slice(0, 1))) || '智育'
  let secondaryDim = SECONDARY[0]
  for (const s of SECONDARY) {
    if (sealBody.includes(s) || otherTexts.some((t) => String(t).includes(s))) {
      secondaryDim = s
      break
    }
  }

  const stampHint = otherTexts.find((t) => /^T\d+/i.test(String(t))) || ''
  const shape = String(resp?.SealShape ?? '')
  const valueNum = shape === '2' ? 10 : shape === '0' ? 8 : 10

  return {
    mode: 'tencent',
    sealBody,
    sealShape: shape,
    otherTexts,
    subject,
    primaryDim,
    secondaryDim,
    codeText,
    valueText: `+${valueNum} ZZE`,
    valueNum,
    teacherStampNo: stampHint || 'T0203',
    raw: resp,
  }
}

function mockRecognize(seed?: string): OcrStampResult {
  const s = String(seed || Date.now())
  let hash = 0
  for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0
  const subject = SUBJECTS[hash % SUBJECTS.length]
  const primaryDim = PRIMARY[hash % PRIMARY.length]
  const secondaryDim = SECONDARY[hash % SECONDARY.length]
  const codeText = String(1000 + (hash % 9000))
  const valueNum = 10
  return {
    mode: 'mock',
    sealBody: `模拟识别·${subject}·${primaryDim}`,
    sealShape: '2',
    otherTexts: [codeText, 'T0203'],
    subject,
    primaryDim,
    secondaryDim,
    codeText,
    valueText: `+${valueNum} ZZE`,
    valueNum,
    teacherStampNo: 'T0203',
  }
}

/** 读取本地临时图片为 base64（去 dataURL 前缀） */
export function readImageBase64(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    // #ifdef H5
    if (typeof fetch === 'function' && filePath.startsWith('blob:')) {
      fetch(filePath)
        .then((r) => r.blob())
        .then(
          (blob) =>
            new Promise<string>((res, rej) => {
              const reader = new FileReader()
              reader.onload = () => {
                const dataUrl = String(reader.result || '')
                resolve(dataUrl.replace(/^data:image\/\w+;base64,/, ''))
              }
              reader.onerror = () => rej(new Error('读取图片失败'))
              reader.readAsDataURL(blob)
            }),
        )
        .catch(reject)
      return
    }
    // #endif
    const fs = uni.getFileSystemManager?.()
    if (!fs) {
      reject(new Error('无法读取本地图片'))
      return
    }
    fs.readFile({
      filePath,
      encoding: 'base64',
      success: (r) => resolve(String(r.data || '')),
      fail: () => reject(new Error('读取图片失败')),
    })
  })
}

export async function recognizeStampImage(filePath: string): Promise<OcrStampResult> {
  if (filePath.startsWith('mock-')) return mockRecognize(filePath)

  // 1) DeepSeek 视觉（桌面印章识别同款提示词与 11 种盖法）
  try {
    const { hasDeepseekOcrConfig, recognizeViaDeepseek } = await import('./deepseekSeal')
    const { DEEPSEEK_OCR } = await import('@/config/deepseek')
    if (hasDeepseekOcrConfig()) {
      try {
        return await recognizeViaDeepseek(filePath)
      } catch (e: any) {
        if (!DEEPSEEK_OCR.allowMockFallback) throw e
        console.warn('[ocr] deepseek failed, fallback', e?.message || e)
      }
    }
  } catch (e: any) {
    console.warn('[ocr] deepseek unavailable', e?.message || e)
  }

  // 2) 桌面 Flask 印章识别服务（可选）
  try {
    const { hasSealApiConfig, recognizeViaSealApi } = await import('./sealRecognize')
    const { SEAL_API } = await import('@/config/sealApi')
    if (hasSealApiConfig()) {
      try {
        return await recognizeViaSealApi(filePath)
      } catch (e: any) {
        if (!SEAL_API.allowFallback) throw e
        console.warn('[ocr] seal-api failed, fallback', e?.message || e)
      }
    }
  } catch (e: any) {
    console.warn('[ocr] seal-api unavailable', e?.message || e)
  }

  // 3) 腾讯云 SealOCR（通用印章，盖法映射较弱）
  const hasKey = !!(TENCENT_OCR.secretId && TENCENT_OCR.secretKey)
  if (hasKey) {
    try {
      const b64 = await readImageBase64(filePath)
      const resp = await callTencentSealOcr(b64)
      return mapTencentToBiz(resp)
    } catch (e: any) {
      if (!TENCENT_OCR.allowMockFallback) throw e
      console.warn('[ocr] tencent failed, fallback mock', e?.message || e)
    }
  }
  return mockRecognize(filePath)
}

export function hasTencentOcrConfig(): boolean {
  return !!(TENCENT_OCR.secretId && TENCENT_OCR.secretKey)
}

export function hasDeepseekConfig(): boolean {
  return !!String(DEEPSEEK_OCR.secretKey || '').trim()
}

export async function hasAnyOcrBackend(): Promise<boolean> {
  try {
    const { hasDeepseekOcrConfig } = await import('./deepseekSeal')
    if (hasDeepseekOcrConfig()) return true
  } catch {
    /* ignore */
  }
  try {
    const { hasSealApiConfig } = await import('./sealRecognize')
    if (hasSealApiConfig()) return true
  } catch {
    /* ignore */
  }
  return hasTencentOcrConfig()
}
