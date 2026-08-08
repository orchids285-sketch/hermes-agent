#!/command/with-contenv sh
# shellcheck shell=sh
# docker/railway-start.sh — the container's main program on Railway.
#
# Railway REPLACES a Dockerfile ENTRYPOINT with the service's start command,
# so `gateway run` alone would bypass s6-overlay's /init and skip the whole
# bootstrap (data-volume chown, config seeding, profile reconcile) — the
# gateway then dies with EACCES on /opt/data. The Railway start command is
# therefore `/init /opt/hermes/docker/railway-start.sh`, which keeps /init as
# PID 1 and runs this script as its main program.
#
# Hermes' model choice lives in config.yaml (never in the environment), and on
# Railway config.yaml sits on the persistent volume, so seed it here on every
# boot — both calls are idempotent. The provider reads OPENROUTER_API_KEY from
# the environment.
set -e

MODEL="${HERMES_DEFAULT_MODEL:-nvidia/nemotron-3-super-120b-a12b:free}"
PROVIDER="${HERMES_MODEL_PROVIDER:-openrouter}"

exec /opt/hermes/docker/main-wrapper.sh sh -c \
    "hermes config set model.provider '$PROVIDER' || true; \
     hermes config set model.default '$MODEL' || true; \
     exec hermes gateway run"
