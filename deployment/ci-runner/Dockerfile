# The CI runner image: the official GitHub Actions runner plus the few tools ci.yml expects
# a GitHub-hosted ubuntu-latest machine to have (docker compose, python3, gh, mysql-client).
# It never talks to the host's Docker: DOCKER_HOST points at the dind sidecar (compose.yml).
FROM ghcr.io/actions/actions-runner:2.338.0

ARG COMPOSE_VERSION=v2.40.3
ARG GH_VERSION=2.102.0

USER root
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends python3 python3-venv mysql-client ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL -o /usr/local/lib/docker/cli-plugins/docker-compose \
       "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
    && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose \
    && curl -fsSL -o /tmp/gh.tgz \
       "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" \
    && tar -xzf /tmp/gh.tgz -C /tmp \
    && install -m 0755 "/tmp/gh_${GH_VERSION}_linux_amd64/bin/gh" /usr/local/bin/gh \
    && rm -rf /tmp/gh.tgz "/tmp/gh_${GH_VERSION}_linux_amd64"

COPY --chmod=0755 entrypoint.sh /usr/local/bin/mcs21-runner-entrypoint
USER runner
ENTRYPOINT ["/usr/local/bin/mcs21-runner-entrypoint"]
