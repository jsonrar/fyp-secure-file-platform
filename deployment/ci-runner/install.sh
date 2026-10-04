#!/usr/bin/env bash
# Install or update the self-hosted CI runner on the VPS. Run as root from this directory:
#
#   bash install.sh            # asks for the registration token the first time
#
# The token comes from the repository's Settings -> Actions -> Runners -> New self-hosted
# runner (admin only), or `gh api -X POST repos/jsonrar/fyp-secure-file-platform/actions/runners/registration-token --jq .token`.
# It is valid for an hour and is only needed once: the registration is kept in a volume.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run as root." >&2; exit 1; }
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST=/opt/mcs21-ci-runner

install -d -m 0750 "$DEST"
install -m 0644 "$SRC/Dockerfile" "$SRC/compose.yml" "$DEST/"
install -m 0755 "$SRC/entrypoint.sh" "$DEST/"
install -m 0644 "$SRC/mcs21-ci-runner-firewall.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now mcs21-ci-runner-firewall.service

cd "$DEST"
PAIRS="1 2 3"
docker compose build --pull runner1
# dind first: it creates the volumes and owns the network namespace its runner joins.
docker compose up -d dind1 dind2 dind3

registered=yes
for i in $PAIRS; do
  # Volumes start root-owned; the runner works as uid 1001.
  docker compose run --rm --user 0:0 --entrypoint chown "runner$i" -R 1001:1001 /home/runner/state /home/runner/_work
  r="$(docker compose run --rm --user 0:0 --entrypoint sh "runner$i" -c 'test -f /home/runner/state/.runner && echo yes || echo no' | tr -d '\r')"
  [ "$r" = yes ] || registered=no
done
if [ "$registered" = no ] && [ -z "${RUNNER_TOKEN:-}" ]; then
  # One token registers all three; it is valid for an hour.
  read -r -s -p "Registration token: " RUNNER_TOKEN; echo
fi
RUNNER_TOKEN="${RUNNER_TOKEN:-}" docker compose up -d --force-recreate runner1 runner2 runner3

echo "== isolation checks (runner1; the pairs are identical)"
if docker compose exec -T runner1 curl -fsS -o /dev/null --max-time 10 https://api.github.com; then
  echo "ok: the runner reaches GitHub"
else
  echo "FAIL: the runner cannot reach GitHub" >&2
fi
for target in 172.17.0.1:8112 172.31.250.1:8288 127.0.0.1:3306; do
  if docker compose exec -T runner1 bash -c "timeout 5 bash -c '</dev/tcp/${target%:*}/${target#*:}'" 2>/dev/null; then
    echo "FAIL: the runner can open ${target}" >&2
  else
    echo "ok: ${target} is unreachable from the runner"
  fi
done

sleep 10
docker compose ps
docker compose logs --tail 5 runner1 runner2 runner3
echo
echo "Check: GitHub -> Settings -> Actions -> Runners should list mcs21-vps-1, -2 and -3 as Idle."
