#!/usr/bin/env bash
set -euo pipefail

echo "=== Backyard Swarm Detect ==="
echo "[OS] $(uname -a || true)"
if [ -f /etc/os-release ]; then . /etc/os-release; echo "[Distro] $PRETTY_NAME"; fi

echo
echo ">> GPU / Driver"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true
else
  echo "nvidia-smi not found. Install NVIDIA drivers."
fi

echo
echo ">> Docker"
if command -v docker >/dev/null 2>&1; then
  docker --version
  echo "- NVIDIA runtime present?"
  if docker info 2>/dev/null | grep -i -q nvidia; then
    echo "  OK: NVIDIA runtime detected in Docker info"
  else
    echo "  WARN: NVIDIA runtime not detected in 'docker info'"
  fi
else
  echo "Docker not installed."
fi

echo
echo ">> Tailscale"
if command -v tailscale >/dev/null 2>&1; then
  tailscale version || true
  echo "Tailnet IP(s):"; tailscale ip -4 || true
else
  echo "Tailscale not installed."
fi

echo
echo ">> Python"
python3 --version || echo "python3 not found"
pip3 --version || echo "pip3 not found"

echo
echo ">> CUDA visible devices env"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-<unset>}"
echo
echo "Detect complete."
