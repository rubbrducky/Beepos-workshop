#!/usr/bin/env python3
# Beepo's Workshop — image-to-video via Wan 2.2 TI2V-5B (native ComfyUI nodes).
# Takes an on-model still (from Flux + beepo_flux_v2 LoRA) as frame 1 and animates it,
# so the motion is unmistakably OUR Beepo. Outputs a looping animated WebP that drops
# straight into index.html (the delivery format Gustav picked).
#
# Params are the OFFICIAL ComfyUI TI2V-5B template values:
#   ModelSamplingSD3 shift=8 | KSampler steps=20 cfg=5 uni_pc/simple | 24 fps.
#
# Usage: gen_workshop_anim.py <start_image_in_ComfyUI_input> <out_prefix> "<motion prompt>" [length]
import json, time, urllib.request, sys, random

HOST = "http://127.0.0.1:8188"
UNET = "wan2.2_ti2v_5B_fp16.safetensors"
CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE  = "wan2.2_vae.safetensors"
FPS  = 24

# Official Wan negative (quality/artifact terms) from the ComfyUI TI2V template,
# + explicit eye-artifact terms (the 5B model fills closed eyes with the teal
# screen colour, so it "blinks green" — suppress that and blur).
NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
       "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，"
       "手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走，"
       "green eyes, glowing green eyes, eyes changing colour, blurry, soft focus, low resolution")

start  = sys.argv[1] if len(sys.argv) > 1 else "wb_build_start.png"
prefix = sys.argv[2] if len(sys.argv) > 2 else "beepo_workshop/anim_beepo_working"
motion = sys.argv[3] if len(sys.argv) > 3 else (
    "the cute mint-teal robot mechanic Beepo happily working, turning a big wrench up and down, "
    "antenna bobbing, blinking, gentle cheerful idle motion, plain white background")
length = int(sys.argv[4]) if len(sys.argv) > 4 else 49   # (49-1)/4+1=13 latent frames ~2s @24fps
W = H  = int(sys.argv[5]) if len(sys.argv) > 5 else 704  # square; 1024 is sharper, 704 is the native TI2V dim
STEPS  = int(sys.argv[6]) if len(sys.argv) > 6 else 20   # 20 = official template; 30 = more fidelity

def wf(seed):
    return {
      "1":  {"class_type":"UNETLoader","inputs":{"unet_name":UNET,"weight_dtype":"default"}},
      "2":  {"class_type":"CLIPLoader","inputs":{"clip_name":CLIP,"type":"wan"}},
      "3":  {"class_type":"VAELoader","inputs":{"vae_name":VAE}},
      "4":  {"class_type":"ModelSamplingSD3","inputs":{"shift":8,"model":["1",0]}},
      "5":  {"class_type":"CLIPTextEncode","inputs":{"text":motion,"clip":["2",0]}},
      "6":  {"class_type":"CLIPTextEncode","inputs":{"text":NEG,"clip":["2",0]}},
      "7":  {"class_type":"LoadImage","inputs":{"image":start}},
      "8":  {"class_type":"Wan22ImageToVideoLatent","inputs":{
                "vae":["3",0],"width":W,"height":H,"length":length,"batch_size":1,"start_image":["7",0]}},
      "9":  {"class_type":"KSampler","inputs":{
                "seed":seed,"steps":STEPS,"cfg":5,"sampler_name":"uni_pc","scheduler":"simple","denoise":1.0,
                "model":["4",0],"positive":["5",0],"negative":["6",0],"latent_image":["8",0]}},
      "10": {"class_type":"VAEDecode","inputs":{"samples":["9",0],"vae":["3",0]}},
      "11": {"class_type":"SaveAnimatedWEBP","inputs":{
                "images":["10",0],"filename_prefix":prefix,"fps":FPS,
                "lossless":False,"quality":95,"method":"default"}},
    }

def get(p): return json.load(urllib.request.urlopen(HOST+p, timeout=30))
def post(graph):
    req = urllib.request.Request(HOST+"/prompt", data=json.dumps({"prompt":graph}).encode(),
                                 headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))["prompt_id"]

try: get("/queue")
except Exception as e: sys.exit(f"[anim] ComfyUI not reachable: {e}")

seed = random.randint(1, 2_000_000_000)
pid = post(wf(seed))
print(f"[anim] queued {prefix}  start={start}  {W}x{H}x{length}f@{FPS}  seed={seed}  pid={pid}", flush=True)

t0 = time.time()
while time.time()-t0 < 1200:
    try: h = get("/history/"+pid)
    except Exception: h = {}
    if pid in h and h[pid].get("outputs"):
        files = [im["filename"] for node in h[pid]["outputs"].values() for im in node.get("images",[])]
        st = h[pid].get("status",{}).get("status_str","")
        print(f"[anim] done in {time.time()-t0:.0f}s  status={st}  -> {', '.join(files) or '(no file)'}", flush=True)
        print("FILES:", json.dumps(files))
        break
    time.sleep(4)
else:
    print("[anim] timed out after 1200s", flush=True)
