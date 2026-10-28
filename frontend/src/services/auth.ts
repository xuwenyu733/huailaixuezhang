import { TRIAL_DAYS } from '@/constants/membership'
import { REFERRAL_REWARD_POINTS } from '@/constants/referral'
import { TABLES } from '@/constants/tables'
import type { MembershipStatus, ParentRow, SessionUser } from '@/types/user'
import { generateInviteCode, normalizeInviteCode } from '@/utils/invite'
import { validatePassword, validatePhone } from '@/utils/security'
import { fieldInt, fieldVarchar, n, q, saveRow, updateBySql } from './pmis'
import {
  findParentById,
  findParentByInviteCode,
  findParentByPhone,
} from './parentRepo'
import { findTeacherByStampNo } from './teacherRepo'
import { bindReferralOnRegister } from './referral'
import {
  clearLocalSession,
  getLocalSession,
  setLocalSession,
} from './session'
import { clearDemoState, syncDemoFromSession } from '@/stores/demo'
import { lockMall } from './mallGate'

export { REFERRAL_REWARD_POINTS }
export { findParentById, findParentByInviteCode, findParentByPhone }

function rowToSession(row: ParentRow): SessionUser {
  return {
    id: String(row.Id),
    role: 'parent',
    name: row.name,
    phone: row.phone,
    avatarText: row.avatar_text || (row.name || '').slice(0, 1),
    inviteCode: row.invite_code,
    points: Number(row.points) || 0,
    membershipStatus: (row.membership_status || 'none') as MembershipStatus,
    membershipExpireAt: row.membership_expire_at || undefined,
    hasPaid: Number(row.has_paid) === 1,
    referredByCode: row.referred_by_code || undefined,
  }
}

async function ensureUniqueInviteCode(seed: string): Promise<string> {
  let code = generateInviteCode(seed)
  for (let i = 0; i < 20; i++) {
    const existed = await findParentByInviteCode(code)
    if (!existed) return code
    code = generateInviteCode(`${seed}-${i}-${Date.now()}`)
  }
  return code
}

export function getCurrentUser(): SessionUser | null {
  const user = getLocalSession()
  if (user) syncDemoFromSession(user)
  return user
}

/** 页面鉴权：无会话则跳转登录 */
export function requireLogin(): SessionUser | null {
  const user = getLocalSession()
  if (!user) {
    uni.reLaunch({ url: '/pages/login/login' })
    return null
  }
  syncDemoFromSession(user)
  return user
}

export async function refreshCurrentUser(): Promise<SessionUser | null> {
  const local = getLocalSession()
  if (!local) return null
  // 本地演示账号不打 PMIS
  if (String(local.id).startsWith('demo_')) {
    syncDemoFromSession(local)
    return local
  }
  // 教师会话按印章号刷新，勿用家长表查找（否则会清掉登录态）
  if (local.role === 'teacher') {
    const stampNo = local.stampNo || local.inviteCode
    const teacher = stampNo ? await findTeacherByStampNo(stampNo) : null
    if (!teacher || String(teacher.Id) !== String(local.id)) {
      clearLocalSession()
      clearDemoState()
      return null
    }
    const session: SessionUser = {
      id: String(teacher.Id),
      role: 'teacher',
      name: teacher.name,
      phone: teacher.phone || '',
      avatarText: (teacher.name || '师').slice(0, 1),
      inviteCode: teacher.stamp_no,
      points: 0,
      membershipStatus: 'active',
      hasPaid: true,
      stampNo: teacher.stamp_no,
      schoolId: String(teacher.school_id),
    }
    setLocalSession(session)
    syncDemoFromSession(session)
    return session
  }
  if (local.role === 'school') {
    syncDemoFromSession(local)
    return local
  }
  const row = await findParentById(local.id)
  if (!row) {
    clearLocalSession()
    clearDemoState()
    return null
  }
  // 试用过期自动降为 expired
  if (
    row.membership_status === 'trial' &&
    row.membership_expire_at &&
    new Date(row.membership_expire_at).getTime() < Date.now()
  ) {
    await updateBySql(`
      update ${TABLES.parent}
      set membership_status = ${q('expired')}
      where Id = ${n(row.Id)} and isDel = 0
    `.replace(/\s+/g, ' ').trim())
    row.membership_status = 'expired'
  }
  const session = rowToSession(row)
  setLocalSession(session)
  syncDemoFromSession(session)
  return session
}

export function logout(): void {
  const local = getLocalSession()
  if (local?.id) lockMall(local.id)
  clearLocalSession()
  clearDemoState()
  uni.reLaunch({ url: '/pages/login/login' })
}

export async function updateParentProfile(payload: {
  name: string
}): Promise<SessionUser> {
  const local = getLocalSession()
  if (!local) throw new Error('请先登录')
  if (String(local.id).startsWith('demo_')) {
    throw new Error('演示账号请使用手机号注册后的正式账号修改资料')
  }
  const name = payload.name.trim()
  if (!name) throw new Error('请填写姓名')
  if (name.length > 20) throw new Error('姓名最多 20 字')

  const avatar = name.slice(0, 1)
  await updateBySql(`
    update ${TABLES.parent}
    set name = ${q(name)}, avatar_text = ${q(avatar)}
    where Id = ${n(local.id)} and isDel = 0
  `.replace(/\s+/g, ' ').trim())

  const refreshed = await refreshCurrentUser()
  if (!refreshed) throw new Error('资料已更新，请重新登录')
  return refreshed
}

export async function changeParentPassword(payload: {
  oldPassword: string
  newPassword: string
}): Promise<void> {
  const local = getLocalSession()
  if (!local) throw new Error('请先登录')
  if (String(local.id).startsWith('demo_')) {
    throw new Error('演示账号不支持修改密码')
  }

  const pwdErr = validatePassword(payload.newPassword)
  if (pwdErr) throw new Error(pwdErr)
  if (payload.newPassword === payload.oldPassword) {
    throw new Error('新密码不能与旧密码相同')
  }

  if (local.role === 'teacher') {
    const stampNo = local.stampNo || local.inviteCode
    const row = stampNo ? await findTeacherByStampNo(stampNo) : null
    if (!row) throw new Error('教师账号不存在')
    if (String(row.password) !== payload.oldPassword) {
      throw new Error('旧密码不正确')
    }
    await updateBySql(`
      update ${TABLES.teacher}
      set password = ${q(payload.newPassword)}
      where Id = ${n(local.id)} and isDel = 0
    `.replace(/\s+/g, ' ').trim())
    return
  }

  const row = await findParentById(local.id)
  if (!row) throw new Error('账号不存在')
  if (String(row.password) !== payload.oldPassword) {
    throw new Error('旧密码不正确')
  }

  await updateBySql(`
    update ${TABLES.parent}
    set password = ${q(payload.newPassword)}
    where Id = ${n(local.id)} and isDel = 0
  `.replace(/\s+/g, ' ').trim())
}

export interface RegisterPayload {
  name: string
  phone: string
  password: string
  inviteCode?: string
}

export async function registerParent(payload: RegisterPayload): Promise<SessionUser> {
  const name = payload.name.trim()
  const phone = payload.phone.trim()
  const password = payload.password
  const inviteCodeInput = payload.inviteCode
    ? normalizeInviteCode(payload.inviteCode)
    : ''

  if (!name) throw new Error('请填写姓名')
  const phoneErr = validatePhone(phone)
  if (phoneErr) throw new Error(phoneErr)
  const pwdErr = validatePassword(password)
  if (pwdErr) throw new Error(pwdErr)

  const existed = await findParentByPhone(phone)
  if (existed) throw new Error('该手机号已注册，请直接登录')

  let referrer: ParentRow | null = null
  if (inviteCodeInput) {
    referrer = await findParentByInviteCode(inviteCodeInput)
    if (!referrer) throw new Error('推荐码无效，请核对后重试')
  }

  const inviteCode = await ensureUniqueInviteCode(phone)
  const now = new Date().toISOString()
  const trialEnd = new Date()
  trialEnd.setDate(trialEnd.getDate() + TRIAL_DAYS)

  // PMIS 新建必须走 saveInfo1，不能用 updateInfo 拼 INSERT
  const recId = await saveRow(TABLES.parent, {
    phone: fieldVarchar('手机号', phone, 20),
    password: fieldVarchar('登录密码', password, 100),
    name: fieldVarchar('家长姓名', name, 50),
    avatar_text: fieldVarchar('头像文字', name.slice(0, 1), 10),
    invite_code: fieldVarchar('本人推荐码', inviteCode, 20),
    referred_by_code: fieldVarchar(
      '注册填写推荐码',
      referrer ? referrer.invite_code : '',
      20,
    ),
    referred_by_user_id: fieldInt(
      '推荐人Id',
      referrer ? referrer.Id : 0,
    ),
    points: fieldInt('当前积分', 0),
    membership_status: fieldVarchar('会员状态', 'trial', 20),
    membership_expire_at: fieldVarchar(
      '会员到期时间',
      trialEnd.toISOString(),
      40,
    ),
    has_paid: fieldInt('是否已付费', 0),
    created_at: fieldVarchar('注册时间', now, 40),
  })

  const created =
    (await findParentByPhone(phone)) || (await findParentById(recId))
  if (!created) throw new Error('注册成功但读取账号失败，请稍后登录')

  if (referrer) {
    await bindReferralOnRegister({ referrer, invitee: created })
  }

  const session = rowToSession(created)
  setLocalSession(session)
  syncDemoFromSession(session)
  return session
}

export interface LoginPayload {
  phone: string
  password: string
}

export async function loginParent(payload: LoginPayload): Promise<SessionUser> {
  const phone = payload.phone.trim()
  const password = payload.password

  const phoneErr = validatePhone(phone)
  if (phoneErr) throw new Error(phoneErr)
  if (!password) throw new Error('请输入密码')

  const user = await findParentByPhone(phone)
  if (!user) throw new Error('账号不存在，请先注册')
  if (String(user.password) !== password) throw new Error('密码错误')

  const session = rowToSession(user)
  setLocalSession(session)
  syncDemoFromSession(session)
  return session
}

/** 教师端：印章编号 + 密码登录 */
export async function loginTeacher(payload: {
  stampNo: string
  password: string
}): Promise<SessionUser> {
  const stampNo = payload.stampNo.trim()
  const password = payload.password
  if (!stampNo) throw new Error('请填写印章编号')
  if (!password) throw new Error('请输入密码')

  const row = await findTeacherByStampNo(stampNo)
  if (!row) throw new Error('教师账号不存在，请由学校管理员分配')
  if (String(row.password) !== password) throw new Error('密码错误')

  const session: SessionUser = {
    id: String(row.Id),
    role: 'teacher',
    name: row.name,
    phone: row.phone || '',
    avatarText: (row.name || '师').slice(0, 1),
    inviteCode: row.stamp_no,
    points: 0,
    membershipStatus: 'active',
    hasPaid: true,
    stampNo: row.stamp_no,
    schoolId: String(row.school_id),
  }
  setLocalSession(session)
  syncDemoFromSession(session)
  return session
}

/** 微信授权登录：需已绑定手机号的家长账号 */
export async function loginByWeixinMock(profile?: {
  nickName?: string
}): Promise<SessionUser | 'need_register'> {
  if (profile?.nickName) {
    uni.setStorageSync('hlxz_wx_nickname', profile.nickName)
  }
  const bound = uni.getStorageSync('hlxz_wx_bound_phone')
  if (bound) {
    const user = await findParentByPhone(String(bound))
    if (user) {
      const session = rowToSession(user)
      setLocalSession(session)
      return session
    }
  }
  return 'need_register'
}
