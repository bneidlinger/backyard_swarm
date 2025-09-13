#Requires -RunAsAdministrator
Write-Host "=== Backyard Swarm Windows Prep (WSL2 + Docker Desktop + Tailscale) ==="

# Enable WSL and Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Install Ubuntu (latest) if not present
if (-not (wsl.exe -l -q | Select-String -Pattern "Ubuntu")) {
  Write-Host "- Installing Ubuntu via wsl --install (may require reboot)"
  wsl.exe --install -d Ubuntu
} else {
  Write-Host "- Ubuntu already present in WSL"
}

# Install Docker Desktop
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
  Write-Host "- Installing Docker Desktop via winget"
  winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
} else {
  Write-Host "- Docker (or Docker Desktop) already detected"
}

# Install Tailscale
if (-not (Get-Command "tailscale" -ErrorAction SilentlyContinue)) {
  Write-Host "- Installing Tailscale via winget"
  winget install -e --id Tailscale.Tailscale --accept-package-agreements --accept-source-agreements
} else {
  Write-Host "- Tailscale already installed"
}

Write-Host "=== Done ==="
Write-Host "Next steps:"
Write-Host "1) Launch Docker Desktop and enable WSL integration."
Write-Host "2) Run 'tailscale up' (from Windows or inside WSL) to join your Tailnet."
Write-Host "3) Open Ubuntu (WSL) and run 'sudo bash scripts/bs_install_linux.sh'."
