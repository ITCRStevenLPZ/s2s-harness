# syntax=docker/dockerfile:1
#
# Multi-stage build for the s2s-harness bridge (docs/BRIDGE_SPEC.md, docs/DEPLOY_SPEC.md).
#
# Status as of this build: src/s2s_harness/cli/ and src/s2s_harness/bridge/ do not exist
# yet (BUILD_PLAN.md Phases 5 and 7). This Dockerfile builds against the documented
# entry point (pyproject.toml [project.scripts] s2s = "s2s_harness.cli.main:app") so the
# dependency-install and layer structure are correct today; `docker run` of the resulting
# image will fail with a ModuleNotFoundError until those modules land, because there is
# nothing to import yet. `docker build` succeeding is what this stage of the project proves.
#
# uv-based (this project uses uv, not pip/poetry). Python 3.12, matching
# pyproject.toml's `requires-python = ">=3.12"`.

# ---- builder ---------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.9.0-python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies before copying source so dependency layers cache
# independently of application code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --extra stt-gemini --extra polish

# Now add the project itself and install it into the same venv.
COPY src ./src
COPY README.md ./
RUN uv sync --frozen --no-dev --extra stt-gemini --extra polish

# ---- final ------------------------------------------------------------------
# python:3.12-slim rather than a distroless base: distroless/python3-debian12 does not
# publish a Python-3.12-pinned tag we could verify against the venv's
# lib/python3.12/site-packages layout, and guessing that alignment risks a broken image
# that "docker build"s fine and fails at import time for the wrong reason. slim keeps a
# shell available, so the hardening below is enforced at the process level instead:
# non-root user, no install of extra packages, and an exec-form entrypoint that never
# invokes /bin/sh at container start.
FROM python:3.12-slim AS final

RUN groupadd --gid 10001 s2s && \
    useradd --uid 10001 --gid s2s --no-create-home --shell /usr/sbin/nologin s2s

WORKDIR /app

COPY --from=builder --chown=s2s:s2s /app/.venv /app/.venv
COPY --from=builder --chown=s2s:s2s /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Cloud Run injects PORT; default matches BRIDGE_SPEC's local port for parity when the
# image is run without Cloud Run's environment.
ENV PORT=8787

USER s2s

# Cloud Run requires listening on 0.0.0.0:$PORT. Binding 0.0.0.0 here is legal only
# because docs/DEPLOY_SPEC.md DEPLOY-6 supersedes the loopback-only clause in
# docs/BRIDGE_SPEC.md for the hosted-deployment case. Local `s2s serve` (run outside
# this image, directly on the operator's machine) still binds 127.0.0.1 per that spec's
# unmodified default. Do not read this line as a violation of the local-mode rule.
EXPOSE 8787

# No shell invoked at container start: exec form runs uvicorn directly.
# bridge.app:app does not exist yet -- see the header comment. This is the documented
# target per docs/BRIDGE_SPEC.md and pyproject.toml's entry point family.
ENTRYPOINT ["uvicorn", "s2s_harness.bridge.app:app", "--host", "0.0.0.0"]
CMD ["--port", "8787"]
