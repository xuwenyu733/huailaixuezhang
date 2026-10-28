/**
 * 印章识别服务对接配置（目录 backend）
 * 本地：先在 backend 目录运行 python app.py（默认 8765）
 * H5 开发可通过 Vite 代理 /seal-api → http://127.0.0.1:8765
 * 正式环境请换成可公网访问的识别服务地址，勿把 DeepSeek 密钥写进小程序。
 */
export const SEAL_API = {
  /** 留空则跳过桌面识别服务，改走腾讯云 / 模拟 */
  // #ifdef H5
  baseUrl: '/seal-api',
  // #endif
  // #ifndef H5
  baseUrl: '',
  // #endif
  /** deepseek | local | 空=服务端自动选 */
  engine: '',
  timeoutMs: 60000,
  allowFallback: true,
}

export default SEAL_API
