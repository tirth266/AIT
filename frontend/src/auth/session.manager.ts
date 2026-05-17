const SESSION_ACTIVITY_KEY = 'auth_last_activity'
const SESSION_TIMEOUT_KEY = 'auth_session_timeout'
const IDLE_TIMEOUT_MS = 30 * 60 * 1000

export interface SessionState {
  lastActivity: number
  sessionTimeout: number
  isExpired: boolean
}

export const sessionManager = {
  init(): void {
    const stored = localStorage.getItem(SESSION_ACTIVITY_KEY)
    if (!stored) {
      this.updateActivity()
    }
  },

  updateActivity(): void {
    const now = Date.now()
    localStorage.setItem(SESSION_ACTIVITY_KEY, now.toString())
    sessionStorage.setItem(SESSION_TIMEOUT_KEY, (now + IDLE_TIMEOUT_MS).toString())
  },

  getLastActivity(): number {
    const stored = localStorage.getItem(SESSION_ACTIVITY_KEY)
    return stored ? parseInt(stored, 10) : 0
  },

  isIdle(): boolean {
    const lastActivity = this.getLastActivity()
    return Date.now() - lastActivity > IDLE_TIMEOUT_MS
  },

  getTimeUntilIdle(): number {
    const lastActivity = this.getLastActivity()
    const idleTime = Date.now() - lastActivity
    return Math.max(0, IDLE_TIMEOUT_MS - idleTime)
  },

  checkSessionTimeout(): boolean {
    const stored = sessionStorage.getItem(SESSION_TIMEOUT_KEY)
    if (!stored) return false
    return Date.now() > parseInt(stored, 10)
  },

  resetSession(): void {
    this.updateActivity()
  },

  clearSession(): void {
    localStorage.removeItem(SESSION_ACTIVITY_KEY)
    sessionStorage.removeItem(SESSION_TIMEOUT_KEY)
  }
}

export default sessionManager