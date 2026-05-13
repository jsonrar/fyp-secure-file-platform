import { defineStore } from 'pinia'

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
    },
  },
})
