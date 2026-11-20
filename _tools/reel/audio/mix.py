"""Broadcast-style audio for a finished Reel: cleaned founder voice + real music ducked under it + soft transition whooshes.
usage: mix.py spec.json   spec: {"video":..., "out":..., "voice":{"file":..,"ss":..,"len":..,"at":0.3},
                                 "music":"media/music/x.mp3", "music_ss":80, "music_vol":0.55, "cuts":[3.3,5.0,...], "whoosh_vol":0.16}
Targets: -14 LUFS integrated, -1 dBTP (Instagram/TikTok/YouTube Shorts loudness), voice ~8-10 dB above the music bed."""
import json, sys, subprocess, tempfile, random
sp = json.load(open(sys.argv[1])); t = tempfile.mkdtemp()
import os
# RNNoise neural speech denoiser (model: GregorR/rnnoise-models beguiling-drafter); fetched on first use
MODEL = os.path.expanduser('~/models/bd.rnnn')
if not os.path.exists(MODEL):
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    subprocess.run(['curl','-sSfL','-o',MODEL,'https://raw.githubusercontent.com/GregorR/rnnoise-models/master/beguiling-drafter-2018-08-30/bd.rnnn'],check=True)
run = lambda a: subprocess.run(['ffmpeg', '-loglevel', 'error', '-y'] + a, check=True)
dur = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',sp['video']],capture_output=True,text=True).stdout)
ins, fl, labels = [], [], []
if sp.get('voice'):
    v = sp['voice']; at = int(v.get('at', 0.3)*1000)
    run(['-ss', str(v['ss']), '-t', str(v['len']), '-i', v['file'], '-af',
         'aresample=48000,highpass=f=80,arnndn=m=' + MODEL + ':mix=0.85,lowpass=f=15000,'
         'equalizer=f=250:t=q:w=1.0:g=-2.5,equalizer=f=3200:t=q:w=1.4:g=2.5,equalizer=f=10000:t=q:w=1.5:g=1.5,'
         'deesser=i=0.4,acompressor=threshold=-22dB:ratio=3.5:attack=5:release=110:makeup=2,'
         f"afade=t=in:st=0:d=0.04,afade=t=out:st={v['len']-0.25:.2f}:d=0.25,adelay={at}|{at},apad,"
         'loudnorm=I=-16:TP=-2:LRA=7', '-ac', '2', '-ar', '48000', '-t', f'{dur:.2f}', f'{t}/vo.wav'])
    ins += ['-i', f'{t}/vo.wav']; labels.append('vo')
if sp.get('music'):
    import re as _r
    run(['-ss', str(sp.get('music_ss', 0)), '-t', f'{dur:.2f}', '-i', sp['music'], '-af',
         f"acompressor=threshold=-26dB:ratio=4:attack=20:release=300,afade=t=in:st=0:d=0.8,afade=t=out:st={dur-1.6:.2f}:d=1.6", '-ac', '2', '-ar', '48000', f'{t}/mu0.wav'])
    e = subprocess.run(['ffmpeg','-i',f'{t}/mu0.wav','-af','ebur128','-f','null','-'],capture_output=True,text=True).stderr
    mi = float(_r.findall(r'I:\s+(-?[\d.]+) LUFS', e)[-1])
    run(['-i', f'{t}/mu0.wav', '-af', f'volume={-18-mi:.2f}dB', f'{t}/mu.wav'])  # static gain: no pumping
    ins += ['-i', f'{t}/mu.wav']; labels.append('mu')
if sp.get('cuts'):
    # soft original whoosh: filtered noise swell, 0.45 s, placed so its peak lands on each cut
    run(['-f', 'lavfi', '-i', 'anoisesrc=color=pink:duration=0.45:sample_rate=48000', '-af',
         'bandpass=f=1400:width_type=q:w=0.8,afade=t=in:st=0:d=0.32:curve=exp,afade=t=out:st=0.32:d=0.13,volume=0.9', '-ac', '2', f'{t}/wh.wav'])
    parts = []
    for i, c in enumerate(sp['cuts']):
        ins += ['-i', f'{t}/wh.wav']; parts.append((len(ins)//2 - 1, int(max(0, c-0.32)*1000)))
n = len(ins)//2; fc = []; mixin = []
idx = {l: i for i, l in enumerate(labels)}
if 'mu' in idx:
    mv = sp.get('music_vol', 0.32)
    if 'vo' in idx:
        fc.append(f"[{idx['vo']}:a]asplit[vk][vv]")
        fc.append(f"[{idx['mu']}:a]volume={mv}[m0];[m0][vk]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=420:makeup=1[mu]")
        mixin += ['[vv]', '[mu]']
    else:
        fc.append(f"[{idx['mu']}:a]volume={mv}[mu]"); mixin.append('[mu]')
elif 'vo' in idx: mixin.append(f"[{idx['vo']}:a]")
if sp.get('cuts'):
    for k, (i, ms) in enumerate(parts):
        fc.append(f"[{i}:a]adelay={ms}|{ms},volume={sp.get('whoosh_vol',0.10)},apad[w{k}]"); mixin.append(f'[w{k}]')
fc.append(''.join(mixin) + f"amix=inputs={len(mixin)}:duration=first:normalize=0,atrim=0:{dur:.2f},alimiter=limit=0.89:level=false[a]")
# input 0 is the video; shift audio input indices by 1
fc2 = ';'.join(fc)
import re
fc2 = re.sub(r'\[(\d+):a\]', lambda m: f'[{int(m.group(1))+1}:a]', fc2)
run(['-i', sp['video']] + ins + ['-filter_complex', fc2, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', sp['out']])
print(sp['out'], 'ok')
# second pass: land integrated loudness on -14 LUFS without clipping
import re as _re, os as _os
m = subprocess.run(['ffmpeg','-i',sp['out'],'-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True).stderr
I = float(_re.findall(r'I:\s+(-?[\d.]+) LUFS', m)[-1])
g = -14.0 - I
if abs(g) > 0.4:
    tmp2 = sp['out'] + '.tmp.mp4'
    run(['-i', sp['out'], '-c:v', 'copy', '-af', f'volume={g:.2f}dB,alimiter=limit=0.89:level=false', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', tmp2])
    _os.replace(tmp2, sp['out'])
print('loudness adjusted', round(g, 1))
