#!/usr/bin/env bash
set -euo pipefail

COORD="${1:-http://localhost:8080}"
echo "=== Status ==="
echo "Coordinator healthz:"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "${COORD}/healthz" || echo "healthz not reachable"
else
  echo "curl not installed"
fi

echo
echo "Docker containers:"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | sed 's/^/  /'
