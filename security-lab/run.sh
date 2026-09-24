#!/usr/bin/env bash
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$LAB_DIR/compose.yml"
ENV_FILE="$(mktemp "${TMPDIR:-/tmp}/secureview-tamper-lab.XXXXXX")"
REPORT_DIR="${REPORT_DIR:-$LAB_DIR/reports}"

cleanup() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down --volumes --remove-orphans >/dev/null
  rm -f "$ENV_FILE"
}
trap cleanup EXIT

umask 077
cat >"$ENV_FILE" <<EOF
LAB_MYSQL_ROOT_PASSWORD=$(openssl rand -hex 32)
LAB_SECRET_KEY=$(openssl rand -hex 48)
EOF

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

compose build target attacker
compose up -d --wait mysql
# Named volumes start root-owned. A one-shot initializer grants only the unprivileged lab uid
# access; every target and attacker phase below still runs as uid 10001 with all caps dropped.
compose run --rm --user 0:0 --cap-add CHOWN target sh -c \
  'mkdir -p /lab/storage /lab/evidence /lab/private && chown -R 10001:10001 /lab/storage /lab/evidence /lab/private'
compose run --rm target python -m alembic upgrade head
compose run --rm target python scripts/tamper_drill_target.py seed

compose run --rm target python scripts/tamper_drill_target.py inspect \
  --expect-result VALID --expect-file-status ACTIVE --download allowed

compose run --rm attacker python scripts/tamper_drill_attacker.py flip
compose run --rm target python scripts/tamper_drill_target.py inspect \
  --expect-result MODIFIED --expect-file-status CORRUPTED --download refused

compose run --rm target python scripts/tamper_drill_target.py restore-baseline
compose run --rm target python scripts/tamper_drill_target.py inspect \
  --expect-result VALID --expect-file-status ACTIVE --download allowed

compose run --rm attacker python scripts/tamper_drill_attacker.py hide
compose run --rm target python scripts/tamper_drill_target.py inspect \
  --expect-result MISSING --expect-file-status ACTIVE --download skip
compose run --rm attacker python scripts/tamper_drill_attacker.py restore
compose run --rm target python scripts/tamper_drill_target.py inspect \
  --expect-result VALID --expect-file-status ACTIVE --download allowed

compose run --rm attacker python scripts/tamper_drill_attacker.py forge
compose run --rm target python scripts/tamper_drill_target.py inspect \
  --expect-result VALID --expect-file-status ACTIVE --download allowed
compose run --rm target python scripts/tamper_drill_target.py prove-client-auth

compose run --rm target python scripts/tamper_drill_target.py restore-baseline
compose run --rm target python scripts/tamper_drill_target.py inspect \
  --expect-result VALID --expect-file-status ACTIVE --download allowed
compose run --rm target python scripts/tamper_drill_target.py finish

mkdir -p "$REPORT_DIR"
REPORT_PATH="$REPORT_DIR/tamper-drill-$(date -u +%Y%m%dT%H%M%SZ).json"
compose run --rm target sh -c 'cat /lab/evidence/report.json' >"$REPORT_PATH"
python3 -m json.tool "$REPORT_PATH" >/dev/null
printf 'Tamper drill passed. Sanitized report: %s\n' "$REPORT_PATH"
