import { http } from './http'

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
}

export const authApi = {
  register(payload: RegisterPayload) {
    return http.post('/auth/register', payload)
  },
  login(payload: LoginPayload) {
    return http.post('/auth/login', payload)
  },
  logout() {
    return http.post('/auth/logout')
  },
  me() {
    return http.get('/auth/me')
  },
}
