import { http } from './http'
import type { ApiEnvelope } from './auth_api'

/**
 * The active recovery public key.
 *
 * Every upload must wrap its file key to this key as well as to the owner's. The matching
 * private key is held offline, so a client can never verify that wrapping — see
 * `docs/crypto/FILE_ENVELOPE.md`, "Required self-tests".
 */
export interface RecoveryPublicKey {
  key_id: string
  algorithm: 'RSA-OAEP-SHA256'
  key_size_bits: number
  public_key_pem: string
  fingerprint: string
  status: 'ACTIVE' | 'REVOKED'
  created_at: string
}

export const recoveryApi = {
  getPublicKey() {
    return http.get<ApiEnvelope<RecoveryPublicKey>>('/recovery/public-key')
  },
  createRequest(payload: unknown) {
    return http.post('/recovery/request', payload)
  },
  approve(requestId: number) {
    return http.post(`/recovery/${requestId}/approve`)
  },
  execute(requestId: number) {
    return http.post(`/recovery/${requestId}/execute`)
  },
  listRequests() {
    return http.get('/recovery/requests')
  },
}
