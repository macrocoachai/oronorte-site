"""Lay the founder's recorded voice over an existing Reel, duck its music, add timed subtitles in the other language.
usage: voice_over.py spec.json
spec: {"video":..., "out":..., "voice":{"file":..., "ss":2.6, "len":13.2}, "at":0.4, "sub_lang":"ESPAÑOL", "subs":["chunk1","chunk2",...], "sub_y":1500}"""
import json, sys, subprocess, tempfile, asyncio, array, math
from playwright.async_api import async_playwright
sp = json.load(open(sys.argv[1])); tmp = tempfile.mkdtemp(); vo = sp['voice']; at = sp.get('at', 0.4)
dur = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',sp['video']],capture_output=True,text=True).stdout)
# 1) clean voice
subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(vo['ss']),'-t',str(vo['len']),'-i',vo['file'],'-af',
  'highpass=f=80,lowpass=f=14000,afftdn=nr=12:nf=-50,equalizer=f=3500:t=q:w=1.2:g=2,acompressor=threshold=-20dB:ratio=3:attack=8:release=120,'
  f"afade=t=in:st=0:d=0.05,afade=t=out:st={vo['len']-0.15:.2f}:d=0.15,loudnorm=I=-16:TP=-1.5",'-ac','1','-ar','16000',f'{tmp}/vc16.wav'],check=True)
# 2) speech segments -> subtitle timing
raw = subprocess.run(['ffmpeg','-loglevel','error','-i',f'{tmp}/vc16.wav','-f','s16le','-'],capture_output=True).stdout
a = array.array('h', raw); st = 1600
lv = [20*math.log10(max(1, math.sqrt(sum(x*x for x in a[i:i+st:4])/(st/4))))-90.3 for i in range(0, len(a)-st, st)]
segs = []; cur = None
for i, x in enumerate(lv):
    t = i*0.1
    if x > -34:
        if cur and t - cur[1] <= 0.35: cur[1] = t+0.1
        else:
            cur = [t, t+0.1]; segs.append(cur)
S = sum(e-s for s, e in segs)
def at_speech(x):  # speech-seconds -> clock
    for s, e in segs:
        if x <= e-s: return s+x
        x -= e-s
    return segs[-1][1]
subs = sp['subs']; tot = sum(len(c) for c in subs); acc = 0; times = []
for c in subs:
    a0 = at_speech(acc/tot*S); acc += len(c); a1 = at_speech(acc/tot*S)
    times.append([a0+at-0.05, a1+at+0.25])
for i in range(len(times)-1): times[i][1] = min(times[i][1], times[i+1][0])
# 3) render subtitle PNGs
CSS = """body{margin:0;width:1080px;height:1920px;background:transparent;font-family:Inter,system-ui,sans-serif}
.sub{position:absolute;left:80px;right:80px;top:%dpx;text-align:center}
.sub span{font-size:48px;line-height:1.5;font-weight:600;color:#fff;background:rgba(0,0,0,.66);padding:6px 18px;border-radius:10px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.sub i{display:block;font-style:normal;font-size:22px;letter-spacing:.3em;color:#D9AE4E;margin-bottom:14px;font-weight:700;text-shadow:0 2px 8px #000}""" % sp.get('sub_y', 1480)
async def render():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1080,'height':1920})
        for i, c in enumerate(subs):
            await pg.set_content(f"<style>{CSS}</style><div class=sub><i>{sp.get('sub_lang','')}</i><span>{c}</span></div>")
            await pg.screenshot(path=f'{tmp}/s{i}.png', omit_background=True)
        await b.close()
asyncio.run(render())
# 4) mix audio: video music ducked under voice
subprocess.run(['ffmpeg','-loglevel','error','-y','-i',f'{tmp}/vc16.wav','-af',f'adelay={int(at*1000)},apad','-ac','2','-ar','48000','-t',str(dur),f'{tmp}/vo.wav'],check=True)
# use the original-quality voice for the mix (re-clean at 48k)
subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(vo['ss']),'-t',str(vo['len']),'-i',vo['file'],'-af',
  'highpass=f=80,lowpass=f=14000,afftdn=nr=12:nf=-50,equalizer=f=3500:t=q:w=1.2:g=2,acompressor=threshold=-20dB:ratio=3:attack=8:release=120,'
  f"afade=t=in:st=0:d=0.05,afade=t=out:st={vo['len']-0.15:.2f}:d=0.15,adelay={int(at*1000)}|{int(at*1000)},apad,loudnorm=I=-16:TP=-1.5",'-ac','2','-ar','48000','-t',str(dur),f'{tmp}/vo.wav'],check=True)
inputs = ['-i', sp['video'], '-i', f'{tmp}/vo.wav'] + sum([['-i', f'{tmp}/s{i}.png'] for i in range(len(subs))], [])
vf = '[0:v]'; chain = []
for i, (s0, s1) in enumerate(times):
    o = f'[v{i}]'; chain.append(f"{vf}[{i+2}:v]overlay=enable='between(t,{s0:.2f},{s1:.2f})'{o}"); vf = o
fc = ';'.join(chain) + f";[0:a]volume=0.4,aformat=channel_layouts=stereo[m];[1:a]asplit[k][v];[m][k]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[d];[d][v]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]"
subprocess.run(['ffmpeg','-loglevel','error','-y',*inputs,'-filter_complex',fc,'-map',vf,'-map','[a]','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000',sp['out']],check=True)
print(sp['out'], [[round(x,1) for x in t] for t in times], 'voice ends', round(at+vo['len'],1), 'video', dur)
