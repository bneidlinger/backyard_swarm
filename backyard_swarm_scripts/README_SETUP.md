# Backyard Swarm — Setup Pack (v0.1)

This pack helps you **script the initial setup** for each machine in your Tangnet swarm: 3070 desktop, 4060 laptop, Pi coordinator, and your brother’s 5090.
Targets **Ubuntu/WSL2** for GPU hosts and a **Raspberry Pi (64‑bit)** for the coordinator (though any node can coordinate).

> Philosophy: keep it simple. Use Tailscale for the overlay, Docker for runtime, containerized workers, and a minimal smoke test.

## What’s inside

```
backyard_swarm_scripts/
├─ ops/
│  └─ compose-coordinator.yml          # Coordinator + MinIO
├─ scripts/
│  ├─ bs_detect.sh                     # Detect GPU/driver/docker/tailscale status
│  ├─ bs_install_linux.sh              # Install Docker, NVIDIA Container Toolkit, Tailscale (Ubuntu/WSL2)
│  ├─ bs_install_wsl.ps1               # Windows prep (WSL2, Docker Desktop, Tailscale via winget)
│  ├─ bs_coordinator_up.sh             # Bring up coordinator+MinIO
│  ├─ bs_worker_up.sh                  # Start a worker container on this host
│  ├─ bs_smoketest.sh                  # Run embeddings + (optional) SD batch tests
│  └─ bs_status.sh                     # Health checks for coordinator/worker
├─ jobs/
│  ├─ embeddings.py                    # Embeddings farm (Ray-based)
│  └─ sd_batch.py                      # Diffusion batch (SDXL turbo by default)
└─ configs/
   └─ example.env                      # Example environment configuration
```

## Quick path

**On every GPU host (Ubuntu or WSL2 Ubuntu):**
```bash
cd backyard_swarm_scripts
sudo bash scripts/bs_install_linux.sh
sudo tailscale up  # login in browser (once)
bash scripts/bs_detect.sh
```

**On the coordinator node (Pi or any always-on box):**
```bash
cd backyard_swarm_scripts
bash scripts/bs_coordinator_up.sh
# Note the coordinator Tailnet IP; you’ll pass it to workers as COORD_ADDR
```

**On each GPU host:**
```bash
cd backyard_swarm_scripts
bash scripts/bs_worker_up.sh -c http://<COORD_TAILSCALE_IP>:8080
```

**Smoke test (run from ANY node with Python 3.10+):**
```bash
python3 jobs/embeddings.py --input /data/corpus.txt --shards 64 --out /data/corpus.embeddings.json
# optional SD batch (requires GPU and diffusers models):
python3 jobs/sd_batch.py --prompts /data/prompts.txt --out /data/outs
```

> If Docker Desktop on Windows is your jam: run `scripts/bs_install_wsl.ps1` in an **elevated** PowerShell to enable WSL + fetch Docker + Tailscale, then use the WSL Ubuntu terminal for the Linux scripts.

## Notes

- You must have **NVIDIA drivers** installed on GPU hosts (use vendor packages).  
- The `ghcr.io/tangnet/*:0.1` images are placeholders for now; replace with your repo once published.  
- The Tailscale login step (`tailscale up`) is interactive; do once per node.  
- `/data` and `/models` are example bind mounts; adjust to your local paths.
