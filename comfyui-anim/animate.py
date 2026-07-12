#!/usr/bin/env python3
# ============================================================================
#  comfyui-anim  —  image-to-video sandbox for Beepo's Workshop
#  Wan 2.2 TI2V-5B (native ComfyUI). Turns a still in ./input/ into a looping
#  animated WebP in ./output/. Stdlib only — runs on any Python 3.
#
#  USAGE (ComfyUI must be running on :8188):
#     start ComfyUI:  cd C:\Users\gusta\ComfyUI && venv\Scripts\python.exe main.py --port 8188
#     then:           python animate.py                      # newest image in ./input/ + prompt.txt
#                     python animate.py grabby_walker.png    # a specific start image
#                     python animate.py beepo_builder.png --size 704 --steps 20   # fast draft
#                     python animate.py --prompt "spinning its propeller, lifting off"
#
#  Options:  --size N (def 1024)  --steps N (def 30)  --length N (def 49, step 4)
#            --prompt "..." (overrides prompt.txt)   --fps N (def 24)
# ============================================================================
import json, sys, os, time, shutil, glob, urllib.request
from datetime import datetime

HOST = "http://127.0.0.1:8188"
UNET = "wan2.2_ti2v_5B_fp16.safetensors"
CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE  = "wan2.2_vae.safetensors"
COMFY_INPUT  = r"C:\Users\gusta\ComfyUI\input"
COMFY_OUTPUT = r"C:\Users\gusta\ComfyUI\output"

HERE   = os.path.dirname(os.path.abspath(__file__))
IN_DIR = os.path.join(HERE, "input")
OUT_DIR= os.path.join(HERE, "output")

# Official Wan negative (quality/artifact terms) + eye-artifact + blur terms.
NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
       "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，"
       "手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走，"
       "green eyes, glowing green eyes, eyes changing colour, blurry, soft focus, low resolution")

# ---- tiny arg parser -------------------------------------------------------
args = sys.argv[1:]
opts = {"--size":1024, "--steps":30, "--length":49, "--fps":24, "--prompt":None}
start_name = None
i = 0
while i < len(args):
    a = args[i]
    if a in opts:
        opts[a] = args[i+1]; i += 2
    elif not a.startswith("-"):
        start_name = a; i += 1
    else:
        sys.exit(f"unknown option {a}")
SIZE, STEPS, LENGTH, FPS = int(opts["--size"]), int(opts["--steps"]), int(opts["--length"]), int(opts["--fps"])

# ---- resolve the start image ----------------------------------------------
imgs = [f for ext in ("*.png","*.jpg","*.jpeg","*.webp")
          for f in glob.glob(os.path.join(IN_DIR, ext))]
if start_name:
    start_path = os.path.join(IN_DIR, start_name)
    if not os.path.exists(start_path): sys.exit(f"[animate] no such start image: {start_path}")
elif imgs:
    start_path = max(imgs, key=os.path.getmtime)          # newest
    print(f"[animate] using newest input: {os.path.basename(start_path)}")
else:
    sys.exit(f"[animate] no images in {IN_DIR} — drop a start frame there first.")

# ---- resolve the prompt ----------------------------------------------------
if opts["--prompt"]:
    prompt = opts["--prompt"]
else:
    pf = os.path.join(HERE, "prompt.txt")
    lines = [l.rstrip("\n") for l in open(pf, encoding="utf-8")]
    prompt = " ".join(l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")).strip()
    if not prompt: sys.exit("[animate] prompt.txt has no prompt (all comments?)")

# ---- stage start frame into ComfyUI/input ---------------------------------
stem = os.path.splitext(os.path.basename(start_path))[0]
staged = f"animsbx_{stem}.png"
shutil.copy(start_path, os.path.join(COMFY_INPUT, staged))

def graph(seed, prefix):
    return {
      "1":  {"class_type":"UNETLoader","inputs":{"unet_name":UNET,"weight_dtype":"default"}},
      "2":  {"class_type":"CLIPLoader","inputs":{"clip_name":CLIP,"type":"wan"}},
      "3":  {"class_type":"VAELoader","inputs":{"vae_name":VAE}},
      "4":  {"class_type":"ModelSamplingSD3","inputs":{"shift":8,"model":["1",0]}},
      "5":  {"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["2",0]}},
      "6":  {"class_type":"CLIPTextEncode","inputs":{"text":NEG,"clip":["2",0]}},
      "7":  {"class_type":"LoadImage","inputs":{"image":staged}},
      "8":  {"class_type":"Wan22ImageToVideoLatent","inputs":{
                "vae":["3",0],"width":SIZE,"height":SIZE,"length":LENGTH,"batch_size":1,"start_image":["7",0]}},
      "9":  {"class_type":"KSampler","inputs":{
                "seed":seed,"steps":STEPS,"cfg":5,"sampler_name":"uni_pc","scheduler":"simple","denoise":1.0,
                "model":["4",0],"positive":["5",0],"negative":["6",0],"latent_image":["8",0]}},
      "10": {"class_type":"VAEDecode","inputs":{"samples":["9",0],"vae":["3",0]}},
      "11": {"class_type":"SaveAnimatedWEBP","inputs":{
                "images":["10",0],"filename_prefix":prefix,"fps":FPS,
                "lossless":False,"quality":95,"method":"default"}},
    }

def get(p): return json.load(urllib.request.urlopen(HOST+p, timeout=30))
def post(g):
    req = urllib.request.Request(HOST+"/prompt", data=json.dumps({"prompt":g}).encode(),
                                 headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))["prompt_id"]

try: get("/queue")
except Exception as e:
    sys.exit(f"[animate] ComfyUI not reachable at {HOST} — start it first:\n"
             f"   cd C:\\Users\\gusta\\ComfyUI && venv\\Scripts\\python.exe main.py --port 8188\n   ({e})")

seed = int(time.time()) & 0x7fffffff
prefix = "animsbx/run"
pid = post(graph(seed, prefix))
print(f"[animate] {stem}  {SIZE}x{SIZE}x{LENGTH}f@{FPS}  steps={STEPS}  seed={seed}\n"
      f"[animate] prompt: {prompt[:110]}{'...' if len(prompt)>110 else ''}\n[animate] rendering...")

t0 = time.time()
while time.time()-t0 < 1800:
    try: h = get("/history/"+pid)
    except Exception: h = {}
    if pid in h and h[pid].get("outputs"):
        # copy result(s) out of ComfyUI/output into this folder's ./output/
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved = []
        for node in h[pid]["outputs"].values():
            for im in node.get("images", []):
                srcp = os.path.join(COMFY_OUTPUT, im.get("subfolder",""), im["filename"])
                dstp = os.path.join(OUT_DIR, f"{stem}_{stamp}{os.path.splitext(im['filename'])[1]}")
                if os.path.exists(srcp): shutil.copy(srcp, dstp); saved.append(dstp)
        dt = time.time()-t0
        print(f"[animate] done in {dt:.0f}s ->")
        for s in saved: print("   ", s)
        break
    time.sleep(3)
else:
    sys.exit("[animate] timed out after 1800s")
