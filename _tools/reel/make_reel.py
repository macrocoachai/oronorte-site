"""LYRA's Reel maker: brand scenes -> 1080x1920 MP4 with sound placed on the cuts.

Usage:  python make_reel.py spec.json out.mp4 [--music bed.mp3 --music-license license.json]

spec.json:
  {"scenes": [{"kicker": "ORONORTE", "title": "Meet the syndicate", "body": "Seven AI agents...",
               "seconds": 3.2}, ...],
   "end": {"title": "oronorte.com", "body": "Founding price for the first 100 paying members"}}

Sound: Earshot's bank (MIT, rendered from code, no recordings, no network): a whoosh peaking
just after each cut, a soft pop when text lands, a logo sting on the end card. Optional music bed:
only CC0 / public-domain or commercial-use CC-BY audio (see openverse.py), logged in the license
file shipped next to the video. Never NC or ND licenses.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EARSHOT = os.environ.get("EARSHOT_DIR", "/tmp/earshot")
FPS = 30
W, H = 1080, 1920

CSS = """*{margin:0;box-sizing:border-box}html,body{width:1080px;height:1920px;overflow:hidden;background:#050506;
font-family:Inter,system-ui,sans-serif;color:#F1EDE3}
body{background:radial-gradient(ellipse at 50% 38%,#1c170d 0%,#08080a 52%,#030304 100%);position:relative}
i{position:absolute;background:#fff3d0;border-radius:50%}
.metal{background:linear-gradient(135deg,#B8872E 0%,#FFF3C4 32%,#E9C25A 50%,#A97B26 70%,#F7DC86 100%);
-webkit-background-clip:text;background-clip:text;color:transparent}
.wrap{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 96px;gap:34px}
.k{font-weight:700;letter-spacing:.34em;font-size:30px;color:#E9C25A;text-transform:uppercase}
.t{font-weight:800;font-size:104px;line-height:1.02;letter-spacing:-.02em}
.b{font-size:44px;line-height:1.38;color:#D8D1C1;max-width:880px}
.foot{position:absolute;left:96px;right:96px;bottom:150px;display:flex;justify-content:space-between;
font-size:28px;letter-spacing:.28em;color:#A39C8C}
.end .wrap{align-items:center;text-align:center}.end .t{font-size:96px}
.hook .t{font-size:128px;line-height:.98}.hook .b{font-size:48px;color:#F1EDE3}
"""
STAR = ('<svg viewBox="0 0 64 64" style="width:{s}px;height:{s}px"><defs><linearGradient id="g" x1="0" y1="0" x2="1" '
        'y2="1"><stop offset="0" stop-color="#9A6E22"/><stop offset=".35" stop-color="#FFF3C4"/><stop offset=".6" '
        'stop-color="#D9AE4E"/><stop offset="1" stop-color="#F7DC86"/></linearGradient></defs><path d="M32 4 L35.6 '
        '28.4 L58 32 L35.6 35.6 L32 58 L28.4 35.6 L6 32 L28.4 28.4 Z" fill="url(#g)"/></svg>')


def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _stars(seed):
    return "".join(f'<i style="left:{(i*137+seed*31)%100}%;top:{(i*61+seed*17)%100}%;opacity:{.12+((i*29)%55)/100};'
                   f'width:{1+(i%3)}px;height:{1+(i%3)}px"></i>' for i in range(150))


def scene_html(sc, n, total, end=False):
    title = _esc(sc.get("title")).replace("\n", "<br>")
    inner = (f'<div class="wrap">{STAR.format(s=210) if end else ""}'
             f'<div class="k">{_esc(sc.get("kicker", "ORONORTE"))}</div>'
             f'<div class="t {"metal" if end or sc.get("gold") else ""}">{title}</div>'
             f'<div class="b">{_esc(sc.get("body"))}</div></div>')
    foot = '' if end else (f'<div class="foot"><span>ORONORTE</span><span>{n:02d} / {total:02d}</span></div>')
    return (f'<html><head><style>{CSS}</style></head><body class="{"end" if end else ""}">{_stars(n)}'
            f'{inner}{foot}</body></html>').replace('<body class="', '<body class="' + ("hook " if sc.get("hook") else ""), 1)


def render_stills(spec, folder):
    from playwright.sync_api import sync_playwright
    scenes = list(spec["scenes"])
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, sc in enumerate(scenes, 1):
            pg.set_content(scene_html(sc, i, len(scenes)))
            pg.wait_for_timeout(150)
            path = os.path.join(folder, f"s{i:02d}.png"); pg.screenshot(path=path); paths.append(path)
        if spec.get("end"):
            pg.set_content(scene_html(dict({"kicker": "ORONORTE"}, **spec["end"]), 0, 0, end=True))
            pg.wait_for_timeout(150)
            path = os.path.join(folder, "end.png"); pg.screenshot(path=path); paths.append(path)
        b.close()
    return paths


def sfx(sound_id, out, **knobs):
    """Render one Earshot bank sound. Uses the scipy WAV shim when soundfile is not installed."""
    env = dict(os.environ)
    shim = os.path.join(HERE, "shims")
    env["PYTHONPATH"] = os.pathsep.join([EARSHOT, env.get("PYTHONPATH", "")] +
                                        ([] if _has("soundfile") else [shim]))
    args = [sys.executable, "-m", "earshot", "sfx", "render", sound_id, "-o", out]
    for k, v in knobs.items():
        args += [f"--{k}", str(v)]
    r = subprocess.run(args, env=env, capture_output=True, text=True)
    if r.returncode or not os.path.exists(out):
        raise RuntimeError(f"earshot could not render {sound_id}: {r.stderr.strip()[:200]}")
    return out


def _has(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def make(spec, out, music=None, music_license=None, xfade=0.45):
    tmp = tempfile.mkdtemp(prefix="reel_")
    stills = render_stills(spec, tmp)
    durs = [float(s.get("seconds", 3.0)) for s in spec["scenes"]] + ([3.2] if spec.get("end") else [])
    # 1) each still becomes a slow push-in clip
    clips = []
    for i, (img, d) in enumerate(zip(stills, durs)):
        frames = int(round((d + xfade) * FPS))
        clip = os.path.join(tmp, f"c{i:02d}.mp4")
        z = "min(1+0.0009*on,1.08)" if i % 2 == 0 else "max(1.08-0.0009*on,1.0)"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", img, "-vf",
                        f"scale=2160:-1,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:"
                        f"s={W}x{H}:fps={FPS},format=yuv420p", "-frames:v", str(frames), "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "20", clip], check=True)
        clips.append(clip)
    # 2) crossfade them; cut i happens at offset[i]
    # clip i is (d_i + xfade) long; fade i starts at sum(durs[:i]); the visible cut is mid-fade
    filt, last, cuts = [], "[0:v]", []
    for i in range(1, len(clips)):
        off = sum(durs[:i])
        cuts.append(off + xfade / 2)
        lab = f"[v{i}]"
        filt.append(f"{last}[{i}:v]xfade=transition=fade:duration={xfade}:offset={off:.3f}{lab}")
        last = lab
    total = sum(durs) + xfade
    silent = os.path.join(tmp, "video.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", c]
    cmd += (["-filter_complex", ";".join(filt), "-map", last] if filt else ["-map", "0:v"])
    cmd += ["-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", silent]
    subprocess.run(cmd, check=True)
    # 3) sound on the cuts: whoosh peak just after each cut, pop when each text lands, sting on the end card
    events = []
    use_sfx = bool(spec.get("sfx"))  # default off: soft original pad instead of effects
    padded = False
    if not use_sfx and not music:
        music = os.path.join(tmp, "pad.wav"); padded = True
        subprocess.run([sys.executable, os.path.join(HERE, "audio", "pad.py"), music, f"{total:.3f}",
                        str(sum(map(ord, os.path.basename(out))) % 97)], check=True)
    if use_sfx:
        whoosh = sfx("whoosh_fast/crisp", os.path.join(tmp, "whoosh.wav"))
        pop = sfx("ui_pop/soft", os.path.join(tmp, "pop.wav"))
        events.append((pop, 0.35, 0.55))
        for i, c in enumerate(cuts):
            events.append((whoosh, max(0.0, c - 0.12), 0.8))
            if not (spec.get("end") and i == len(cuts) - 1):
                events.append((pop, c + 0.35, 0.5))
        if spec.get("end") and cuts:
            sting = sfx("logo_sting/soft_bloom", os.path.join(tmp, "sting.wav"))
            events.append((sting, cuts[-1] + 0.05, 0.9))
    acmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent]
    parts, n = [], 1
    for f, at, vol in events:
        acmd += ["-i", f]
        ms = int(at * 1000)
        parts.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={vol},adelay={ms}|{ms}[a{n}]")
        n += 1
    if music:
        acmd += ["-i", music]
        parts.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={1.0 if padded else 0.35},"
                     f"afade=t=out:st={max(0, total-1.2):.2f}:d=1.2[a{n}]")
        n += 1
    mix = "".join(f"[a{k}]" for k in range(1, n))
    parts.append(f"{mix}amix=inputs={n-1}:normalize=0,loudnorm=I={-20 if padded else -14}:TP=-1.5:LRA=11[aout]")
    acmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[aout]", "-t", f"{total:.3f}",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out]
    subprocess.run(acmd, check=True)
    # 4) license log next to the video
    log = {"video": os.path.basename(out), "visuals": "ORONORTE original (rendered from code)",
           "sound_effects": "earshot bank (MIT, github.com/Leonxlnx/earshot), rendered from code: "
                            "whoosh_fast/crisp, ui_pop/soft" + (", logo_sting/soft_bloom" if spec.get("end") else ""),
           "music": None}
    if padded:
        log["sound_effects"] = None
        log["music"] = "ORONORTE original ambient pad, synthesized in code (_tools/reel/audio/pad.py)"
    elif music:
        lic = json.load(open(music_license)) if music_license else None
        if not lic or lic.get("license") not in ("cc0", "pdm", "by"):
            raise SystemExit("music needs a license file with license cc0, pdm or by (never nc/nd/sa for brand posts)")
        log["music"] = lic
    json.dump(log, open(os.path.splitext(out)[0] + ".license.json", "w"), indent=2)
    shutil.rmtree(tmp, ignore_errors=True)
    return {"out": out, "seconds": round(total, 2), "cuts": [round(c, 2) for c in cuts], "license": log}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("out")
    ap.add_argument("--music"); ap.add_argument("--music-license")
    a = ap.parse_args()
    print(json.dumps(make(json.load(open(a.spec)), a.out, a.music, a.music_license), indent=2))
