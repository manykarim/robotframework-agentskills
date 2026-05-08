# Docker test harness for the rf-agentskills installer.
#
# Builds a clean container with:
#   * uv (Python package manager — used to install rf-agentskills)
#   * Node 20  (for npm-distributed coding agents)
#   * The four CLI coding agents we can validate headlessly:
#         Claude Code, Codex, OpenCode, Goose
#   * jq (JSON inspection in check scripts)
#
# At runtime the entrypoint runs the installer for each requested
# agent and then a per-agent check script that verifies the install
# took effect — without making any API call by default. See
# docs/installer/docker.md for invocation.

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:/usr/local/bin:${PATH}"

# ── 1. System tools ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates git build-essential jq \
    && rm -rf /var/lib/apt/lists/*

# ── 2. uv ──────────────────────────────────────────────────────────────────
# Astral's installer drops to ~/.local/bin. We move it to /usr/local/bin
# so the binary survives a `--tmpfs /root` mount at runtime (used for
# inter-test state isolation).
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx \
    && uv --version

# ── 3. Node 20 ─────────────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version && npm --version

# ── 4. Coding agents (npm-distributed) ─────────────────────────────────────
# Versions intentionally floating — the harness is for *your* environment;
# pinning here would defeat the "what does today's release do" signal.
RUN npm install -g \
        @anthropic-ai/claude-code \
        @openai/codex \
        opencode-ai \
    && claude --version \
    && codex --version \
    && opencode --version

# ── 5. Goose (binary release) ──────────────────────────────────────────────
# The release script tries an interactive `goose configure` step at the
# end; CONFIGURE=false skips it. We then move the binary to /usr/local/bin
# so it's on PATH for non-root users (we run as root in the container,
# but this keeps the layout sensible if someone bind-mounts).
RUN curl -fsSL https://github.com/block/goose/releases/latest/download/download_cli.sh \
        | CONFIGURE=false bash \
    && mv /root/.local/bin/goose /usr/local/bin/goose \
    && goose --version

# ── 6. rf-agentskills installer (built from the mounted source) ────────────
# The actual rf-agentskills install happens at container *run* time using
# the source mounted at /work — that way iterating on the installer
# doesn't require rebuilding the image. We pre-install the runtime deps
# here so `uv pip install` at runtime is a near-instant no-op.
WORKDIR /work
RUN mkdir -p /work/installer
COPY installer/pyproject.toml /work/installer/pyproject.toml
RUN cd /work/installer \
    && uv pip install --system --no-deps "hatchling>=1.21" "tomli-w>=1.0" "pyyaml>=6.0" "rich>=13.7"

# ── 7. Harness scripts ─────────────────────────────────────────────────────
COPY docs/installer/docker/entrypoint.sh /usr/local/bin/rf-harness-entry
COPY docs/installer/docker/checks/ /usr/local/lib/rf-harness-checks/
RUN chmod +x /usr/local/bin/rf-harness-entry \
    && chmod +x /usr/local/lib/rf-harness-checks/*.sh

# Where the test will write its diagnostics for the host to read back.
ENV RF_HARNESS_LOG=/tmp/rf-harness.log

ENTRYPOINT ["/usr/local/bin/rf-harness-entry"]
CMD []
