"""Footage Reel: licensed B-roll + gold ORONORTE type + end card + original pad.
usage: footage_reel.py spec.json out.mp4
spec: {"scenes":[{"clip":"media/footage/nasa/x.mp4","kicker":"...","title":"line1\\nline2","dur":3.0}], "endcard":"media/reels/x.mp4", "credit":"Video: NASA"}"""
import json, sys, subprocess, os, asyncio, tempfile
from playwright.async_api import async_playwright
spec = json.load(open(sys.argv[1])); out = sys.argv[2]; tmp = tempfile.mkdtemp()
CSS = """body{margin:0;width:1080px;height:1920px;background:transparent;font-family:Inter,system-ui,sans-serif}
.s{position:absolute;left:0;right:0;top:0;height:1000px;background:linear-gradient(180deg,rgba(0,0,0,.82) 0%,rgba(0,0,0,.7) 45%,rgba(0,0,0,0) 100%)}
.f{position:absolute;left:0;right:0;bottom:0;height:320px;background:linear-gradient(0deg,rgba(0,0,0,.6),rgba(0,0,0,0))}
.k{position:absolute;left:84px;top:300px;font-size:34px;letter-spacing:.32em;font-weight:700;color:#D9AE4E;text-transform:uppercase}
.t{position:absolute;left:80px;right:80px;top:356px;font-size:104px;line-height:1.02;font-weight:800;color:#fff;text-shadow:0 4px 30px rgba(0,0,0,.6)}
.g{background:linear-gradient(100deg,#9A6E22,#FFF3C4 45%,#D9AE4E);-webkit-background-clip:text;color:transparent}
.c{position:absolute;right:56px;bottom:70px;font-size:24px;color:rgba(255,255,255,.55)}
.sub{position:absolute;left:90px;right:90px;top:1330px;text-align:center}
.sub span{display:inline;font-size:46px;line-height:1.5;font-weight:600;color:#fff;background:rgba(0,0,0,.55);padding:6px 18px;border-radius:10px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.sub i{display:block;font-style:normal;font-size:22px;letter-spacing:.3em;color:#D9AE4E;margin-bottom:14px;font-weight:700}
.b{position:absolute;left:84px;bottom:150px;font-size:30px;letter-spacing:.3em;color:#e8d9b0;font-weight:700}"""
async def render():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1080,'height':1920})
        for i, s in enumerate(spec['scenes']):
            lines = s['title'].split('\n'); last = lines[-1]
            t = '<br>'.join(lines[:-1] + [f'<span class="g">{last}</span>'])
            await pg.set_content(f"<style>{CSS}</style><div class=s></div><div class=f></div><div class=k>{s.get('kicker','')}</div><div class=t>{t}</div>{('<div class=sub><i>'+spec.get('sub_lang','')+'</i><span>'+s['sub']+'</span></div>') if s.get('sub') else ''}<div class=b>✦ ORONORTE</div><div class=c>{spec.get('credit','')}</div>")
            await pg.screenshot(path=f'{tmp}/o{i}.png', omit_background=True)
        await b.close()
asyncio.run(render())
parts = []
for i, s in enumerate(spec['scenes']):
    d = s.get('dur', 3.0); o = f'{tmp}/s{i}.mp4'
    subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(s.get('ss',0)),'-i',s['clip'],'-loop','1','-i',f'{tmp}/o{i}.png','-t',str(d),
        '-filter_complex',f"[0]trim=0:{d},setpts=PTS-STARTPTS,scale=1080:1920,eq=brightness=-0.12:saturation=0.85,colorchannelmixer=rr=1.05:bb=0.9,fade=in:0:8[v];[1]format=rgba,fade=in:st=0.15:d=0.35:alpha=1[t];[v][t]overlay,fps=30,format=yuv420p",
        '-an','-c:v','libx264','-preset','veryfast','-crf','20',o], check=True)
    parts.append(o)
ec = spec['endcard']; d = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',ec],capture_output=True,text=True).stdout)
subprocess.run(['ffmpeg','-loglevel','error','-y','-sseof','-2.8','-i',ec,'-an','-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','20',f'{tmp}/end.mp4'],check=True)
parts.append(f'{tmp}/end.mp4')
open(f'{tmp}/l.txt','w').write(''.join(f"file '{p}'\n" for p in parts))
subprocess.run(['ffmpeg','-loglevel','error','-y','-f','concat','-safe','0','-i',f'{tmp}/l.txt','-c','copy',f'{tmp}/v.mp4'],check=True)
total = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f'{tmp}/v.mp4'],capture_output=True,text=True).stdout)
here = os.path.dirname(os.path.abspath(__file__))
if spec.get('music'):
    ms = spec.get('music_ss', 0)
    subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(ms),'-t',str(total),'-i',spec['music'],'-af',f'afade=t=in:st=0:d=0.6,afade=t=out:st={total-1.4:.2f}:d=1.4,loudnorm=I=-16','-ar','48000',f'{tmp}/p.wav'],check=True)
else:
    subprocess.run(['python3',os.path.join(here,'..','audio','pad.py'),f'{tmp}/p.wav',str(total+0.5),'7'],check=True)
subprocess.run(['ffmpeg','-loglevel','error','-y','-i',f'{tmp}/v.mp4','-i',f'{tmp}/p.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-ar','48000','-shortest',out],check=True)
print(out, round(total,1))
