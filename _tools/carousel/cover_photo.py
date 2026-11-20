import asyncio, base64, sys
from playwright.async_api import async_playwright
bg = base64.b64encode(open('/tmp/bg-skyscraper-office-night-lights-1.png','rb').read()).decode()
T = {'en': ('Everyone is saying it', 'AI is coming<br>for your job.', 'Small-business data just said <b>the opposite.</b>', 'Swipe →'),
     'es': ('Todos lo dicen', 'La IA viene<br>por tu trabajo.', 'Los datos de pequeños negocios dicen <b>lo contrario.</b>', 'Desliza →')}
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1080,'height':1350})
        for l,(k,h,s,sw) in T.items():
            html = f"""<style>body{{margin:0;width:1080px;height:1350px;font-family:Inter,system-ui,sans-serif;background:#000;overflow:hidden}}
.bg{{position:absolute;inset:0;background:url(data:image/png;base64,{bg}) center 25%/cover;filter:saturate(.9) brightness(1.15) contrast(1.05)}}
.sh{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.15) 0%,rgba(0,0,0,.05) 30%,rgba(0,0,0,.75) 58%,#000 82%)}}
.box{{position:absolute;left:68px;right:60px;bottom:150px}}
.k{{margin-bottom:22px;color:#D9AE4E;font-size:30px;letter-spacing:.3em;font-weight:700;text-transform:uppercase}}
.h{{margin-bottom:34px;font-size:118px;line-height:.98;font-weight:900;letter-spacing:-.035em;text-transform:uppercase;
background:linear-gradient(100deg,#B8862E,#FFF3C4 45%,#D9AE4E);-webkit-background-clip:text;color:transparent}}
.s{{color:#fff;font-size:42px;line-height:1.25;font-weight:500}}
.s b{{color:#FFF3C4}}
.f{{position:absolute;left:72px;right:72px;bottom:56px;display:flex;justify-content:space-between;color:#e8d9b0;font-size:26px;letter-spacing:.28em;font-weight:700}}
.st{{position:absolute;right:64px;top:60px;font-size:48px;color:#FFF3C4}}</style>
<div class=bg></div><div class=sh></div><div class=st>✦</div><div class=box><div class=k>{k}</div><div class=h>{h}</div><div class=s>{s}</div></div><div class=f><span>✦ ORONORTE</span><span>{sw}</span></div>"""
            await pg.set_content(html); await pg.wait_for_timeout(300)
            await pg.screenshot(path=f'media/carousels/2026-11-20-ai-jobs-data-{l}/slide-01.png')
        await b.close()
asyncio.run(main())
