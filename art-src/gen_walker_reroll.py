#!/usr/bin/env python3
# Grabby Walker re-roll: force LEGS not wheels. Flux@cfg1.0 ignores negatives,
# so win it positively — lead with "robot legs", drop "vehicle", say "standing upright".
import json, time, urllib.request, sys
HOST="http://127.0.0.1:8188"; CKPT="flux1-dev-fp8.safetensors"; W=H=1024; STEPS=24; GUID=3.5
SEEDS=[31002,47701,62203,90905]

# "toy machine" (NOT "robot" -> humanoid, NOT "vehicle" -> wheels). Middle ground = walker mech.
STYLE=("cute soft 3D cartoon render, chunky rounded toy machine, thick dark charcoal outline, glossy "
       "highlights, soft cel shading with smooth gradients, warm soft lighting, pastel candy colors, "
       "big sparkly happy eyes and rosy cheeks, super cute, centered single subject, plain flat white "
       "background, high quality")
# machine on legs with a claw crane on top, NO humanoid side-arms (only legs + one crane appendage)
PROMPT=("a cute little walking crane machine, one compact boxy body standing on two short chunky robot "
        "legs with round feet planted on the ground, a single tall grabber claw crane arm mounted on top "
        "reaching up high, one big friendly smiling face with big shiny eyes and rosy cheeks on the front "
        "of the boxy body, full standing pose, pastel colors, "+STYLE)

def wf(seed,pre):
    return {
      "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CKPT}},
      "6":{"class_type":"CLIPTextEncode","inputs":{"text":PROMPT,"clip":["4",1]}},
      "22":{"class_type":"FluxGuidance","inputs":{"guidance":GUID,"conditioning":["6",0]}},
      "7":{"class_type":"CLIPTextEncode","inputs":{"text":"","clip":["4",1]}},
      "5":{"class_type":"EmptySD3LatentImage","inputs":{"width":W,"height":H,"batch_size":1}},
      "3":{"class_type":"KSampler","inputs":{"seed":seed,"steps":STEPS,"cfg":1.0,"sampler_name":"euler","scheduler":"simple","denoise":1.0,"model":["4",0],"positive":["22",0],"negative":["7",0],"latent_image":["5",0]}},
      "8":{"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}},
      "9":{"class_type":"SaveImage","inputs":{"filename_prefix":pre,"images":["8",0]}}}
def get(p): return json.load(urllib.request.urlopen(HOST+p,timeout=30))
def post(g):
    r=urllib.request.Request(HOST+"/prompt",data=json.dumps({"prompt":g}).encode(),headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(r,timeout=30))["prompt_id"]
try: get("/queue")
except Exception as e: sys.exit(f"ComfyUI not reachable: {e}")
jobs={}
for s in SEEDS:
    pre=f"beepo_workshop/veh_walker3_{s}"; jobs[s]=post(wf(s,pre)); print(f"[queued] walker3 {s}",flush=True)
done=set(); files=[]; t0=time.time()
while len(done)<len(jobs) and time.time()-t0<900:
    for s,pid in list(jobs.items()):
        if s in done: continue
        try: h=get("/history/"+pid)
        except Exception: continue
        if pid in h and h[pid].get("outputs"):
            fs=[im["filename"] for node in h[pid]["outputs"].values() for im in node.get("images",[])]
            files+=fs; done.add(s); print(f"[done {len(done)}/{len(jobs)}] {s} -> {', '.join(fs)}",flush=True)
    time.sleep(3)
print(f"[walker2] complete {len(done)}/{len(jobs)} in {time.time()-t0:.0f}s",flush=True)
print("FILES:",json.dumps(files))
