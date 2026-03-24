"""
Storyboard Visual Engine v7 — Web Edition
Deploy to Railway.app or run locally.
Phone: open browser → use from anywhere.
"""
import os, json, time, threading, shutil, base64
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_file, send_from_directory
from engine import (
    STYLE_PRESETS, CHARACTERS, ENVIRONMENTS, MASTER_SHOT_DETAILS,
    active_preset, image_settings, RESOLUTION_MAP, AR_OPTIONS, MODEL_OPTIONS,
    parse_storyboard, get_asset_type, get_image_prompt, get_section,
    detect_characters, detect_environment, count_words,
    get_world_anchor, get_primary_style, get_secondary_style,
    get_char_base, get_grade_params, get_char_view_prompt, get_env_prompt,
    get_master_shot_prompt, build_prompt,
    get_config, gen_single, gen_chat_section, extract_image,
    post_process, VisualMemoryBank,
    load_config, save_config,
)
import engine

app = Flask(__name__)

# ── STATE ──
state = {
    "panels": [], "noir": [], "fern": [],
    "char_map": {}, "env_map": {}, "used_chars": [], "used_envs": [],
    "warnings": [], "output_dir": None, "memory_bank": None,
    "running": False, "stop": False, "log": [], "progress": 0, "total": 0,
    "storyboard_text": "",
}

def log(msg, tag="info"):
    state["log"].append({"msg": msg, "tag": tag, "ts": time.time()})

def prog(done, total):
    state["progress"] = done
    state["total"] = total

# ── ROUTES ──
@app.route("/")
def index():
    cfg = load_config()
    # API key priority: config file > env var
    saved_key = cfg.get("api_key", "") or os.environ.get("GEMINI_API_KEY", "")
    return render_template("index.html",
        presets=list(STYLE_PRESETS.keys()),
        resolutions=list(RESOLUTION_MAP.keys()),
        ar_options=AR_OPTIONS,
        model_options=list(MODEL_OPTIONS.keys()),
        saved_key=saved_key,
        saved_style=cfg.get("style", list(STYLE_PRESETS.keys())[0]),
        saved_res=cfg.get("resolution", "2K (recommended)"),
        saved_ar=cfg.get("aspect_ratio", "16:9"),
        saved_model=cfg.get("model", "Nano Banana Pro (Best)"),
    )

@app.route("/api/upload", methods=["POST"])
def upload():
    f = request.files.get("storyboard")
    if not f:
        return jsonify(error="No file"), 400

    # Save storyboard
    upload_dir = Path("workspace")
    upload_dir.mkdir(exist_ok=True)
    path = upload_dir / f.filename
    f.save(str(path))

    text = path.read_text(encoding="utf-8")
    panels = parse_storyboard(text)
    if not panels:
        return jsonify(error="No panels found"), 400

    # Setup output dirs
    out = upload_dir / "generated_images"
    for d in ["characters/front", "characters/three_quarter", "characters/action",
              "environments", "master_shots", "scenes", "post_processed", "final"]:
        (out / d).mkdir(parents=True, exist_ok=True)

    state["panels"] = panels
    state["storyboard_text"] = text
    state["output_dir"] = out
    state["memory_bank"] = VisualMemoryBank(out)

    noir = [p for p in panels if get_asset_type(p) == 'noir' and get_image_prompt(p)]
    fern = [p for p in panels if get_asset_type(p) == 'fern' and get_image_prompt(p)]
    state["noir"] = noir
    state["fern"] = fern

    gen = noir + fern
    warnings = []
    char_map = {}; env_map = {}

    for p in gen:
        pid = p['id']
        prompt = get_image_prompt(p)
        vo = p.get('vo', '')
        chars = detect_characters(prompt, vo)
        char_map[pid] = chars
        env_map[pid] = detect_environment(prompt, vo)
        if len(chars) > 1:
            warnings.append(f"{pid}: {len(chars)} chars, using @{chars[0]}")
        if count_words(prompt) > 60:
            warnings.append(f"{pid}: {count_words(prompt)} words (max 60)")
        cold = p.get('co', p.get('coldOpen', 0))
        if cold and get_asset_type(p) != 'noir':
            warnings.append(f"{pid}: Cold open must be Noir")

    state["char_map"] = char_map
    state["env_map"] = env_map
    state["used_chars"] = list(set(c for cs in char_map.values() for c in cs))
    state["used_envs"] = list(set(e for e in env_map.values() if e))
    state["warnings"] = warnings
    state["log"] = []

    # Build sections
    sections = []
    sec_dict = {}
    for p in gen:
        sec = get_section(p)
        if sec not in sec_dict:
            sec_dict[sec] = []
            sections.append(sec)
        sec_dict[sec].append(p)

    # Count done per section
    sec_info = []
    for sec in sections:
        panels_in = sec_dict[sec]
        done = sum(1 for p in panels_in if (out / "scenes" / f"{p.get('f', p['id'])}.png").exists())
        sec_info.append({"name": sec, "total": len(panels_in), "done": done,
                         "noir": sum(1 for p in panels_in if get_asset_type(p)=='noir'),
                         "fern": sum(1 for p in panels_in if get_asset_type(p)=='fern'),
                         })

    return jsonify(
        total=len(panels), noir=len(noir), fern=len(fern),
        chars=len(state["used_chars"]), envs=len(state["used_envs"]),
        gen_count=len(gen), warnings=warnings, sections=sec_info,
    )

@app.route("/api/settings", methods=["POST"])
def settings():
    data = request.json
    if data.get("api_key"):
        save_config({"api_key": data["api_key"]})
    if data.get("style"):
        name = data["style"]
        if name in STYLE_PRESETS:
            engine.active_preset = STYLE_PRESETS[name]
        save_config({"style": name})
    if data.get("resolution"):
        engine.image_settings["resolution"] = data["resolution"]
        save_config({"resolution": data["resolution"]})
    if data.get("aspect_ratio"):
        engine.image_settings["aspect_ratio"] = data["aspect_ratio"]
        save_config({"aspect_ratio": data["aspect_ratio"]})
    if data.get("model"):
        model_label = data["model"]
        if model_label in MODEL_OPTIONS:
            engine.image_settings["model"] = MODEL_OPTIONS[model_label]
        save_config({"model": model_label})
    return jsonify(ok=True)

@app.route("/api/run/<step>", methods=["POST"])
def run_step(step):
    if state["running"]:
        return jsonify(error="Already running"), 409
    data = request.json or {}
    key = data.get("api_key") or load_config().get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not key:
        return jsonify(error="No API key"), 400
    save_config({"api_key": key})

    state["running"] = True
    state["stop"] = False
    state["log"] = []

    if step == "characters":
        threading.Thread(target=run_characters, args=(key,), daemon=True).start()
    elif step == "environments":
        threading.Thread(target=run_environments, args=(key,), daemon=True).start()
    elif step == "master_shots":
        threading.Thread(target=run_master_shots, args=(key,), daemon=True).start()
    elif step == "scenes":
        sec = data.get("section", "__ALL__")
        threading.Thread(target=run_scenes, args=(key, sec), daemon=True).start()
    elif step == "color_grade":
        threading.Thread(target=run_color_grade, daemon=True).start()
    elif step == "export":
        threading.Thread(target=run_export, daemon=True).start()
    else:
        state["running"] = False
        return jsonify(error="Unknown step"), 400

    return jsonify(ok=True)

@app.route("/api/stop", methods=["POST"])
def stop():
    state["stop"] = True
    return jsonify(ok=True)

@app.route("/api/delete_panel", methods=["POST"])
def delete_panel():
    """Delete a single panel image so it can be regenerated."""
    data = request.json or {}
    panel_id = data.get("panel_id")
    if not panel_id or not state["output_dir"]:
        return jsonify(error="No panel ID or no storyboard loaded"), 400

    out = state["output_dir"]
    deleted = []

    # Find and delete matching files in scenes/ and final/
    for folder in ["scenes", "final", "post_processed"]:
        d = out / folder
        if d.exists():
            for f in d.glob(f"*{panel_id}*"):
                f.unlink()
                deleted.append(str(f.name))

    if deleted:
        return jsonify(ok=True, deleted=deleted)
    return jsonify(ok=True, deleted=[], msg="No files found")

@app.route("/api/stream")
def stream():
    """SSE endpoint for real-time log + progress."""
    def gen():
        idx = 0
        while True:
            while idx < len(state["log"]):
                entry = state["log"][idx]
                yield f"data: {json.dumps({'type':'log','msg':entry['msg'],'tag':entry['tag']})}\n\n"
                idx += 1
            yield f"data: {json.dumps({'type':'progress','done':state['progress'],'total':state['total'],'running':state['running']})}\n\n"
            time.sleep(0.5)
    return Response(gen(), mimetype="text/event-stream")

@app.route("/api/images/<path:filename>")
def serve_image(filename):
    if state["output_dir"]:
        return send_from_directory(str(state["output_dir"]), filename)
    return "", 404

@app.route("/api/export_html")
def serve_export():
    path = Path("workspace/storyboard_visual.html")
    if path.exists():
        return send_file(str(path))
    return "Not exported yet", 404

# ── GENERATION WORKERS ──
def get_client(key):
    from google import genai
    
    # Vertex AI Express Mode — uses $300 free credits
    # vertexai=True + api_key, NO project, NO location
    # Routes to global express endpoint, credits apply
    return genai.Client(
        vertexai=True,
        api_key=key,
    )

def run_characters(key):
    try:
        client = get_client(key)
        out = state["output_dir"]
        views = ["front", "three_quarter", "action"]
        chars = sorted(state["used_chars"])
        total = len(chars) * len(views)
        done = 0
        log(f"STEP 1: CHARACTERS ({len(chars)} x 3 = {total})", "head")

        for cid in chars:
            if state["stop"]: break
            for view in views:
                if state["stop"]: break
                done += 1; prog(done, total)
                p = out / "characters" / view / f"@{cid}.png"
                if p.exists():
                    log(f"[SKIP] @{cid} ({view})")
                    continue
                log(f"[GEN] @{cid} ({view})...")
                try:
                    img = gen_single(client, get_char_view_prompt(cid, view))
                    if img: p.write_bytes(img); log(f"OK → @{cid}_{view}", "ok")
                    else: log(f"WARN @{cid}", "warn")
                except Exception as e:
                    log(f"FAIL: {str(e)[:60]}", "fail")
                    if "429" in str(e): time.sleep(30)
                time.sleep(4)
        log("Step 1 done!", "ok")
    finally:
        state["running"] = False

def run_environments(key):
    try:
        client = get_client(key)
        out = state["output_dir"]
        envs = sorted(state["used_envs"])
        total = len(envs)
        log(f"STEP 2: ENVIRONMENTS ({total})", "head")
        for i, eid in enumerate(envs):
            if state["stop"]: break
            prog(i+1, total)
            p = out / "environments" / f"{eid}.png"
            if p.exists(): log(f"[SKIP] {eid}"); continue
            log(f"[GEN] {eid}...")
            try:
                img = gen_single(client, get_env_prompt(eid))
                if img: p.write_bytes(img); log(f"OK → {eid}", "ok")
                else: log(f"WARN {eid}", "warn")
            except Exception as e:
                log(f"FAIL: {str(e)[:60]}", "fail")
                if "429" in str(e): time.sleep(30)
            time.sleep(4)
        log("Step 2 done!", "ok")
    finally:
        state["running"] = False

def run_master_shots(key):
    try:
        client = get_client(key)
        out = state["output_dir"]
        envs = sorted(state["used_envs"])
        total = len(envs)
        log(f"STEP 2b: MASTER SHOTS ({total})", "head")
        for i, eid in enumerate(envs):
            if state["stop"]: break
            prog(i+1, total)
            p = out / "master_shots" / f"{eid}_master.png"
            if p.exists(): log(f"[SKIP] {eid}"); continue
            env_ref = out / "environments" / f"{eid}.png"
            refs = [str(env_ref)] if env_ref.exists() else []
            prompt = get_master_shot_prompt(eid)
            if not prompt: continue
            log(f"[GEN] {eid} MASTER...")
            try:
                img = gen_single(client, prompt, refs)
                if img: p.write_bytes(img); log(f"OK → {eid}_master (L6)", "ok")
                else: log(f"WARN {eid}", "warn")
            except Exception as e:
                log(f"FAIL: {str(e)[:60]}", "fail")
                if "429" in str(e): time.sleep(30)
            time.sleep(4)
        log("Master shots locked!", "ok")
    finally:
        state["running"] = False

def run_scenes(key, section_filter):
    try:
        client = get_client(key)
        out = state["output_dir"]
        mb = state["memory_bank"]
        all_gen = state["noir"] + state["fern"]

        target = all_gen if section_filter == "__ALL__" else [p for p in all_gen if get_section(p) == section_filter]
        label = "ALL" if section_filter == "__ALL__" else section_filter

        # Gather refs
        char_refs = {}
        for cid in CHARACTERS:
            front = out / "characters" / "front" / f"@{cid}.png"
            tq = out / "characters" / "three_quarter" / f"@{cid}.png"
            if front.exists():
                char_refs[cid] = [str(front)]
                if tq.exists(): char_refs[cid].append(str(tq))

        env_refs = {}
        for eid in ENVIRONMENTS:
            master = out / "master_shots" / f"{eid}_master.png"
            basic = out / "environments" / f"{eid}.png"
            if master.exists(): env_refs[eid] = str(master)
            elif basic.exists(): env_refs[eid] = str(basic)

        total = len(target)
        log(f"STEP 3: {label} ({total} panels, L1-L7)", "head")

        # Group by section
        sections = {}
        for p in target:
            sec = get_section(p)
            if sec not in sections: sections[sec] = []
            pid = p['id']; chars = state["char_map"].get(pid, [])
            env_id = state["env_map"].get(pid); asset = get_asset_type(p)
            fname = f"{p.get('f', pid)}.png"
            primary_char = chars[0] if chars else None
            refs = []
            if primary_char and primary_char in char_refs and asset != 'fern':
                refs = mb.get_char_refs(primary_char, char_refs[primary_char][:2])
            if env_id and env_id in env_refs and asset != 'fern' and len(refs) < 6:
                refs.extend(mb.get_env_ref(env_id, env_refs.get(env_id)))
            prompt = build_prompt(p, primary_char, env_id)
            sections[sec].append({
                "id": pid, "prompt": prompt, "refs": refs,
                "output": str(out / "scenes" / fname),
                "info": f"@{primary_char or '-'} {asset}", "char": primary_char, "env": env_id, "stop": False,
            })

        done = 0; ok_n = 0; fail_n = 0

        def cb(event, *args):
            nonlocal done, ok_n, fail_n
            if event == "generating":
                done += 1; prog(done, total)
                log(f"[{done}/{total}] {args[0]} {args[1] if len(args)>1 else ''}")
            elif event == "ok":
                ok_n += 1; pid = args[0]
                log(f"OK → {pid}", "ok")
                if pid in {pd["id"]: pd for sec in sections.values() for pd in sec}:
                    pd = {pd["id"]: pd for sec in sections.values() for pd in sec}[pid]
                    if pd.get("char"): mb.update_char(pd["char"], pd["output"])
                    if pd.get("env"): mb.update_env(pd["env"], pd["output"])
            elif event == "skip":
                done += 1; prog(done, total)
            elif event == "fail":
                fail_n += 1; log(f"FAIL {args[0]}: {args[1] if len(args)>1 else ''}", "fail")
            elif event == "warn":
                fail_n += 1; log(f"WARN {args[0]}", "warn")

        # Stop propagation
        def check_stop():
            while state["running"]:
                time.sleep(1)
                for sp in sections.values():
                    for pd in sp: pd["stop"] = state["stop"]
        threading.Thread(target=check_stop, daemon=True).start()

        for sec_name, sec_panels in sections.items():
            if state["stop"]: break
            log(f"\n--- {sec_name} ({len(sec_panels)} panels) ---", "head")
            gen_chat_section(client, sec_name, sec_panels, callback=cb)

        log(f"DONE! OK:{ok_n} Fail:{fail_n}", "ok")
    finally:
        state["running"] = False

def run_color_grade():
    try:
        out = state["output_dir"]
        src = out / "scenes"; dst = out / "post_processed"
        files = list(src.glob("*.png"))
        total = len(files)
        log(f"STEP 4: COLOR GRADE ({total})", "head")
        for i, f in enumerate(files):
            if state["stop"]: break
            prog(i+1, total)
            try:
                post_process(str(f), str(dst / f.name))
                log(f"OK → {f.name}", "ok")
            except Exception as e:
                log(f"FAIL {f.name}: {str(e)[:60]}", "fail")

        # Auto-finalize
        log("Finalizing → final/", "head")
        final = out / "final"; final.mkdir(exist_ok=True)
        copied = 0
        for p in state["panels"]:
            asset = get_asset_type(p)
            if asset in ('media', 'unknown'): continue
            fname = f"{p.get('f', p['id'])}.png"
            s = dst / fname
            if not s.exists(): s = src / fname
            if not s.exists(): continue
            shutil.copy2(str(s), str(final / fname)); copied += 1
        log(f"{copied} images → final/", "ok")
    finally:
        state["running"] = False

def run_export():
    try:
        out = state["output_dir"]
        final_dir = out / "final"; pp_dir = out / "post_processed"; scenes_dir = out / "scenes"

        def find_img(p):
            fname = f"{p.get('f', p['id'])}.png"
            for d in [final_dir, pp_dir, scenes_dir]:
                if (d / fname).exists(): return d / fname
            return None

        log("STEP 5: EXPORTING", "head")
        sections = []; sec_dict = {}
        for p in state["panels"]:
            sec = get_section(p)
            if sec not in sec_dict: sec_dict[sec] = []; sections.append(sec)
            sec_dict[sec].append(p)

        img_count = sum(1 for p in state["panels"] if find_img(p))
        style_name = load_config().get("style", "Unknown")

        html = f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Visual Production Bible</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Sora:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'DM Sans',sans-serif;background:#07090e;color:#c9d1d9;line-height:1.6}}
.header{{background:#0d1117;padding:24px;border-bottom:1px solid #1c2333;text-align:center}}
.title{{font-family:'Sora',sans-serif;font-size:24px;font-weight:800;background:linear-gradient(135deg,#2dd4bf,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{color:#484f58;font-size:12px;font-family:'JetBrains Mono',monospace;margin-top:4px}}
.section-hdr{{padding:20px;border-bottom:1px solid #1c2333;margin-top:24px;font-family:'Sora',sans-serif;font-size:18px;font-weight:700;color:#f97316}}
.panel{{max-width:900px;margin:16px auto;background:#0d1117;border:1px solid #1c2333;border-radius:12px;overflow:hidden}}
.panel img{{width:100%;display:block;border-bottom:1px solid #1c2333}}
.panel-miss{{width:100%;aspect-ratio:16/9;background:#131820;display:flex;align-items:center;justify-content:center;color:#484f58;border-bottom:1px solid #1c2333}}
.body{{padding:14px 18px}}.badges{{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}}
.b{{padding:2px 8px;border-radius:5px;font-size:10px;font-weight:600;font-family:'JetBrains Mono',monospace}}
.b-id{{background:#1c2333;color:#2dd4bf}}.b-noir{{background:#0f766e33;color:#2dd4bf}}.b-fern{{background:#7c3aed22;color:#a78bfa}}.b-cold{{background:#7f1d1d44;color:#f87171}}
.vo{{background:#131820;border-left:3px solid #2dd4bf;border-radius:6px;padding:10px 14px;margin:8px 0;font-size:13px;color:#e6edf3}}
.meta{{font-size:11px;color:#484f58;margin-top:8px}}.meta span{{color:#8b949e}}
.cam{{background:#0f766e15;border:1px solid #0f766e33;border-radius:6px;padding:8px 12px;margin-top:6px;font-size:11px;color:#2dd4bf}}
</style></head><body>
<div class="header"><div class="title">VISUAL PRODUCTION BIBLE</div>
<div class="sub">v7 · {datetime.now().strftime('%Y-%m-%d %H:%M')} · {style_name} · {len(state["panels"])} panels · {img_count} images</div></div>'''

        for sec in sections:
            html += f'<div class="section-hdr">{sec} ({len(sec_dict[sec])})</div>'
            for p in sec_dict[sec]:
                pid = p.get('id','?'); asset = get_asset_type(p)
                vo = p.get('vo',''); cam = p.get('k','')
                cold = p.get('co', p.get('coldOpen', 0))
                al = {"noir":"Primary","fern":"Secondary"}.get(asset, asset)
                img_path = find_img(p)
                if img_path:
                    b64 = base64.b64encode(img_path.read_bytes()).decode()
                    img_html = f'<img src="data:image/png;base64,{b64}" alt="{pid}">'
                else:
                    img_html = f'<div class="panel-miss">⏳ Not generated</div>'
                html += f'<div class="panel">{img_html}<div class="body"><div class="badges"><span class="b b-id">{pid}</span><span class="b b-{asset}">{al}</span>{"<span class=\'b b-cold\'>COLD OPEN</span>" if cold else ""}</div>'
                if vo: html += f'<div class="vo">🎙 {vo}</div>'
                if cam: html += f'<div class="cam">🎥 {cam}</div>'
                chars = state["char_map"].get(pid, [])
                if chars: html += f'<div class="meta">👤 {", ".join(["@"+c for c in chars])}</div>'
                html += '</div></div>'

        html += '</body></html>'

        path = Path("workspace/storyboard_visual.html")
        path.write_text(html, encoding="utf-8")
        size = path.stat().st_size / 1024 / 1024
        log(f"Exported: {size:.1f} MB", "ok")
    finally:
        state["running"] = False


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
