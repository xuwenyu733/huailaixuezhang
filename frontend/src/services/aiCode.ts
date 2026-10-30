/**
 * AI 编码识别（对话 / 语音转写 / 行为描述 → 4 位编码）。
 *
 * 走后端 Flask：POST /api/ai/code-suggest
 * 本地开发经 Vite 代理 /seal-api，正式环境由 SEAL_API.baseUrl 指定公网地址。
 * 密钥只在后端，前端不持有。
 */
import { SEAL_API } from '@/config/sealApi'

export interface AiCodeResult {
  matched: boolean
  /** 主线三位，如 1-1-1 */
  code: string
  level1: number | null
  level2: number
  level3: number
  /** 右下个性化位，无则 0 */
  personal: number
  digits: number[]
  dim_name: string
  method: string
  stamp_type: 'know' | 'do' | 'combo'
  know_kind: string
  quote: string
  advice: string
  confidence: number
  reason: string
}

export function hasAiCodeConfig(): boolean {
  return Boolean(SEAL_API.baseUrl)
}

export async function suggestCode(
  text: string,
  opts: { grade?: string; scene?: string; role?: 'parent' | 'teacher' } = {},
): Promise<AiCodeResult> {
  if (!SEAL_API.baseUrl) {
    throw new Error('未配置 AI 编码服务地址，请联系管理员')
  }

  const res: any = await new Promise((resolve, reject) => {
    uni.request({
      url: `${SEAL_API.baseUrl}/api/ai/code-suggest`,
      method: 'POST',
      timeout: SEAL_API.timeoutMs,
      header: { 'Content-Type': 'application/json' },
      data: {
        text,
        grade: opts.grade || '',
        scene: opts.scene || '',
        role: opts.role || 'parent',
      },
      success: (r: any) => resolve(r),
      fail: (e: any) => reject(new Error(e?.errMsg || '网络异常，请检查识别服务')),
    })
  })

  const data = res?.data || {}
  if (res?.statusCode === 402) {
    throw new Error(data.error || '识别服务额度不足或密钥失效，请联系管理员')
  }
  if (!data.ok) {
    throw new Error(data.error || `AI 编码识别失败（HTTP ${res?.statusCode}）`)
  }
  return data as AiCodeResult
}
