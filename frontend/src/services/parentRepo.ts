import { TABLES } from '@/constants/tables'
import type { ParentRow } from '@/types/user'
import { normalizeInviteCode } from '@/utils/invite'
import { n, q, queryBySql } from './pmis'

export async function findParentByPhone(phone: string): Promise<ParentRow | null> {
  const sql = `select * from ${TABLES.parent} where isDel = 0 and phone = ${q(phone)} limit 1`
  const rows = await queryBySql(sql)
  return (rows[0] as ParentRow) || null
}

export async function findParentById(id: string | number): Promise<ParentRow | null> {
  const sql = `select * from ${TABLES.parent} where isDel = 0 and Id = ${n(id)} limit 1`
  const rows = await queryBySql(sql)
  return (rows[0] as ParentRow) || null
}

export async function findParentByInviteCode(code: string): Promise<ParentRow | null> {
  const normalized = normalizeInviteCode(code)
  const sql = `select * from ${TABLES.parent} where isDel = 0 and invite_code = ${q(normalized)} limit 1`
  const rows = await queryBySql(sql)
  return (rows[0] as ParentRow) || null
}
