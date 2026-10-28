/**
 * PMIS（wiidu）SQL 读写封装
 * 统一使用 uniapp 专用 request（@/utils/request），不用旧版 request.js
 *
 * 注意：新建记录请用 saveInfo1.jsp（saveRow），
 * updateInfo.jsp 对 INSERT 常返回 code=10000 但实际失败。
 */
import request from '@/utils/request'
import { TABLES } from '@/constants/tables'

export { TABLES }

/** 防 SQL 注入的字符串转义并加引号 */
export function q(value: unknown): string {
  const s = String(value ?? '')
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/\u0000/g, '')
  return `'${s}'`
}

export function n(value: unknown): string {
  const num = Number(value)
  return Number.isFinite(num) ? String(num) : '0'
}

/** saveInfo1 字段：varchar */
export function fieldVarchar(comment: string, value: unknown, length = 100): string {
  const v = String(value ?? '').replace(/'/g, "\\'")
  const c = String(comment ?? '').replace(/'/g, "\\'")
  return `varchar(${length}) NOT NULL DEFAULT '' COMMENT '${c}';${v}`
}

/** saveInfo1 字段：int */
export function fieldInt(comment: string, value: unknown, length = 11): string {
  const num = Number(value)
  const v = Number.isFinite(num) ? String(num) : '0'
  const c = String(comment ?? '').replace(/'/g, "\\'")
  return `int(${length}) DEFAULT NULL COMMENT '${c}';${v}`
}

function unwrapPayload(raw: any): any {
  if (raw && typeof raw === 'object' && 'data' in raw && ('statusCode' in raw || 'header' in raw)) {
    return raw.data
  }
  return raw
}

function assertPmisOk(payload: any, action: string) {
  if (!payload || typeof payload !== 'object') return
  const code = payload.code
  const msg = String(payload.msg || payload.message || '')
  const data = payload.data
  const failedByCode =
    code !== undefined &&
    Number(code) !== 10000 &&
    Number(code) !== 200 &&
    Number(code) !== 0
  const failedByMsg = msg.includes('出错') || msg.includes('失败')
  const failedByData = typeof data === 'string' && data.includes('ErrorId')
  if (failedByCode || failedByMsg || failedByData) {
    throw new Error(msg || `${action}失败`)
  }
}

function resultGroups(raw: any): any[] | null {
  let payload = unwrapPayload(raw)
  if (typeof payload === 'string') {
    const text = payload.replace(/^\uFEFF/, '').trim()
    if (!text) return null
    try {
      payload = JSON.parse(text)
    } catch {
      return null
    }
  }
  if (payload == null) return null
  if (Array.isArray(payload)) return payload

  if (typeof payload === 'object') {
    assertPmisOk(payload, 'PMIS 查询')
    if (Object.prototype.hasOwnProperty.call(payload, 'data')) {
      const inner = payload.data
      if (Array.isArray(inner)) return inner
      if (inner && typeof inner === 'object' && Array.isArray(inner.list)) {
        return [inner.list]
      }
    }
    if (Array.isArray(payload.list)) return [payload.list]
  }
  return null
}

/** 查询：mysql/getDataListBySql.jsp */
export async function queryBySql(sql: string): Promise<Record<string, any>[]> {
  const res = await request.post(
    'mysql/getDataListBySql.jsp',
    { sqlstring: [sql] },
    { noVerify: true, noAuth: true },
  )
  const groups = resultGroups(res)
  if (!groups) return []
  if (groups.length && groups[0] && !Array.isArray(groups[0]) && typeof groups[0] === 'object') {
    return groups as Record<string, any>[]
  }
  return Array.isArray(groups[0]) ? groups[0] : []
}

/** 更新：mysql/updateInfo.jsp（仅用于 UPDATE，不要用 INSERT） */
export async function updateBySql(sqls: string | string[]): Promise<void> {
  const list = Array.isArray(sqls) ? sqls : [sqls]
  const res = await request.post(
    'mysql/updateInfo.jsp',
    { sqlstring: list },
    { noVerify: true, noAuth: true },
  )
  assertPmisOk(unwrapPayload(res), 'PMIS 写入')
}

/**
 * 新建记录：mysql/saveInfo1.jsp
 * fields 值为 fieldVarchar/fieldInt 生成的「类型;值」字符串
 * @returns 新记录 Id / recId
 */
export async function saveRow(
  tableName: string,
  fields: Record<string, string>,
): Promise<string> {
  const payload: Record<string, any> = {
    tableName,
    recId: '',
    ...fields,
  }
  const res = await request.post('mysql/saveInfo1.jsp', payload, {
    noVerify: true,
    noAuth: true,
  })
  const body = unwrapPayload(res)
  assertPmisOk(body, 'PMIS 新建')
  const recId =
    body?.recId ||
    body?.data?.[0]?.recId ||
    body?.data?.recId ||
    ''
  if (!recId && recId !== 0) {
    throw new Error('新建成功但未返回记录 Id')
  }
  return String(recId)
}
