<template>
  <section class="card">
    <h1>Dashboard</h1>
    <p>This dashboard summarises encrypted files, sharing activity, integrity status, and audit events.</p>
  </section>

  <section class="card">
    <h2>Core Security Design</h2>
    <ul>
      <li>AES-256-GCM encrypts uploaded files.</li>
      <li>RSA-OAEP wraps the AES file key for authorised users.</li>
      <li>SHA-256 verifies encrypted file integrity.</li>
      <li>Audit logs use hash chaining for tamper evidence.</li>
    </ul>
  </section>
</template>
