import { reactive } from 'vue'
import type { SessionUser } from '@/types/user'
import { clearLocalSession, getLocalSession, setLocalSession } from '@/services/session'
import { displayPhone } from '@/utils/security'

export type AppRole = 'family' | 'school'

export interface DemoProfile {
  role: AppRole
  name: string
  sub: string
  avatar: string
  userId: string
  phone?: string
  points?: number
  inviteCode?: string
  membershipStatus?: string
  membershipExpireAt?: string
}

const state = reactive({
  role: 'family' as AppRole,
  loggedIn: false,
  profile: {
    role: 'family',
    name: '王芳',
    sub: '家长 · 会员演示',
    avatar: '王',
    userId: 'HADEMO01',
  } as DemoProfile,
})

const ROLE_MAP: Record<AppRole, DemoProfile> = {
  family: {
    role: 'family',
    name: '王芳',
    sub: '家长 · 会员演示',
    avatar: '王',
    userId: 'HADEMO01',
  },
  school: {
    role: 'school',
    name: '淮安实验小学',
    sub: '学校管理员（演示）',
    avatar: '淮',
    userId: 'HASCHOOL01',
  },
}

export function useDemoStore() {
  return state
}

export function loginAs(role: AppRole) {
  state.role = role
  state.loggedIn = true
  state.profile = { ...ROLE_MAP[role] }
  const session: SessionUser = {
    id: role === 'family' ? 'demo_family' : 'demo_school',
    role: role === 'school' ? 'school' : 'parent',
    name: state.profile.name,
    phone: role === 'school' ? '02500000000' : '13800138000',
    avatarText: state.profile.avatar,
    inviteCode: role === 'school' ? 'HASCHOOL01' : 'HADEMO01',
    points: role === 'school' ? 0 : 260,
    membershipStatus: role === 'school' ? 'none' : 'active',
    membershipExpireAt: role === 'school' ? undefined : '2027-06-30T00:00:00.000Z',
    hasPaid: role !== 'school',
  }
  setLocalSession(session)
  syncDemoFromSession(session)
}

export function logoutDemo() {
  clearDemoState()
  clearLocalSession()
}

export function clearDemoState() {
  state.loggedIn = false
}

/** 用真实/演示会话驱动「我的」等页面展示 */
export function syncDemoFromSession(user: SessionUser) {
  const isSchool = user.id === 'demo_school' || user.role === 'school'
  const isTeacher = user.role === 'teacher'
  state.role = isSchool ? 'school' : isTeacher ? 'school' : 'family'
  state.loggedIn = true
  const membershipLabel =
    user.membershipStatus === 'active'
      ? `会员至 ${String(user.membershipExpireAt || '').slice(0, 10) || '—'}`
      : user.membershipStatus === 'trial'
        ? `试用至 ${String(user.membershipExpireAt || '').slice(0, 10) || '—'}`
        : user.membershipStatus === 'expired'
          ? '会员已过期'
          : '未开通会员'
  state.profile = {
    role: state.role,
    name: user.name,
    sub: isTeacher
      ? `教师 · 印章 ${user.stampNo || user.inviteCode}`
      : isSchool
        ? '学校管理员'
        : `${displayPhone(user.phone)} · ${membershipLabel}`,
    avatar: user.avatarText || (user.name || '').slice(0, 1),
    userId: user.inviteCode || user.id,
    phone: user.phone,
    points: user.points,
    inviteCode: user.inviteCode,
    membershipStatus: user.membershipStatus,
    membershipExpireAt: user.membershipExpireAt,
  }
}

export function ensureDemoLogin(): boolean {
  const session = getLocalSession()
  if (!session?.id) {
    // 兼容旧版直接写 storage 的演示会话
    let raw: any = uni.getStorageSync('hlxz_session_user')
    if (!raw) return false
    try {
      if (typeof raw === 'string') raw = JSON.parse(raw)
      if (typeof raw === 'string') raw = JSON.parse(raw)
      if (!raw?.id) return false
      setLocalSession(raw as SessionUser)
      syncDemoFromSession(raw as SessionUser)
      return true
    } catch {
      return false
    }
  }
  syncDemoFromSession(session)
  return true
}
