# Repository Agent Rules

These rules apply to the entire repository.

## Application HTTP Methods

- Application-layer HTTP endpoints, clients, tests, examples, and OpenAPI contracts may use
  only `GET` and `POST`.
- Infrastructure may still handle protocol-level behavior required by browsers and HTTP
  servers (for example, automatic CORS preflight handling), but application code must not
  define or initiate those methods as business API operations.
- Use `GET` only for read-only operations. Use `POST` for creation, updates, deletion,
  revocation, and every other state-changing command or action.
- State-changing action routes must use an explicit action path when needed for clarity, for
  example `POST /files/{file_id}/delete` and
  `POST /auth/sessions/{session_id}/revoke`.
- Do not add or retain application HTTP `PUT`, `PATCH`, or `DELETE` routes or client calls.
- CORS `allow_methods` must contain only `GET` and `POST`. Keep route implementations,
  frontend clients, tests, documentation, examples, and generated OpenAPI behavior aligned
  with this policy.
- This HTTP restriction does not prohibit SQL `UPDATE`/`DELETE`, database privileges,
  migrations, foreign-key actions, or internal repository operations. Do not rewrite
  database terminology as though it were an HTTP method.
