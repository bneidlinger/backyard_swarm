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
