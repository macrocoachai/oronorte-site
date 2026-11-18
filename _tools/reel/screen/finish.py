# finish.py raw.webm marks.json total_beats_seconds out.mp4 [es]
import sys, json, os, subprocess, tempfile
sys.path.insert(0, "/home/claude/site/_tools/reel")
import make_reel as M
raw, marksf, total, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
es = len(sys.argv) > 5
marks = json.load(open(marksf))["marks"]
tmp = tempfile.mkdtemp()
end = {"title": "oronorte.com", "body": ("Precio fundador para los primeros 100 miembros que paguen, fijo mientras sigas suscrito." if es else "Founding price for the first 100 paying members, locked while you stay subscribed.")}
stills = M.render_stills({"scenes": [{"kicker": "x", "title": "x", "body": "", "seconds": 1}], "end": end}, tmp)
endpng = stills[-1]
dur = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",raw]).decode())
ss = max(0, dur - total)
w = M.sfx("whoosh_fast", f"{tmp}/w.wav", **{}) if False else None
def snd(i, k): 
    try: return M.sfx(i, f"{tmp}/{k}.wav")
    except Exception as e: print("sfx", i, e); return None
wh = snd("whoosh_fast/crisp", "w"); pop = snd("ui_pop/soft", "p"); st = snd("logo_sting/soft_bloom", "s")
endlen = 2.6
inputs = ["-ss", f"{ss:.2f}", "-i", raw, "-loop", "1", "-t", str(endlen), "-i", endpng]
filt = [f"[0:v]fps=30,scale=1080:1920,setsar=1,trim=0:{total},setpts=PTS-STARTPTS[a];[1:v]fps=30,scale=1080:1920,setsar=1,format=yuv420p[b];[a]format=yuv420p[a2];[a2][b]xfade=transition=fade:duration=0.4:offset={total-0.4}[v]"]
aud = []; idx = 2
for t in marks[1:]:
    if wh: inputs += ["-i", wh]; aud.append((idx, max(0,t-0.12))); idx += 1
if st: inputs += ["-i", st]; aud.append((idx, total-0.3)); idx += 1
if aud:
    parts = []
    for n,(i,t) in enumerate(aud):
        parts.append(f"[{i}:a]aresample=48000,adelay={int(t*1000)}|{int(t*1000)}[s{n}]")
    filt.append(";".join(parts) + ";" + "".join(f"[s{n}]" for n in range(len(aud))) + f"amix=inputs={len(aud)}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,apad,atrim=0:{total+endlen-0.4}[au]")
cmd = ["ffmpeg","-loglevel","error","-y",*inputs,"-filter_complex",";".join(filt),"-map","[v]"] + (["-map","[au]","-c:a","aac","-ar","48000"] if aud else []) + ["-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",out]
subprocess.check_call(cmd)
json.dump({"video": os.path.basename(out), "visuals": "ORONORTE original: screen recording of oronorte.com/demo/board.html in a launch-day demo state (no real or invented results)", "sound_effects": "earshot bank (MIT, github.com/Leonxlnx/earshot), rendered from code", "music": None}, open(out.replace(".mp4", ".license.json"), "w"), indent=1)
print("ok", out)
