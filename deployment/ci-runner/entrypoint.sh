#!/usr/bin/env bash
# Registers the runner once, keeps its registration in the `runner-state` volume so a restart
# does not need a new token, then runs jobs until stopped.
set -euo pipefail

STATE=/home/runner/state
cd /home/runner

for f in .runner .credentials .credentials_rsaparams; do
  [ -f "$STATE/$f" ] && cp "$STATE/$f" "./$f"
done

if [ ! -f .runner ]; then
  if [ -z "${RUNNER_TOKEN:-}" ]; then
    echo "Not registered yet and RUNNER_TOKEN is empty. Run install.sh with a registration token." >&2
    exit 1
  fi
  ./config.sh --unattended \
    --url "https://github.com/${RUNNER_REPO}" \
    --token "$RUNNER_TOKEN" \
    --name "${RUNNER_NAME:-mcs21-vps}" \
    --labels "${RUNNER_LABELS:-mcs21-ci}" \
    --work _work \
    --replace
  for f in .runner .credentials .credentials_rsaparams; do cp "./$f" "$STATE/$f"; done
fi

# Wait for the dind sidecar before taking a job.
for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
docker info >/dev/null

exec ./run.sh
