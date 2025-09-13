#!/usr/bin/env bash
set -euo pipefail

COORD="${1:-}"
while getopts "c:" opt; do
  case $opt in
    c) COORD="$OPTARG" ;;
    *) ;;
  esac
done

if [ -z "${COORD}" ]; then
  echo "Usage: bash scripts/bs_worker_up.sh -c http://<COORD_TAILSCALE_IP>:8080"
  exit 1
fi

NODE_NAME="$(hostname)"
MODELS_DIR="${MODELS_DIR:-/mnt/models}"
DATA_DIR="${DATA_DIR:-/mnt/data}"

echo "=== Starting Backyard Swarm worker ==="
echo "Coordinator: ${COORD}"
echo "Node name:   ${NODE_NAME}"
echo "Models dir:  ${MODELS_DIR}"
echo "Data dir:    ${DATA_DIR}"

docker run --gpus all -d --restart unless-stopped --name backyard-worker   -e COORD_ADDR="${COORD}"   -e NODE_NAME="${NODE_NAME}"   -v "${MODELS_DIR}:/models" -v "${DATA_DIR}:/data"   ghcr.io/tangnet/backyard-worker:0.1

echo "Worker launched. Check 'docker logs -f backyard-worker' for status."
