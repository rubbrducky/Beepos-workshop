#!/usr/bin/env python3
# Beepo's Workshop — all 25 machine-combo stills (5 bases x 5 tops).
# House style, NO LoRA (machines aren't Beepo). Flux dev fp8, 1024, 24 steps, guid 3.5.
# Base-appropriate framing + the "walking machine on robot legs" fix for legs bases
# (Flux: "legs"->wheels, "robot legs"->humanoid; "walking X machine on robot legs"+"toy machine"=right).
# Skips the 3 already-locked combos. 2 seeds each. Outputs -> ComfyUI/output/beepo_workshop/mch_*.
import json, time, urllib.request, sys

HOST="http://127.0.0.1:8188"; CKPT="flux1-dev-fp8.safetensors"; W=H=1024; STEPS=24; GUID=3.5
SEEDS=[10101,73939]

BASES=['wheels','legs','hull','rails','rocket']
TOPS =['smokestack','propeller','claw','light','bubbles']
RECIPES={  # base-top index -> name (from index.html)
 (0,0):'Steam Car',(0,1):'Fan Racer',(0,2):'Digger',(0,3):'Night Racer',(0,4):'Bubble Buggy',
 (1,0):'Stompy Steamer',(1,1):'Flap-Bot',(1,2):'Grabby Walker',(1,3):'Robot',(1,4):'Bubble Stomper',
 (2,0):'Steam Boat',(2,1):'Speed Boat',(2,2):'Crab Boat',(2,3):'Lighthouse Boat',(2,4):'Bubble Tug',
 (3,0):'Train',(3,1):'Whirly Train',(3,2):'Crane Train',(3,3):'Night Train',(3,4):'Bubble Express',
 (4,0):'Puff Rocket',(4,1):'Whirly Rocket',(4,2):'Star Grabber',(4,3):'Star Ship',(4,4):'Bubble Blaster'}
LOCKED={(0,0),(1,2),(4,1)}   # Steam Car, Grabby Walker, Whirly Rocket already curated & kept

STYLE_TAIL=("thick dark charcoal outline, glossy highlights, soft cel shading with smooth gradients, "
            "warm soft lighting, pastel candy colors, big sparkly happy eyes and rosy cheeks, super cute, "
            "centered single subject, plain flat white background, high quality")
VEH_STYLE  = "cute soft 3D cartoon render, chunky rounded toy, "+STYLE_TAIL
MACH_STYLE = "cute soft 3D cartoon render, chunky rounded toy machine, "+STYLE_TAIL   # for legs (no 'vehicle'/'robot')

# body per base (legs handled specially in build())
BODY={
 'wheels':"toy car with a rounded body and two big round black wheels with cream hubs",
 'hull':  "toy boat with a rounded floating boat hull sitting on a little water",
 'rails': "toy train engine with a rounded body on little wheels on a short piece of railway track",
 'rocket':"toy rocket ship standing upright on three little fins with a small orange flame at the bottom",
}
GADGET={
 'smokestack':"a tall smokestack chimney on top puffing one small white smoke puff",
 'propeller':"a spinning propeller mounted on top",
 'claw':"a grabber claw crane arm reaching up from the top",
 'light':"a glowing lighthouse beacon lamp shining on top",
 'bubbles':"a bubble blower on top blowing a few little round soap bubbles",
}

def build(bi,ti):
    b,t=BASES[bi],TOPS[ti]; g=GADGET[t]
    if b=='legs':   # walking machine on robot legs (the validated fix)
        return (f"a cute little walking machine standing upright on two chunky robot legs with round feet, "
                f"{g}, one big friendly smiling face with big shiny eyes and rosy cheeks on the front of its "
                f"boxy body, full standing pose, pastel colors, {MACH_STYLE}")
    return (f"a cute chunky {BODY[b]}, {g}, a happy smiling face with big shiny eyes and rosy cheeks on the "
            f"front of its body, pastel colors, {VEH_STYLE}")

def wf(prompt,seed,pre):
    return {
      "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CKPT}},
      "6":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["4",1]}},
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

combos=[(bi,ti) for bi in range(5) for ti in range(5) if (bi,ti) not in LOCKED]
print(f"[machines] {len(combos)} combos x {len(SEEDS)} seeds = {len(combos)*len(SEEDS)} renders (skipping {len(LOCKED)} locked)\n",flush=True)
jobs={}
for bi,ti in combos:
    for s in SEEDS:
        pre=f"beepo_workshop/mch_{bi}{ti}_{BASES[bi]}-{TOPS[ti]}_{s}"
        jobs[(bi,ti,s)]=post(wf(build(bi,ti),s,pre)); print(f"[q] {RECIPES[(bi,ti)]:16s} {BASES[bi]}+{TOPS[ti]} {s}",flush=True)

print(f"\n[machines] polling...",flush=True)
done=set(); files=[]; t0=time.time()
while len(done)<len(jobs) and time.time()-t0<3600:
    for k,pid in list(jobs.items()):
        if k in done: continue
        try: h=get("/history/"+pid)
        except Exception: continue
        if pid in h and h[pid].get("outputs"):
            fs=[im["filename"] for node in h[pid]["outputs"].values() for im in node.get("images",[])]
            files+=fs; done.add(k)
            print(f"[{len(done)}/{len(jobs)}] {RECIPES[(k[0],k[1])]} {k[2]} -> {', '.join(fs)}",flush=True)
    time.sleep(3)
print(f"\n[machines] complete {len(done)}/{len(jobs)} in {time.time()-t0:.0f}s",flush=True)
print("FILES:",json.dumps(files))
