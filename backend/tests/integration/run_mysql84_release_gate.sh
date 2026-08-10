#!/usr/bin/env bash
set -Eeuo pipefail

task_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
task_repo_root="$(cd "$task_script_dir/../../.." && pwd)"
task_run_id="$(date -u +%Y%m%d%H%M%S)-$$"
task_network="mcs21-mysql84-gate-$task_run_id"
task_mysql_container="mcs21-mysql84-$task_run_id"
task_test_image="mcs21/mysql84-release-gate:$task_run_id"
task_temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/mcs21-mysql84-gate.XXXXXX")"
task_tls_dir="$task_temp_dir/tls"
task_ca_key_file="$task_temp_dir/ca-key.pem"
task_env_file="$task_temp_dir/gate.env"
task_root_password_file="$task_temp_dir/mysql-root-password"

printf '%s\n' "MySQL 8.4 release gate started at $(date -u +%Y-%m-%dT%H:%M:%SZ)."

cleanup() {
  docker rm --force "$task_mysql_container" >/dev/null 2>&1 || true
  docker network rm "$task_network" >/dev/null 2>&1 || true
  docker image rm --force "$task_test_image" >/dev/null 2>&1 || true
  rm -rf "$task_temp_dir"
}
trap cleanup EXIT

command -v docker >/dev/null 2>&1 || {
  printf '%s\n' "Docker is required for the MySQL 8.4 release gate." >&2
  exit 2
}
command -v openssl >/dev/null 2>&1 || {
  printf '%s\n' "OpenSSL is required for the MySQL 8.4 release gate." >&2
  exit 2
}

mkdir -p "$task_tls_dir"
umask 077
task_root_password="$(openssl rand -hex 24)"
task_runtime_password="$(openssl rand -hex 24)"
task_migration_password="$(openssl rand -hex 24)"
task_upgrade_runtime_password="$(openssl rand -hex 24)"
task_upgrade_migration_password="$(openssl rand -hex 24)"
task_secret_key="$(openssl rand -hex 32)"
printf '%s' "$task_root_password" >"$task_root_password_file"

openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 1 \
  -subj "/CN=MCS21 MySQL 8.4 Test CA" \
  -keyout "$task_ca_key_file" \
  -out "$task_tls_dir/ca.pem" >/dev/null 2>&1
openssl req -newkey rsa:2048 -sha256 -nodes \
  -subj "/CN=mysql84-gate" \
  -keyout "$task_tls_dir/server-key.pem" \
  -out "$task_tls_dir/server.csr" >/dev/null 2>&1
openssl x509 -req -sha256 -days 1 \
  -in "$task_tls_dir/server.csr" \
  -CA "$task_tls_dir/ca.pem" \
  -CAkey "$task_ca_key_file" \
  -CAcreateserial \
  -extfile "$task_script_dir/mysql84-server-ext.cnf" \
  -extensions server_ext \
  -out "$task_tls_dir/server-cert.pem" >/dev/null 2>&1
chmod 0644 "$task_tls_dir/ca.pem" "$task_tls_dir/server-cert.pem" \
  "$task_tls_dir/server-key.pem"

printf '%s\n' \
  "MYSQL84_RELEASE_GATE=1" \
  "MYSQL84_RELEASE_GATE_CONFIRM=disposable-mysql-8.4-only" \
  "APP_ENV=ci" \
  "APP_DEBUG=false" \
  "SECRET_KEY=$task_secret_key" \
  "CORS_ORIGINS=[\"https://mysql84-gate.example.test\"]" \
  "DB_HOST=mysql84-gate" \
  "DB_PORT=3306" \
  "DB_NAME=fyp_auth_test_gate" \
  "DB_USER=mcs21_gate_runtime" \
  "DB_PASSWORD=$task_runtime_password" \
  "DB_SSL_CA=/run/mysql84-gate/ca.pem" \
  "MIGRATION_DB_USER=mcs21_gate_migrator" \
  "MIGRATION_DB_PASSWORD=$task_migration_password" \
  "MYSQL_ADMIN_HOST=mysql84-gate" \
  "MYSQL_ADMIN_PORT=3306" \
  "MYSQL_ADMIN_USER=root" \
  "MYSQL_ADMIN_PASSWORD=$task_root_password" \
  "MYSQL_RUNTIME_USER_HOST=%" \
  "MYSQL_MIGRATION_USER_HOST=%" \
  "AUTH_TEST_DATABASE_URL=mysql+pymysql://mcs21_gate_migrator:$task_migration_password@mysql84-gate:3306/fyp_auth_test_gate?charset=utf8mb4" \
  "MYSQL84_UPGRADE_DB_NAME=fyp_release_test_upgrade" \
  "MYSQL84_UPGRADE_RUNTIME_USER=mcs21_gate_runtime_upgrade" \
  "MYSQL84_UPGRADE_RUNTIME_PASSWORD=$task_upgrade_runtime_password" \
  "MYSQL84_UPGRADE_MIGRATION_USER=mcs21_gate_migrator_upgrade" \
  "MYSQL84_UPGRADE_MIGRATION_PASSWORD=$task_upgrade_migration_password" \
  >"$task_env_file"
chmod 0600 "$task_env_file" "$task_root_password_file"

docker network create "$task_network" >/dev/null
docker run --detach \
  --name "$task_mysql_container" \
  --network "$task_network" \
  --network-alias mysql84-gate \
  --env MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql-root-password \
  --env MYSQL_ROOT_HOST=% \
  --mount "type=bind,src=$task_root_password_file,dst=/run/secrets/mysql-root-password,readonly" \
  --mount "type=bind,src=$task_tls_dir,dst=/etc/mysql/gate-tls,readonly" \
  --mount "type=bind,src=$task_script_dir/mysql84-gate.cnf,dst=/etc/mysql/conf.d/mysql84-gate.cnf,readonly" \
  mysql:8.4 >/dev/null

task_ready=0
for _ in $(seq 1 90); do
  if docker exec "$task_mysql_container" mysqladmin ping -h 127.0.0.1 --silent \
    >/dev/null 2>&1; then
    task_ready=1
    break
  fi
  sleep 1
done
if [[ "$task_ready" != "1" ]]; then
  docker logs "$task_mysql_container" >&2
  printf '%s\n' "MySQL 8.4 did not become ready within 90 seconds." >&2
  exit 2
fi

docker build \
  --file "$task_script_dir/Dockerfile.mysql84" \
  --tag "$task_test_image" \
  "$task_repo_root"

docker run --rm \
  "$task_test_image" \
  sh -c "python -m ruff check app tests migrations && python -m pytest -m 'not integration' -ra"

docker run --rm \
  --network "$task_network" \
  --env-file "$task_env_file" \
  --mount "type=bind,src=$task_tls_dir/ca.pem,dst=/run/mysql84-gate/ca.pem,readonly" \
  "$task_test_image" \
  python -m pytest -m integration -ra

printf '%s\n' "MySQL 8.4 release gate passed at $(date -u +%Y-%m-%dT%H:%M:%SZ)."
