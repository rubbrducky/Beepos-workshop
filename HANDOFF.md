# Beepo's Workshop — Handoff

A tiny single-file web game (`index.html`) where kids build silly machines for Beepo the robot,
plus an **AI art pipeline** (ComfyUI + Flux + a Beepo character LoRA + Wan 2.2 video) for reskinning
the game's inline-SVG art with rendered stills and looping animations.

> Status (2026-07-12): game is 100% inline SVG and fully playable. Art pipeline is **proven** —
> a first set of stills + animations exist — but the SVG→raster reskin is **not wired into the game yet**.

---

## Repo layout
```
index.html               The game (single file, no build step, no deps). Just open it.
HANDOFF.md               This file.
art-src/                 Still-image generators (ComfyUI HTTP API drivers)
  gen_workshop_proof.py    Beepo host stills WITH the beepo_flux_v2 LoRA (hard hat + wrench)
  gen_workshop_batch.py    Batch: Beepo poses (LoRA) + full vehicles (no LoRA, house style)
  gen_walker_reroll.py     Legs-base machine re-roll experiment (the "robot legs" saga)
  gen_workshop_anim.py     Older ad-hoc I2V animation driver (superseded by comfyui-anim/)
comfyui-anim/            Canonical animation sandbox (image-to-video)
  animate.py               Self-contained I2V driver, stdlib-only
  prompt.txt               Motion prompt + recipe cheat-sheet
  input/                   Drop start frames here (seeded w/ beepo_builder, grabby_walker)
  output/                  Rendered looping WebPs land here (gitignored)
assets/                  Curated keeper art (the picks so far)
  beepo/                   Beepo host stills (builder, wow, cheer, wave, present)
  vehicles/                The 3 locked vehicles (steam_car, whirly_rocket, grabby_walker)
  anim/                    Looping animations (beepo_working, grabby_walker)
```

## Prerequisites (all already installed on the 5090 PC)
- **ComfyUI** at `C:\Users\gusta\ComfyUI` (v0.26.0 — has native Wan/LTX/Hunyuan video nodes).
  Start: `cd C:\Users\gusta\ComfyUI && venv\Scripts\python.exe main.py --port 8188` (API on :8188).
- **Flux dev fp8**: `models/checkpoints/flux1-dev-fp8.safetensors`.
- **Beepo LoRA**: `beepo_flux_v2.safetensors` — lives in the *Robo Pals* project's `loras/`, which
  ComfyUI sees via `ComfyUI/extra_model_paths.yaml`.
- **Wan 2.2 TI2V-5B** (~17 GB, image-to-video): `models/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors`,
  `models/vae/wan2.2_vae.safetensors`, `models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors`.
- Rendered art currently accumulates in `C:\Users\gusta\ComfyUI\output\beepo_workshop\` (raw, uncurated).
- **GPU-gate**: a separate session sometimes uses the 5090 — check `nvidia-smi` (>5 GB used = busy)
  before big runs.

---

## Art pipeline A — STILLS (Flux dev fp8, 1024², 24 steps, euler/simple, FluxGuidance 3.5, cfg 1.0)

Two kinds, deliberately different:

**Beepo host → USE the LoRA.** `LoraLoader` @ strength **1.3** (model + clip). Trigger word `beepo` +
the full descriptor (LoRA alone with minimal prompts is NOT enough — keep the descriptor):
> `beepo, a cute friendly robot mascot ... mint teal and cream white ... big rounded square head with a
> large glowing teal screen face, huge shiny round black eyes ... antenna with a ball ... control panel
> on its belly, short stubby arms and legs`

**Machines → do NOT use the LoRA** (it would robot-ify them). Flux base + the kawaii house-style suffix
(`VEH_STYLE` in `gen_workshop_batch.py`). They still share Beepo's soft-3D glossy look, so they live in
the same world.

Run: `python art-src/gen_workshop_batch.py` (queues Beepo poses + 3 vehicles, 2 seeds each).

### Prompt-craft learnings (Flux @ cfg 1.0 IGNORES negatives — win everything positively)
- `legs` → Flux renders **wheels**. `robot legs` → fixes legs but overshoots to a **humanoid robot**
  (grows arms, drops the top gadget). Winning phrase = **"a walking [X] machine on two chunky robot
  legs with a [gadget] on top"** + style word **"toy machine"** (not "vehicle" → wheels, not "robot" → humanoid).
- Flux occasionally duplicates the body/face (a Steam Car seed came out two-faced) → just reroll.

---

## Art pipeline B — ANIMATION (Wan 2.2 TI2V-5B, image-to-video)

**Image-to-video, not text-to-video** — animate an existing on-model still so identity is preserved.
Delivery = **looping animated WebP** (`SaveAnimatedWEBP`, native node), which drops into `index.html`
like an image.

Canonical driver = `comfyui-anim/animate.py`. With ComfyUI running:
```
python comfyui-anim/animate.py                       # newest input/ image + prompt.txt
python comfyui-anim/animate.py grabby_walker.png     # a specific start frame
python comfyui-anim/animate.py beepo_builder.png --size 704 --steps 20   # fast draft
python comfyui-anim/animate.py --prompt "spinning its propeller, lifting off"
```
Defaults: 1024², 49 frames (~2 s @ 24 fps), 30 steps. Graph params (official ComfyUI TI2V-5B template):
`ModelSamplingSD3` shift **8**; `KSampler` steps **20–30**, cfg **5**, **uni_pc / simple**, denoise 1.

### Animation learnings
- **Blur fix**: render **1024² + 30 steps** (the 704²/20 draft is fast ~35 s but soft).
- **Green-blink fix**: the 5B model fills closed eyes with the screen colour → add
  "eyes stay open, no blinking" + eye terms in the negative (already baked into `animate.py`).
  The game's SVG already blinks, so we lose nothing.
- Clips are **not seamless loops** yet (end ≠ start). For clean loops: author return-to-rest motion,
  ping-pong the frames, or use `WanFirstLastFrameToVideo` (first = last). Not done.

---

## Current inventory (in `assets/`)
- **Beepo host**: builder (hard hat + wrench), wow, cheer, wave, present — all on-model, consistent.
- **Vehicles (locked)**: Steam Car, Whirly Rocket, Grabby Walker.
- **Animations**: Beepo working (wrench), Grabby Walker (claw swing + leg bob).

## Measured throughput (RTX 5090)
- Still @ 1024² ≈ **~25–30 s** each.
- Animation @ 1024²/30 steps ≈ **~110–165 s** each; @ 704²/20 draft ≈ **~35 s**.

## Open items / next steps
1. Finish the still set: the full **25 machine combos** (5 bases × 5 tops, see `RECIPES` in index.html)
   + the rest of the Beepo reaction set.
2. Animate the "central" moments (remaining vehicles "doing their thing", more Beepo clips).
3. **Seamless loops** for anything that repeats on screen.
4. **Transparency/cutout** (rembg u2net, per the Kitchen project) if sprites need to sit over the scene.
5. **Wire art into the game** — the SVG→raster reskin of `index.html` (scoped like the Kitchen's reskin).
   This is the big remaining piece and has not been started.
