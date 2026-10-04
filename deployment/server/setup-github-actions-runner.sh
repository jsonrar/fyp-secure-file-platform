#!/usr/bin/env bash
set -Eeuo pipefail

# Bootstrap the repository's self-hosted GitHub Actions runner inside Docker.
# This deliberately does NOT install or reconfigure packages on the MCS21 host:
# production MySQL already runs there via Docker and host-level apt/dpkg changes
# can interfere with the deployed stack.

REPO_URL="${REPO_URL:-https://github.com/jsonrar/fyp-secure-file-platform}"
RUNNER_NAME="${RUNNER_NAME:-mcs21-ci}"
RUNNER_LABELS="${RUNNER_LABELS:-fyp-ci}"
BASE_DIR="${BASE_DIR:-/opt/mcs21-github-runner}"
IMAGE_NAME="${IMAGE_NAME:-mcs21-github-runner:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-mcs21-github-runner}"
WORK_VOLUME="${WORK_VOLUME:-mcs21-github-runner-work}"

for command in docker curl python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required host command is missing: $command" >&2
    exit 1
  fi
done

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not available to the current user." >&2
  exit 1
fi

if [[ -z "${RUNNER_TOKEN:-}" ]]; then
  read -rsp "Paste the GitHub runner registration token: " RUNNER_TOKEN
  echo
fi

install -d -m 0755 "${BASE_DIR}"

cat > "${BASE_DIR}/Dockerfile" <<'DOCKERFILE'
FROM ubuntu:24.04

ARG RUNNER_VERSION

ENV DEBIAN_FRONTEND=noninteractive
ENV RUNNER_ALLOW_RUNASROOT=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    gh \
    jq \
    python3 \
    python3-pip \
    sudo \
    unzip \
    docker.io \
    tar \
    gzip \
    zstd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /actions-runner

RUN curl -fL \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
    -o runner.tar.gz \
    && tar xzf runner.tar.gz \
    && rm runner.tar.gz \
    && ./bin/installdependencies.sh

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
DOCKERFILE

cat > "${BASE_DIR}/entrypoint.sh" <<'ENTRYPOINT'
#!/usr/bin/env bash
set -Eeuo pipefail

cd /actions-runner

if [[ ! -f .runner ]]; then
    : "${REPO_URL:?REPO_URL is required}"
    : "${RUNNER_TOKEN:?RUNNER_TOKEN is required}"

    ./config.sh \
        --unattended \
        --url "${REPO_URL}" \
        --token "${RUNNER_TOKEN}" \
        --name "${RUNNER_NAME:-mcs21-ci}" \
        --labels "${RUNNER_LABELS:-fyp-ci}" \
        --work "_work" \
        --replace
fi

exec ./run.sh
ENTRYPOINT

chmod +x "${BASE_DIR}/entrypoint.sh"

RUNNER_VERSION="$(
  curl -fsSL https://api.github.com/repos/actions/runner/releases/latest |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))'
)"

echo "Building GitHub Actions runner version ${RUNNER_VERSION}..."
docker build \
  --build-arg RUNNER_VERSION="${RUNNER_VERSION}" \
  -t "${IMAGE_NAME}" \
  "${BASE_DIR}"

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  --network host \
  -e RUNNER_ALLOW_RUNASROOT=1 \
  -e REPO_URL="${REPO_URL}" \
  -e RUNNER_TOKEN="${RUNNER_TOKEN}" \
  -e RUNNER_NAME="${RUNNER_NAME}" \
  -e RUNNER_LABELS="${RUNNER_LABELS}" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "${WORK_VOLUME}:/actions-runner/_work" \
  "${IMAGE_NAME}" >/dev/null

unset RUNNER_TOKEN

echo
echo "Runner container started."
echo "Container: ${CONTAINER_NAME}"
echo "Expected labels: self-hosted, Linux, X64, ${RUNNER_LABELS}"
echo
docker ps --filter "name=^${CONTAINER_NAME}$"
echo
docker logs --tail=40 "${CONTAINER_NAME}"
