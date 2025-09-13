#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo bash $0"
  exit 1
fi

echo "=== Install: Docker, NVIDIA Container Toolkit, Tailscale (Ubuntu/WSL2) ==="
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release

# Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "- Installing Docker CE"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker || true
else
  echo "- Docker already installed"
fi

# NVIDIA Container Toolkit
if ! dpkg -l | grep -q nvidia-container-toolkit; then
  echo "- Installing NVIDIA Container Toolkit"
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -fsSL https://nvidia.github.io/libnvidia-container/$(. /etc/os-release; echo $ID)/$(. /etc/os-release; echo $VERSION_ID)/libnvidia-container.list |     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' |     tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update -y
  apt-get install -y nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker
  systemctl restart docker || true
else
  echo "- NVIDIA Container Toolkit already installed"
fi

# Tailscale
if ! command -v tailscale >/dev/null 2>&1; then
  echo "- Installing Tailscale"
  curl -fsSL https://tailscale.com/install.sh | bash
  systemctl enable --now tailscaled || true
else
  echo "- Tailscale already installed"
fi

echo "=== Install complete ==="
echo "Next: 'tailscale up' (once) to join your Tailnet."
