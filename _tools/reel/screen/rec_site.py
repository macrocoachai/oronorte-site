import asyncio, base64, json, sys, os
from playwright.async_api import async_playwright
URL=sys.argv[1]; OUT=sys.argv[2]; PLAN=json.loads(sys.argv[3])  # [[action,arg,seconds],...]
async def main():
    os.makedirs(OUT, exist_ok=True); frames=[]
    async with async_playwright() as p:
        b=await p.chromium.launch(args=["--use-gl=swiftshader","--enable-webgl","--ignore-gpu-blocklist"])
        pg=await b.new_page(viewport={"width":540,"height":960},device_scale_factor=2)
        await pg.add_init_script("""(()=>{const f=CanvasRenderingContext2D.prototype.fillText;CanvasRenderingContext2D.prototype.fillText=function(t,...a){t=String(t);if(/\$\s?[\d,]+/.test(t)&&/LEDGER|REGISTRO|LIVRO|ledger/i.test(t))t=t.replace(/\s*·\s*\$[\d,.]+/,'');if(/^(sample data|datos de muestra|dados de exemplo)$/i.test(t.trim()))return;return f.call(this,t,...a)}})()""")
        await pg.goto(URL); await pg.wait_for_timeout(2500)
        cdp=await pg.context.new_cdp_session(pg)
        def on(ev):
            frames.append((ev["metadata"]["timestamp"], ev["data"]))
            asyncio.ensure_future(cdp.send("Page.screencastFrameAck",{"sessionId":ev["sessionId"]}))
        cdp.on("Page.screencastFrame", on)
        await cdp.send("Page.startScreencast",{"format":"jpeg","quality":92,"maxWidth":1080,"maxHeight":1920,"everyNthFrame":1})
        for act,arg,sec in PLAN:
            if act=="hold": await pg.wait_for_timeout(int(sec*1000))
            elif act=="scrollto":
                await pg.evaluate("""([sel,ms])=>new Promise(res=>{const el=document.querySelector(sel);const y0=scrollY,y1=el?el.getBoundingClientRect().top+scrollY-40:y0;const t0=performance.now();
                 function f(t){const k=Math.min(1,(t-t0)/ms);const e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;scrollTo(0,y0+(y1-y0)*e);k<1?requestAnimationFrame(f):res()}requestAnimationFrame(f)})""",[arg,int(sec*1000)])
            elif act=="click":
                await pg.click(arg); await pg.wait_for_timeout(int(sec*1000))
        await cdp.send("Page.stopScreencast"); await b.close()
    t0=frames[0][0]; lines=[]
    for i,(ts,data) in enumerate(frames):
        fn=f"{OUT}/f{i:05d}.jpg"; open(fn,"wb").write(base64.b64decode(data))
        if i: lines.append(f"duration {ts-frames[i-1][0]:.4f}")
        lines.append(f"file '{fn}'")
    lines.append("duration 0.04"); open(f"{OUT}/list.txt","w").write("\n".join(lines)+"\n")
    print(len(frames), frames[-1][0]-t0)
asyncio.run(main())
