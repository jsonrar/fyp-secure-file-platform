# Self-hosted CI runner

[English](README.md) | [简体中文](README.zh-CN.md)

Every job in `.github/workflows/ci.yml` runs on these runners on the staging VPS, not on
GitHub-hosted machines. There are three independent runners, so the five test jobs of one run go
in parallel and a full run takes about as long as on GitHub (about 5 minutes). A private repository on GitHub's free plan has 2,000 Actions minutes a month. That ran
out on 2026-10-04, after 145 runs in four days at about 13 billed minutes each. A self-hosted
runner's minutes are not billed.

## Isolation from production

The VPS also runs SecureView itself: the API on `127.0.0.1:8000` and MySQL on `127.0.0.1:3306`.
CI uses the same ports, and it runs every pull request's code plus several hundred npm and pip
packages. So no runner touches the host directly. Each of the three is paired with its own Docker
daemon in its own network namespace, so two jobs that both publish MySQL on 3306 never meet.

| What | How |
| --- | --- |
| Containers a job starts (MySQL services, the tamper lab) | Run in the runner's own Docker daemon (`dind`). They cannot see the host's containers, images, volumes or ports. The host's Docker socket is never mounted. |
| Ports | The runner shares only dind's network namespace. A service a job publishes on 3306 is `127.0.0.1:3306` to that job, and unrelated to the host's 3306. |
| Reaching the host | `mcs21-ci-runner-firewall.service` drops new connections from the CI subnet `172.31.250.0/24` to any address of the host itself: sshd, the WeChat bot on the Docker bridge, MySQL. Internet access stays open (GitHub, npm, PyPI, Docker Hub). |
| Load | Each runner and each dind is capped at 2 CPUs and 2.5 GB, and has a low CPU weight (`cpu_shares: 256`): when production and CI compete, production gets about four times the share. A typical run peaks well under the caps. |
| Secrets | Nothing from `/opt/mcs21`, `/run/secrets` or `/etc` is mounted. The only state is three named volumes. |

**Residual risk:** dind needs `privileged: true`, so a container escape from a malicious package
in CI would reach the host. This was accepted because the repository is private and only the five
team members can push. If that changes (for example, the repository becomes public), stop the
runner first.

## Install or update (root, on the VPS)

1. A repository **admin** creates a registration token, valid for an hour, through **Settings → Actions → Runners → New self-hosted runner**, or:

   ```bash
   gh api -X POST repos/jsonrar/fyp-secure-file-platform/actions/runners/registration-token --jq .token
   ```

2. On the VPS, from this directory:

   ```bash
   bash install.sh
   ```

   It asks for the token the first time only. It copies the files to `/opt/mcs21-ci-runner`,
   enables the firewall unit, builds the image and starts both containers. It then checks
   isolation: GitHub must be reachable, and `172.17.0.1:8112`, the host's sshd and
   `127.0.0.1:3306` must not be.
3. **Settings → Actions → Runners** lists `mcs21-vps-1`, `-2` and `-3` as *Idle*. One token registers all three.

Running `install.sh` again updates the runner and keeps its registration.

## Operating it

```bash
cd /opt/mcs21-ci-runner
docker compose ps                      # six containers Up
docker compose logs --tail 50 runner1  # "Listening for Jobs", job start and finish
docker compose restart                 # after a dind restart, also: docker compose up -d --force-recreate runner1 runner2 runner3
docker compose stop runner3 dind3      # fewer parallel jobs, for example during a load test
docker compose down                    # stop CI; jobs queue on GitHub until it is back
```

- Three runners take three jobs at once; a run's other two jobs start as soon as one finishes.
  During a load test or the live demo, `docker compose stop` one or two pairs to give
  production the whole machine.
- To fall back to GitHub-hosted machines, change `runs-on: [self-hosted, mcs21-ci]` back to
  `ubuntu-latest` in `ci.yml`. That only helps while GitHub minutes remain.
- The dind volume keeps pulled images (MySQL, the tamper lab). Clear it when the disk fills:
  `docker compose exec dind1 docker system prune -af` (and `dind2`, `dind3`).
