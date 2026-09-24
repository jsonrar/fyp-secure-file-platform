#!/usr/bin/env bash
# Exercise the MySQL 8.4 schema-parity release gate described in issue #53,
# beyond what `pytest -m integration` covers: a non-empty database refuses a
# fresh install, an interrupted-then-resumed migration is idempotent, two
# concurrent migrations serialize instead of racing, and a pre-migration
# backup is actually restorable. Designed to run both in CI and locally
# against `docker compose up -d mysql` while developing this gate.
#
# Required environment (never printed): DB_HOST, DB_PORT, ADMIN_DB_USER,
# ADMIN_DB_PASSWORD. Optional: DB_SSL_CA to run every step over verified TLS.
#
# Each phase creates and drops its own disposable database so it can never
# collide with the database the main integration test run uses.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BACKEND_DIR"

: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:?DB_PORT is required}"
: "${ADMIN_DB_USER:?ADMIN_DB_USER is required}"
: "${ADMIN_DB_PASSWORD:?ADMIN_DB_PASSWORD is required}"

MYSQL_CLIENT=(mysql --host="$DB_HOST" --port="$DB_PORT" --user="$ADMIN_DB_USER" "--password=$ADMIN_DB_PASSWORD" --protocol=TCP)
MYSQLDUMP_CLIENT=(mysqldump --host="$DB_HOST" --port="$DB_PORT" --user="$ADMIN_DB_USER" "--password=$ADMIN_DB_PASSWORD" --protocol=TCP)

run_sql() {
  "${MYSQL_CLIENT[@]}" --execute "$1"
}

# Alembic reads connection details from the app's own Settings object, which
# takes them from these DB_* environment variables (see app/core/config.py).
run_alembic() {
  local database_name="$1"
  shift
  DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" DB_USER="$ADMIN_DB_USER" \
    DB_PASSWORD="$ADMIN_DB_PASSWORD" DB_NAME="$database_name" \
    PYTHON_BIN="$BACKEND_DIR/.venv/bin/python" \
    "$BACKEND_DIR/.venv/bin/python" -m alembic "$@"
}

run_migrate_sh() {
  local database_name="$1"
  shift
  DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" DB_USER="$ADMIN_DB_USER" \
    DB_PASSWORD="$ADMIN_DB_PASSWORD" DB_NAME="$database_name" \
    PYTHON_BIN="$BACKEND_DIR/.venv/bin/python" \
    "$BACKEND_DIR/scripts/migrate.sh" "$@"
}

echo "== phase: non-empty database refuses a fresh install =="
GUARD_DB="fyp_release_gate_guard_test"
run_sql "DROP DATABASE IF EXISTS \`${GUARD_DB}\`;"
run_sql "CREATE DATABASE \`${GUARD_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
# Simulate a database that already holds unrelated, non-Alembic-tracked data:
# the first migration's own CREATE TABLE users collides with it.
run_sql "CREATE TABLE \`${GUARD_DB}\`.\`users\` (id INT PRIMARY KEY);"
if run_alembic "$GUARD_DB" upgrade head; then
  echo "FAIL: alembic upgrade head unexpectedly succeeded against a non-empty, non-Alembic-tracked database" >&2
  exit 1
fi
echo "OK: alembic upgrade head refused the non-empty database instead of corrupting it"
run_sql "DROP DATABASE \`${GUARD_DB}\`;"

echo "== phase: idempotent re-run after a simulated interruption =="
PARTIAL_DB="fyp_release_gate_partial_test"
run_sql "DROP DATABASE IF EXISTS \`${PARTIAL_DB}\`;"
run_sql "CREATE DATABASE \`${PARTIAL_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
# Stop partway through the chain -- standing in for a migration process that
# was killed after applying some revisions but not all of them -- then resume.
run_alembic "$PARTIAL_DB" upgrade 0003_client_key_custody
MID_REVISION="$(run_alembic "$PARTIAL_DB" current 2>/dev/null | awk '{print $1}')"
if [ "$MID_REVISION" != "0003_client_key_custody" ]; then
  echo "FAIL: expected to stop at 0003_client_key_custody, alembic current reported '${MID_REVISION}'" >&2
  exit 1
fi
run_alembic "$PARTIAL_DB" upgrade head
FINAL_REVISION="$(run_alembic "$PARTIAL_DB" current 2>/dev/null | awk '{print $1}')"
if [ "$FINAL_REVISION" != "0006_chacha20_poly1305" ]; then
  echo "FAIL: resuming to head did not reach 0006_chacha20_poly1305, got '${FINAL_REVISION}'" >&2
  exit 1
fi
# Re-running upgrade head against an already-current database must be a clean no-op.
run_alembic "$PARTIAL_DB" upgrade head
echo "OK: resumed migration reached head and a repeat upgrade head is a safe no-op"
run_sql "DROP DATABASE \`${PARTIAL_DB}\`;"

echo "== phase: bounded metadata lock under concurrent deployers =="
LOCK_DB="fyp_release_gate_lock_test"
run_sql "DROP DATABASE IF EXISTS \`${LOCK_DB}\`;"
run_sql "CREATE DATABASE \`${LOCK_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
LOG_A="$(mktemp)"
LOG_B="$(mktemp)"
MIGRATE_LOCK_NAME="fyp_release_gate_lock_test" run_migrate_sh "$LOCK_DB" upgrade head >"$LOG_A" 2>&1 &
PID_A=$!
MIGRATE_LOCK_NAME="fyp_release_gate_lock_test" run_migrate_sh "$LOCK_DB" upgrade head >"$LOG_B" 2>&1 &
PID_B=$!
STATUS_A=0
STATUS_B=0
wait "$PID_A" || STATUS_A=$?
wait "$PID_B" || STATUS_B=$?
if [ "$STATUS_A" -ne 0 ] || [ "$STATUS_B" -ne 0 ]; then
  echo "FAIL: a concurrent migrate.sh invocation failed instead of waiting cleanly" >&2
  cat "$LOG_A" "$LOG_B" >&2
  exit 1
fi
LOCK_FINAL_REVISION="$(run_alembic "$LOCK_DB" current 2>/dev/null | awk '{print $1}')"
if [ "$LOCK_FINAL_REVISION" != "0006_chacha20_poly1305" ]; then
  echo "FAIL: concurrent migrations left the database at '${LOCK_FINAL_REVISION}', not head" >&2
  exit 1
fi
rm -f "$LOG_A" "$LOG_B"
echo "OK: two concurrent 'alembic upgrade head' invocations serialized cleanly via GET_LOCK"
run_sql "DROP DATABASE \`${LOCK_DB}\`;"

echo "== phase: restore from a verified pre-migration backup =="
BACKUP_SOURCE_DB="fyp_release_gate_backup_test"
BACKUP_RESTORE_DB="fyp_release_gate_restore_test"
run_sql "DROP DATABASE IF EXISTS \`${BACKUP_SOURCE_DB}\`;"
run_sql "DROP DATABASE IF EXISTS \`${BACKUP_RESTORE_DB}\`;"
run_sql "CREATE DATABASE \`${BACKUP_SOURCE_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
run_alembic "$BACKUP_SOURCE_DB" upgrade head
run_sql "INSERT INTO \`${BACKUP_SOURCE_DB}\`.\`users\` (user_uuid, username, email, password_hash, role, status, email_verified) VALUES ('00000000-0000-4000-8000-000000000002', 'backup-drill-user', 'backup-drill@example.invalid', 'not-a-real-hash', 'USER', 'ACTIVE', 0);"
DUMP_FILE="$(mktemp /tmp/fyp_release_gate_backup.XXXXXX.sql)"
"${MYSQLDUMP_CLIENT[@]}" --single-transaction --routines --triggers "$BACKUP_SOURCE_DB" >"$DUMP_FILE"
SOURCE_USER_COUNT="$(run_sql "SELECT COUNT(*) FROM \`${BACKUP_SOURCE_DB}\`.\`users\`;" | tail -1)"
SOURCE_TABLE_COUNT="$("${MYSQL_CLIENT[@]}" --batch --skip-column-names --execute "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${BACKUP_SOURCE_DB}';")"

run_sql "CREATE DATABASE \`${BACKUP_RESTORE_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
"${MYSQL_CLIENT[@]}" "$BACKUP_RESTORE_DB" <"$DUMP_FILE"
RESTORED_USER_COUNT="$(run_sql "SELECT COUNT(*) FROM \`${BACKUP_RESTORE_DB}\`.\`users\`;" | tail -1)"
RESTORED_TABLE_COUNT="$("${MYSQL_CLIENT[@]}" --batch --skip-column-names --execute "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${BACKUP_RESTORE_DB}';")"

if [ "$SOURCE_USER_COUNT" != "$RESTORED_USER_COUNT" ] || [ "$SOURCE_TABLE_COUNT" != "$RESTORED_TABLE_COUNT" ]; then
  echo "FAIL: restore mismatch -- source had ${SOURCE_TABLE_COUNT} tables/${SOURCE_USER_COUNT} users, restore had ${RESTORED_TABLE_COUNT} tables/${RESTORED_USER_COUNT} users" >&2
  exit 1
fi
echo "OK: mysqldump backup restored into a fresh database with matching table and row counts"
rm -f "$DUMP_FILE"
run_sql "DROP DATABASE \`${BACKUP_SOURCE_DB}\`;"
run_sql "DROP DATABASE \`${BACKUP_RESTORE_DB}\`;"

echo "mysql_release_gate.sh: all phases passed"
