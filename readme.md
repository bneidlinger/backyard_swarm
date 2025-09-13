# Backyard Swarm 🐝 — Tangnet P2P GPU Mesh (v0.1)

> *Cool, calm, and a little dangerous.* Think **Cool Rick** (from *Patriot*), sipping burnt office coffee, quietly wiring the building to run on vibes — with a dash of **Rick Sanchez** muttering, “Yeah, decentralized, Morty — because WAN bandwidth doesn’t care about your monolithic attention layer.”

**Mission:** If datacenters are booked out till the heat death, we conscript the suburbs. **Backyard Swarm** lets you stitch together consumer GPUs (3070, 4060, your brother’s 5090 in Ann Arbor, and a Pi control node) into a small **P2P compute mesh** that runs *useful* AI workloads **today**, and evolves toward **federated LoRA** training + **MoE/speculative** inference.

---

![status](https://img.shields.io/badge/status-pre--alpha-ff7de9) ![cuda](https://img.shields.io/badge/GPU-NVIDIA%20CUDA-7df9ff) ![license](https://img.shields.io/badge/license-TBD-lightgrey)

- **Docs**: see `docs/backyard_swarm.html` (or GitHub Pages if enabled).
- **Scope**: practical, LAN/WAN-friendly workloads. No synchronous all‑reduce across the open internet. We like our hair.

---

## Why this exists

- **Problem:** Can’t build datacenters fast enough to keep up with AI compute demand.  
- **Anti-Pattern:** Treating the public internet like an NVLink cable. It’s not.  
- **Bet:** Change the workload and match it to the topology. Don’t fight physics.

**What splits cleanly right now**  
- Diffusion image/video batches  
- Dataset preprocessing & embeddings  
- Evaluation suites & hyperparameter sweeps

**What we reshape to split (near‑term)**  
- **Federated LoRA/QLoRA** — ship adapter deltas, not 10s of GB  
- **Mixture‑of‑Experts** (MoE) inference — experts across peers, route tokens  
- **Speculative decoding** — many “drafts”, one “verifier”, throughput win  
- (Plus ensembles/rerankers when that’s good enough for the job)

> *Cool Rick voice:* “Steady hands. Smaller pieces. Fewer fires.”

---

## Architecture (high level)

```
[ Clients ]  ->  [ Router / Coordinator ]  ->  [ Peers: GPU boxes ]
                    |         |                  ├─ RTX 5090 (verifier / big jobs)
                    |         └─ MinIO/S3        ├─ RTX 3070 (drafts / shards)
                    |                            └─ RTX 4060 (drafts / shards)
             (Tailscale/WireGuard for stable overlay IPs)
```

- **Coordinator (control plane):** peer registry, task DAGs, health, artifact indexing (S3/MinIO).  
- **Worker agent:** Dockerized tasks (PyTorch/CUDA), resource advert (VRAM/FLOPs), retries/checkpoints.  
- **Overlay:** Tailscale/WireGuard now; libp2p/QUIC later. Everything encrypted, task manifests signed.  
- **Scheduler:** heterogeneity‑aware packing, speculative backups for stragglers, lightweight reputation.

**Design stance:** *No* global synchronous all‑reduce over WAN. It’s not 2019… and even in 2019 it hurt.

---

## Quick Start (Tonight)

> Pre-reqs: Docker with NVIDIA runtime on GPU hosts; Python 3.10+ for jobs; **Tailscale** (or WireGuard) on all nodes so you get stable `100.x.y.z` IPs.

### 0) Coordinator (can be the Pi or any always‑on node)
Create `ops/compose-coordinator.yml`:
```yaml
services:
  coordinator:
    image: ghcr.io/tangnet/backyard-coordinator:0.1
    container_name: backyard-coordinator
    ports:
      - "8080:8080"   # REST
      - "8265:8265"   # Ray dashboard (if using Ray)
    environment:
      - STORAGE_URL=http://minio:9000
      - STORAGE_BUCKET=backyard
      - STORAGE_ACCESS=minio
      - STORAGE_SECRET=minio123
    networks: [swarm]
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports: ["9000:9000","9001:9001"]
    environment:
      - MINIO_ROOT_USER=minio
      - MINIO_ROOT_PASSWORD=minio123
    volumes:
      - ./minio:/data
    networks: [swarm]
networks:
  swarm: {}
```

Bring it up:
```bash
docker compose -f ops/compose-coordinator.yml up -d
```

### 1) Workers on each GPU box
```bash
docker run --gpus all -d --restart unless-stopped --name backyard-worker \
  -e COORD_ADDR=http://<COORD_TAILSCALE_IP>:8080 \
  -e NODE_NAME=$(hostname) \
  -v /mnt/models:/models -v /mnt/data:/data \
  ghcr.io/tangnet/backyard-worker:0.1
```

Optional perf env:
```bash
# 3070=8.6, 4060=8.9, 5090≈9.x (leave flexible)
export TORCH_CUDA_ARCH_LIST="8.6;8.9"
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128,garbage_collection_threshold:0.9"
```

### 2) Run a useful job (embeddings farm)
`jobs/embeddings.py`:
```python
import os, math, json, ray
from pathlib import Path
from typing import List
ray.init(address="auto")

MODEL_NAME = os.getenv("EMB_MODEL","sentence-transformers/all-MiniLM-L6-v2")

@ray.remote(num_gpus=0.2)
def embed_shard(lines: List[str]) -> List[List[float]]:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    return model.encode(lines, convert_to_numpy=True).tolist()

def chunk(lst, n):
    k = math.ceil(len(lst)/n)
    for i in range(0, len(lst), k):
        yield lst[i:i+k]

if __name__ == "__main__":
    import argparse; p=argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--shards", type=int, default=32)
    p.add_argument("--out", required=True)
    args=p.parse_args()

    lines = [l.strip() for l in Path(args.input).read_text(encoding="utf-8").splitlines() if l.strip()]
    shards = list(chunk(lines, args.shards))
    futures = [embed_shard.remote(s) for s in shards]
    results = ray.get(futures)
    vecs = [v for block in results for v in block]
    Path(args.out).write_text(json.dumps({"model": MODEL_NAME, "vectors": vecs}), encoding="utf-8")
    print(f"Embedded {len(lines)} lines → {args.out}")
```

Run it:
```bash
python jobs/embeddings.py --input /data/corpus.txt --shards 64 --out /data/corpus.embeddings.json
```

### 3) Throughput demo (diffusion batch)
`jobs/sd_batch.py`:
```python
import os, ray, torch, json
from pathlib import Path
ray.init(address="auto")

@ray.remote(num_gpus=1)
def render(prompt, outdir, seed):
    from diffusers import StableDiffusionPipeline
    model = os.getenv("SD_MODEL","stabilityai/sdxl-turbo")
    pipe = StableDiffusionPipeline.from_pretrained(model, torch_dtype=torch.float16, use_safetensors=True).to("cuda")
    g = torch.Generator(device="cuda").manual_seed(seed)
    img = pipe(prompt, guidance_scale=0.0, num_inference_steps=4, generator=g).images[0]
    p = Path(outdir) / (str(abs(hash(prompt)))[:10] + ".png")
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(p)
    return str(p)

if __name__ == "__main__":
    import argparse; a=argparse.ArgumentParser()
    a.add_argument("--prompts", required=True); a.add_argument("--out", required=True)
    args=a.parse_args()
    prompts = [l.strip() for l in Path(args.prompts).read_text(encoding="utf-8").splitlines() if l.strip()]
    futures = [render.remote(p, args.out, i*13+7) for i,p in enumerate(prompts)]
    print(json.dumps(ray.get(futures), indent=2))
```

Run it (pin the 5090 for the heavy lifting):
```bash
python jobs/sd_batch.py --prompts /data/prompts.txt --out /data/outs
```

---

## Roadmap

**Phase 0 (now):** Ray + Docker; embeddings + SD batches; basic credit counter  
**Phase 1:** Federated **LoRA/QLoRA** (adapter-only), FedAvg & resume, metrics dashboard  
**Phase 2:** **MoE** experts across peers + **speculative decoding** (8B drafts, bigger verifier)  
**Phase 3:** libp2p discovery, optimistic verification (spot checks, k‑redundancy), reputation; payouts optional later

**Stretch:** split learning for privacy; zk‑style proofs of learning (later); energy‑aware scheduling; edge video VA farm.

---

## Repo Layout (suggested)

```
backyard_swarm/
├─ ops/
│  └─ compose-coordinator.yml
├─ jobs/
│  ├─ embeddings.py
│  └─ sd_batch.py
├─ docs/
│  └─ backyard_swarm.html   # publish via GitHub Pages if desired
├─ scripts/
│  └─ install_nvidia_docker.sh (optional)
└─ README.md
```

---

## Security model (v0.1)

- Tailnet‑only access; no public internet ingress.  
- Containers with read‑only root; bind only `/data` and `/models`.  
- Signed task specs; image digests verified.  
- **Do not** run untrusted jobs from strangers in this phase. Future versions add audits/reputation.

> *Rick S. aside:* “Trust is good. Verifiable execution is better. We’ll get weird with zk later.”

---

## FAQ

**Q: Why not just shard attention across peers?**  
A: Because RTT and bandwidth scream. We change the game: LoRA (tiny deltas), MoE (activations), speculative decoding (accept/reject).

**Q: AMD/ROCm?**  
A: Not yet. NVIDIA first for momentum. ROCm support welcome via PRs.

**Q: Windows?**  
A: Works well via WSL2 + NVIDIA CUDA. Native Windows containers possible with some elbow grease.

**Q: Payments/tokens?**  
A: Not the point right now. Build utility first. Credits/ledger exist; external payouts later if you must.

---

## Contributing

- Open an issue with your hardware/OS, describe the job you want to run.  
- PRs that reduce network chatter or improve hetero‑GPU packing are cherished.  
- Style: keep it terse, testable, and WAN‑aware.

---

## License

TBD (leaning MIT). Don’t sue us if your nephew mines Stable Diffusion anime on your 5090 all weekend.

---

*Cool Rick sign‑off:* “Steady tempo. Clean wiring. We ship.”  
*Rick S. addendum:* “And if it breaks, good — better entropy for the next run.”
