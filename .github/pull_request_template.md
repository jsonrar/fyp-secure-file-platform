## What changed and why

<!-- Explain the user/security/operations outcome, not only the files changed. -->

## Linked Issue

Closes #

## Evidence checklist

### Product records

- [ ] `changelog/CHANGELOG.md` updated in English and 简体中文, or `N/A` explained below.
- [ ] `README.md` and `README.zh-CN.md` still describe current capabilities/setup, or `N/A`.
- [ ] `TODO.md`, `TODO.zh-CN.md`, and the linked GitHub Issue still agree, or `N/A`.
- [ ] Design/API/schema/deployment documents affected by this change are updated, or `N/A`.
- [ ] `docs/presentation/TALKING_POINTS.md` and `REFLECTION.md` reflect this change, or `N/A`.
- [ ] Every changed Markdown document is updated in both English and 简体中文.

### Verification and safety

- [ ] Relevant format, lint, typecheck, unit, integration, build, and migration checks ran.
- [ ] Any skipped test suite is listed explicitly; a skip is not reported as a pass.
- [ ] Migration and production-SQL impact was reviewed, including backup/rollback when relevant.
- [ ] Staged files and generated artifacts were checked for credentials, tokens, private keys,
      plaintext test files, and deployment secrets.

### Merge and deployment

- [ ] This PR is safe to merge independently and its rollback boundary is documented.
- [ ] Runtime impact: `yes` / `no`.
- [ ] After merge, automatic deployment reached the exact merge SHA, or deployment is `N/A`.
- [ ] Health checks and the affected live user flow were verified after deployment, or `N/A`.
- [ ] Deployment evidence was linked to the Issue before it was closed.

## Commands and results

<!-- Include concise counts/results and the environment used. Never paste secrets. -->

## N/A explanations, residual risks, and follow-up

<!-- An unchecked item must be explained here; link new follow-up Issues rather than hiding debt. -->
