/** 用户角色 */
export type UserRole = 'parent' | 'teacher' | 'school'

export type MembershipStatus = 'none' | 'trial' | 'active' | 'expired'

export interface ChildRow {
  Id: number | string
  parent_id: number | string
  name: string
  avatar_text: string
  student_no: string
  school: string
  class_name: string
  class_code: string
  card_no: string
  tag: string
  is_current: number
  created_at: string
}

export interface TeacherRow {
  Id: number | string
  school_id: number | string
  name: string
  job_no: string
  job_desc: string
  stamp_no: string
  phone: string
  password: string
  created_at: string
}

export interface StampRow {
  Id: number | string
  owner_id: number | string
  owner_role: string
  child_id: number | string
  child_name: string
  card_no: string
  source: 'virtual' | 'physical'
  stamp_type: string
  know_kind: string
  stack_kind: string
  subject: string
  primary_dim: string
  secondary_dim: string
  code_tl: number
  code_tr: number
  code_bl: number
  code_br: number
  code_text: string
  value_text: string
  value_num: number
  teacher_name: string
  teacher_stamp_no: string
  image_url: string
  note: string
  status: string
  created_at: string
}

/** PMIS 家长表行 */
export interface ParentRow {
  Id: number | string
  phone: string
  password: string
  name: string
  avatar_text: string
  invite_code: string
  referred_by_code?: string
  referred_by_user_id?: number | string
  points: number
  membership_status: MembershipStatus
  membership_expire_at?: string
  has_paid: number
  created_at: string
  isDel?: number
}

export interface ReferralRow {
  Id: number | string
  referrer_id: number | string
  invitee_id: number | string
  invitee_name: string
  invitee_phone: string
  invite_code: string
  status: 'pending' | 'rewarded' | 'invalid'
  reward_points: number
  created_at: string
  rewarded_at?: string
  isDel?: number
}

export interface SessionUser {
  id: string
  role: UserRole
  name: string
  phone: string
  avatarText: string
  inviteCode: string
  points: number
  membershipStatus: MembershipStatus
  membershipExpireAt?: string
  hasPaid: boolean
  referredByCode?: string
  /** 教师印章编号 */
  stampNo?: string
  schoolId?: string
}
