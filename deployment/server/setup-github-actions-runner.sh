#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/jsonrar/fyp-secure-file-platform"
RUNNER_USER="${RUNNER_USER:-github-runner}"
RUNNER_NAME="${RUNNER_NAME:-mcs21-ci}"
RUNNER_LABEL="${RUNNER_LABEL:-fyp-ci}"
RUNNER_DIR="${RUNNER_DIR:-/opt/github-actions-runner}"

if [[ ${EUID} -ne 0 ]]; then
  exec sudo -E bash "$0" "$@"
fi

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "This bootstrap currently targets x86_64/X64 only."
  exit 1
fi

if [[ -z "${RUNNER_TOKEN:-}" ]]; then
  read -rsp "Paste the GitHub runner registration token: " RUNNER_TOKEN
  echo
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl git gnupg jq python3 python3-pip sudo unzip \
  docker.io default-mysql-client

systemctl enable --now docker

# GitHub CLI is required by the promote job.
if ! command -v gh >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    -o /etc/apt/keyrings/githubcli-archive-keyring.gpg
  chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update
  apt-get install -y gh
fi

if ! id "${RUNNER_USER}" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "${RUNNER_USER}"
fi

usermod -aG docker "${RUNNER_USER}"

# The current workflow installs packages during CI (mysql-client and Playwright
# system dependencies). Docker membership is already root-equivalent, so on a
# dedicated CI host passwordless sudo does not materially widen the trust
# boundary and keeps the workflow compatible with GitHub-hosted behavior.
cat > "/etc/sudoers.d/${RUNNER_USER}-github-actions" <<EOF
${RUNNER_USER} ALL=(ALL) NOPASSWD: ALL
EOF
chmod 0440 "/etc/sudoers.d/${RUNNER_USER}-github-actions"

mkdir -p "${RUNNER_DIR}"
chown -R "${RUNNER_USER}:${RUNNER_USER}" "${RUNNER_DIR}"

release_json="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest)"
tag="$(jq -r '.tag_name' <<<"${release_json}")"
version="${tag#v}"
asset="actions-runner-linux-x64-${version}.tar.gz"
download_url="$(jq -r --arg asset "${asset}" '.assets[] | select(.name == $asset) | .browser_download_url' <<<"${release_json}")"
digest="$(jq -r --arg asset "${asset}" '.assets[] | select(.name == $asset) | (.digest // empty)' <<<"${release_json}")"

if [[ -z "${download_url}" || "${download_url}" == "null" ]]; then
  echo "Could not locate runner asset ${asset}"
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
curl -fL "${download_url}" -o "${tmp}/${asset}"

if [[ "${digest}" == sha256:* ]]; then
  expected="${digest#sha256:}"
  actual="$(sha256sum "${tmp}/${asset}" | awk '{print $1}')"
  if [[ "${expected}" != "${actual}" ]]; then
    echo "Runner archive checksum verification failed."
    exit 1
  fi
fi

if [[ ! -f "${RUNNER_DIR}/config.sh" ]]; then
  tar -xzf "${tmp}/${asset}" -C "${RUNNER_DIR}"
  chown -R "${RUNNER_USER}:${RUNNER_USER}" "${RUNNER_DIR}"
fi

# Install native dependencies required by the GitHub runner itself.
"${RUNNER_DIR}/bin/installdependencies.sh"

if [[ ! -f "${RUNNER_DIR}/.runner" ]]; then
  sudo -u "${RUNNER_USER}" -H bash -lc "
    cd '${RUNNER_DIR}'
    ./config.sh --unattended \
      --url '${REPO_URL}' \
      --token '${RUNNER_TOKEN}' \
      --name '${RUNNER_NAME}' \
      --labels '${RUNNER_LABEL}' \
      --work '_work' \
      --replace
  "
else
  echo "Runner is already configured locally; leaving registration unchanged."
fi

cd "${RUNNER_DIR}"
if [[ ! -f .service ]]; then
  ./svc.sh install "${RUNNER_USER}"
fi
./svc.sh start
./svc.sh status

echo
echo "Self-hosted runner setup finished."
echo "Expected labels: self-hosted, Linux, X64, ${RUNNER_LABEL}"
echo "Repository: ${REPO_URL}"
