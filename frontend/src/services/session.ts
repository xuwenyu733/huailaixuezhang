import type { SessionUser } from '@/types/user'
import { getStorage, removeStorage, setStorage } from '@/utils/storage'

const SESSION_KEY = 'session_user'

export function getLocalSession(): SessionUser | null {
  return getStorage<SessionUser | null>(SESSION_KEY, null)
}

export function setLocalSession(user: SessionUser): void {
  setStorage(SESSION_KEY, user)
}

export function clearLocalSession(): void {
  removeStorage(SESSION_KEY)
}
