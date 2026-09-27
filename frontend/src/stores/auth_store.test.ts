import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const logoutApi = vi.fn()
const clearSession = vi.fn()
const forgetUnlockedKeys = vi.fn()
const forgetSeenShares = vi.fn()

vi.mock('@/api/auth_api', () => ({
  authApi: {
    logout: (...args: unknown[]) => logoutApi(...args),
    me: vi.fn(),
  },
}))

vi.mock('@/api/avatar_api', () => ({
  avatarApi: {
    getBytes: vi.fn(),
    upload: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/api/session', () => ({
  clearSession: () => clearSession(),
  readAccessToken: () => 'access-token',
  writeSession: vi.fn(),
}))

vi.mock('@/crypto/download', () => ({
  forgetUnlockedKeys: () => forgetUnlockedKeys(),
}))

vi.mock('@/utils/seen-shares', () => ({
  forgetSeenShares: () => forgetSeenShares(),
}))

import { useAuthStore } from './auth_store'

describe('auth store logout', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    logoutApi.mockReset()
    clearSession.mockReset()
    forgetUnlockedKeys.mockReset()
    forgetSeenShares.mockReset()
  })

  it('calls POST /auth/logout before clearing the local session', async () => {
    logoutApi.mockResolvedValue({ data: { success: true } })
    const auth = useAuthStore()
    auth.accessToken = 'access-token'

    await auth.logout()

    expect(logoutApi).toHaveBeenCalledOnce()
    expect(clearSession).toHaveBeenCalledOnce()
    expect(forgetUnlockedKeys).toHaveBeenCalledOnce()
    expect(forgetSeenShares).toHaveBeenCalledOnce()
    expect(auth.accessToken).toBe('')
    expect(auth.user).toBeNull()
  })

  it('still clears locally when the server logout call fails', async () => {
    logoutApi.mockRejectedValue(new Error('network down'))
    const auth = useAuthStore()
    auth.accessToken = 'access-token'

    await auth.logout()

    expect(logoutApi).toHaveBeenCalledOnce()
    expect(clearSession).toHaveBeenCalledOnce()
    expect(auth.accessToken).toBe('')
  })

  it('clearLocalSession does not call the server', () => {
    const auth = useAuthStore()
    auth.accessToken = 'access-token'
    auth.clearLocalSession()
    expect(logoutApi).not.toHaveBeenCalled()
    expect(clearSession).toHaveBeenCalledOnce()
  })

  it('exposes admin and recovery-reviewer role getters', () => {
    const auth = useAuthStore()
    auth.user = {
      id: '1',
      username: 'admin',
      email: 'admin@example.com',
      role: 'ADMIN',
      status: 'ACTIVE',
      email_verified: true,
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    }
    expect(auth.isAdmin).toBe(true)
    expect(auth.isRecoveryReviewer).toBe(true)

    auth.user = { ...auth.user, role: 'RECOVERY_OFFICER', username: 'officer' }
    expect(auth.isAdmin).toBe(false)
    expect(auth.isRecoveryReviewer).toBe(true)

    auth.user = { ...auth.user, role: 'USER', username: 'member' }
    expect(auth.isAdmin).toBe(false)
    expect(auth.isRecoveryReviewer).toBe(false)
  })
})
