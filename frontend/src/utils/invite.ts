/** 生成 6 位家长推荐码，如 HA8K2M */
export function generateInviteCode(seed?: string): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  let hash = 0
  const base = seed || `${Date.now()}${Math.random()}`
  for (let i = 0; i < base.length; i++) {
    hash = (hash * 31 + base.charCodeAt(i)) >>> 0
  }
  let code = ''
  let n = hash
  for (let i = 0; i < 6; i++) {
    code += chars[n % chars.length]
    n = Math.floor(n / chars.length) + i * 17
  }
  return `HA${code}`
}

export function normalizeInviteCode(code: string): string {
  return code.trim().toUpperCase().replace(/\s+/g, '')
}

export function isValidInviteCodeFormat(code: string): boolean {
  return /^HA[A-Z0-9]{6}$/.test(normalizeInviteCode(code))
}
