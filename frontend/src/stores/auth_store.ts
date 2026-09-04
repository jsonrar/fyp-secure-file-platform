import { defineStore } from 'pinia'

import {
  clearSession,
  readAccessToken,
  readUsername,
  writeSession,
  writeUsername,
} from '@/api/session'
import { forgetUnlockedKeys } from '@/crypto/download'
import { forgetSeenShares } from '@/utils/seen-shares'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: readAccessToken(),
    username: readUsername(),
  }),
  getters: {
    isAuthed: (state) => Boolean(state.accessToken),
    /** One or two letters for the header avatar when no photo is available. */
    avatarInitials: (state) => {
      const name = state.username.trim()
      if (!name) return '?'
      const parts = name.split(/[\s._-]+/).filter(Boolean)
      if (parts.length >= 2) {
        return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase()
      }
      return name.slice(0, 2).toUpperCase()
    },
  },
  actions: {
    /**
     * Both tokens, together.
     *
     * The refresh token was previously dropped on the floor at login, which is why a
     * session died 30 minutes in: the credential that exists to renew it was never stored.
     */
    setSession(accessToken: string, refreshToken: string, username = '') {
      this.accessToken = accessToken
      writeSession({ accessToken, refreshToken })
      if (username.trim()) {
        this.setUsername(username)
      }
    },
    setUsername(username: string) {
      this.username = username.trim()
      writeUsername(this.username)
    },
    /** Adopt a token the refresh interceptor has already written to storage. */
    syncFromStorage() {
      this.accessToken = readAccessToken()
      this.username = readUsername()
    },
    logout() {
      this.accessToken = ''
      this.username = ''
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
