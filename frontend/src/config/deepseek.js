/**
 * DeepSeek 视觉印章识别（对齐桌面「印章识别」项目）
 *
 * 填写方式（任选其一，勿提交真实密钥到公开仓库）：
 * 1. 本文件 secretKey
 * 2. 项目根目录 .env：VITE_DEEPSEEK_API_KEY=sk-xxx
 *
 * 注意：不要写 typeof import.meta，小程序编译会打出 require('url') 导致白屏。
 */
const envKey = String(import.meta.env.VITE_DEEPSEEK_API_KEY || '').trim()

export const DEEPSEEK_OCR = {
  /** DeepSeek API Key，形如 sk-xxx；也可直接写在这里覆盖 */
  secretKey: envKey,
  /** 视觉模型：deepseek-flash / deepseek-chat 等 */
  model: String(import.meta.env.VITE_DEEPSEEK_MODEL || 'deepseek-flash').trim(),
  baseUrl: 'https://api.deepseek.com',
  /** 失败时是否回退腾讯云 / 模拟 */
  allowMockFallback: true,
}

export default DEEPSEEK_OCR
