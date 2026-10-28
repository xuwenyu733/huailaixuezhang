import type { NotifyCategory } from '@/constants/prefs'
import { TABLES } from '@/constants/tables'
import {
  fieldInt,
  fieldVarchar,
  n,
  queryBySql,
  saveRow,
  updateBySql,
} from './pmis'
import { getUserPrefs } from './prefsRepo'

export interface MessageRow {
  Id: number | string
  owner_id: number | string
  title: string
  content: string
  is_read: number
  created_at: string
}

export async function listMessages(ownerId: string | number): Promise<MessageRow[]> {
  const sql = `
    select * from ${TABLES.message}
    where isDel = 0 and owner_id = ${n(ownerId)}
    order by Id desc
    limit 50
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as MessageRow[]
}

async function shouldPush(
  ownerId: string | number,
  category: NotifyCategory,
): Promise<boolean> {
  if (category === 'system') return true
  const prefs = await getUserPrefs(ownerId)
  if (category === 'stamp') return prefs.notifyStamp
  if (category === 'report') return prefs.notifyReport
  if (category === 'order') return prefs.notifyOrder
  if (category === 'referral') return prefs.notifyReferral
  return true
}

export async function pushMessage(payload: {
  ownerId: string | number
  title: string
  content: string
  category?: NotifyCategory
}): Promise<boolean> {
  if (!payload.ownerId || String(payload.ownerId).startsWith('demo_')) return false
  const category = payload.category || 'system'
  if (!(await shouldPush(payload.ownerId, category))) return false
  await saveRow(TABLES.message, {
    owner_id: fieldInt('接收人Id', payload.ownerId),
    title: fieldVarchar('标题', payload.title, 80),
    content: fieldVarchar('内容', payload.content, 200),
    is_read: fieldInt('是否已读', 0),
    created_at: fieldVarchar('时间', new Date().toISOString(), 40),
  })
  return true
}

export async function markMessageRead(id: string | number): Promise<void> {
  await updateBySql(
    `update ${TABLES.message} set is_read = 1 where Id = ${n(id)} and isDel = 0`,
  )
}

export async function markAllMessagesRead(ownerId: string | number): Promise<void> {
  await updateBySql(
    `update ${TABLES.message} set is_read = 1 where owner_id = ${n(ownerId)} and isDel = 0`,
  )
}

export async function countUnreadMessages(
  ownerId: string | number,
): Promise<number> {
  const sql = `
    select count(*) as cnt from ${TABLES.message}
    where isDel = 0 and owner_id = ${n(ownerId)} and is_read = 0
  `.replace(/\s+/g, ' ').trim()
  const rows = await queryBySql(sql)
  return Number(rows[0]?.cnt ?? rows[0]?.CNT ?? 0) || 0
}
