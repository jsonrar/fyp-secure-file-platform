# SecureView load test

A client that behaves like the browser: it encrypts every upload with the real file envelope
and decrypts and SHA-256-verifies every download, while timing each operation.

- Plan, known limits, findings and the full procedure:
  [`docs/PERFORMANCE_TESTING.md`](../docs/PERFORMANCE_TESTING.md)
  ([简体中文](../docs/PERFORMANCE_TESTING.zh-CN.md)).
- Local dry run against a disposable stack: `bash loadtest/run_local.sh` (needs `DB_*` for a
  `_test` database).
- Tests: `.venv/bin/python -m pytest tests`.

| File | What it is |
| --- | --- |
| `secureview_load/envelope.py` | The browser's file envelope (AAD-3, AES-GCM / ChaCha20-Poly1305, RSA-OAEP), pinned to `docs/crypto/test_vectors.json` |
| `secureview_load/client.py` | One virtual user over the public API |
| `secureview_load/runner.py` | Scenarios: `smoke`, `steps`, `parallel`, `mixed`, `sizes`, `logins` |
| `secureview_load/report.py` | Markdown report and charts, lined up with the server sampler |
| `server_sampler.py` | Runs on the server with the system Python: CPU, memory, disk, network, process and connection counts |
| `../backend/scripts/seed_load_users.py` | Creates the test accounts on the server |

Never point it at a shared server without telling the team; it refuses a non-local host unless
`--confirm-remote` is given.
