"""Fetch legally reusable B-roll for ORONORTE Reels, run in GitHub Actions (open internet).
NASA: public domain; no NASA logos, no implied endorsement; credit "Video: NASA".
Pexels / Pixabay: free commercial use under their licenses; needs PEXELS_API_KEY / PIXABAY_API_KEY repo secrets.
Each candidate: 8 s from the middle of the source, cropped 1080x1920, muted. Up to 3 candidates per query; a human/AI picks."""
import json, os, re, subprocess, urllib.request, urllib.parse
def get(u, h=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'oronorte-footage', **(h or {})}), timeout=60))
def dur(src):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except: return 0
def cut(src, dst):
    d = dur(src); ss = max(0, d * 0.45 - 4) if d > 12 else 0
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', f'{ss:.1f}', '-t', '8', '-i', src, '-an',
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst])
    return r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 80000
def slug(q): return re.sub(r'[^a-z0-9]+', '-', q.lower()).strip('-')[:40]
def lines(p): return [l.strip() for l in open(p) if l.strip()] if os.path.exists(p) else []
def run(name, queries, finder):
    out = f'media/footage/{name}'; os.makedirs(out, exist_ok=True)
    lp = os.path.join(out, 'credits.json'); log = json.load(open(lp)) if os.path.exists(lp) else {}
    for q in queries:
        s = slug(q)
        if any(k.startswith(s + '-') for k in log): continue
        n = 0
        try:
            for src, meta in finder(q):
                key = f'{s}-{n+1}'
                if cut(src, os.path.join(out, key + '.mp4')):
                    log[key] = dict(meta, query=q); n += 1; print('ok', key)
                if n == 3: break
        except Exception as e: print('fail', name, q, e)
    json.dump(log, open(lp, 'w'), indent=1)
def nasa(q):
    for it in get('https://images-api.nasa.gov/search?' + urllib.parse.urlencode({'q': q, 'media_type': 'video'}))['collection']['items'][:12]:
        d = it['data'][0]; files = get(it['href'])
        mp4 = [f for f in files if f.endswith('~mobile.mp4')] or [f for f in files if f.endswith('~small.mp4')] or [f for f in files if f.endswith('~orig.mp4')]
        if mp4: yield mp4[0].replace('http://', 'https://').replace(' ', '%20'), {'title': d.get('title'), 'source': 'https://images.nasa.gov/details/' + d.get('nasa_id', ''), 'credit': 'Video: NASA', 'license': 'NASA media guidelines (public domain, no endorsement, no insignia)'}
def pexels(q):
    k = os.environ.get('PEXELS_API_KEY')
    if not k: return
    for v in get('https://api.pexels.com/videos/search?' + urllib.parse.urlencode({'query': q, 'orientation': 'portrait', 'per_page': 6}), {'Authorization': k})['videos']:
        f = sorted([f for f in v['video_files'] if f.get('height') and f['height'] >= 1280], key=lambda f: f['height'])
        if f: yield f[0]['link'], {'source': v['url'], 'credit': 'Video: ' + v['user']['name'] + ' on Pexels', 'license': 'Pexels License'}
def pixabay(q):
    k = os.environ.get('PIXABAY_API_KEY')
    if not k: return
    for h in get('https://pixabay.com/api/videos/?' + urllib.parse.urlencode({'key': k, 'q': q, 'per_page': 6}))['hits']:
        f = h['videos'].get('large') or h['videos'].get('medium')
        if f and f.get('url'): yield f['url'], {'source': h['pageURL'], 'credit': 'Video: ' + h['user'] + ' on Pixabay', 'license': 'Pixabay Content License'}
run('nasa', lines('_footage/nasa.txt'), nasa)
run('pexels', lines('_footage/stock.txt'), pexels)
run('pixabay', lines('_footage/stock.txt'), pixabay)
