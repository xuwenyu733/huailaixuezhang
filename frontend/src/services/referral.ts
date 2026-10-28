import { REFERRAL_REWARD_POINTS } from '@/constants/referral'
import { TABLES } from '@/constants/tables'
import type { ParentRow, ReferralRow } from '@/types/user'
import { findParentById } from './parentRepo'
import {
  fieldInt,
  fieldVarchar,
  n,
  q,
  queryBySql,
  saveRow,
  updateBySql,
} from './pmis'

export interface BindReferralParams {
  referrer: ParentRow
  invitee: ParentRow
}

/** 注册成功后建立推荐关系（待付费后发积分） */
export async function bindReferralOnRegister(
  params: BindReferralParams,
): Promise<ReferralRow | null> {
  const { referrer, invitee } = params
  if (String(referrer.Id) === String(invitee.Id)) {
    throw new Error('不能填写自己的推荐码')
  }

  const checkSql = `select * from ${TABLES.referral} where isDel = 0 and invitee_id = ${n(invitee.Id)} limit 1`
  const existed = await queryBySql(checkSql)
  if (existed[0]) return existed[0] as ReferralRow

  const now = new Date().toISOString()
  await saveRow(TABLES.referral, {
    referrer_id: fieldInt('推荐人Id', referrer.Id),
    invitee_id: fieldInt('被推荐人Id', invitee.Id),
    invitee_name: fieldVarchar('被推荐人姓名', invitee.name, 50),
    invitee_phone: fieldVarchar('被推荐人手机号', invitee.phone, 20),
    invite_code: fieldVarchar('使用的推荐码', referrer.invite_code, 20),
    status: fieldVarchar('关系状态', 'pending', 20),
    reward_points: fieldInt('奖励积分', REFERRAL_REWARD_POINTS),
    created_at: fieldVarchar('建立关系时间', now, 40),
    rewarded_at: fieldVarchar('发奖时间', '', 40),
  })
  const rows = await queryBySql(checkSql)
  return (rows[0] as ReferralRow) || null
}

export async function getReferralsByReferrer(
  referrerId: string | number,
): Promise<ReferralRow[]> {
  const sql = `
    select * from ${TABLES.referral}
    where isDel = 0 and referrer_id = ${n(referrerId)}
    order by Id desc
  `.replace(/\s+/g, ' ').trim()
  const rows = await queryBySql(sql)
  return rows as ReferralRow[]
}

export async function getReferralByInvitee(
  inviteeId: string | number,
): Promise<ReferralRow | null> {
  const sql = `select * from ${TABLES.referral} where isDel = 0 and invitee_id = ${n(inviteeId)} limit 1`
  const rows = await queryBySql(sql)
  return (rows[0] as ReferralRow) || null
}

/**
 * 被推荐人缴费开通会员后，给推荐人发放积分。
 * 需求：被推荐人注册缴费后推荐人获 50 积分。
 */
export async function markInviteePaidAndReward(inviteeId: string | number): Promise<{
  rewarded: boolean
  pointsAwarded: number
}> {
  const invitee = await findParentById(inviteeId)
  if (!invitee) throw new Error('用户不存在')

  const expire = new Date()
  expire.setFullYear(expire.getFullYear() + 1)
  const expireAt = expire.toISOString()

  await updateBySql(`
    update ${TABLES.parent}
    set has_paid = 1,
        membership_status = ${q('active')},
        membership_expire_at = ${q(expireAt)}
    where Id = ${n(inviteeId)} and isDel = 0
  `.replace(/\s+/g, ' ').trim())

  const record = await getReferralByInvitee(inviteeId)
  if (!record || record.status === 'rewarded') {
    return { rewarded: false, pointsAwarded: 0 }
  }

  const referrer = await findParentById(record.referrer_id)
  if (!referrer) {
    await updateBySql(
      `update ${TABLES.referral} set status = ${q('invalid')} where Id = ${n(record.Id)}`,
    )
    return { rewarded: false, pointsAwarded: 0 }
  }

  const reward = Number(record.reward_points) || REFERRAL_REWARD_POINTS
  const now = new Date().toISOString()

  await updateBySql([
    `update ${TABLES.parent} set points = points + ${n(reward)} where Id = ${n(referrer.Id)} and isDel = 0`,
    `update ${TABLES.referral} set status = ${q('rewarded')}, rewarded_at = ${q(now)} where Id = ${n(record.Id)} and isDel = 0`,
  ])

  const { pushMessage } = await import('./messageRepo')
  await pushMessage({
    ownerId: referrer.Id,
    title: '推荐积分到账',
    content: `好友 ${invitee.name || invitee.phone} 已开通会员，你获得 ${reward} 积分`,
    category: 'referral',
  })

  return { rewarded: true, pointsAwarded: reward }
}

/** 积分抵扣年费：满 50 分开通一年 */
export async function redeemPointsForMembership(userId: string | number): Promise<void> {
  const user = await findParentById(userId)
  if (!user) throw new Error('用户不存在')
  if (Number(user.points) < REFERRAL_REWARD_POINTS) {
    throw new Error(`积分不足，需满 ${REFERRAL_REWARD_POINTS} 分可抵扣年费`)
  }

  const expire = new Date()
  expire.setFullYear(expire.getFullYear() + 1)

  await updateBySql(`
    update ${TABLES.parent}
    set points = points - ${n(REFERRAL_REWARD_POINTS)},
        has_paid = 1,
        membership_status = ${q('active')},
        membership_expire_at = ${q(expire.toISOString())}
    where Id = ${n(userId)} and isDel = 0
  `.replace(/\s+/g, ' ').trim())
}

export async function getReferralSummary(referrerId: string | number) {
  const list = await getReferralsByReferrer(referrerId)
  const pending = list.filter((r) => r.status === 'pending').length
  const rewarded = list.filter((r) => r.status === 'rewarded').length
  const earnedPoints = list
    .filter((r) => r.status === 'rewarded')
    .reduce((sum, r) => sum + (Number(r.reward_points) || 0), 0)
  return { total: list.length, pending, rewarded, earnedPoints, list }
}
