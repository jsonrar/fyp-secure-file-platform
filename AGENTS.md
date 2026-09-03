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

## Change Log

- Record every notable change in `changelog/CHANGELOG.md`, under the section matching the area
  you changed. A change is notable when a teammate would be surprised to discover it by
  reading the diff instead of the log.
- Write the entry as a pair of lines, English first then 简体中文, matching the rest of the
  file. State why the change mattered, not only what moved: the diff already records what.
- Work-package records — a baseline taken, a scope declared, a limitation confirmed and left
  open — go in `changelog/work-packages/<track>.md` instead, even when no code changed. Work
  that both shipped a change and closed a package belongs in both; they answer different
  questions and are not duplicates.
- See `changelog/README.md` for the full convention.

## Project-status synchronization

- Treat GitHub Issues as the executable backlog. `TODO.md` and `TODO.zh-CN.md` are prioritized
  summaries and must link to Issues rather than maintain independent work lists.
- Keep `README.md` and `README.zh-CN.md` aligned with current user-visible capabilities,
  schema/runtime requirements, and staging entry points. Do not leave a shipped feature
  described as missing.
- Every pull request must review changelog, README, TODO, linked Issues, tests, migrations,
  secrets, and deployment impact. Update the affected records or state why each is `N/A`.
- A runtime change is not complete when it merges. Verify that automatic deployment reaches
  the exact merged SHA, check health and the affected user flow, then link that evidence before
  closing its Issue.
- Use `.github/pull_request_template.md` for the evidence checklist. Never claim a skipped
  integration suite passed, and never close an Issue on merge alone when deployment evidence
  is required.
