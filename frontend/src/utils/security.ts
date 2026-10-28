/** 基础信息安全：校验与脱敏（不上报明文密码） */

import { getStorage } from '@/utils/storage'

/** 按隐私设置决定是否脱敏（读 hlxz_user_prefs 本地缓存） */
export function displayPhone(phone: string): string {
  const prefs = getStorage<{ maskPhone?: boolean }>('user_prefs', { maskPhone: true })
  return prefs.maskPhone === false ? String(phone || '') : maskPhone(phone)
}

export function maskPhone(phone: string): string {
  const p = String(phone || '').replace(/\D/g, '')
  if (p.length < 7) return phone || ''
  return `${p.slice(0, 3)}****${p.slice(-4)}`
}

export function validatePhone(phone: string): string | null {
  if (!/^1\d{10}$/.test(String(phone || '').trim())) {
    return '请输入正确的手机号'
  }
  return null
}

/** 至少 6 位，且同时含字母与数字 */
export function validatePassword(password: string): string | null {
  const p = String(password || '')
  if (p.length < 6) return '密码至少 6 位'
  if (p.length > 32) return '密码最多 32 位'
  if (!/[A-Za-z]/.test(p) || !/\d/.test(p)) {
    return '密码需同时包含字母和数字'
  }
  return null
}

export function formatShortDate(iso?: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 10)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
