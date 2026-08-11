# FOSS 3D Reconstruction Tools for Real Estate Tours

## NoPoSplat — github.com/cvg/NoPoSplat
ICLR 2025 Oral. Feed-forward 3D Gaussian Splats from sparse unposed images.
**Use:** Best option for Zillow's ~20 photos. No camera poses needed.
**GPU:** 8GB+ VRAM
**Output:** .ply file

## Splatt3R — github.com/btsmart/splatt3r
Zero-shot GS from uncalibrated image pairs. 4FPS at 512×512.
**Use:** Even lighter than NoPoSplat. Demo on HF: huggingface.co/spaces/brandonsmart/splatt3r
**GPU:** Consumer

## Nerfstudio/gsplat — github.com/nerfstudio-project/gsplat (12K★)
Full CUDA-accelerated GS training. COLMAP → train → export.
**Use:** Highest quality but needs 100+ photos with poses. Gold standard.
**GPU:** 8GB+ VRAM

## Postshot (Jawset) — jawset.com
Windows desktop app. Drag-drop photos/video → GS.
**Pricing:** All tiers €0/mo (Free/Indie/Studio). Indie = commercial, no watermark, PLY export.
**Use:** Zero-code option for non-technical users. Free commercial license.

## DUSt3R / MASt3R — github.com/naver/dust3r (7K★)
3D reconstruction from image pairs. Backs Splatt3R. No camera info needed.
**Use:** Foundation model for other tools.

## GaussianSplats3D — npm @mkkellogg/gaussian-splats-3d (1.8K★)
Three.js renderer. Embed .ply/.splat files in any website.
**Use:** Embed GS viewer in tour HTML pages. Free, npm-installable.

## antimatter15/splat — github.com/antimatter15/splat (5K★)
Pure WebGL GS viewer. Drag-drop .splat files.
**Use:** Simple embedding for previews.

## Recommended Stack
| Layer | Tool | Cost |
|-------|------|------|
| Photos→3DGS (sparse) | NoPoSplat | Free |
| Photos→3DGS (desktop) | Postshot Indie | €0 |
| Web viewer | GaussianSplats3D npm | Free |
| Camera-flight video | Higgsfield Seedance 2.0 | ~$9/house |
