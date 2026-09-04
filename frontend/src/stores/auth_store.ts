import { defineStore } from 'pinia'

import { authApi, type AuthUserOut } from '@/api/auth_api'
import { clearSession, readAccessToken, writeSession } from '@/api/session'
import { forgetUnlockedKeys } from '@/crypto/download'
import { forgetSeenShares } from '@/utils/seen-shares'

/**
 * Two letters for the avatar. `jlii0421` has no second word to take an initial from, so a
 * single-word name falls back to its first two characters rather than rendering one lonely
 * letter in a circle sized for two.
 */
function toInitials(username: string): string {
  const parts = username.split(/[^A-Za-z0-9]+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: readAccessToken(),
    user: null as AuthUserOut | null,
  }),
  getters: {
    isAuthed: (state) => Boolean(state.accessToken),
    /** The header renders before `/auth/me` answers, so this has to survive a null user. */
    displayName: (state) => state.user?.username ?? 'Account',
    initials: (state) => (state.user ? toInitials(state.user.username) : '?'),
  },
  actions: {
    /**
     * Both tokens, together.
     *
     * The refresh token was previously dropped on the floor at login, which is why a
     * session died 30 minutes in: the credential that exists to renew it was never stored.
     */
    setSession(accessToken: string, refreshToken: string) {
      this.accessToken = accessToken
      writeSession({ accessToken, refreshToken })
    },
    /** Adopt a token the refresh interceptor has already written to storage. */
    syncFromStorage() {
      this.accessToken = readAccessToken()
    },
    /**
     * Who is signed in, for the avatar and the profile page.
     *
     * Cached, because every authenticated screen wants the same answer and the identity does
     * not change mid-session. A failure leaves `user` null instead of throwing: the account
     * menu is navigation chrome, and it must not be the thing that breaks a working page.
     */
    async loadUser(force = false) {
      if (!this.accessToken) {
        this.user = null
        return null
      }
      if (this.user && !force) return this.user
      try {
        const response = await authApi.me()
        this.user = response.data?.data?.user ?? null
      } catch {
        this.user = null
      }
      return this.user
    },
    logout() {
      this.accessToken = ''
      // Otherwise the next account to sign in at this machine inherits the previous one's
      // name and email in the avatar menu until `/auth/me` answers.
      this.user = null
      clearSession()
      // The unwrapped account key outlives the token otherwise: the next person at this
      // machine would sign in and find the previous session's files already decryptable.
      forgetUnlockedKeys()
      // The next person to sign in at this machine should not inherit a marker saying they
      // have already seen the previous account's shared files.
      forgetSeenShares()
    },
  },
})
