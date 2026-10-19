# Security Policy

English | [简体中文](SECURITY.zh-CN.md)

SecureView is a Monash FIT3162 final-year project. It is run by a student team, not a company,
and there is no bug bounty. We still want to hear about security problems and will fix them.

## Reporting a vulnerability

Report privately. Do not open a public issue, pull request or discussion for a security problem.

- Email `swen0027@student.monash.edu` with a subject starting `[SecureView] Security`. This is the
  team's contact address, the same one the site's **Contact us** page uses.
- If you have access to this repository, you can instead open a draft security advisory under
  **Security → Advisories → New draft security advisory**. Only the maintainers can see it.

Include what you found, the steps to reproduce it, the commit or page it affects, and what an
attacker could do with it. Use your own test account. Do not send other people's data.

We will reply as soon as we can, tell you whether we can reproduce it and what we plan to do, and
tell you when it is fixed. We can credit you in the changelog if you want.

## Scope

In scope:

- The code in this repository: the Vue frontend, including its in-browser cryptography; the
  FastAPI backend; the MySQL schema and its privileges; and the deployment scripts under
  `deployment/`.
- The staging deployment at `https://secureview.tech`, within the rules below.

Out of scope:

- Problems in third-party services or libraries that are already public. Report those upstream;
  tell us if SecureView is affected in a way the upstream advice does not cover.
- Findings that need a compromised device, a malicious browser extension, or physical access.
- Missing best-practice headers or settings with no demonstrated impact.
- Social engineering of the team or the teaching staff.
- Risks the threat model already records as accepted. Check
  [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) first.

## What not to do

- Do not test against the live deployment using anyone else's account, and do not try to read,
  change or delete anyone else's files. Register your own accounts.
- Do not run destructive tests: no load or denial-of-service testing, no mass account creation,
  no attempts to fill the disk, and nothing that deletes or corrupts data.
- Do not run automated scanners against `https://secureview.tech` without asking first. The
  server is shared and has per-address limits.
- Do not try to reach the server itself (SSH, MySQL, the CI runner). They are not in scope.
- Stop and report as soon as you have shown the problem. Do not keep or share any data you saw.

To test something destructive, run the stack locally. [README.md](README.md) explains how, and
[security-lab/](security-lab/) holds the team's own attack scripts.

## Further reading

- [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md): what is protected, from whom, and the findings
  register.
- [docs/SECURITY_FLOWS.md](docs/SECURITY_FLOWS.md): how the encryption, sharing and recovery
  flows work.
- [docs/security/](docs/security/): dated scan reports.
