import { DEFAULT_PREFS, type UserPrefs } from '@/constants/prefs'
import { TABLES } from '@/constants/tables'
import { getStorage, setStorage } from '@/utils/storage'
import {
  fieldInt,
  fieldVarchar,
  n,
  q,
  queryBySql,
  saveRow,
  updateBySql,
} from './pmis'

const LOCAL_KEY = 'user_prefs'

function boolInt(v: unknown, fallback = 1): number {
  if (v === true || v === 1 || v === '1') return 1
  if (v === false || v === 0 || v === '0') return 0
  return fallback
}

function rowToPrefs(row: Record<string, unknown> | null | undefined): UserPrefs {
  if (!row) return { ...DEFAULT_PREFS }
  return {
    notifyStamp: boolInt(row.notify_stamp, 1) === 1,
    notifyReport: boolInt(row.notify_report, 1) === 1,
    notifyOrder: boolInt(row.notify_order, 1) === 1,
    notifyReferral: boolInt(row.notify_referral, 1) === 1,
    maskPhone: boolInt(row.mask_phone, 1) === 1,
    shareTeacher: boolInt(row.share_teacher, 1) === 1,
  }
}

/** 当前设备本地缓存（脱敏展示等即时读） */
export function getLocalPrefs(): UserPrefs {
  return getStorage<UserPrefs>(LOCAL_KEY, { ...DEFAULT_PREFS })
}

export function setLocalPrefs(prefs: UserPrefs): void {
  setStorage(LOCAL_KEY, { ...DEFAULT_PREFS, ...prefs })
}

export async function getUserPrefs(
  ownerId: string | number,
): Promise<UserPrefs> {
  if (!ownerId || String(ownerId).startsWith('demo_')) {
    return getLocalPrefs()
  }
  try {
    const sql = `
      select * from ${TABLES.prefs}
      where isDel = 0 and owner_id = ${n(ownerId)}
      limit 1
    `.replace(/\s+/g, ' ').trim()
    const rows = await queryBySql(sql)
    if (rows[0]) {
      const prefs = rowToPrefs(rows[0] as Record<string, unknown>)
      setLocalPrefs(prefs)
      return prefs
    }
  } catch {
    /* 表尚未创建时走本地 */
  }
  return getLocalPrefs()
}

export async function saveUserPrefs(
  ownerId: string | number,
  prefs: UserPrefs,
): Promise<UserPrefs> {
  const next = { ...DEFAULT_PREFS, ...prefs }
  setLocalPrefs(next)
  if (!ownerId || String(ownerId).startsWith('demo_')) return next

  const now = new Date().toISOString()
  const sql = `
    select Id from ${TABLES.prefs}
    where isDel = 0 and owner_id = ${n(ownerId)}
    limit 1
  `.replace(/\s+/g, ' ').trim()
  let existedId: string | number | null = null
  try {
    const rows = await queryBySql(sql)
    existedId = rows[0]?.Id ?? null
  } catch {
    existedId = null
  }

  if (existedId != null) {
    await updateBySql(`
      update ${TABLES.prefs}
      set notify_stamp = ${n(next.notifyStamp ? 1 : 0)},
          notify_report = ${n(next.notifyReport ? 1 : 0)},
          notify_order = ${n(next.notifyOrder ? 1 : 0)},
          notify_referral = ${n(next.notifyReferral ? 1 : 0)},
          mask_phone = ${n(next.maskPhone ? 1 : 0)},
          share_teacher = ${n(next.shareTeacher ? 1 : 0)},
          updated_at = ${q(now)}
      where Id = ${n(existedId)} and isDel = 0
    `.replace(/\s+/g, ' ').trim())
  } else {
    await saveRow(TABLES.prefs, {
      owner_id: fieldInt('账号Id', ownerId),
      notify_stamp: fieldInt('盖章通知', next.notifyStamp ? 1 : 0),
      notify_report: fieldInt('报告通知', next.notifyReport ? 1 : 0),
      notify_order: fieldInt('订单通知', next.notifyOrder ? 1 : 0),
      notify_referral: fieldInt('推荐通知', next.notifyReferral ? 1 : 0),
      mask_phone: fieldInt('手机脱敏', next.maskPhone ? 1 : 0),
      share_teacher: fieldInt('教师可见', next.shareTeacher ? 1 : 0),
      mall_pin: fieldVarchar('商城独立密码', '', 20),
      updated_at: fieldVarchar('更新时间', now, 40),
    })
  }
  return next
}

/** 批量查出不允许教师看当量的家长 Id */
export async function listHiddenParentIds(
  parentIds: Array<string | number>,
): Promise<Set<string>> {
  const ids = [...new Set(parentIds.map(String).filter((id) => id && id !== '0'))]
  const hidden = new Set<string>()
  if (!ids.length) return hidden
  try {
    const sql = `
      select owner_id from ${TABLES.prefs}
      where isDel = 0
        and share_teacher = 0
        and owner_id in (${ids.map((id) => n(id)).join(',')})
    `.replace(/\s+/g, ' ').trim()
    const rows = await queryBySql(sql)
    rows.forEach((r: any) => {
      if (r?.owner_id != null) hidden.add(String(r.owner_id))
    })
  } catch {
    /* ignore */
  }
  return hidden
}
