/** 用户通知 / 隐私偏好默认值 */
export interface UserPrefs {
  notifyStamp: boolean
  notifyReport: boolean
  notifyOrder: boolean
  notifyReferral: boolean
  maskPhone: boolean
  shareTeacher: boolean
}

export const DEFAULT_PREFS: UserPrefs = {
  notifyStamp: true,
  notifyReport: true,
  notifyOrder: true,
  notifyReferral: true,
  maskPhone: true,
  shareTeacher: true,
}

export type NotifyCategory = 'stamp' | 'report' | 'order' | 'referral' | 'system'
