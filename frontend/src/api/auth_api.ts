import { http } from './http'
import type { ClientKeyMaterial } from '@/utils/account-crypto'

export type VerificationPurpose = 'REGISTRATION' | 'PASSWORD_RESET'

export interface LoginPayload {
  username: string
  password: string
}

export interface SendVerificationCodePayload {
  email: string
  purpose: VerificationPurpose
}

export interface SendVerificationCodeData {
  code_sent: boolean
  expires_in_seconds: number
  resend_available_in_seconds: number
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
  verification_code: string
  key_material: ClientKeyMaterial
}

export interface RegisterData {
  user: {
    id: string
    username: string
    email: string
    role: string
    status: string
    email_verified: boolean
    created_at: string
  }
  key_id: string
  public_key_fingerprint: string
}

export interface ResetPasswordPayload {
  username: string
  email: string
  verification_code: string
  new_password: string
}

export interface ResetPasswordData {
  password_reset: boolean
  revoked_sessions: number
  key_envelopes_unchanged: boolean
}

export interface ApiEnvelope<T> {
  success: boolean
  message: string
  data: T
}

export const authApi = {
  sendVerificationCode(payload: SendVerificationCodePayload) {
    return http.post<ApiEnvelope<SendVerificationCodeData>>(
      '/auth/verification-codes/send',
      payload,
    )
  },
  register(payload: RegisterPayload) {
    return http.post<ApiEnvelope<RegisterData>>('/auth/register', payload)
  },
  resetPassword(payload: ResetPasswordPayload) {
    return http.post<ApiEnvelope<ResetPasswordData>>('/auth/password-reset', payload)
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
