# 🐝 Backyard Swarm — Getting Started

Complete guide to deploying your distributed GPU mesh in under 30 minutes.

## Prerequisites

- **Hardware**: 2+ machines with NVIDIA GPUs (RTX 3070, 4060, 5090, etc.)
- **OS**: Ubuntu 20.04+ or Windows with WSL2
- **Network**: All machines on same network or VPN (Tailscale recommended)
- **Software**: Docker with NVIDIA runtime

## 🚀 Quick Start (3 Steps)

### Step 1: Build the Docker Images

```bash
cd backyard_swarm_scripts
bash docker/build.sh
```

This creates:
- `ghcr.io/tangnet/backyard-coordinator:0.1` (Ray head + API)
- `ghcr.io/tangnet/backyard-worker:0.1` (Ray worker + GPU detection)

### Step 2: Start the Coordinator

On your **coordinator machine** (Pi, server, or any always-on box):

```bash
# Make sure you're in the backyard_swarm_scripts directory
bash scripts/bs_coordinator_up.sh
```

The coordinator will start:
- **API**: `http://<coordinator-ip>:8080`
- **Ray Dashboard**: `http://<coordinator-ip>:8265`
- **MinIO Console**: `http://<coordinator-ip>:9001` (admin: minio/minio123)

### Step 3: Join GPU Workers

On each **GPU machine**, run:

```bash
# Replace <COORDINATOR_IP> with your coordinator's IP address
bash scripts/bs_worker_up.sh -c http://<COORDINATOR_IP>:8080
```

## 🧪 Test Your Swarm

### Basic Health Check

```bash
bash scripts/bs_status.sh http://<COORDINATOR_IP>:8080
```

### Run Embeddings Job

```bash
bash scripts/bs_smoketest.sh
```

This will:
1. Create test data
2. Run embeddings across your GPU mesh
3. Verify results are written to `/data/corpus.embeddings.json`

### Check Distributed Execution

Visit the Ray dashboard at `http://<coordinator-ip>:8265` to see:
- Active worker nodes
- GPU utilization
- Task distribution
- Real-time metrics

## 🔧 Advanced Configuration

### Environment Variables

Worker configuration (`configs/example.env`):

```bash
# GPU worker settings
MODELS_DIR=/mnt/models                    # Where to mount model weights
DATA_DIR=/mnt/data                        # Where to mount datasets
COORD_ADDR=http://coordinator:8080        # Coordinator address
NODE_NAME=gpu-workstation                 # Custom node name

# Performance tuning
TORCH_CUDA_ARCH_LIST="8.6;8.9"          # GPU architectures
PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128"
```

### Custom Model Storage

Mount your model directory when starting workers:

```bash
# Example: Mount local models directory
docker run --gpus all -d --restart unless-stopped --name backyard-worker \
  -e COORD_ADDR=http://<COORDINATOR_IP>:8080 \
  -e NODE_NAME=$(hostname) \
  -v /home/user/models:/models \
  -v /home/user/data:/data \
  ghcr.io/tangnet/backyard-worker:0.1
```

### Tailscale Mesh (Recommended)

For secure networking across different locations:

```bash
# Install on all machines
sudo bash scripts/bs_install_linux.sh

# Join Tailscale network (once per machine)
sudo tailscale up

# Use Tailscale IPs for coordination
tailscale ip -4  # Get your Tailscale IP
```

## 📊 Monitoring

### Health Endpoints

- **Coordinator health**: `http://<coordinator>:8080/healthz`
- **Worker list**: `http://<coordinator>:8080/workers`
- **Cluster status**: `http://<coordinator>:8080/cluster/status`

### Ray Dashboard

The Ray dashboard (`http://<coordinator>:8265`) shows:
- Node topology and resources
- Active jobs and task progress
- GPU memory usage
- Network traffic between nodes

### Logs

```bash
# Coordinator logs
docker logs -f backyard-coordinator

# Worker logs (on each GPU machine)
docker logs -f backyard-worker
```

## 🎯 Example Workloads

### 1. Text Embeddings

```bash
python jobs/embeddings.py \
  --input /data/documents.txt \
  --shards 32 \
  --out /data/embeddings.json
```

### 2. Image Generation

```bash
python jobs/sd_batch.py \
  --prompts /data/prompts.txt \
  --out /data/generated_images
```

### 3. Custom Ray Job

```python
import ray
ray.init(address="auto")  # Connects to your swarm

@ray.remote(num_gpus=0.5)
def my_gpu_task(data):
    # Your CUDA/PyTorch code here
    return result

# Distributes across your mesh
futures = [my_gpu_task.remote(batch) for batch in data_batches]
results = ray.get(futures)
```

## 🛠️ Troubleshooting

### Worker Can't Connect

```bash
# Check network connectivity
ping <coordinator-ip>
curl http://<coordinator-ip>:8080/healthz

# Check Docker logs
docker logs backyard-worker
```

### GPU Not Detected

```bash
# Verify NVIDIA runtime
bash scripts/bs_detect.sh

# Check Docker GPU access
docker run --gpus all nvidia/cuda:12.1-runtime-ubuntu20.04 nvidia-smi
```

### Out of Memory Errors

Adjust GPU memory allocation in worker environment:

```bash
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:64,garbage_collection_threshold:0.8"
```

### Jobs Not Distributing

1. Verify all workers are registered: `curl http://<coordinator>:8080/workers`
2. Check Ray cluster status: `http://<coordinator>:8265`
3. Ensure Ray jobs use `ray.init(address="auto")`

## 🚀 Next Steps

1. **Scale Up**: Add more GPU workers with different hardware
2. **Model Storage**: Set up shared model storage with MinIO
3. **Custom Jobs**: Create your own distributed AI workloads
4. **Production**: Add monitoring, logging, and automatic restarts

## 💡 Cool Rick Pro Tips

- **Start small**: Get 2 machines working before adding more
- **Use Tailscale**: Eliminates network configuration headaches
- **Monitor resources**: Watch the Ray dashboard during jobs
- **Containerize everything**: Your jobs should run in Docker too
- **Test locally first**: Verify your job works on one machine

*"Steady tempo. Clean wiring. We ship working systems."* — Cool Rick

---

**Need help?** Check the logs, visit the Ray dashboard, or run `bash scripts/bs_status.sh` for diagnostics.