#!/usr/bin/env bash
# run_cron.sh — the cosmic pipeline

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCK_FILE="${PROJECT_DIR}/.cron.lock"
ENV_FILE="${PROJECT_DIR}/.env"
VENV_ACTIVATE="${PROJECT_DIR}/.venv/bin/activate"
LOG_DIR="${PROJECT_DIR}/logs"
RUN_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_TS_SAFE="${RUN_TS//:/-}"
LOG_FILE="${LOG_DIR}/run_${RUN_TS_SAFE}.log"

mkdir -p "${LOG_DIR}"

exec 200>"${LOCK_FILE}"
if ! flock -n 200; then
  echo "Another run_cron.sh is already active. Exiting."
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

if [[ ! -f "${VENV_ACTIVATE}" ]]; then
  echo "Missing virtualenv at ${VENV_ACTIVATE}. Create it with: python3 -m venv .venv"
  exit 1
fi

# shellcheck disable=SC1090
source "${VENV_ACTIVATE}"

# Ensure claude CLI is available (installed in ~/.local/bin)
export PATH="${HOME}/.local/bin:${PATH}"

cd "${PROJECT_DIR}"

echo "=== horoscopo pipeline start (${RUN_TS}) ===" | tee -a "${LOG_FILE}"

python run_cron.py 2>&1 | tee -a "${LOG_FILE}"
EXIT_CODE=${PIPESTATUS[0]}

if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "=== horoscopo pipeline complete (${RUN_TS}) ===" | tee -a "${LOG_FILE}"
else
    echo "=== horoscopo pipeline FAILED (exit=${EXIT_CODE}) ===" | tee -a "${LOG_FILE}"
fi

exit "${EXIT_CODE}"
