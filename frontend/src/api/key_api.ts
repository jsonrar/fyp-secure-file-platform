import { http } from './http'
import type { ApiEnvelope } from './auth_api'

/** A public encryption key as the API returns it. Never contains private material. */
export interface PublicEncryptionKey {
  key_id: string
  user_id: string
  algorithm: string
  key_size_bits: number
  public_key_pem: string
  fingerprint: string
  created_at: string
}

export interface KeyProtectionProfile {
  profile_id: string
  format_version: number
  kdf_algorithm: string
  kdf_version: number
  kdf_salt: string
  kdf_memory_kib: number
  kdf_iterations: number
  kdf_parallelism: number
  derived_key_length: number
  amk_wrapping_algorithm: string
  wrapped_amk: string
  amk_nonce: string
  amk_auth_tag: string
  aad_version: number
  revision: number
  updated_at: string
}

export interface EncryptedPrivateKeyBundle {
  bundle_id: string
  format_version: number
  private_key_format: string
  derivation_algorithm: string
  derivation_salt: string
  encryption_algorithm: string
  encrypted_private_key: string
  nonce: string
  auth_tag: string
  aad_version: number
  ciphertext_sha256: string
  revision: number
  updated_at: string
}

export interface MyKeyBundle {
  key: PublicEncryptionKey
  protection: KeyProtectionProfile
  private_key_bundle: EncryptedPrivateKeyBundle
}

export const keyApi = {
  /** The caller's active public key plus the encrypted envelopes only they can open. */
  myBundle() {
    return http.get<ApiEnvelope<MyKeyBundle>>('/keys/me')
  },
  /** A historical bundle, needed to decrypt files still wrapped to a superseded key. */
  ownedBundle(keyId: string) {
    return http.get<ApiEnvelope<MyKeyBundle>>(`/keys/me/${keyId}`)
  },
  /** Another user's active public key, for wrapping a shared file key to them. */
  activePublicKey(userId: string) {
    return http.get<ApiEnvelope<PublicEncryptionKey>>(`/keys/users/${userId}/active`)
  },
}
