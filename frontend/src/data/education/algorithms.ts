export type AlgorithmId = 'aes' | 'rsa' | 'sha' | 'des3des' | 'chacha20' | 'argon2id'

export type AlgorithmType = 'symmetric' | 'asymmetric' | 'hash' | 'kdf'

export interface AlgorithmStep {
  title: string
  description: string
}

export interface AlgorithmInfo {
  id: AlgorithmId
  name: string
  shortLabel: string
  type: AlgorithmType
  tagline: string
  summary: string
  howItWorks: AlgorithmStep[]
  useCases: string[]
  strengths: string[]
  limitations: string[]
  keyFacts: string[]
}

export const algorithms: AlgorithmInfo[] = [
  {
    id: 'aes',
    name: 'AES (Advanced Encryption Standard)',
    shortLabel: 'AES',
    type: 'symmetric',
    tagline: 'Industry-standard symmetric encryption for files and data at rest.',
    summary:
      'AES uses the same secret key to encrypt and decrypt data. It processes data in fixed-size blocks (128 bits) through multiple rounds of substitution and permutation, making brute-force attacks impractical at 256-bit key sizes.',
    howItWorks: [
      {
        title: 'Key setup',
        description: 'A shared secret key (128, 192, or 256 bits) is agreed upon by sender and receiver before any data is encrypted.',
      },
      {
        title: 'Block division',
        description: 'Plaintext is split into 128-bit blocks. Each block is transformed through the AES round function.',
      },
      {
        title: 'Round transformations',
        description: 'Each round applies SubBytes, ShiftRows, MixColumns, and AddRoundKey using derived round keys.',
      },
      {
        title: 'Decryption',
        description: 'The receiver applies inverse round operations in reverse order with the same secret key.',
      },
    ],
    useCases: ['File encryption on SecureView', 'Database encryption', 'VPN tunnels', 'Disk encryption (BitLocker, FileVault)'],
    strengths: ['Very fast on modern hardware', 'Well-studied and widely trusted', 'Supports large files efficiently'],
    limitations: ['Both parties must securely share the same key', 'Key compromise exposes all encrypted data'],
    keyFacts: ['AES-256 is used by SecureView for file encryption', 'NIST approved in 2001', 'No practical attacks against full AES-256'],
  },
  {
    id: 'rsa',
    name: 'RSA (Rivest–Shamir–Adleman)',
    shortLabel: 'RSA',
    type: 'asymmetric',
    tagline: 'Public-key cryptography for secure key exchange and digital signatures.',
    summary:
      'RSA uses a mathematically linked key pair: a public key anyone can use to encrypt, and a private key only the owner holds to decrypt. Security relies on the difficulty of factoring large prime numbers.',
    howItWorks: [
      {
        title: 'Key pair generation',
        description: 'Two large prime numbers produce a public key (shared openly) and a private key (kept secret).',
      },
      {
        title: 'Encryption with public key',
        description: 'Anyone encrypts using the recipient\'s public key. Only the matching private key can decrypt.',
      },
      {
        title: 'Digital signatures',
        description: 'The owner signs data with their private key. Others verify authenticity using the public key.',
      },
      {
        title: 'Hybrid use with AES',
        description: 'RSA encrypts a random AES session key; AES encrypts the actual file — combining speed with secure key delivery.',
      },
    ],
    useCases: ['Encrypting AES keys for file sharing', 'TLS/HTTPS handshake', 'Code signing', 'Email encryption (PGP)'],
    strengths: ['No pre-shared secret needed for key delivery', 'Enables digital signatures', 'Foundation of PKI infrastructure'],
    limitations: ['Slow for large files', 'Vulnerable if key size is too small', 'Requires secure key storage'],
    keyFacts: ['Minimum 2048-bit keys recommended today', 'Often paired with AES in hybrid encryption', 'Used in SecureView for wrapping file keys'],
  },
  {
    id: 'sha',
    name: 'SHA (Secure Hash Algorithm)',
    shortLabel: 'SHA',
    type: 'hash',
    tagline: 'One-way fingerprinting — verify integrity, not confidentiality.',
    summary:
      'The SHA family (SHA-256, SHA-384, SHA-512) produces a fixed-size digest from any input. It is one-way: you cannot recover the input from the hash. Any change to the input produces a completely different digest.',
    howItWorks: [
      {
        title: 'Padding the message',
        description: 'Input is padded to a multiple of 512 bits, appending a length field at the end.',
      },
      {
        title: 'Process in chunks',
        description: 'Each 512-bit chunk passes through multiple rounds of bitwise operations, updating internal state.',
      },
      {
        title: 'Produce fixed output',
        description: 'SHA-256 outputs 256 bits (64 hex chars); SHA-512 outputs 512 bits.',
      },
      {
        title: 'Verification',
        description: 'Hash the received file and compare digests. A match confirms the file was not altered.',
      },
    ],
    useCases: ['File integrity checks on SecureView', 'Password storage (with salt)', 'Blockchain', 'Digital signature inputs'],
    strengths: ['Deterministic and fast', 'Collision-resistant in practice', 'Fixed output size regardless of input'],
    limitations: ['Not encryption — cannot decrypt a hash', 'Rainbow tables without salt (passwords)', 'Not a substitute for AES/RSA'],
    keyFacts: ['SHA-256 output is always 64 hex characters', 'Used for file hash verification in SecureView', 'Part of the SHA-2 family (SHA-224/256/384/512)'],
  },
  {
    id: 'des3des',
    name: 'DES / 3DES',
    shortLabel: 'DES / 3DES',
    type: 'symmetric',
    tagline: 'Historical block ciphers — DES is obsolete; 3DES extended its life but is now deprecated.',
    summary:
      'DES (Data Encryption Standard) uses a 56-bit key and 64-bit blocks. 3DES applies DES three times with two or three keys (112/168-bit effective strength). Both are largely replaced by AES due to small key sizes and performance.',
    howItWorks: [
      {
        title: 'DES block structure',
        description: 'Each 64-bit block passes through 16 Feistel rounds with substitution (S-boxes) and permutation.',
      },
      {
        title: 'Key schedule',
        description: 'The 56-bit key generates 16 round subkeys used in each Feistel round.',
      },
      {
        title: '3DES triple application',
        description: '3DES encrypts with Key1, decrypts with Key2, encrypts again with Key3 (EDE mode): E(K1) → D(K2) → E(K3).',
      },
      {
        title: 'Why deprecated',
        description: '56-bit DES keys are brute-forced in hours. 3DES is slow and offers only 112-bit security — NIST deprecated it in 2023.',
      },
    ],
    useCases: ['Legacy banking systems (being phased out)', 'Historical reference', 'Understanding Feistel cipher design'],
    strengths: ['Simple Feistel structure taught in textbooks', '3DES was a practical DES upgrade for decades', 'Influenced modern block cipher design'],
    limitations: ['DES key space is far too small today', '3DES is slow compared to AES', 'Officially deprecated — use AES instead'],
    keyFacts: ['DES published in 1977, broken by brute force in 1998', '3DES effective key: 112 bits (meet-in-the-middle attack)', 'NIST recommends AES for all new systems'],
  },
  {
    id: 'chacha20',
    name: 'ChaCha20',
    shortLabel: 'ChaCha20',
    type: 'symmetric',
    tagline: 'Modern stream cipher — fast, secure, and widely used in TLS and mobile apps.',
    summary:
      'ChaCha20 generates a pseudorandom keystream from a 256-bit key and 96-bit nonce, then XORs it with plaintext. Combined with Poly1305 (ChaCha20-Poly1305), it provides authenticated encryption used by Google, WireGuard, and TLS 1.3.',
    howItWorks: [
      {
        title: 'Initialize state',
        description: 'A 512-bit state matrix is filled with constants, the key, nonce, and a block counter.',
      },
      {
        title: 'Generate keystream',
        description: '20 rounds of quarter-round operations (ARX: Add, Rotate, XOR) scramble the state to produce keystream bytes.',
      },
      {
        title: 'XOR with plaintext',
        description: 'Each plaintext byte is XORed with a keystream byte. Decryption XORs the same keystream again.',
      },
      {
        title: 'Authentication (Poly1305)',
        description: 'Poly1305 produces a MAC tag so tampering is detected. ChaCha20-Poly1305 is an AEAD mode.',
      },
    ],
    useCases: ['TLS 1.3 cipher suites', 'WireGuard VPN', 'Signal Protocol messaging', 'Alternative to AES-GCM on devices without AES hardware'],
    strengths: ['Fast in software without AES-NI hardware', 'Resistant to timing side-channel attacks', 'Simple, auditable design'],
    limitations: ['Nonce must never be reused with the same key', 'Less hardware acceleration than AES on some platforms', 'Requires Poly1305 for integrity in practice'],
    keyFacts: ['Designed by Daniel Bernstein (2008)', 'Used in Chrome HTTPS and Android', 'RFC 8439 standardizes ChaCha20-Poly1305'],
  },
  {
    id: 'argon2id',
    name: 'Argon2id',
    shortLabel: 'Argon2id',
    type: 'kdf',
    tagline: 'Memory-hard password hashing — winner of the Password Hashing Competition (2015).',
    summary:
      'Argon2id converts passwords into cryptographic keys or stored hashes. It deliberately consumes memory and CPU time, making brute-force and GPU/ASIC attacks expensive. It is the recommended algorithm for password storage today.',
    howItWorks: [
      {
        title: 'Salt and parameters',
        description: 'A unique random salt is generated per password. Parameters include memory cost, time iterations, and parallelism.',
      },
      {
        title: 'Memory filling',
        description: 'Argon2 fills a large memory block with pseudorandom data derived from the password and salt.',
      },
      {
        title: 'Pass over memory',
        description: 'Multiple passes read and write the memory block in a password-dependent pattern, resisting parallel attacks.',
      },
      {
        title: 'Output hash',
        description: 'The final memory state is compressed into a fixed-length hash stored in the database — never store plaintext passwords.',
      },
    ],
    useCases: ['User password storage', 'Key derivation from passphrases', 'Secure credential databases', 'Replacing bcrypt/scrypt/PBKDF2'],
    strengths: ['Memory-hard — defeats GPU/ASIC brute force', 'Argon2id resists both side-channel and GPU attacks', 'Configurable cost parameters scale with hardware'],
    limitations: ['Higher memory use than bcrypt', 'Wrong parameters can be too fast or too slow', 'Not for encrypting files directly — use for passwords/KDF'],
    keyFacts: ['Winner of Password Hashing Competition (2015)', 'Argon2id = hybrid of Argon2i and Argon2d', 'Recommended by OWASP for password hashing'],
  },
]

export function getAlgorithm(id: AlgorithmId): AlgorithmInfo | undefined {
  return algorithms.find((a) => a.id === id)
}
