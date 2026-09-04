export type KnowledgeCategory =
  | 'basics'
  | 'symmetric'
  | 'asymmetric'
  | 'keys'
  | 'hashing'
  | 'best-practices'

export interface KnowledgeArticle {
  id: string
  title: string
  category: KnowledgeCategory
  tags: string[]
  summary: string
  content: string
}

export const categoryLabels: Record<KnowledgeCategory, string> = {
  basics: 'Encryption Basics',
  symmetric: 'Symmetric Encryption',
  asymmetric: 'Asymmetric Encryption',
  keys: 'Keys & Key Management',
  hashing: 'Hashing & Integrity',
  'best-practices': 'Best Practices',
}

export const knowledgeArticles: KnowledgeArticle[] = [
  {
    id: 'what-is-encryption',
    title: 'What Is Encryption?',
    category: 'basics',
    tags: ['encryption', 'basics', 'privacy', 'security'],
    summary: 'Encryption transforms readable data into unreadable ciphertext so only authorized parties can access it.',
    content: `Encryption is the process of converting plaintext (readable data) into ciphertext (unreadable data) using an algorithm and a key. Only someone with the correct key can reverse the process and recover the original data — this is called decryption.

Encryption protects data in three common scenarios:
• **At rest** — files stored on disk or in the cloud
• **In transit** — data traveling over networks (HTTPS, VPN)
• **In use** — emerging techniques for processing encrypted data

Modern encryption does not rely on hiding the algorithm. Algorithms like AES and RSA are public. Security comes from keeping the **key** secret.`,
  },
  {
    id: 'symmetric-vs-asymmetric',
    title: 'Symmetric vs Asymmetric Encryption',
    category: 'basics',
    tags: ['symmetric', 'asymmetric', 'comparison', 'AES', 'RSA'],
    summary: 'Symmetric uses one shared key; asymmetric uses a public/private key pair. Most systems combine both.',
    content: `**Symmetric encryption** uses a single secret key for both encryption and decryption. Both parties must possess the same key before communication begins. Examples: AES, ChaCha20. It is fast and ideal for encrypting large amounts of data.

**Asymmetric encryption** uses a key pair: a public key (shared openly) and a private key (kept secret). Data encrypted with the public key can only be decrypted with the private key. Examples: RSA, ECC. It solves the key distribution problem but is slower.

**Hybrid approach (used by SecureView and TLS):**
1. Generate a random AES session key
2. Encrypt the file with AES (fast)
3. Encrypt the AES key with the recipient's RSA public key (secure key delivery)
4. Send both the encrypted file and encrypted key

This gives you the speed of symmetric encryption with the key-exchange convenience of asymmetric encryption.`,
  },
  {
    id: 'public-private-keys',
    title: 'What Are Public and Private Keys?',
    category: 'keys',
    tags: ['public key', 'private key', 'RSA', 'PKI', 'key pair'],
    summary: 'A key pair where the public key encrypts or verifies, and the private key decrypts or signs. Never share your private key.',
    content: `In asymmetric cryptography, each user has two mathematically linked keys:

**Public key** — Can be shared with anyone. Others use it to:
• Encrypt messages meant only for you
• Verify digital signatures you created

**Private key** — Must remain secret. You use it to:
• Decrypt messages encrypted with your public key
• Create digital signatures proving you authored data

Think of the public key as an open padlock you give to others — they can lock a box (encrypt) but only you have the key to unlock it (decrypt).

**Critical rules:**
• Never share, email, or store your private key in plain text
• If your private key is compromised, generate a new key pair immediately
• Public keys can be published on key servers or embedded in certificates`,
  },
  {
    id: 'aes-128-explained',
    title: 'How AES-128 Works',
    category: 'symmetric',
    tags: ['AES', 'AES-128', 'symmetric', 'block cipher'],
    summary: 'AES-128 encrypts 128-bit blocks with a 128-bit key through 10 transformation rounds.',
    content: `AES-128 is the Advanced Encryption Standard configured with a **128-bit key**.

**Key size:** 128 bits (16 bytes).
**Block size:** Always 128 bits — the same for every AES variant.
**Rounds:** 10.

Each round applies:
1. **SubBytes** — Replace each byte using a lookup table (S-box)
2. **ShiftRows** — Rotate rows of the state matrix
3. **MixColumns** — Mix column data (skipped in the final round)
4. **AddRoundKey** — XOR the state with a round key derived from the main key

AES-128 remains NIST-approved and is widely used (for example in many TLS suites). SecureView’s education materials cover it as a distinct topic from AES-256. **AES-192 is intentionally omitted for now.**

**Note on DES / 3DES:** Those older block ciphers are not taught here. NIST removed 3DES from its recommendations in 2023; use AES instead.`,
  },
  {
    id: 'aes-256-explained',
    title: 'How AES-256 Works',
    category: 'symmetric',
    tags: ['AES', 'AES-256', 'symmetric', 'block cipher', 'file encryption', 'SecureView'],
    summary: 'AES-256 uses a 256-bit key and 14 rounds — SecureView’s default for encrypting files in the browser.',
    content: `AES-256 is the Advanced Encryption Standard configured with a **256-bit key**.

**Key size:** 256 bits (32 bytes).
**Block size:** 128 bits (same as AES-128).
**Rounds:** 14 — four more than AES-128, which increases the security margin.

Round operations are the same family as AES-128 (SubBytes, ShiftRows, MixColumns, AddRoundKey), but the longer key schedule and extra rounds make exhaustive search far harder.

**In SecureView:** Files are encrypted in the browser with **AES-256-GCM** so the server only stores authenticated ciphertext. AES-192 is out of scope on this education page for now.

**Why not DES / 3DES?** NIST deprecated and removed 3DES from approved algorithms in 2023. Modern systems should use AES (or ChaCha20-Poly1305), not triple-DES.`,
  },
  {
    id: 'rsa-explained',
    title: 'How RSA Encryption Works',
    category: 'asymmetric',
    tags: ['RSA', 'asymmetric', 'public key', 'prime numbers', 'key exchange'],
    summary: 'RSA security relies on the difficulty of factoring large numbers into their prime components.',
    content: `RSA is named after its inventors: Rivest, Shamir, and Adleman (1977).

**Key generation (simplified):**
1. Choose two large random prime numbers p and q
2. Compute n = p × q (the modulus)
3. Choose public exponent e (commonly 65537)
4. Compute private exponent d such that (e × d) mod φ(n) = 1
5. Public key = (n, e), Private key = (n, d)

**Encryption:** Ciphertext = Plaintext^e mod n
**Decryption:** Plaintext = Ciphertext^d mod n

Because factoring n back into p and q is computationally infeasible for large n (2048+ bits), an attacker cannot derive d from the public key alone.

**In SecureView:** RSA wraps AES keys so recipients can decrypt shared files using their private key without both parties sharing a symmetric secret in advance.`,
  },
  {
    id: 'hashing-vs-encryption',
    title: 'Hashing vs Encryption — What\'s the Difference?',
    category: 'hashing',
    tags: ['hash', 'SHA-256', 'integrity', 'one-way', 'encryption'],
    summary: 'Encryption is reversible with a key; hashing is one-way and used to verify data has not changed.',
    content: `These are often confused but serve different purposes:

| | Encryption | Hashing |
|---|---|---|
| **Reversible?** | Yes, with the key | No — one-way |
| **Purpose** | Confidentiality | Integrity verification |
| **Output size** | Same as input (+ padding) | Fixed (e.g., 256 bits for SHA-256) |
| **Example** | AES, RSA | SHA-256, SHA-3 |

**When to use hashing:**
• Verify a downloaded file has not been tampered with
• Store password digests (always with a unique salt)
• Create blockchain block links
• Generate fixed-size fingerprints for large files

**When to use encryption:**
• Protect file contents from unauthorized reading
• Secure data in transit
• Protect stored credentials (though passwords should be hashed, not encrypted)

SecureView uses SHA-256 hashes to let you verify file integrity after decryption.`,
  },
  {
    id: 'key-management',
    title: 'Key Management Best Practices',
    category: 'keys',
    tags: ['key management', 'password', 'storage', 'rotation', 'backup'],
    summary: 'Strong keys, secure storage, and regular rotation are essential for maintaining encryption security.',
    content: `Even the strongest algorithm fails if keys are poorly managed.

**Creating strong keys:**
• Use at least 256 bits of entropy for AES keys
• Prefer randomly generated keys over memorable passwords for file encryption
• If using a password, make it long (16+ characters) with mixed character types

**Storing keys safely:**
• Never store private keys in plain text on shared drives
• Use OS keychains or hardware security modules (HSM) when possible
• Encrypt private keys with a passphrase before storage

**Key rotation:**
• Rotate keys periodically or after any suspected compromise
• Re-encrypt files with new keys after rotation
• Maintain an audit log of key usage (SecureView provides access records)

**Backup and recovery:**
• Store recovery keys in a separate secure location
• Test your recovery process before you need it
• Document who has access to which keys in team environments`,
  },
  {
    id: 'caesar-cipher-history',
    title: 'Caesar Cipher — History and Weaknesses',
    category: 'basics',
    tags: ['caesar', 'substitution', 'classical', 'frequency analysis'],
    summary: 'One of the oldest ciphers, easily broken by trying all 25 shifts or analyzing letter frequencies.',
    content: `The Caesar cipher shifts each letter by a fixed number of positions in the alphabet. Julius Caesar reportedly used a shift of 3 to protect military messages.

**Why it fails today:**
• Only 25 possible keys — exhaustive search takes milliseconds
• **Frequency analysis** — in English, 'E' is the most common letter. If 'H' appears most often in ciphertext with shift 3, the key is likely 3.
• Structure is preserved — word lengths and punctuation remain visible

**Learning value:** Despite being insecure, the Caesar cipher teaches:
• The concept of a key parameter
• Substitution as an encryption technique
• Why modern algorithms need large key spaces and diffusion

Try breaking and creating Caesar ciphers in the Playground section of this page.`,
  },
  {
    id: 'xor-foundation',
    title: 'XOR — The Bit-Level Foundation',
    category: 'symmetric',
    tags: ['XOR', 'binary', 'stream cipher', 'one-time pad'],
    summary: 'Exclusive-or is reversible and fast, forming the core operation in AES, ChaCha20, and one-time pads.',
    content: `XOR (exclusive or) operates on individual bits:

\`\`\`
0 ⊕ 0 = 0
0 ⊕ 1 = 1
1 ⊕ 0 = 1
1 ⊕ 1 = 0
\`\`\`

**Self-inverse property:** A ⊕ K ⊕ K = A

This means encryption and decryption are the same operation — XOR plaintext with key to encrypt, XOR ciphertext with the same key to decrypt.

**One-time pad:** If the key is truly random, as long as the message, and used only once, XOR encryption is theoretically unbreakable (proven by Shannon, 1949). In practice, generating and distributing such keys is impractical for most use cases.

**In modern ciphers:** AES internally uses XOR in its AddRoundKey step. Stream ciphers like ChaCha20 XOR a keystream with plaintext.`,
  },
  {
    id: 'secure-file-sharing',
    title: 'Secure File Sharing Workflow',
    category: 'best-practices',
    tags: ['file sharing', 'SecureView', 'workflow', 'access control'],
    summary: 'Encrypt files before sharing, distribute keys separately, and set access limits on shared links.',
    content: `Follow this workflow when sharing sensitive files through SecureView:

**1. Encrypt before upload**
Upload your file and let SecureView generate or accept an encryption key. The platform encrypts with AES-256 before storage.

**2. Share keys through a separate channel**
Never send the encryption key in the same email as the download link. Use a phone call, encrypted messenger, or in-person exchange.

**3. Use access controls**
Set link expiration dates and download limits. Revoke access when the recipient no longer needs the file.

**4. Verify integrity**
Compare SHA-256 hashes before and after transfer to confirm the file was not modified in transit.

**5. Audit access**
Review access logs to confirm only authorized parties downloaded the file.

**6. Delete when done**
Remove shared links and encrypted copies from storage when they are no longer needed.`,
  },
  {
    id: 'encryption-at-rest-transit',
    title: 'Encryption at Rest vs In Transit',
    category: 'basics',
    tags: ['at rest', 'in transit', 'HTTPS', 'TLS', 'storage'],
    summary: 'Data needs protection both while stored and while moving across networks — they require different approaches.',
    content: `**Encryption at rest** protects stored data:
• Full-disk encryption (BitLocker, FileVault)
• Database column encryption
• SecureView file encryption before cloud storage
• Protects against physical theft or unauthorized storage access

**Encryption in transit** protects data during transmission:
• HTTPS/TLS for web traffic
• VPN for network tunnels
• SFTP/SCP for file transfers
• Protects against network eavesdropping (man-in-the-middle)

**Both are needed:** Encrypting files at rest does not protect them during upload/download unless transit encryption is also used. SecureView uses HTTPS for transit and AES-256 for storage — defense in depth.`,
  },
  {
    id: 'digital-signatures',
    title: 'Digital Signatures Explained',
    category: 'asymmetric',
    tags: ['digital signature', 'RSA', 'integrity', 'authentication', 'non-repudiation'],
    summary: 'Sign with your private key; anyone can verify with your public key. Proves authorship and detects tampering.',
    content: `A digital signature provides three guarantees:
• **Authentication** — Confirms who created the message
• **Integrity** — Detects any modification after signing
• **Non-repudiation** — Signer cannot deny having signed

**How it works:**
1. Hash the message (e.g., with SHA-256)
2. Encrypt the hash with the signer's **private key** → this is the signature
3. Recipient decrypts the signature with the signer's **public key** to recover the hash
4. Recipient hashes the received message and compares — match means authentic and unmodified

Note: Signing uses the **private** key (opposite of encryption). This confuses many beginners.

Digital signatures are used in code signing, PDF signing, blockchain transactions, and secure software update verification.`,
  },
]

export function searchKnowledge(query: string, category?: KnowledgeCategory | 'all'): KnowledgeArticle[] {
  const q = query.trim().toLowerCase()
  return knowledgeArticles.filter((article) => {
    if (category && category !== 'all' && article.category !== category) return false
    if (!q) return true
    const haystack = [
      article.title,
      article.summary,
      article.content,
      ...article.tags,
      categoryLabels[article.category],
    ]
      .join(' ')
      .toLowerCase()
    return haystack.includes(q)
  })
}
