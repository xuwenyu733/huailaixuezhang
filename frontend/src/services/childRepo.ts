import { TABLES } from '@/constants/tables'
import type { ChildRow } from '@/types/user'
import {
  fieldInt,
  fieldVarchar,
  n,
  q,
  queryBySql,
  saveRow,
  updateBySql,
} from './pmis'

const MAX_CHILDREN = 2

export async function listChildrenByParent(
  parentId: string | number,
): Promise<ChildRow[]> {
  const sql = `
    select * from ${TABLES.child}
    where isDel = 0 and parent_id = ${n(parentId)}
    order by is_current desc, Id desc
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as ChildRow[]
}

export async function findChildByCardNo(cardNo: string): Promise<ChildRow | null> {
  const sql = `select * from ${TABLES.child} where isDel = 0 and card_no = ${q(cardNo)} limit 1`
  const rows = await queryBySql(sql)
  return (rows[0] as ChildRow) || null
}

export async function addChild(payload: {
  parentId: string | number
  name: string
  studentNo?: string
  school?: string
  className?: string
  classCode?: string
  cardNo: string
  tag?: string
}): Promise<ChildRow> {
  const name = payload.name.trim()
  const cardNo = payload.cardNo.trim()
  if (!name) throw new Error('请填写学生姓名')
  if (!cardNo) throw new Error('请填写记录卡编号')

  const existed = await findChildByCardNo(cardNo)
  if (existed) throw new Error('该记录卡编号已被绑定')

  const list = await listChildrenByParent(payload.parentId)
  if (list.length >= MAX_CHILDREN) {
    throw new Error(`每个账号最多绑定 ${MAX_CHILDREN} 个孩子`)
  }

  const now = new Date().toISOString()
  const isCurrent = list.length === 0 ? 1 : 0
  const tag =
    payload.tag?.trim() ||
    `${name.slice(0, 1)}${Math.floor(Math.random() * 90 + 10)}`

  await saveRow(TABLES.child, {
    parent_id: fieldInt('家长Id', payload.parentId),
    name: fieldVarchar('学生姓名', name, 50),
    avatar_text: fieldVarchar('头像文字', name.slice(0, 1), 10),
    student_no: fieldVarchar('学号', payload.studentNo || '', 40),
    school: fieldVarchar('学校', payload.school || '', 80),
    class_name: fieldVarchar('班级', payload.className || '', 40),
    class_code: fieldVarchar('班级码', payload.classCode || '', 40),
    card_no: fieldVarchar('记录卡编号', cardNo, 40),
    tag: fieldVarchar('标签', tag, 40),
    is_current: fieldInt('是否当前', isCurrent),
    created_at: fieldVarchar('创建时间', now, 40),
  })

  const rows = await listChildrenByParent(payload.parentId)
  const created = rows.find((r) => r.card_no === cardNo)
  if (!created) throw new Error('添加成功但读取失败')
  return created
}

export async function setCurrentChild(
  parentId: string | number,
  childId: string | number,
): Promise<void> {
  await updateBySql([
    `update ${TABLES.child} set is_current = 0 where parent_id = ${n(parentId)} and isDel = 0`,
    `update ${TABLES.child} set is_current = 1 where Id = ${n(childId)} and parent_id = ${n(parentId)} and isDel = 0`,
  ])
}

export async function getCurrentChild(
  parentId: string | number,
): Promise<ChildRow | null> {
  const list = await listChildrenByParent(parentId)
  return list.find((c) => Number(c.is_current) === 1) || list[0] || null
}

export async function listChildrenByClassCode(
  classCode: string,
): Promise<ChildRow[]> {
  const code = classCode.trim()
  if (!code) return []
  const sql = `
    select * from ${TABLES.child}
    where isDel = 0 and class_code = ${q(code)}
    order by Id desc
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as ChildRow[]
}

export async function listAllChildren(limit = 200): Promise<ChildRow[]> {
  const sql = `
    select * from ${TABLES.child}
    where isDel = 0
    order by Id desc
    limit ${n(limit)}
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as ChildRow[]
}

export async function softDeleteChild(
  parentId: string | number,
  childId: string | number,
): Promise<void> {
  await updateBySql(
    `update ${TABLES.child} set isDel = 1 where Id = ${n(childId)} and parent_id = ${n(parentId)} and isDel = 0`,
  )
}
