import { TABLES } from '@/constants/tables'
import { getStorage, removeStorage, setStorage } from '@/utils/storage'
import { n, q, queryBySql, updateBySql } from './pmis'
import { getLocalSession } from './session'

const UNLOCK_MS = 30 * 60 * 1000

function pinKey(userId: string) {
  return `mall_pin_${userId}`
}
function unlockKey(userId: string) {
  return `mall_unlock_${userId}`
}

/** 商城仅家长端（含家长演示）可进 */
export function canAccessMall(): boolean {
  const user = getLocalSession()
  if (!user) return false
  if (user.role === 'teacher' || user.role === 'school') return false
  if (user.id === 'demo_school') return false
  return user.role === 'parent' || user.id === 'demo_family'
}

export function hasMallPin(userId?: string): boolean {
  const id = userId || getLocalSession()?.id
  if (!id) return false
  return !!getStorage(pinKey(String(id)), '')
}

export function isMallUnlocked(userId?: string): boolean {
  const id = userId || getLocalSession()?.id
  if (!id) return false
  const until = Number(getStorage(unlockKey(String(id)), 0)) || 0
  return until > Date.now()
}

export function lockMall(userId?: string): void {
  const id = userId || getLocalSession()?.id
  if (!id) return
  removeStorage(unlockKey(String(id)))
}

export function unlockMall(userId?: string): void {
  const id = userId || getLocalSession()?.id
  if (!id) return
  setStorage(unlockKey(String(id)), Date.now() + UNLOCK_MS)
}

export async function loadMallPin(userId: string): Promise<string> {
  const local = getStorage(pinKey(userId), '')
  if (local) return String(local)
  if (String(userId).startsWith('demo_')) return ''
  try {
    const rows = await queryBySql(`
      select mall_pin from ${TABLES.prefs}
      where isDel = 0 and owner_id = ${n(userId)}
      limit 1
    `.replace(/\s+/g, ' ').trim())
    const pin = String(rows[0]?.mall_pin || '')
    if (pin) setStorage(pinKey(userId), pin)
    return pin
  } catch {
    return ''
  }
}

export async function setMallPin(userId: string, pin: string): Promise<void> {
  const p = String(pin || '').trim()
  if (!/^\d{4,6}$/.test(p)) {
    throw new Error('商城密码需为 4–6 位数字')
  }
  setStorage(pinKey(userId), p)
  if (String(userId).startsWith('demo_')) return
  try {
    const rows = await queryBySql(`
      select Id from ${TABLES.prefs}
      where isDel = 0 and owner_id = ${n(userId)}
      limit 1
    `.replace(/\s+/g, ' ').trim())
    if (rows[0]?.Id != null) {
      await updateBySql(`
        update ${TABLES.prefs}
        set mall_pin = ${q(p)}, updated_at = ${q(new Date().toISOString())}
        where Id = ${n(rows[0].Id)} and isDel = 0
      `.replace(/\s+/g, ' ').trim())
    } else {
      // 无偏好行时只写本地；首次保存偏好时再同步
      const { saveUserPrefs, getUserPrefs } = await import('./prefsRepo')
      await saveUserPrefs(userId, await getUserPrefs(userId))
      await updateBySql(`
        update ${TABLES.prefs}
        set mall_pin = ${q(p)}
        where owner_id = ${n(userId)} and isDel = 0
      `.replace(/\s+/g, ' ').trim())
    }
  } catch {
    /* 列尚未存在时本地仍可用；下次 saveRow 可补列 */
  }
}

export async function verifyMallPin(userId: string, pin: string): Promise<boolean> {
  const saved = await loadMallPin(userId)
  return !!saved && saved === String(pin || '').trim()
}

/**
 * 进入商城前鉴权：仅校验家长端身份，不再要求独立密码。
 */
export function requireMallAccess(_redirect = true): boolean {
  if (!canAccessMall()) {
    uni.showToast({ title: '周边商城仅家长端可使用', icon: 'none' })
    return false
  }
  return !!getLocalSession()
}
