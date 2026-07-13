# Reskin scope — wiring the AI art into the game

Goal: replace `index.html`'s inline-SVG art with the rendered stills (`assets/vehicles/`, `assets/beepo/`)
and looping animations (`assets/anim/`).

## The core reality
The game's art is **not decorative** — it's a live procedural **SVG + CSS** system:
- **Modular build**: a machine is composed at runtime from separate parts — `baseSlot` (locomotion) +
  `bodySlot` (a shell that *reshapes per base* via `adaptBody()`/`SHELLS`) + `topSlot` (gadget), plus
  per-combo `FUSION` decoration layers. You see "just the base", then "base + top" as you build.
- **Per-base idle motion** (`move-wheels/legs/hull/rails/rocket` CSS).
- **Elaborate test-drive**: scrolling `#terrain`, drive bounce (`drv-*`), stunts, rocket blast-off +
  parachute home. All CSS.
- **Poke reactions**: poke a part → bubbles emit, smokestack puffs, light flashes, claw grabs (particle
  FX live in a *separate* `#fx`/`#props` layer, not inside the machine SVG).
- **Beepo host**: one SVG with face states (`f-normal/grin/wow`) + hop/cheer/wrench-swing animations.

Our AI art is the opposite: **flat monolithic full-combo sprites** (each whole machine is one image) +
**pre-baked gentle looping WebP**. They can't be assembled part-by-part, recolored, or have parts poked
independently. So this is a **design decision about how much of the live system to keep vs replace**, not
a find-and-replace of `src`.

## Prep required for ANY approach
1. **Transparency / cutouts** — sprites + anim frames are on WHITE; the workshop scene has a colored
   background. Cut them out (rembg `u2net`, same as the Kitchen project) → RGBA. Anim = matte per frame.
   Est. ~1–2 h. (Or present them on white "cards", skipping cutouts.)
2. **Asset loading** — current game is one 127 KB file; the art is ~30–50 MB (25 stills + 25 anims +
   Beepo). Need a preload/lazy-load strategy + keep the SVG as a **fallback** (like the Kitchen reskin did).

## Approaches
### Approach 1 — Hero-swap (recommended first, ~1–2 days)
Reskin the two highest-impact surfaces, keep everything else SVG:
- **Beepo host** → `beepo_idle.webp` loop; swap to `beepo_cheer.webp` on star/trophy; use pose stills
  (`beepo_grin/wow/...`) for reaction beats. Clean, low-risk, big visual lift.
- **Finished machine** → once base+top are both chosen, reveal the combo **sprite** (or its anim loop)
  in place of the composed SVG. Keep SVG for the *in-progress* build (dragging parts in) and the drive.
- Preserves ALL interactivity (build, drive, pokes) because we only swap the "resting" presentation.

### Approach 2 — Full raster (~4–6 days + more art)
Replace the machine entirely with sprites. Costs:
- Rebuild/lose the **part-by-part build reveal** (can't show "just the base" from a full sprite).
- **Poke reactions**: the per-part wiggle is baked into the loop; particle FX (`#fx`) can still fire.
- **Test-drive**: our loops are *gentle idles*, not rocket-blast-off — a dramatic drive needs **new
  "action" clips per machine** (extra generation, ~1 h GPU + curation).
- `FUSION` decoration layers and paint recolor (paint already removed) are dropped.

## Recommendation
Do **Approach 1** first — highest visual ROI, keeps the game's charm and interactivity intact, and
validates the raster look in-game before committing to a bigger rebuild. Sequence:
1. Cutouts (prep). 2. Beepo host swap. 3. Finished-machine sprite/loop reveal + SVG fallback.
4. Playtest. Then decide whether Approach-2 pieces (action drive clips, full machine replacement) are worth it.

## Rough effort
| Piece | Est. |
|---|---|
| Transparency cutouts (rembg) | 1–2 h |
| Beepo host reskin | ~½ day |
| Finished-machine reveal + fallback + loading | ~½–1 day |
| Playtest + polish | ~½ day |
| **Approach 1 total** | **~1–2 days** |
| (Approach 2 add-ons: action clips, full replacement, poke rework) | +3–4 days |
