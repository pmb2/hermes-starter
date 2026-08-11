# Key Corrections from v5 Development

## User: "Consistent zooms are nauseating"
- **Date**: 2026-06-12
- **Symptom**: Every shot had Ken Burns zoom pan — user reported it as nauseating
- **Fix**: **Static by default, zoom only for emphasis** (`emphasis: true` in script JSON shots)
- **Implementation**: `assemble_v5.py` — static shots use simple `scale+pad` with 0.4s fade-in; emphasis shots use `zoompan` with GSAP-style text overlay
- **Emphasis heuristics**: peak energy = first+last shot, hook = opening shot only, build = occasional, release/transition = never
- **Ratio**: ~20% emphasis, ~80% static

## User: "Too many images, flashing too quickly, no relevance to one another"
- **Date**: 2026-06-12
- **Symptom**: 108 shots at 1.4s each with no visual connection between consecutive images
- **Fix**: **Fewer shots (60 vs 108), longer durations (2.5s vs 1.4s), and img2img evolution** for visual continuity
- **Key insight**: The problem wasn't just pacing — it was that every shot was independently generated from different prompts with no visual relationship to its neighbors
- **Architecture change**: v5 flipbook (shot 1 = text2img, shots 2+ = img2img from previous at denoise 0.6)

## User: "Build everything modularly with easy reversion"
- **Approach**: Git commit before every pipeline stage
- **Implementation**: `run_v5.py` calls `git add -A && git commit -m "v5: stage done" && git push` after each step
- **Revert**: `git log` to find the commit before the bad stage → `git revert <hash>`
- **Resume**: Checkpointed FLUX generation scans frames directory for existing files

## User: "Make a documentation file for the YouTube setup"
- **Result**: `docs/youtube-setup.md` — complete Google Cloud → OAuth → upload flow
- **Key discovery**: Port 8080 is used by Docker, so YouTube OAuth must use port 8081
