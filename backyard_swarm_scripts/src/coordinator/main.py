#!/usr/bin/env python3
"""
Backyard Swarm Coordinator Service

The central control plane that orchestrates the P2P GPU mesh:
- Ray cluster head for distributed compute
- REST API for health checks and job management
- Worker registry and resource tracking
- MinIO integration for artifact storage

Cool Rick philosophy: "Steady hands. Minimal complexity. Maximum effectiveness."
"""

import os
import sys
import time
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

import ray
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError

# Configure logging with Rick-level professionalism
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backyard-coordinator")

# Configuration from environment
STORAGE_URL = os.getenv("STORAGE_URL", "http://minio:9000")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "backyard")
STORAGE_ACCESS = os.getenv("STORAGE_ACCESS", "minio")
STORAGE_SECRET = os.getenv("STORAGE_SECRET", "minio123")
RAY_HEAD_PORT = int(os.getenv("RAY_HEAD_PORT", "10001"))
API_PORT = int(os.getenv("API_PORT", "8080"))

class WorkerInfo(BaseModel):
    node_id: str
    node_name: str
    gpu_count: int
    gpu_memory_total: int
    last_heartbeat: datetime
    status: str = "active"

class JobRequest(BaseModel):
    job_type: str
    parameters: Dict
    priority: int = 1

class CoordinatorService:
    def __init__(self):
        self.workers: Dict[str, WorkerInfo] = {}
        self.s3_client = None
        self.app = FastAPI(
            title="Backyard Swarm Coordinator",
            description="P2P GPU mesh coordination service",
            version="0.1.0"
        )
        self._setup_routes()

    def _setup_routes(self):
        """Configure API endpoints with Cool Rick efficiency"""

        @self.app.get("/healthz")
        async def health_check():
            """Health endpoint for load balancers and monitoring"""
            try:
                # Check Ray cluster status
                ray_status = ray.cluster_resources()

                # Check MinIO connectivity
                minio_ok = await self._check_minio()

                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "ray_cluster": {
                        "nodes": len(ray.nodes()),
                        "resources": ray_status
                    },
                    "storage": {"minio": "ok" if minio_ok else "error"},
                    "workers": len(self.workers)
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

        @self.app.get("/workers")
        async def list_workers():
            """List all registered workers and their capabilities"""
            return {"workers": list(self.workers.values())}

        @self.app.post("/workers/register")
        async def register_worker(worker: WorkerInfo):
            """Register a new worker node in the mesh"""
            logger.info(f"Registering worker: {worker.node_name} ({worker.node_id})")
            worker.last_heartbeat = datetime.utcnow()
            self.workers[worker.node_id] = worker
            return {"status": "registered", "node_id": worker.node_id}

        @self.app.post("/workers/{node_id}/heartbeat")
        async def worker_heartbeat(node_id: str):
            """Update worker heartbeat - called periodically by workers"""
            if node_id in self.workers:
                self.workers[node_id].last_heartbeat = datetime.utcnow()
                self.workers[node_id].status = "active"
                return {"status": "heartbeat_received"}
            else:
                raise HTTPException(status_code=404, detail="Worker not registered")

        @self.app.get("/cluster/status")
        async def cluster_status():
            """Get comprehensive cluster status for monitoring"""
            try:
                ray_nodes = ray.nodes()
                ray_resources = ray.cluster_resources()

                return {
                    "cluster": {
                        "total_nodes": len(ray_nodes),
                        "alive_nodes": len([n for n in ray_nodes if n["Alive"]]),
                        "total_cpus": ray_resources.get("CPU", 0),
                        "total_gpus": ray_resources.get("GPU", 0),
                        "memory_gb": ray_resources.get("memory", 0) / (1024**3)
                    },
                    "workers": {
                        "registered": len(self.workers),
                        "active": len([w for w in self.workers.values() if w.status == "active"])
                    }
                }
            except Exception as e:
                logger.error(f"Cluster status failed: {e}")
                raise HTTPException(status_code=500, detail=f"Cluster status error: {e}")

        @self.app.post("/jobs/submit")
        async def submit_job(job: JobRequest):
            """Submit a job to the Ray cluster"""
            # Placeholder for job submission logic
            # Your existing Ray jobs (embeddings.py, sd_batch.py) will connect directly to Ray
            logger.info(f"Job submission requested: {job.job_type}")
            return {
                "status": "accepted",
                "message": "Job queued for execution",
                "job_type": job.job_type,
                "ray_address": f"ray://localhost:{RAY_HEAD_PORT}"
            }

    async def _check_minio(self) -> bool:
        """Verify MinIO connectivity"""
        try:
            if not self.s3_client:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=STORAGE_URL,
                    aws_access_key_id=STORAGE_ACCESS,
                    aws_secret_access_key=STORAGE_SECRET
                )

            # Try to list buckets as connectivity test
            self.s3_client.list_buckets()
            return True
        except Exception as e:
            logger.warning(f"MinIO connectivity check failed: {e}")
            return False

    async def _cleanup_stale_workers(self):
        """Remove workers that haven't sent heartbeats recently"""
        cutoff = datetime.utcnow().timestamp() - 300  # 5 minutes
        stale_workers = []

        for node_id, worker in self.workers.items():
            if worker.last_heartbeat.timestamp() < cutoff:
                stale_workers.append(node_id)

        for node_id in stale_workers:
            logger.info(f"Removing stale worker: {self.workers[node_id].node_name}")
            del self.workers[node_id]

    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_stale_workers()

        # Start cleanup task
        asyncio.create_task(cleanup_loop())

def initialize_ray_cluster():
    """Initialize Ray as cluster head"""
    try:
        # Check if Ray is already running
        try:
            ray.init(address="auto", ignore_reinit_error=True)
            logger.info("Connected to existing Ray cluster")
        except:
            # Start new Ray head
            ray.init(
                head=True,
                port=RAY_HEAD_PORT,
                dashboard_host="0.0.0.0",
                dashboard_port=8265,
                include_dashboard=True
            )
            logger.info(f"Started Ray head on port {RAY_HEAD_PORT}")

        # Log cluster info
        resources = ray.cluster_resources()
        logger.info(f"Ray cluster resources: {resources}")

    except Exception as e:
        logger.error(f"Failed to initialize Ray cluster: {e}")
        sys.exit(1)

def main():
    """
    Main coordinator entry point

    Cool Rick approach: Start Ray head, launch API, handle graceful shutdown
    """
    logger.info("🐝 Starting Backyard Swarm Coordinator")

    # Initialize Ray cluster as head
    initialize_ray_cluster()

    # Create coordinator service
    coordinator = CoordinatorService()

    # Start background tasks
    asyncio.create_task(coordinator.start_background_tasks())

    logger.info(f"🚀 Coordinator API starting on port {API_PORT}")
    logger.info(f"📊 Ray dashboard available at http://localhost:8265")
    logger.info(f"💾 Storage backend: {STORAGE_URL}")

    # Run the API server
    uvicorn.run(
        coordinator.app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info"
    )

if __name__ == "__main__":
    main()