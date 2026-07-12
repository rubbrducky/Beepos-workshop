#!/usr/bin/env python3
# PROOF: reuse the Beepo character LoRA (from Robo Pals) on the SAME ComfyUI/Flux
# pipeline the Kitchen used, but for Beepo's Workshop -> Beepo the builder host.
# Verified recipe (Robo Pals gen_flux_hero.py, 2026-07-05): LoraLoader @1.3 + full
# descriptor prompt = identity locked. Base flux1-dev-fp8, 24 steps, euler/simple,
# FluxGuidance 3.5, cfg 1.0. ComfyUI already sees the LoRA via extra_model_paths.yaml.
import json, time, urllib.request, sys

HOST = "http://127.0.0.1:8188"
CKPT = "flux1-dev-fp8.safetensors"
LORA = "beepo_flux_v2.safetensors"
STR  = 1.3

# The trained trigger word + descriptor (must keep the descriptor per the memory note).
BEEPO = ("beepo, a cute friendly robot mascot character named Beepo, mint teal and cream white colored, "
         "big rounded square head with a large glowing teal screen face, huge shiny round black eyes, "
         "happy open smile, rosy cheeks, a small antenna with a ball on top, a little control panel on "
         "its belly, short stubby arms and legs")
# Workshop persona: builder host — hard hat + wrench (matches the in-game #beepo hard hat + bwrench).
TAIL = "cute soft 3d cartoon render, glossy cel shading, plain flat white background"

SUBJECTS = {
 "wb_build": f"{BEEPO}, wearing a chunky yellow construction hard hat, holding up a big cartoon wrench in one hand, standing facing forward in a workshop, {TAIL}",
 "wb_grin":  f"{BEEPO}, wearing a chunky yellow construction hard hat, holding a big cartoon wrench, big proud toothy grin, cheering, standing facing forward, {TAIL}",
 "wb_wow":   f"{BEEPO}, wearing a chunky yellow construction hard hat, holding a big cartoon wrench, wide open surprised wow expression, eyebrows up, standing facing forward, {TAIL}",
}
SEEDS = [12345, 271828]  # 2 seeds each = 6 images

def wf(prompt, seed, pre):
    return {
      "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CKPT}},
      "10":{"class_type":"LoraLoader","inputs":{"lora_name":LORA,"strength_model":STR,"strength_clip":STR,"model":["4",0],"clip":["4",1]}},
      "6":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["10",1]}},
      "22":{"class_type":"FluxGuidance","inputs":{"guidance":3.5,"conditioning":["6",0]}},
      "7":{"class_type":"CLIPTextEncode","inputs":{"text":"","clip":["10",1]}},
      "5":{"class_type":"EmptySD3LatentImage","inputs":{"width":1024,"height":1024,"batch_size":1}},
      "3":{"class_type":"KSampler","inputs":{"seed":seed,"steps":24,"cfg":1.0,"sampler_name":"euler","scheduler":"simple","denoise":1.0,"model":["10",0],"positive":["22",0],"negative":["7",0],"latent_image":["5",0]}},
      "8":{"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}},
      "9":{"class_type":"SaveImage","inputs":{"filename_prefix":pre,"images":["8",0]}}}

def get(p): return json.load(urllib.request.urlopen(HOST+p, timeout=30))
def post(graph):
    req = urllib.request.Request(HOST+"/prompt", data=json.dumps({"prompt":graph}).encode(),
                                 headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))["prompt_id"]

# sanity: LoRA visible to ComfyUI?
try:
    info = get("/object_info/LoraLoader")
    loras = info["LoraLoader"]["input"]["required"]["lora_name"][0]
    print(f"[proof] LoRA visible to ComfyUI: {LORA in loras}  (total {len(loras)} loras)", flush=True)
    if LORA not in loras:
        print("[proof] available:", loras); sys.exit("LoRA not found by ComfyUI")
except Exception as e:
    sys.exit(f"[proof] ComfyUI not reachable / no LoraLoader node: {e}")

jobs = {}
for tag, prompt in SUBJECTS.items():
    for s in SEEDS:
        pre = f"beepo_workshop/{tag}_{s}"
        jobs[(tag, s)] = post(wf(prompt, s, pre))
        print(f"[queued] {tag} seed={s}", flush=True)

print(f"[proof] {len(jobs)} queued, polling...", flush=True)
done, files, t0 = set(), [], time.time()
while len(done) < len(jobs) and time.time()-t0 < 1200:
    for key, pid in list(jobs.items()):
        if key in done: continue
        try: h = get("/history/"+pid)
        except Exception: continue
        if pid in h and h[pid].get("outputs"):
            fs = [im["filename"] for node in h[pid]["outputs"].values() for im in node.get("images",[])]
            files += fs; done.add(key)
            print(f"[done {len(done)}/{len(jobs)}] {key[0]} seed={key[1]} -> {', '.join(fs)}", flush=True)
    time.sleep(3)
print(f"[proof] complete {len(done)}/{len(jobs)} in {time.time()-t0:.0f}s", flush=True)
print("FILES:", json.dumps(files))
