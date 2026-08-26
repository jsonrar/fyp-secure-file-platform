import { defineStore } from 'pinia'

import { clearSession, readAccessToken, writeSession } from '@/api/session'
import { forgetUnlockedKeys } from '@/crypto/download'

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
    },
  },
})
