#!/usr/bin/env python3
"""
Resume interrupted FLUX generation + assemble video.
Usage:
  python scripts/resume_flux_generation.py --script-json outputs/<slug>/script.json
  python scripts/resume_flux_generation.py --script-json outputs/<slug>/script.json --frames-dir custom/path

Scans the frames directory, compares against script JSON, generates only missing shots,
then assembles the video. No state file needed — reads filesystem for resume point.
"""
import json, os, random, re, subprocess, sys, time, uuid
from pathlib import Path
import requests

COMFY_URL = "http://127.0.0.1:8188"
WF_PATH = Path("workflows/flux_dev_text_to_image.json")  # or flux_text_to_image.json
MODEL = r"flux1-schnell-fp8/AiAF/flux1-schnell-fp8.safetensors"
NEGATIVE = "blurry, low quality, deformed"
WIDTH, HEIGHT, FPS, STEPS = 1920, 1080, 12, 4

def log(m): print(f"[resume] {m}", flush=True)

def load_workflow_template():
    return json.loads(WF_PATH.read_text(encoding="utf-8"))

def walk_replace(obj, pos_prompt, repl):
    """Dict-based template injection — avoids JSON control char issues from string replacement."""
    if isinstance(obj, dict):
        return {k: walk_replace(v, pos_prompt, repl) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [walk_replace(v, pos_prompt, repl) for v in obj]
    elif isinstance(obj, str):
        s = obj
        if "{{POSITIVE_PROMPT}}" in s:
            s = s.replace("{{POSITIVE_PROMPT}}", pos_prompt)
        for k, v in repl.items():
            if k in s:
                s = s.replace(k, v)
        return s
    return obj

def scan_frames(frames_dir, script):
    """Scan frames directory, return set of (scene, shot) tuples that exist."""
    have = set()
    for f in os.listdir(frames_dir):
        m = re.match(r"s(\d+)_kf(\d+)", f)
        if m: have.add((int(m.group(1)), int(m.group(2))))
    need = set()
    for scene in script["scenes"]:
        for j, _ in enumerate(scene["shots"]):
            need.add((scene["index"], j+1))
    missing = sorted(need - have)
    return have, need, missing

def generate_one(wf_template, shot, scene, j, frames_dir, client_id):
    """Generate a single FLUX image via ComfyUI. Returns Path or None."""
    si, kj = scene["index"], j+1
    sn = f"s{si:03d}_kf{kj:02d}"
    fp = shot["prompt"].strip().encode("ascii", "replace").decode("ascii")
    
    replacements = {
        "{{MODEL_NAME}}": MODEL, "{{NEGATIVE_PROMPT}}": NEGATIVE,
        "{{WIDTH}}": str(WIDTH), "{{HEIGHT}}": str(HEIGHT),
        "{{SEED}}": str(random.randint(1, 2147483647)),
        "{{STEPS}}": str(STEPS), "{{CFG}}": "1.0"
    }
    
    wf = json.loads(json.dumps(wf_template))
    wf = walk_replace(wf, fp, replacements)
    
    try:
        resp = requests.post(f"{COMFY_URL}/prompt",
            json={"prompt": wf, "client_id": client_id}, timeout=120)
        if resp.status_code >= 400:
            log(f"  {sn}: ComfyUI {resp.status_code}"); return None
        pid = resp.json().get("prompt_id", "")
    except Exception as e:
        log(f"  {sn}: POST error {e}"); return None
    
    start = time.time(); history = None
    while time.time() - start < 600:
        try:
            hr = requests.get(f"{COMFY_URL}/history/{pid}", timeout=60)
            if hr.status_code == 200 and pid in hr.json():
                history = hr.json()[pid]; break
        except: pass
        time.sleep(1)
    if not history: log(f"  {sn}: timeout"); return None
    
    for node_data in history.get("outputs", {}).values():
        for fd in node_data.get("images", []):
            fn = fd.get("filename", "")
            if not fn: continue
            r = requests.get(f"{COMFY_URL}/view",
                params={"filename": fn, "subfolder": fd.get("subfolder",""), "type": fd.get("type","output")}, timeout=300)
            if r.status_code == 200:
                target = frames_dir / f"{sn}_{fn}"
                target.write_bytes(r.content)
                log(f"  {sn}: OK ({len(r.content)//1024}KB)")
                return target
    log(f"  {sn}: download failed"); return None

def main():
    import argparse
    p = argparse.ArgumentParser(description="Resume interrupted FLUX generation + assembly")
    p.add_argument("--script-json", required=True, help="Path to script.json")
    p.add_argument("--frames-dir", default=None, help="Frames directory (default: <script dir>/frames)")
    args = p.parse_args()
    
    script_path = Path(args.script_json)
    out_dir = script_path.parent
    frames_dir = Path(args.frames_dir) if args.frames_dir else out_dir / "frames"
    audio_file = out_dir / "audio" / "narration_full.wav"
    sv_dir = out_dir / "scene_videos"
    final_dir = out_dir / "final"
    
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    with open(script_path) as f: script = json.load(f)
    
    have, need, missing = scan_frames(frames_dir, script)
    log(f"Found {len(have)} images, {len(missing)} missing")
    
    if missing:
        wf_template = load_workflow_template()
        client_id = str(uuid.uuid4())
        for scene, j, shot in missing:
            generate_one(wf_template, shot, scene, j, frames_dir, client_id)
    
    # Assembly
    log("\n=== Assembly ===")
    audio_dur = 0.0
    if audio_file.exists():
        r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
            "-of","default=noprint_wrappers=1:nokey=1",str(audio_file)],
            capture_output=True,text=True)
        audio_dur = float(r.stdout.strip() or 154.0)
        log(f"Audio: {audio_dur:.1f}s")
    
    have, _, _ = scan_frames(frames_dir, script)
    shot_images = []
    for s_idx, s in enumerate(script["scenes"]):
        for j in range(len(s["shots"])):
            si, kj = s["index"], j+1
            if (si, kj) in have:
                candidates = list(frames_dir.glob(f"s{si:03d}_kf{kj:02d}_*.png"))
                if candidates:
                    shot_images.append((si, j, candidates[0]))
    
    log(f"Total for assembly: {len(shot_images)}/{sum(len(s['shots']) for s in script['scenes'])}")
    
    # Build scene videos
    sv_dir.mkdir(parents=True, exist_ok=True)
    _ts_re = re.compile(r"_(\d{5})_(\d{5})_")
    all_sv = []
    
    for scene in script["scenes"]:
        ss = [s for s in shot_images if s[0] == scene["index"]]
        if not ss: continue
        svs = []
        for si in ss:
            fn = si[2].name
            m = _ts_re.search(fn)
            dur = max(0.5, (int(m.group(2))-int(m.group(1)))/1000.0) if m else max(0.5, audio_dur/max(len(shot_images),1))
            sv_path = sv_dir / f"scene{scene['index']:03d}_shot{si[1]+1:02d}.mp4"
            subprocess.run(["ffmpeg","-y","-loop","1","-i",str(si[2]),
                "-c:v","libx264","-t",str(dur),"-pix_fmt","yuv420p",
                "-vf",f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
                "-r",str(FPS),str(sv_path)], capture_output=True)
            svs.append(sv_path)
        
        # Concat scene shots
        if len(svs) > 1:
            cp = sv_dir / f"scene{scene['index']:03d}.mp4"
            with open(sv_dir / f"list_{scene['index']:03d}.txt","w") as f:
                for s in svs: f.write(f"file '{s.resolve()}'\n")
            subprocess.run(["ffmpeg","-y","-f","concat","-safe","0",
                "-i",str(sv_dir/f"list_{scene['index']:03d}.txt"),"-c","copy",str(cp)], capture_output=True)
            all_sv.append(cp)
        elif svs: all_sv.append(svs[0])
        log(f"  Scene {scene['index']}: {len(svs)} shots")
    
    # Final video
    final_dir.mkdir(parents=True, exist_ok=True)
    name = script.get("title", "video").replace(" ","-").lower()[:50]
    na = final_dir / f"{name}_noaudio.mp4"
    fv = final_dir / f"{name}.final.mp4"
    
    with open(final_dir / "concat.txt","w") as f:
        for s in all_sv: f.write(f"file '{s.resolve()}'\n")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0",
        "-i",str(final_dir/"concat.txt"),"-c","copy",str(na)], capture_output=True)
    subprocess.run(["ffmpeg","-y","-i",str(na),"-i",str(audio_file),
        "-c:v","copy","-c:a","aac","-shortest",str(fv)], capture_output=True)
    
    dur = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(fv)],
        capture_output=True,text=True).stdout.strip()
    log(f"\nVIDEO: {fv}")
    log(f"Duration: {float(dur or 0):.1f}s | {len(shot_images)} images")
    return 0

if __name__ == "__main__":
    sys.exit(main())
