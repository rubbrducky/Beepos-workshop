#!/usr/bin/env python3
# Workshop still batch: a few more Beepo host poses (WITH the beepo_flux_v2 LoRA)
# + 3 full vehicles (NO LoRA — Flux base + kawaii house-style suffix, Kitchen approach,
# because the machines aren't Beepo). All Flux dev fp8, 1024², 24 steps, guid 3.5.
import json, time, urllib.request, sys

HOST = "http://127.0.0.1:8188"
CKPT = "flux1-dev-fp8.safetensors"
LORA = "beepo_flux_v2.safetensors"
STR  = 1.3
W = H = 1024
STEPS, GUID = 24, 3.5
SEEDS = [10101, 73939]

BEEPO = ("beepo, a cute friendly robot mascot character named Beepo, mint teal and cream white colored, "
         "big rounded square head with a large glowing teal screen face, huge shiny round black eyes, "
         "happy open smile, rosy cheeks, a small antenna with a ball on top, a little control panel on "
         "its belly, short stubby arms and legs")
TAIL = "cute soft 3d cartoon render, glossy cel shading, plain flat white background"

# House style for the machines: matches Beepo's render (soft 3D, glossy) + kawaii face. No LoRA.
VEH_STYLE = ("cute soft 3D cartoon render, chunky rounded toy vehicle, thick dark charcoal outline, "
             "glossy highlights, soft cel shading with smooth gradients, warm soft lighting, pastel candy "
             "colors, big sparkly happy eyes and rosy cheeks, super cute, centered single subject, "
             "plain flat white background, high quality")

BEEPOS = {  # LoRA
 "wb_cheer":   f"{BEEPO}, wearing a chunky yellow construction hard hat, both stubby arms raised up cheering happily, big excited open grin, standing facing forward, {TAIL}",
 "wb_wave":    f"{BEEPO}, wearing a chunky yellow construction hard hat, waving hello with one stubby hand raised, friendly happy smile, standing facing forward, {TAIL}",
 "wb_present": f"{BEEPO}, wearing a chunky yellow construction hard hat, one arm extended to the side presenting ta-da, proud happy smile, standing facing forward, {TAIL}",
}
VEHICLES = {  # no LoRA
 "veh_steamcar":     f"a cute chunky toy steam car with two big round black wheels and cream hubs, a rounded pastel car body, a tall little smokestack chimney on top puffing one small white smoke puff, a happy smiling face with big shiny eyes and rosy cheeks on the front of the body, warm pastel colors, {VEH_STYLE}",
 "veh_whirlyrocket": f"a cute chunky toy rocket ship standing upright on three little fins with a small orange flame at the bottom, a spinning propeller mounted on top of its nose cone, a happy smiling face with big shiny eyes and rosy cheeks on the rocket body, pastel colors, {VEH_STYLE}",
 "veh_grabbywalker": f"a cute chunky toy walking machine with two short stubby mechanical legs and round feet, a grabber claw crane arm reaching up from its top, a happy smiling face with big shiny eyes and rosy cheeks on its boxy body, pastel colors, {VEH_STYLE}",
}

def wf_lora(prompt, seed, pre):
    return {
      "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CKPT}},
      "10":{"class_type":"LoraLoader","inputs":{"lora_name":LORA,"strength_model":STR,"strength_clip":STR,"model":["4",0],"clip":["4",1]}},
      "6":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["10",1]}},
      "22":{"class_type":"FluxGuidance","inputs":{"guidance":GUID,"conditioning":["6",0]}},
      "7":{"class_type":"CLIPTextEncode","inputs":{"text":"","clip":["10",1]}},
      "5":{"class_type":"EmptySD3LatentImage","inputs":{"width":W,"height":H,"batch_size":1}},
      "3":{"class_type":"KSampler","inputs":{"seed":seed,"steps":STEPS,"cfg":1.0,"sampler_name":"euler","scheduler":"simple","denoise":1.0,"model":["10",0],"positive":["22",0],"negative":["7",0],"latent_image":["5",0]}},
      "8":{"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}},
      "9":{"class_type":"SaveImage","inputs":{"filename_prefix":pre,"images":["8",0]}}}

def wf_plain(prompt, seed, pre):
    g = wf_lora(prompt, seed, pre)
    del g["10"]                                  # drop LoRA node
    g["6"]["inputs"]["clip"] = ["4",1]           # CLIP straight from checkpoint
    g["7"]["inputs"]["clip"] = ["4",1]
    g["3"]["inputs"]["model"] = ["4",0]          # model straight from checkpoint
    return g

def get(p): return json.load(urllib.request.urlopen(HOST+p, timeout=30))
def post(g):
    req=urllib.request.Request(HOST+"/prompt",data=json.dumps({"prompt":g}).encode(),headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req,timeout=30))["prompt_id"]

try: get("/queue")
except Exception as e: sys.exit(f"ComfyUI not reachable: {e}")

jobs={}
for tag,p in BEEPOS.items():
    for s in SEEDS:
        pre=f"beepo_workshop/{tag}_{s}"; jobs[(tag,s)]=post(wf_lora(p,s,pre)); print(f"[queued LoRA] {tag} {s}",flush=True)
for tag,p in VEHICLES.items():
    for s in SEEDS:
        pre=f"beepo_workshop/{tag}_{s}"; jobs[(tag,s)]=post(wf_plain(p,s,pre)); print(f"[queued plain] {tag} {s}",flush=True)

print(f"[batch] {len(jobs)} queued, polling...",flush=True)
done=set(); files=[]; t0=time.time()
while len(done)<len(jobs) and time.time()-t0<1800:
    for k,pid in list(jobs.items()):
        if k in done: continue
        try: h=get("/history/"+pid)
        except Exception: continue
        if pid in h and h[pid].get("outputs"):
            fs=[im["filename"] for node in h[pid]["outputs"].values() for im in node.get("images",[])]
            files+=fs; done.add(k); print(f"[done {len(done)}/{len(jobs)}] {k[0]} {k[1]} -> {', '.join(fs)}",flush=True)
    time.sleep(3)
print(f"[batch] complete {len(done)}/{len(jobs)} in {time.time()-t0:.0f}s",flush=True)
print("FILES:",json.dumps(files))
