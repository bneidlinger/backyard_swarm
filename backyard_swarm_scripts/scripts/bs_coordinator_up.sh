#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not installed."
  exit 1
fi

echo "=== Bringing up Backyard Swarm coordinator ==="
if [ ! -f ops/compose-coordinator.yml ]; then
  echo "ERROR: ops/compose-coordinator.yml not found"; exit 1
fi

docker compose -f ops/compose-coordinator.yml up -d
echo "Coordinator up. Check:"
echo "  - API:       http://<this-host>:8080/"
echo "  - Dashboard: http://<this-host>:8265/  (if enabled)"
echo "MinIO console: http://<this-host>:9001/ (user: minio / pass: minio123)"
