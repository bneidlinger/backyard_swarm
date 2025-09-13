#!/usr/bin/env bash
set -euo pipefail

echo "🐝 Building Backyard Swarm Docker Images"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

# Build coordinator image
echo "📊 Building coordinator image..."
docker build -f docker/coordinator.dockerfile -t ghcr.io/tangnet/backyard-coordinator:0.1 .
docker tag ghcr.io/tangnet/backyard-coordinator:0.1 ghcr.io/tangnet/backyard-coordinator:latest

# Build worker image
echo "🔧 Building worker image..."
docker build -f docker/worker.dockerfile -t ghcr.io/tangnet/backyard-worker:0.1 .
docker tag ghcr.io/tangnet/backyard-worker:0.1 ghcr.io/tangnet/backyard-worker:latest

echo "✅ Build complete!"
echo ""
echo "Images built:"
echo "  - ghcr.io/tangnet/backyard-coordinator:0.1"
echo "  - ghcr.io/tangnet/backyard-worker:0.1"
echo ""
echo "To push to registry:"
echo "  docker push ghcr.io/tangnet/backyard-coordinator:0.1"
echo "  docker push ghcr.io/tangnet/backyard-worker:0.1"