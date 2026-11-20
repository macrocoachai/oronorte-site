"""Time board-tour beats to the founder's voice. usage: plan_beats.py spec.json phrases.json out_beats.json
phrases: [[phrase_text, focus, kicker, title], ...] — beats switch when each phrase starts being spoken."""
import json, sys, subprocess, array, math, tempfile
sp = json.load(open(sys.argv[1])); ph = json.load(open(sys.argv[2])); vo = sp['voice']; at = sp.get('at', 0.4); tmp = tempfile.mkdtemp()
subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(vo['ss']),'-t',str(vo['len']),'-i',vo['file'],'-af','highpass=f=80,afftdn=nr=12:nf=-50,loudnorm=I=-16','-ac','1','-ar','16000',f'{tmp}/v.wav'],check=True)
a = array.array('h', subprocess.run(['ffmpeg','-loglevel','error','-i',f'{tmp}/v.wav','-f','s16le','-'],capture_output=True).stdout); st = 1600
lv = [20*math.log10(max(1, math.sqrt(sum(x*x for x in a[i:i+st:4])/(st/4))))-90.3 for i in range(0, len(a)-st, st)]
segs = []; cur = None
for i, x in enumerate(lv):
    t = i*0.1
    if x > -34:
        if cur and t-cur[1] <= 0.35: cur[1] = t+0.1
        else: cur = [t, t+0.1]; segs.append(cur)
S = sum(e-s for s, e in segs)
def clk(x):
    for s, e in segs:
        if x <= e-s: return s+x
        x -= e-s
    return segs[-1][1]
tot = sum(len(p[0]) for p in ph); acc = 0; starts = []
for p in ph: starts.append(clk(acc/tot*S)+at); acc += len(p[0])
end = segs[-1][1]+at+0.6
bounds = [0] + [max(0.1, s-0.15) for s in starts[1:]] + [end]
beats = [[round(bounds[i+1]-bounds[i], 2), p[1], p[2], p[3]] for i, p in enumerate(ph)]
json.dump(beats, open(sys.argv[3], 'w'), ensure_ascii=False); print(sys.argv[3], beats, 'total', round(end, 2))
