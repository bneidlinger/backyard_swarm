#!/usr/bin/env python3
"""
Backyard Swarm Worker Service

The GPU worker node that joins the P2P mesh:
- Connects to Ray cluster as worker
- Detects and advertises GPU capabilities
- Reports resource utilization to coordinator
- Executes distributed AI workloads

Rick Sanchez assessment: "Look Morty, it's just a compute node that actually knows
what hardware it's running on. Revolutionary stuff, really."
"""

import os
import sys
import time
import socket
import logging
import asyncio
import subprocess
from typing import Dict, List, Optional
from datetime import datetime

import ray
import psutil
import requests
from pydantic import BaseModel

# Configure logging with Cool Rick precision
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backyard-worker")

# Configuration from environment
COORD_ADDR = os.getenv("COORD_ADDR", "http://localhost:8080")
NODE_NAME = os.getenv("NODE_NAME", socket.gethostname())
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))  # seconds

class GPUInfo(BaseModel):
    """GPU capability information"""
    name: str
    memory_total: int  # MB
    memory_free: int   # MB
    utilization: int   # percentage
    temperature: int   # celsius

class WorkerService:
    def __init__(self):
        self.node_id = None
        self.coordinator_url = COORD_ADDR.rstrip('/')
        self.gpu_info = self._detect_gpu_capabilities()
        self.registered = False

    def _detect_gpu_capabilities(self) -> List[GPUInfo]:
        """
        Detect NVIDIA GPU capabilities using nvidia-ml-py or nvidia-smi

        Cool Rick approach: Try the proper API first, fallback to CLI scraping
        """
        gpus = []

        try:
            # Try nvidia-ml-py first (more reliable)
            import pynvml

            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)

                # Get device info
                name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temp = 0

                gpu = GPUInfo(
                    name=name,
                    memory_total=memory_info.total // (1024 * 1024),  # Convert to MB
                    memory_free=memory_info.free // (1024 * 1024),
                    utilization=utilization.gpu,
                    temperature=temp
                )
                gpus.append(gpu)

            logger.info(f"Detected {len(gpus)} GPUs via pynvml")

        except ImportError:
            logger.info("pynvml not available, falling back to nvidia-smi")
            gpus = self._detect_gpu_via_smi()
        except Exception as e:
            logger.warning(f"GPU detection via pynvml failed: {e}")
            gpus = self._detect_gpu_via_smi()

        return gpus

    def _detect_gpu_via_smi(self) -> List[GPUInfo]:
        """Fallback GPU detection using nvidia-smi command"""
        gpus = []

        try:
            # Query GPU info via nvidia-smi
            cmd = [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 5:
                        gpu = GPUInfo(
                            name=parts[0],
                            memory_total=int(parts[1]),
                            memory_free=int(parts[2]),
                            utilization=int(parts[3]) if parts[3] != '[Not Supported]' else 0,
                            temperature=int(parts[4]) if parts[4] != '[Not Supported]' else 0
                        )
                        gpus.append(gpu)

            logger.info(f"Detected {len(gpus)} GPUs via nvidia-smi")

        except subprocess.CalledProcessError as e:
            logger.error(f"nvidia-smi failed: {e}")
        except Exception as e:
            logger.error(f"GPU detection error: {e}")

        return gpus

    def _get_system_info(self) -> Dict:
        """Get system resource information"""
        memory = psutil.virtual_memory()

        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "hostname": socket.gethostname(),
            "platform": sys.platform
        }

    async def register_with_coordinator(self) -> bool:
        """Register this worker node with the coordinator"""
        try:
            # Prepare registration payload
            total_gpu_memory = sum(gpu.memory_total for gpu in self.gpu_info)

            registration_data = {
                "node_id": f"{NODE_NAME}-{int(time.time())}",  # Unique node ID
                "node_name": NODE_NAME,
                "gpu_count": len(self.gpu_info),
                "gpu_memory_total": total_gpu_memory,
                "last_heartbeat": datetime.utcnow().isoformat(),
                "status": "active"
            }

            # Send registration request
            response = requests.post(
                f"{self.coordinator_url}/workers/register",
                json=registration_data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                self.node_id = result["node_id"]
                self.registered = True
                logger.info(f"Successfully registered with coordinator as {self.node_id}")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to register with coordinator: {e}")
            return False

    async def send_heartbeat(self) -> bool:
        """Send periodic heartbeat to coordinator"""
        if not self.registered or not self.node_id:
            return False

        try:
            response = requests.post(
                f"{self.coordinator_url}/workers/{self.node_id}/heartbeat",
                timeout=5
            )

            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Heartbeat failed: {response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"Heartbeat error: {e}")
            return False

    async def connect_to_ray_cluster(self):
        """Connect to the Ray cluster managed by coordinator"""
        try:
            # Extract coordinator host from URL
            coord_host = self.coordinator_url.replace('http://', '').replace('https://', '').split(':')[0]
            ray_address = f"ray://{coord_host}:10001"

            logger.info(f"Connecting to Ray cluster at {ray_address}")

            ray.init(
                address=ray_address,
                runtime_env={
                    "pip": [
                        "torch",
                        "sentence-transformers",
                        "diffusers",
                        "transformers"
                    ]
                }
            )

            # Verify connection
            resources = ray.cluster_resources()
            logger.info(f"Connected to Ray cluster. Available resources: {resources}")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Ray cluster: {e}")
            return False

    async def heartbeat_loop(self):
        """Background task to send periodic heartbeats"""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            if self.registered:
                success = await self.send_heartbeat()
                if not success:
                    logger.warning("Heartbeat failed, attempting re-registration")
                    self.registered = False

    async def registration_loop(self):
        """Background task to maintain registration with coordinator"""
        while True:
            if not self.registered:
                logger.info("Attempting to register with coordinator...")
                success = await self.register_with_coordinator()

                if not success:
                    logger.warning("Registration failed, retrying in 30 seconds")
                    await asyncio.sleep(30)
                    continue

            await asyncio.sleep(60)  # Check registration status every minute

    def log_system_status(self):
        """Log current system and GPU status"""
        system_info = self._get_system_info()
        current_gpu_info = self._detect_gpu_capabilities()

        logger.info(f"System Status:")
        logger.info(f"  CPU: {system_info['cpu_count']} cores, {system_info['cpu_usage_percent']}% usage")
        logger.info(f"  Memory: {system_info['memory_available_gb']:.1f}GB / {system_info['memory_total_gb']:.1f}GB available")

        for i, gpu in enumerate(current_gpu_info):
            logger.info(f"  GPU {i}: {gpu.name} - {gpu.memory_free}MB / {gpu.memory_total}MB free, {gpu.utilization}% util")

async def main():
    """
    Main worker entry point

    Rick Sanchez philosophy: "Connect to the cluster, report what you've got,
    and execute whatever compute jobs show up. It's not rocket science, Morty."
    """
    logger.info("🔧 Starting Backyard Swarm Worker")

    # Create worker service
    worker = WorkerService()

    # Log initial system status
    worker.log_system_status()

    if not worker.gpu_info:
        logger.warning("No GPUs detected! This worker will only handle CPU tasks.")
    else:
        total_gpu_memory = sum(gpu.memory_total for gpu in worker.gpu_info)
        logger.info(f"Detected {len(worker.gpu_info)} GPUs with {total_gpu_memory}MB total VRAM")

    # Connect to Ray cluster
    ray_connected = await worker.connect_to_ray_cluster()
    if not ray_connected:
        logger.error("Failed to connect to Ray cluster, exiting")
        sys.exit(1)

    # Start background tasks
    heartbeat_task = asyncio.create_task(worker.heartbeat_loop())
    registration_task = asyncio.create_task(worker.registration_loop())

    logger.info(f"🚀 Worker active: {NODE_NAME}")
    logger.info(f"📡 Coordinator: {COORD_ADDR}")
    logger.info(f"💪 Ready to execute distributed AI workloads")

    try:
        # Keep worker running
        await asyncio.gather(heartbeat_task, registration_task)
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
    except Exception as e:
        logger.error(f"Worker error: {e}")
    finally:
        # Cleanup
        if ray.is_initialized():
            ray.shutdown()
        logger.info("Worker stopped")

if __name__ == "__main__":
    asyncio.run(main())