/**
 * 演示账号本地假数据（不写 PMIS）
 * 家长演示登录 demo_family / 学校演示登录 demo_school
 */
import type { ChildRow, ReferralRow, StampRow, TeacherRow } from '@/types/user'
import type { GoalRow } from '@/services/goalRepo'
import type { MessageRow } from '@/services/messageRepo'
import type { OrderRow } from '@/services/orderRepo'
import type { ReportBundle } from '@/services/reportRepo'

export const DEMO_FAMILY_ID = 'demo_family'
export const DEMO_SCHOOL_ID = 'demo_school'

export function isDemoId(id: string | number | undefined | null): boolean {
  return String(id || '').startsWith('demo_')
}

function daysAgo(n: number, hour = 9): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  d.setHours(hour, 30, 0, 0)
  return d.toISOString()
}

/** 演示家长名下孩子 */
export const DEMO_CHILDREN: ChildRow[] = [
  {
    Id: 'demo_child_1',
    parent_id: DEMO_FAMILY_ID,
    name: '张明',
    avatar_text: '张',
    student_no: '20260302015',
    school: '淮安实验小学',
    class_name: '三年级(2)班',
    class_code: 'HA-G3-02',
    card_no: 'CARD-ZM-001',
    tag: '张15',
    is_current: 1,
    created_at: daysAgo(60),
  },
  {
    Id: 'demo_child_2',
    parent_id: DEMO_FAMILY_ID,
    name: '张晓',
    avatar_text: '晓',
    student_no: '20260302088',
    school: '淮安实验小学',
    class_name: '一年级(1)班',
    class_code: 'HA-G1-01',
    card_no: 'CARD-ZX-002',
    tag: '晓88',
    is_current: 0,
    created_at: daysAgo(40),
  },
]

/** 演示盖章记录（按时间倒序） */
export const DEMO_STAMPS: StampRow[] = [
  {
    Id: 'ds1',
    owner_id: DEMO_FAMILY_ID,
    owner_role: 'parent',
    child_id: 'demo_child_1',
    child_name: '张明',
    card_no: 'CARD-ZM-001',
    source: 'physical',
    stamp_type: 'know',
    know_kind: '正向章（知章）',
    stack_kind: '无',
    subject: '语文',
    primary_dim: '智育',
    secondary_dim: '课堂参与',
    code_tl: 2,
    code_tr: 1,
    code_bl: 3,
    code_br: 0,
    code_text: '2130',
    value_text: '+10 ZZE',
    value_num: 10,
    teacher_name: '李老师',
    teacher_stamp_no: 'T0203',
    image_url: '',
    note: '主动举手发言',
    status: 'confirmed',
    created_at: daysAgo(0, 16),
  },
  {
    Id: 'ds2',
    owner_id: DEMO_FAMILY_ID,
    owner_role: 'parent',
    child_id: 'demo_child_1',
    child_name: '张明',
    card_no: 'CARD-ZM-001',
    source: 'virtual',
    stamp_type: 'know',
    know_kind: '知章二叠章',
    stack_kind: '二叠章',
    subject: '德育',
    primary_dim: '德育',
    secondary_dim: '志愿服务',
    code_tl: 1,
    code_tr: 4,
    code_bl: 2,
    code_br: 1,
    code_text: '1421',
    value_text: '+20 ZZE',
    value_num: 20,
    teacher_name: '',
    teacher_stamp_no: '',
    image_url: '',
    note: '家庭端家长认证',
    status: 'confirmed',
    created_at: daysAgo(1, 20),
  },
  {
    Id: 'ds3',
    owner_id: DEMO_FAMILY_ID,
    owner_role: 'teacher',
    child_id: 'demo_child_1',
    child_name: '张明',
    card_no: 'CARD-ZM-001',
    source: 'physical',
    stamp_type: 'combo',
    know_kind: '知行对章',
    stack_kind: '叠章',
    subject: '综合',
    primary_dim: '品格',
    secondary_dim: '习惯养成',
    code_tl: 6,
    code_tr: 5,
    code_bl: 1,
    code_br: 0,
    code_text: '6510',
    value_text: '+500 ZZE',
    value_num: 500,
    teacher_name: '李老师',
    teacher_stamp_no: 'T0203',
    image_url: '',
    note: '学期节点认证',
    status: 'confirmed',
    created_at: daysAgo(3, 11),
  },
  {
    Id: 'ds4',
    owner_id: DEMO_FAMILY_ID,
    owner_role: 'parent',
    child_id: 'demo_child_1',
    child_name: '张明',
    card_no: 'CARD-ZM-001',
    source: 'virtual',
    stamp_type: 'know',
    know_kind: '正向章（知章）',
    stack_kind: '无',
    subject: '数学',
    primary_dim: '智育',
    secondary_dim: '作业完成',
    code_tl: 2,
    code_tr: 2,
    code_bl: 1,
    code_br: 0,
    code_text: '2210',
    value_text: '+10 ZZE',
    value_num: 10,
    teacher_name: '',
    teacher_stamp_no: '',
    image_url: '',
    note: '',
    status: 'confirmed',
    created_at: daysAgo(5, 19),
  },
  {
    Id: 'ds5',
    owner_id: DEMO_FAMILY_ID,
    owner_role: 'teacher',
    child_id: 'demo_child_1',
    child_name: '张明',
    card_no: 'CARD-ZM-001',
    source: 'physical',
    stamp_type: 'do',
    know_kind: '行章',
    stack_kind: '无',
    subject: '体育',
    primary_dim: '体育',
    secondary_dim: '体能达标',
    code_tl: 3,
    code_tr: 8,
    code_bl: 0,
    code_br: 0,
    code_text: '3800',
    value_text: '+100 ZZE',
    value_num: 100,
    teacher_name: '王老师',
    teacher_stamp_no: 'T0311',
    image_url: '',
    note: '课间操达标进阶',
    status: 'confirmed',
    created_at: daysAgo(8, 10),
  },
  {
    Id: 'ds6',
    owner_id: DEMO_FAMILY_ID,
    owner_role: 'parent',
    child_id: 'demo_child_2',
    child_name: '张晓',
    card_no: 'CARD-ZX-002',
    source: 'virtual',
    stamp_type: 'know',
    know_kind: '正向章（知章）',
    stack_kind: '无',
    subject: '习惯',
    primary_dim: '德育',
    secondary_dim: '习惯养成',
    code_tl: 1,
    code_tr: 5,
    code_bl: 1,
    code_br: 0,
    code_text: '1510',
    value_text: '+10 ZZE',
    value_num: 10,
    teacher_name: '',
    teacher_stamp_no: '',
    image_url: '',
    note: '自己收拾书包',
    status: 'confirmed',
    created_at: daysAgo(2, 21),
  },
]

export const DEMO_MESSAGES: MessageRow[] = [
  {
    Id: 'dm1',
    owner_id: DEMO_FAMILY_ID,
    title: '虚拟盖章成功',
    content: '张明 +20 ZZE（知章二叠章）',
    is_read: 0,
    created_at: daysAgo(1, 20),
  },
  {
    Id: 'dm2',
    owner_id: DEMO_FAMILY_ID,
    title: '盖章已记录',
    content: '张明 获得实体章 +10 ZZE',
    is_read: 0,
    created_at: daysAgo(0, 16),
  },
  {
    Id: 'dm3',
    owner_id: DEMO_FAMILY_ID,
    title: '激励目标已达成',
    content: '张明完成「本月课堂积极」，可兑换 多功能铅笔盒',
    is_read: 1,
    created_at: daysAgo(4, 18),
  },
  {
    Id: 'dm4',
    owner_id: DEMO_FAMILY_ID,
    title: '推荐积分到账',
    content: '好友 刘敏 已开通会员，你获得 50 积分',
    is_read: 1,
    created_at: daysAgo(12, 14),
  },
  {
    Id: 'dm5',
    owner_id: DEMO_FAMILY_ID,
    title: '会员已开通',
    content: '年度会员费 ¥198 已记录',
    is_read: 1,
    created_at: daysAgo(30, 11),
  },
]

export const DEMO_ORDERS: OrderRow[] = [
  {
    Id: 'do1',
    owner_id: DEMO_FAMILY_ID,
    title: '年度会员费',
    amount: '198.00',
    pay_type: '年度会员费',
    pay_time: daysAgo(30).slice(0, 10),
    note: '已附支付凭证',
    voucher_url: '',
    status: 'paid',
    created_at: daysAgo(30),
  },
  {
    Id: 'do2',
    owner_id: DEMO_FAMILY_ID,
    title: '专用光敏印油',
    amount: '15.00',
    pay_type: '光敏印油',
    pay_time: daysAgo(15).slice(0, 10),
    note: '蓝色印油 · 演示订单',
    voucher_url: '',
    status: 'pending',
    created_at: daysAgo(15),
  },
  {
    Id: 'do3',
    owner_id: DEMO_FAMILY_ID,
    title: '成长记录册',
    amount: '38.00',
    pay_type: '成长记录册',
    pay_time: daysAgo(7).slice(0, 10),
    note: '一学期装',
    voucher_url: '',
    status: 'paid',
    created_at: daysAgo(7),
  },
]

export const DEMO_GOALS: GoalRow[] = [
  {
    Id: 'dg1',
    parent_id: DEMO_FAMILY_ID,
    child_id: 'demo_child_1',
    child_name: '张明',
    title: '本月课堂积极',
    reward_name: '多功能铅笔盒',
    reward_price: '15.00',
    target_points: 50,
    current_points: 50,
    status: 'done',
    created_at: daysAgo(25),
    done_at: daysAgo(4),
  },
  {
    Id: 'dg2',
    parent_id: DEMO_FAMILY_ID,
    child_id: 'demo_child_1',
    child_name: '张明',
    title: '累计知行对章',
    reward_name: '《三体》',
    reward_price: '38.00',
    target_points: 500,
    current_points: 500,
    status: 'active',
    created_at: daysAgo(20),
  },
  {
    Id: 'dg3',
    parent_id: DEMO_FAMILY_ID,
    child_id: 'demo_child_2',
    child_name: '张晓',
    title: '自己收拾书包一周',
    reward_name: '百乐圆珠笔',
    reward_price: '5.00',
    target_points: 30,
    current_points: 10,
    status: 'active',
    created_at: daysAgo(10),
  },
]

export const DEMO_REFERRALS: ReferralRow[] = [
  {
    Id: 'dr1',
    referrer_id: DEMO_FAMILY_ID,
    invitee_id: 'demo_invitee_1',
    invitee_name: '刘敏',
    invitee_phone: '13900001111',
    invite_code: 'HADEMO01',
    status: 'rewarded',
    reward_points: 50,
    created_at: daysAgo(45),
    rewarded_at: daysAgo(12),
  },
  {
    Id: 'dr2',
    referrer_id: DEMO_FAMILY_ID,
    invitee_id: 'demo_invitee_2',
    invitee_name: '陈浩',
    invitee_phone: '13700002222',
    invite_code: 'HADEMO01',
    status: 'pending',
    reward_points: 50,
    created_at: daysAgo(8),
  },
  {
    Id: 'dr3',
    referrer_id: DEMO_FAMILY_ID,
    invitee_id: 'demo_invitee_3',
    invitee_name: '赵雨',
    invitee_phone: '13600003333',
    invite_code: 'HADEMO01',
    status: 'rewarded',
    reward_points: 50,
    created_at: daysAgo(60),
    rewarded_at: daysAgo(50),
  },
]

export const DEMO_TEACHERS: TeacherRow[] = [
  {
    Id: 'dt1',
    school_id: DEMO_SCHOOL_ID,
    name: '李老师',
    job_no: 'T0203',
    job_desc: '三年级(2)班 · 语文',
    stamp_no: 'T0203',
    phone: '13800002003',
    password: '123456a',
    created_at: daysAgo(90),
  },
  {
    Id: 'dt2',
    school_id: DEMO_SCHOOL_ID,
    name: '王老师',
    job_no: 'T0311',
    job_desc: '三年级(2)班 · 体育',
    stamp_no: 'T0311',
    phone: '13800003111',
    password: '123456a',
    created_at: daysAgo(80),
  },
  {
    Id: 'dt3',
    school_id: DEMO_SCHOOL_ID,
    name: '周老师',
    job_no: 'T0408',
    job_desc: '一年级(1)班 · 班主任',
    stamp_no: 'T0408',
    phone: '13800004008',
    password: '123456a',
    created_at: daysAgo(70),
  },
]

/** 学校端学生列表演示行 */
export interface DemoStudentRow {
  id: string
  av: string
  name: string
  know: number
  combo: number
  card: string
  zze: number
}

export const DEMO_CLASS_STUDENTS: DemoStudentRow[] = [
  { id: 'demo_child_1', av: '张', name: '张明', know: 18, combo: 2, card: 'CARD-ZM-001', zze: 650 },
  { id: 'ds_s2', av: '李', name: '李华', know: 15, combo: 1, card: 'CARD-LH-003', zze: 420 },
  { id: 'ds_s3', av: '王', name: '王芳', know: 12, combo: 1, card: 'CARD-WF-004', zze: 380 },
  { id: 'ds_s4', av: '陈', name: '陈杰', know: 10, combo: 0, card: 'CARD-CJ-005', zze: 210 },
  { id: 'ds_s5', av: '刘', name: '刘洋', know: 9, combo: 0, card: 'CARD-LY-006', zze: 180 },
]

export function getDemoCurrentChild(): ChildRow {
  return DEMO_CHILDREN.find((c) => Number(c.is_current) === 1) || DEMO_CHILDREN[0]
}

export function getDemoStampStats() {
  const rows = DEMO_STAMPS
  let zze = 0
  let know = 0
  let combo = 0
  let physical = 0
  rows.forEach((r) => {
    zze += Number(r.value_num) || 0
    if (r.stamp_type === 'combo') combo += 1
    else know += 1
    if (r.source === 'physical') physical += 1
  })
  return { zze, know, combo, physical, unread: DEMO_MESSAGES.filter((m) => !m.is_read).length }
}

export function getDemoReferralSummary() {
  const list = DEMO_REFERRALS
  const pending = list.filter((r) => r.status === 'pending').length
  const rewarded = list.filter((r) => r.status === 'rewarded').length
  const earnedPoints = list
    .filter((r) => r.status === 'rewarded')
    .reduce((sum, r) => sum + (Number(r.reward_points) || 0), 0)
  return { total: list.length, pending, rewarded, earnedPoints, list }
}

export function getDemoReport(): ReportBundle {
  return {
    months: ['9月', '10月', '11月', '12月', '1月', '2月'],
    growth: [200, 380, 550, 720, 950, 1280],
    rate: [200, 180, 170, 170, 230, 330],
    fusion: { knowStrong: 65, doStrong: 20, balance: 15 },
    dims: [
      { name: '德', me: 85, norm: 75 },
      { name: '智', me: 92, norm: 72 },
      { name: '体', me: 70, norm: 68 },
      { name: '美', me: 78, norm: 70 },
      { name: '劳', me: 65, norm: 66 },
      { name: '格', me: 80, norm: 73 },
      { name: '致', me: 88, norm: 70 },
      { name: '诚', me: 75, norm: 72 },
      { name: '正', me: 82, norm: 74 },
    ],
    advice:
      '该生认知积累扎实，课堂表现活跃，但实践转化能力有待提升。建议加强知识应用类任务，提升行章获取速率，促进知行深度融合。',
    totalZze: 1280,
    ranks: [
      { av: '王', name: '王梓轩', zze: '1,856', me: false },
      { av: '李', name: '李思琪', zze: '1,542', me: false },
      { av: '我', name: '我', zze: '1,280', me: true },
      { av: '陈', name: '陈杰', zze: '980', me: false },
      { av: '刘', name: '刘洋', zze: '860', me: false },
    ],
  }
}
