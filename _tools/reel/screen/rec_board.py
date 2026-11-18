import asyncio, sys, json, glob, os, shutil
from playwright.async_api import async_playwright
# beats: (seconds, focus key or 'all', caption kicker, caption title)
BEATS = json.loads(open(sys.argv[1]).read())
OUT = sys.argv[2]
LAUNCH = """
(()=>{const now=Date.now()/1000;
const A=(id,name,role,kind,task)=>({id,name,role,kind,rank:0,earned:0,spent:0,profit:0,trophies:0,assignment:task,last_active:now-60,recent:[]});
return {live:false,treasury:20,deposits:20,profit_30d:0,tier:{name:'Starter',daily_transfer_cap:5,approval_above:1},
agents:[A('polaris','POLARIS','Chief Executive Agent','ceo','Set this week\\'s goals and report to the Founder.'),
A('atlas','ATLAS','Chief Strategist','research','Research the market.'),A('vega','VEGA','Builder','build','Build the first offer.'),
A('orion','ORION','Closer','sales','Prepare outreach.'),A('lyra','LYRA','Brand','content','Make the reels.'),
A('nova','NOVA','Trader','trading','Paper trading only.'),A('sirius','SIRIUS','Scout','leads','Find public leads.')],
approvals:[],feed:[],pipeline:[]};})()
"""
CAP_CSS = """
#capx{position:fixed;left:0;right:0;top:0;padding-top:300px!important;padding-bottom:140px!important;background:linear-gradient(#000 0%,rgba(0,0,0,.92) 60%,rgba(0,0,0,0));z-index:99;text-align:left;padding:0 64px;font-family:Inter,sans-serif;pointer-events:none;transition:opacity .35s}
#capx .k{color:#D9AE4E;font-size:30px;letter-spacing:.22em;font-weight:700;text-transform:uppercase;margin-bottom:18px}
#capx .t{color:#fff;font-size:84px;line-height:1.04;font-weight:800;letter-spacing:-.02em;white-space:pre-line;text-shadow:0 4px 30px #000}
#pv{background:#140f05!important;border-color:#7a5a1c!important;color:#F2D27C!important}
.legend,#panel,.ctrl,.controls{display:none!important}
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=swiftshader","--enable-webgl","--ignore-gpu-blocklist"])
        ctx = await b.new_context(viewport={"width":1080,"height":1920}, record_video_dir="vid", record_video_size={"width":1080,"height":1920})
        pg = await ctx.new_page()
        await pg.goto("http://localhost:8765/demo/board.html"+("#es" if "es" in sys.argv[1] else "")); await pg.wait_for_timeout(1500)
        await pg.evaluate(f"render({LAUNCH});fitAll()")
        await pg.add_style_tag(content=CAP_CSS)
        await pg.evaluate("""document.getElementById('pv').textContent=''+(location.hash=='#es'?'DEMO · DÍA 1 · SIN RESULTADOS AÚN':'DEMO · LAUNCH DAY · NO RESULTS YET')+'';
          const d=document.createElement('div');d.id='capx';d.innerHTML='<div class=k></div><div class=t></div>';document.body.appendChild(d);
          document.querySelectorAll('.cb').forEach(e=>e.style.display='none')""")
        await pg.wait_for_timeout(800)
        t0 = await pg.evaluate("performance.now()")
        marks=[]
        for sec,key,k,t in BEATS:
            marks.append((await pg.evaluate("performance.now()")-t0)/1000)
            await pg.evaluate("([k,t])=>{const c=document.getElementById('capx');c.querySelector('.k').textContent=k;c.querySelector('.t').textContent=t}", [k,t])
            if key=='all': await pg.evaluate("closePanel();fitAll()")
            else: await pg.evaluate(f"focusOn('{key}');document.getElementById('panel').classList.remove('open')")
            await pg.wait_for_timeout(int(sec*1000))
        await ctx.close(); await b.close()
        v = sorted(glob.glob("vid/*.webm"), key=os.path.getmtime)[-1]
        shutil.move(v, OUT+".raw.webm")
        json.dump({"lead":0.8,"marks":marks}, open(OUT+".marks.json","w"))
asyncio.run(main())
