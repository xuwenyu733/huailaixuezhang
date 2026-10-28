/**
 * 腾讯云印章识别 SealOCR 配置
 * 填入密钥后，采集页将走真实识别；留空则自动使用增强模拟识别。
 * 勿把密钥提交到公开仓库。
 */
export const TENCENT_OCR = {
  secretId: '',
  secretKey: '',
  region: 'ap-guangzhou',
  /** 是否允许无密钥时回退模拟识别 */
  allowMockFallback: true,
}

export default TENCENT_OCR
