import { defineStore } from 'pinia'

import { forgetUnlockedKeys } from '@/crypto/download'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('access_token') || '',
  }),
  getters: {
    isAuthed: (state) => Boolean(state.accessToken),
  },
  actions: {
    setToken(token: string) {
      this.accessToken = token
      localStorage.setItem('access_token', token)
    },
    logout() {
      this.accessToken = ''
      localStorage.removeItem('access_token')
      // The unwrapped account key outlives the token otherwise: the next person at this
      // machine would sign in and find the previous session's files already decryptable.
      forgetUnlockedKeys()
    },
  },
})
