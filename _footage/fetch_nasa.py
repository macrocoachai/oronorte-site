"""Fetch public-domain NASA video clips listed in _footage/nasa.txt.
Each clip: first good mp4 for the query, 8 s, cropped 1080x1920, no audio.
NASA media guidelines: no NASA logos/insignia, no implied endorsement; credit "Video: NASA"."""
import json, os, re, subprocess, urllib.request, urllib.parse
OUT = 'media/footage/nasa'; os.makedirs(OUT, exist_ok=True)
log_path = os.path.join(OUT, 'credits.json')
log = json.load(open(log_path)) if os.path.exists(log_path) else {}
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'oronorte-footage'}), timeout=60))
for q in [l.strip() for l in open('_footage/nasa.txt') if l.strip()]:
    slug = re.sub(r'[^a-z0-9]+', '-', q.lower()).strip('-')[:40]
    if slug in log: continue
    try:
        items = get('https://images-api.nasa.gov/search?' + urllib.parse.urlencode({'q': q, 'media_type': 'video'}))['collection']['items']
        for it in items[:8]:
            d = it['data'][0]
            files = get(it['href'])
            mp4 = [f for f in files if f.endswith('~mobile.mp4')] or [f for f in files if f.endswith('~small.mp4')] or [f for f in files if f.endswith('~orig.mp4')]
            if not mp4: continue
            src = mp4[0].replace('http://', 'https://').replace(' ', '%20')
            dst = os.path.join(OUT, slug + '.mp4')
            r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', '3', '-t', '8', '-i', src, '-an',
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst])
            if r.returncode == 0 and os.path.getsize(dst) > 50000:
                log[slug] = {'query': q, 'nasa_id': d.get('nasa_id'), 'title': d.get('title'), 'center': d.get('center'),
                             'source': 'https://images.nasa.gov/details/' + d.get('nasa_id', ''), 'credit': 'Video: NASA'}
                print('ok', slug, d.get('nasa_id')); break
    except Exception as e:
        print('fail', q, e)
json.dump(log, open(log_path, 'w'), indent=1)
