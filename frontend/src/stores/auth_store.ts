import { defineStore } from 'pinia'

import { clearSession, readAccessToken, writeSession } from '@/api/session'
import { forgetUnlockedKeys } from '@/crypto/download'
import { forgetSeenShares } from '@/utils/seen-shares'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: readAccessToken(),
  }),
  getters: {
    isAuthed: (state) => Boolean(state.accessToken),
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
    logout() {
      this.accessToken = ''
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
