"""Render a code-drawn canvas animation to MP4 deterministically (frame by frame, piped to ffmpeg; no PNG files).
usage: render_anim.py page.html lang seconds out.mp4 [preview_times]"""
import asyncio, sys, subprocess, os
from playwright.async_api import async_playwright
page, lang, secs, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
prev = [float(x) for x in sys.argv[5].split(',')] if len(sys.argv) > 5 else None
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1080,'height':1920})
        await pg.goto('file://' + os.path.abspath(page)); await pg.evaluate(f"setLang('{lang}')")
        if prev:
            for t in prev:
                await pg.evaluate(f"render({t})"); await pg.screenshot(path=f'/tmp/prev-{lang}-{t}.jpg', type='jpeg', quality=85)
            await b.close(); return
        tmp = out[:-4] + '.part.mp4'
        ff = subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','image2pipe','-framerate','30','-c:v','mjpeg','-i','-','-c:v','libx264','-crf','18','-preset','veryfast','-pix_fmt','yuv420p',tmp], stdin=subprocess.PIPE)
        n = int(secs*30)
        for i in range(n):
            await pg.evaluate(f"render({i/30})")
            ff.stdin.write(await pg.screenshot(type='jpeg', quality=92))
        ff.stdin.close(); ff.wait(); await b.close()
        if ff.returncode == 0: os.replace(tmp, out)
asyncio.run(main())
