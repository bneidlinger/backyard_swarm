#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

PY=python3
if ! command -v ${PY} >/dev/null 2>&1; then
  echo "python3 not found"; exit 1
fi

echo "=== Embeddings smoke test ==="
mkdir -p /data || true
if [ ! -f /data/corpus.txt ]; then
  cat > /data/corpus.txt <<EOF
Backyard Swarm is alive.
Distributed systems are social systems with failure baked in.
LoRA adapters keep traffic small.
Speculative decoding boosts throughput with a verifier.
EOF
fi

${PY} jobs/embeddings.py --input /data/corpus.txt --shards 8 --out /data/corpus.embeddings.json || exit 1
echo "Embeddings written to /data/corpus.embeddings.json"

if [ -f /data/prompts.txt ]; then
  echo "=== SD batch smoke (prompts found) ==="
  ${PY} jobs/sd_batch.py --prompts /data/prompts.txt --out /data/outs || true
else
  echo "No /data/prompts.txt found; skipping SD batch."
fi

echo "=== Smoke test complete ==="
