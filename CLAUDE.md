# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Backyard Swarm is a P2P GPU mesh project for distributed AI workloads. Currently in v0.1 pre-alpha phase - this is primarily a documentation/planning repository with no implementation code yet.

**Core Concept**: Stitch together consumer GPUs (RTX 3070, 4060, 5090, etc.) across different machines into a P2P compute mesh for distributed AI tasks like federated LoRA training, MoE inference, and speculative decoding.

## Repository Structure

```
backyard_swarm/
├─ docs/
│  └─ index.html           # Main project documentation (HTML)
├─ readme.md               # Primary project documentation
└─ CLAUDE.md              # This file
```

**Planned Structure** (per README):
```
├─ ops/
│  └─ compose-coordinator.yml  # Docker Compose for coordinator
├─ jobs/
│  ├─ embeddings.py           # Ray-based embedding jobs
│  └─ sd_batch.py             # Stable Diffusion batch processing
├─ scripts/
│  └─ install_nvidia_docker.sh
```

## Architecture

**High-level design** (from README):
- **Coordinator**: Central control plane for peer registry, task DAGs, health monitoring
- **Worker agents**: Dockerized PyTorch/CUDA tasks on GPU nodes
- **Overlay network**: Tailscale/WireGuard for stable IPs, later libp2p/QUIC
- **Storage**: MinIO/S3 for artifact management
- **Scheduler**: Heterogeneity-aware task packing with speculative backups

**Key Technologies**:
- Ray for distributed computing
- Docker with NVIDIA runtime
- Tailscale/WireGuard for networking
- MinIO for object storage
- PyTorch for ML workloads

## Development Commands

Since this is a pre-alpha project with no code yet, there are no build/test commands defined. Future implementation will likely use:

- Docker Compose for coordinator: `docker compose -f ops/compose-coordinator.yml up -d`
- Worker containers with GPU support: `docker run --gpus all ...`
- Python Ray jobs: `python jobs/embeddings.py --input ... --out ...`

## Target Workloads

**Current focus** (embarrassingly parallel):
- Diffusion image/video batches
- Dataset preprocessing & embeddings
- Evaluation suites & hyperparameter sweeps

**Future roadmap**:
- Federated LoRA/QLoRA training (adapter deltas)
- Mixture-of-Experts (MoE) inference across peers
- Speculative decoding (multiple drafts, single verifier)

## Security Model

- Tailnet-only access (no public internet)
- Containerized execution with read-only root
- Signed task specifications
- Image digest verification
- **Note**: Currently designed for trusted networks only

## Key Files to Reference

- `readme.md`: Complete project vision, architecture, and quick-start examples
- `docs/index.html`: Formatted documentation (GitHub Pages ready)

When implementing this project, follow the WAN-aware design principles outlined in the README - avoid synchronous all-reduce across the internet and focus on workloads that split cleanly across heterogeneous hardware.