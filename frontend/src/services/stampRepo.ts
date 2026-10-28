import { TABLES } from '@/constants/tables'
import type { StampRow } from '@/types/user'
import {
  fieldInt,
  fieldVarchar,
  n,
  q,
  queryBySql,
  saveRow,
  updateBySql,
} from './pmis'

export interface SaveStampInput {
  ownerId: string | number
  ownerRole?: string
  childId?: string | number
  childName?: string
  cardNo?: string
  source: 'virtual' | 'physical'
  stampType: string
  knowKind?: string
  stackKind?: string
  subject?: string
  primaryDim?: string
  secondaryDim?: string
  codeTl?: number
  codeTr?: number
  codeBl?: number
  codeBr?: number
  codeText?: string
  valueText?: string
  valueNum?: number
  teacherName?: string
  teacherStampNo?: string
  imageUrl?: string
  note?: string
  status?: string
  /** 可选；虚假/补录数据可指定时间 */
  createdAt?: string
}

export async function saveStamp(input: SaveStampInput): Promise<string> {
  const now = input.createdAt || new Date().toISOString()
  const codeText =
    input.codeText ||
    `${input.codeTl ?? 0}${input.codeTr ?? 0}${input.codeBl ?? 0}${input.codeBr ?? 0}`
  return saveRow(TABLES.stamp, {
    owner_id: fieldInt('归属账号Id', input.ownerId),
    owner_role: fieldVarchar('归属角色', input.ownerRole || 'parent', 20),
    child_id: fieldInt('孩子Id', input.childId || 0),
    child_name: fieldVarchar('学生姓名', input.childName || '', 50),
    card_no: fieldVarchar('记录卡编号', input.cardNo || '', 40),
    source: fieldVarchar('来源', input.source, 20),
    stamp_type: fieldVarchar('章型', input.stampType, 20),
    know_kind: fieldVarchar('知章类型', input.knowKind || '', 20),
    stack_kind: fieldVarchar('叠章', input.stackKind || '无', 20),
    subject: fieldVarchar('学科', input.subject || '', 20),
    primary_dim: fieldVarchar('一级维度', input.primaryDim || '', 40),
    secondary_dim: fieldVarchar('二级维度', input.secondaryDim || '', 40),
    code_tl: fieldInt('编码左上', input.codeTl || 0),
    code_tr: fieldInt('编码右上', input.codeTr || 0),
    code_bl: fieldInt('编码左下', input.codeBl || 0),
    code_br: fieldInt('编码右下', input.codeBr || 0),
    code_text: fieldVarchar('编码文本', codeText, 20),
    value_text: fieldVarchar('当量文案', input.valueText || '', 80),
    value_num: fieldInt('当量数值', input.valueNum || 0),
    teacher_name: fieldVarchar('教师姓名', input.teacherName || '', 50),
    teacher_stamp_no: fieldVarchar('教师印章编号', input.teacherStampNo || '', 40),
    image_url: fieldVarchar('采集图片', input.imageUrl || '', 255),
    note: fieldVarchar('补充说明', input.note || '', 200),
    status: fieldVarchar('状态', input.status || 'confirmed', 20),
    created_at: fieldVarchar('创建时间', now, 40),
  })
}

export async function listStampsByOwner(
  ownerId: string | number,
  limit = 20,
): Promise<StampRow[]> {
  const sql = `
    select * from ${TABLES.stamp}
    where isDel = 0 and owner_id = ${n(ownerId)}
    order by Id desc
    limit ${n(limit)}
  `.replace(/\s+/g, ' ').trim()
  const rows = await queryBySql(sql)
  return rows as StampRow[]
}

export async function listStampsByChild(
  childId: string | number,
  limit = 100,
): Promise<StampRow[]> {
  const sql = `
    select * from ${TABLES.stamp}
    where isDel = 0 and child_id = ${n(childId)}
    order by Id desc
    limit ${n(limit)}
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as StampRow[]
}

export async function listStampsByTeacherStamp(
  stampNo: string,
  limit = 200,
): Promise<StampRow[]> {
  const sql = `
    select * from ${TABLES.stamp}
    where isDel = 0 and teacher_stamp_no = ${q(stampNo)}
    order by Id desc
    limit ${n(limit)}
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as StampRow[]
}

export async function updateStampFields(
  id: string | number,
  fields: Partial<Pick<StampRow, 'primary_dim' | 'secondary_dim' | 'subject' | 'note' | 'value_text' | 'value_num' | 'status'>>,
): Promise<void> {
  const sets: string[] = []
  if (fields.primary_dim !== undefined) sets.push(`primary_dim = ${q(fields.primary_dim)}`)
  if (fields.secondary_dim !== undefined) sets.push(`secondary_dim = ${q(fields.secondary_dim)}`)
  if (fields.subject !== undefined) sets.push(`subject = ${q(fields.subject)}`)
  if (fields.note !== undefined) sets.push(`note = ${q(fields.note)}`)
  if (fields.value_text !== undefined) sets.push(`value_text = ${q(fields.value_text)}`)
  if (fields.value_num !== undefined) sets.push(`value_num = ${n(fields.value_num)}`)
  if (fields.status !== undefined) sets.push(`status = ${q(fields.status)}`)
  if (!sets.length) return
  await updateBySql(
    `update ${TABLES.stamp} set ${sets.join(', ')} where Id = ${n(id)} and isDel = 0`,
  )
}
