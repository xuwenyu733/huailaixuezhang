/**
 * DeepSeek 视觉 API 印章识别（从桌面「印章识别」deepseek_ocr.py 移植）
 */
import { DEEPSEEK_OCR } from '@/config/deepseek'
import {
  DEEPSEEK_SEAL_SYSTEM,
  DEEPSEEK_SEAL_USER,
} from '@/constants/deepseekSealPrompt'
import { mapSealStampToOcr, type SealApiStamp } from './sealRecognize'
import type { OcrStampResult } from './ocr'
import { readImageBase64 } from './ocr'

export function hasDeepseekOcrConfig(): boolean {
  return !!String(DEEPSEEK_OCR.secretKey || '').trim()
}

function extractJson(text: string): Record<string, any> {
  let raw = String(text || '').trim()
  if (!raw) throw new Error('模型返回为空')
  const fence = raw.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (fence) raw = fence[1].trim()
  try {
    const data = JSON.parse(raw)
    if (Array.isArray(data)) return { stamps: data }
    if (data && typeof data === 'object') return data
  } catch {
    /* try slice */
  }
  const start = raw.indexOf('{')
  const end = raw.lastIndexOf('}')
  if (start >= 0 && end > start) {
    return JSON.parse(raw.slice(start, end + 1))
  }
  throw new Error('无法从模型回复中解析 JSON')
}

function normDigit(v: unknown): number | null {
  if (v === null || v === undefined || v === '' || v === '—' || v === '-') return null
  if (typeof v === 'boolean') return null
  if (typeof v === 'number') {
    const n = Math.trunc(v)
    return n >= 0 && n <= 9 ? n : null
  }
  const s = String(v).trim()
  if (/^\d$/.test(s)) return Number(s)
  return null
}

function normalizeStamps(raw: Record<string, any>): SealApiStamp[] {
  let items = raw.stamps
  if (items == null && raw.data && typeof raw.data === 'object') {
    items = raw.data.stamps
  }
  if (!Array.isArray(items)) throw new Error('JSON 缺少 stamps 数组')

  return items
    .filter((st) => st && typeof st === 'object')
    .map((st: any, i: number) => {
      const cornersIn = st.corner_digits && typeof st.corner_digits === 'object' ? st.corner_digits : {}
      const methodId = Number(st.method_id)
      return {
        row: Number.isFinite(Number(st.row)) ? Number(st.row) : -1,
        col: Number.isFinite(Number(st.col)) ? Number(st.col) : -1,
        method_id: Number.isFinite(methodId) ? methodId : 0,
        method_name: String(st.method_name || `盖法${st.method_id || i + 1}`),
        zhi: Number(st.zhi) || 0,
        xing: Number(st.xing) || 0,
        orientation_deg: st.orientation_deg != null ? Number(st.orientation_deg) : undefined,
        corner_digits: {
          左上: normDigit(cornersIn['左上']),
          右上: normDigit(cornersIn['右上']),
          左下: normDigit(cornersIn['左下']),
          右下: normDigit(cornersIn['右下']),
        },
        confidence: Number(st.confidence) || 0.8,
        bbox: st.bbox,
      } as SealApiStamp
    })
}

async function callDeepseekVision(imageBase64: string): Promise<SealApiStamp[]> {
  const key = String(DEEPSEEK_OCR.secretKey || '').trim()
  if (!key) throw new Error('未配置 DeepSeek API Key')

  const pure = imageBase64.replace(/^data:image\/\w+;base64,/, '')
  const dataUrl = `data:image/jpeg;base64,${pure}`
  const base = String(DEEPSEEK_OCR.baseUrl || 'https://api.deepseek.com').replace(/\/$/, '')
  const model = DEEPSEEK_OCR.model || 'deepseek-flash'

  const resp = await new Promise<UniApp.RequestSuccessCallbackResult>((resolve, reject) => {
    uni.request({
      url: `${base}/chat/completions`,
      method: 'POST',
      timeout: 90000,
      header: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${key}`,
      },
      data: {
        model,
        messages: [
          { role: 'system', content: DEEPSEEK_SEAL_SYSTEM },
          {
            role: 'user',
            content: [
              { type: 'text', text: DEEPSEEK_SEAL_USER },
              {
                type: 'image_url',
                image_url: { url: dataUrl, detail: 'high' },
              },
            ],
          },
        ],
        temperature: 0.1,
        max_tokens: 8192,
        // deepseek-flash 默认 thinking 会占满 max_tokens，导致 content 为空
        thinking: { type: 'disabled' },
      },
      success: resolve,
      fail: (e) => reject(new Error(e.errMsg || 'DeepSeek 请求失败')),
    })
  })

  const status = Number(resp.statusCode || 0)
  const body: any = resp.data
  if (status < 200 || status >= 300) {
    const msg = body?.error?.message || body?.msg || `HTTP ${status}`
    throw new Error(`DeepSeek 调用失败：${msg}`)
  }

  const msg = body?.choices?.[0]?.message
  const content = String(msg?.content || '').trim()
  if (!content) {
    const finish = body?.choices?.[0]?.finish_reason
    throw new Error(
      `模型返回为空（finish=${finish || 'unknown'}）。请确认已关闭 thinking 后重试。`,
    )
  }

  const parsed = extractJson(content)
  return normalizeStamps(parsed)
}

/** 用 DeepSeek 识别本地图片，取置信度最高的一枚盖印 */
export async function recognizeViaDeepseek(
  filePath: string,
): Promise<OcrStampResult> {
  const b64 = await readImageBase64(filePath)
  const stamps = await callDeepseekVision(b64)
  if (!stamps.length) {
    throw new Error('未识别到印章，请重拍或改用虚拟盖章')
  }
  const best = [...stamps].sort(
    (a, b) => Number(b.confidence || 0) - Number(a.confidence || 0),
  )[0]
  const mapped = mapSealStampToOcr(best, 'deepseek')
  mapped.mode = 'deepseek'
  return mapped
}
