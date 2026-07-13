#!/usr/bin/env python3
# Beepo's Workshop — batch-animate the locked machine stills (Wan 2.2 TI2V-5B I2V -> looping WebP).
# Per-base locomotion motion + per-top gadget action. Tuned defaults: 1024, 49f, 30 steps, 16 fps
# (gentle/slow motion + eye-open negative). Start frames = assets/vehicles/<clean>.png.
# Skips the 5 already animated. Outputs -> ComfyUI/output/beepo_workshop/anim_<clean>.
import json, time, urllib.request, sys, shutil, os
HOST="http://127.0.0.1:8188"
UNET="wan2.2_ti2v_5B_fp16.safetensors"; CLIP="umt5_xxl_fp8_e4m3fn_scaled.safetensors"; VAE="wan2.2_vae.safetensors"
W=H=1024; LENGTH=49; STEPS=30; FPS=16
PROJ="C:/Users/gusta/OneDrive/Desktop/Claude/Beepos workshop"; CIN="C:/Users/gusta/ComfyUI/input"
NEG=("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
     "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，"
     "手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走，"
     "green eyes, glowing green eyes, eyes changing colour, blurry, soft focus, low resolution, motion blur")

BASES=['wheels','legs','hull','rails','rocket']; TOPS=['smokestack','propeller','claw','light','bubbles']
NAME={(0,0):'Steam Car',(0,1):'Fan Racer',(0,2):'Digger',(0,3):'Night Racer',(0,4):'Bubble Buggy',
 (1,0):'Stompy Steamer',(1,1):'Flap-Bot',(1,2):'Grabby Walker',(1,3):'Robot',(1,4):'Bubble Stomper',
 (2,0):'Steam Boat',(2,1):'Speed Boat',(2,2):'Crab Boat',(2,3):'Lighthouse Boat',(2,4):'Bubble Tug',
 (3,0):'Train',(3,1):'Whirly Train',(3,2):'Crane Train',(3,3):'Night Train',(3,4):'Bubble Express',
 (4,0):'Puff Rocket',(4,1):'Whirly Rocket',(4,2):'Star Grabber',(4,3):'Star Ship',(4,4):'Bubble Blaster'}
CLEAN={(0,0):'steam_car',(0,1):'fan_racer',(0,2):'digger',(0,3):'night_racer',(0,4):'bubble_buggy',
 (1,0):'stompy_steamer',(1,1):'flap_bot',(1,2):'grabby_walker',(1,3):'robot',(1,4):'bubble_stomper',
 (2,0):'steam_boat',(2,1):'speed_boat',(2,2):'crab_boat',(2,3):'lighthouse_boat',(2,4):'bubble_tug',
 (3,0):'train',(3,1):'whirly_train',(3,2):'crane_train',(3,3):'night_train',(3,4):'bubble_express',
 (4,0):'puff_rocket',(4,1):'whirly_rocket',(4,2):'star_grabber',(4,3):'star_ship',(4,4):'bubble_blaster'}
SKIP={'steam_car','steam_boat','train','puff_rocket','grabby_walker'}  # already animated

BASE_MO={'wheels':"happily rolling forward and bobbing gently on its round wheels",
 'legs':"gently stomping and swaying in place on its two robot legs",
 'hull':"gently bobbing and rocking on the water",
 'rails':"slowly chugging along its track with its wheels turning",
 'rocket':"gently wobbling and hovering as its flame flickers at the bottom"}
TOP_MO={'smokestack':"its smokestack chimney puffing small white smoke puffs",
 'propeller':"its propeller spinning gently on top",
 'claw':"its grabber arm slowly swinging",
 'light':"its light softly glowing and pulsing",
 'bubbles':"blowing a few little bubbles that float up"}

def motion(bi,ti):
    return (f"the little toy {NAME[(bi,ti)]} {BASE_MO[BASES[bi]]}, {TOP_MO[TOPS[ti]]}, its eyes stay open "
            f"and steady, no blinking, gentle slow calm subtle motion, sharp crisp clean, plain white background")

def graph(start_name, mo, seed, prefix):
    return {
      "1":{"class_type":"UNETLoader","inputs":{"unet_name":UNET,"weight_dtype":"default"}},
      "2":{"class_type":"CLIPLoader","inputs":{"clip_name":CLIP,"type":"wan"}},
      "3":{"class_type":"VAELoader","inputs":{"vae_name":VAE}},
      "4":{"class_type":"ModelSamplingSD3","inputs":{"shift":8,"model":["1",0]}},
      "5":{"class_type":"CLIPTextEncode","inputs":{"text":mo,"clip":["2",0]}},
      "6":{"class_type":"CLIPTextEncode","inputs":{"text":NEG,"clip":["2",0]}},
      "7":{"class_type":"LoadImage","inputs":{"image":start_name}},
      "8":{"class_type":"Wan22ImageToVideoLatent","inputs":{"vae":["3",0],"width":W,"height":H,"length":LENGTH,"batch_size":1,"start_image":["7",0]}},
      "9":{"class_type":"KSampler","inputs":{"seed":seed,"steps":STEPS,"cfg":5,"sampler_name":"uni_pc","scheduler":"simple","denoise":1.0,"model":["4",0],"positive":["5",0],"negative":["6",0],"latent_image":["8",0]}},
      "10":{"class_type":"VAEDecode","inputs":{"samples":["9",0],"vae":["3",0]}},
      "11":{"class_type":"SaveAnimatedWEBP","inputs":{"images":["10",0],"filename_prefix":prefix,"fps":FPS,"lossless":False,"quality":95,"method":"default"}}}
def get(p): return json.load(urllib.request.urlopen(HOST+p,timeout=30))
def post(g):
    r=urllib.request.Request(HOST+"/prompt",data=json.dumps({"prompt":g}).encode(),headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(r,timeout=30))["prompt_id"]
try: get("/queue")
except Exception as e: sys.exit(f"ComfyUI not reachable: {e}")

todo=[(bi,ti) for bi in range(5) for ti in range(5) if CLEAN[(bi,ti)] not in SKIP]
print(f"[anim-machines] {len(todo)} clips (skipping {len(SKIP)} done), {W}x{H} {LENGTH}f {STEPS}steps {FPS}fps\n",flush=True)
jobs={}
for bi,ti in todo:
    clean=CLEAN[(bi,ti)]; stg=f"animm_{clean}.png"
    shutil.copy(os.path.join(PROJ,"assets/vehicles",clean+".png"), os.path.join(CIN,stg))
    jobs[clean]=post(graph(stg,motion(bi,ti),int(time.time()*1000)&0x7fffffff,f"beepo_workshop/anim_{clean}"))
    print(f"[q] {NAME[(bi,ti)]}",flush=True); time.sleep(0.05)
print(f"\n[anim-machines] polling...",flush=True)
done=set(); t0=time.time()
while len(done)<len(jobs) and time.time()-t0<3600:
    for clean,pid in list(jobs.items()):
        if clean in done: continue
        try: h=get("/history/"+pid)
        except Exception: continue
        if pid in h and h[pid].get("outputs"):
            done.add(clean); print(f"[{len(done)}/{len(jobs)}] {clean}",flush=True)
    time.sleep(3)
print(f"\n[anim-machines] complete {len(done)}/{len(jobs)} in {time.time()-t0:.0f}s",flush=True)
print("DONE")
