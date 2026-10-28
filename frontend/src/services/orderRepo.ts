import { TABLES } from '@/constants/tables'
import {
  fieldInt,
  fieldVarchar,
  n,
  queryBySql,
  saveRow,
} from './pmis'

export interface OrderRow {
  Id: number | string
  owner_id: number | string
  title: string
  amount: string
  pay_type: string
  pay_time: string
  note: string
  voucher_url: string
  status: string
  created_at: string
}

export async function listOrders(ownerId: string | number): Promise<OrderRow[]> {
  const sql = `
    select * from ${TABLES.order}
    where isDel = 0 and owner_id = ${n(ownerId)}
    order by Id desc
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as OrderRow[]
}

export async function createOrder(payload: {
  ownerId: string | number
  title: string
  amount: string
  payType: string
  payTime?: string
  note?: string
  voucherUrl?: string
  status?: string
}): Promise<void> {
  const now = new Date().toISOString()
  const voucher = String(payload.voucherUrl || '').slice(0, 250)
  const noteBase = String(payload.note || '').trim()
  const note = voucher
    ? `${noteBase}${noteBase ? ' · ' : ''}已附支付凭证`.slice(0, 200)
    : noteBase.slice(0, 200)
  await saveRow(TABLES.order, {
    owner_id: fieldInt('账号Id', payload.ownerId),
    title: fieldVarchar('订单名称', payload.title, 80),
    amount: fieldVarchar('金额', payload.amount, 20),
    pay_type: fieldVarchar('支付类型', payload.payType, 40),
    pay_time: fieldVarchar('支付时间', payload.payTime || now.slice(0, 10), 40),
    note: fieldVarchar('备注', note, 200),
    voucher_url: fieldVarchar('凭证图片', voucher, 255),
    status: fieldVarchar('状态', payload.status || 'paid', 20),
    created_at: fieldVarchar('创建时间', now, 40),
  })
}
