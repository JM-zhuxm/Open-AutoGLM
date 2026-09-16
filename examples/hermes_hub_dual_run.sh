#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Hermes HUB x Open-AutoGLM: dual-run script.
#
# Starts both processes side-by-side on the same A58:
#   - Open-AutoGLM (screen UI automation via ADB)
#   - Hermes voice_bridge (CoreS3SE face + servo + track via USB CDC)
#
# They share the same Hermes LLM backend but act on independent channels.

set -euo pipefail

# ---- A58 ADB (Open-AutoGLM will use this) ----
export A58_IP="${A58_IP:-100.110.37.65}"
export A58_ADB_PORT="${A58_ADB_PORT:-35229}"
echo "[dual_run] A58 adb: ${A58_IP}:${A58_ADB_PORT}"

adb connect "${A58_IP}:${A58_ADB_PORT}" >/dev/null 2>&1 || true

# ---- Start Hermes voice_bridge if not already running ----
HERMES_PORT="${HERMES_PORT:-8766}"
if ! curl -sf "http://127.0.0.1:${HERMES_PORT}/health" -o /dev/null --max-time 2; then
  echo "[dual_run] voice_bridge not up; start it separately (see phonebot-r1/hermes-integration/)"
else
  echo "[dual_run] voice_bridge ok on :${HERMES_PORT}"
fi

# ---- Start Open-AutoGLM ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/.."

if [[ ! -d ".venv" ]]; then
  echo "[dual_run] creating .venv ..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

python main.py --device-ip "${A58_IP}" --device-port "${A58_ADB_PORT}" "$@"