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
})
