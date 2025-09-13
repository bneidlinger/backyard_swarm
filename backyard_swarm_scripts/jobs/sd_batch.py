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
