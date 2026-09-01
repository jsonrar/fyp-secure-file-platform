# Automatic staging deployment

[English](AUTOMATIC_DEPLOYMENT.md) | [Simplified Chinese](AUTOMATIC_DEPLOYMENT.zh-CN.md)

The MCS21 staging VPS automatically deploys a new commit after it is merged into GitHub
`main`. A root-owned systemd timer checks the private repository approximately every two
minutes and invokes the existing guarded `mcs21-deploy` release command with the exact commit
SHA. Team members continue to develop on branches and merge reviewed pull requests; they do
not need to share a server account or Deploy Key.

This is a server-pull deployment, not a GitHub Actions workflow. The repository Deploy Key is
read-only and remains under the dedicated `mcs21-deploy` service account on the VPS. No VPS
SSH private key or production secret is stored in GitHub.

## Release flow and safeguards

```text
branch -> pull request -> merge into main
       -> systemd timer fetches main -> deploy exact commit
       -> database backup and read-only verification
       -> build and preflight -> atomic release switch
       -> service restart and health check -> audit record
```

The underlying release command serializes deployments, preserves the prior release, and rolls
the application back when its post-switch health check fails. Automatic database handling is
limited to backup and read-only production SQL verification. The runtime account cannot alter
the schema, and the automatic deployment service has no MySQL administrator or migration
credential. A schema change therefore requires a separately reviewed DBA SQL release, and it must be
applied to the database **before** the code that expects it is pushed — pushing first aborts
the deploy and quarantines the SHA, which blocks every later commit behind it. See
[Applying a schema revision to a running deployment](DEPLOYMENT.md#applying-a-schema-revision-to-a-running-deployment).

The verifier distinguishes a fresh audit chain (`OK`) from a valid chain that already contains
application events (`LIVE_DATA`). A live chain is accepted only when the singleton head keeps
the exact release schema marker, points to the newest audit row, and carries the same hash as
that row. `REVIEW`, `MISSING`, and `UNEXPECTED` remain blocking results. This allows ordinary
code-only releases without treating legitimate audit evidence as schema drift or weakening the
database, account, grant, and structural checks.

When deployment of a `main` commit fails, that SHA is quarantined. The timer will not repeatedly
retry the same broken commit; it tries again when `main` changes, or after an administrator
investigates and explicitly clears the quarantine. Scheduled checks that encounter the same
quarantined SHA exit successfully after reporting the skip, so the original failure remains
visible without generating a new systemd failure every two minutes.

## Operations

Every authorized deploy operator may inspect the current state:

```bash
sudo mcs21-auto-deploy status
systemctl status mcs21-auto-deploy.timer --no-pager
journalctl -u mcs21-auto-deploy.service --no-pager -n 100
sudo mcs21-deploy history
```

After correcting a transient failure, clear quarantine and retry the current `main` commit:

```bash
sudo mcs21-auto-deploy retry
```

Administrators may run a forced validation or retain the manual release path:

```bash
sudo mcs21-auto-deploy force
sudo mcs21-deploy all
```

## Installed artifacts

The versioned reference files are under `deployment/server/`. On the staging VPS they are
installed as:

- `mcs21-deploy` -> `/usr/local/sbin/mcs21-deploy`, the guarded manual/automatic release
  implementation;
- `mcs21-auto-deploy` -> `/usr/local/sbin/mcs21-auto-deploy`, owned by root and not writable
  by deploy operators;
- `mcs21-auto-deploy.service` and `mcs21-auto-deploy.timer` -> `/etc/systemd/system/`.

The server additionally provides its environment-specific mirror, Deploy Key, release command,
secrets, backup storage, and sudo policy. Environment-specific values must not be copied into
Git.

The timer is enabled with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mcs21-auto-deploy.timer
```

Moving to GitHub Actions later requires repository administration, protected deployment
environment secrets, a mandatory test gate, and an explicitly reviewed credential design.
Never commit a VPS private key or paste it into a workflow file.
