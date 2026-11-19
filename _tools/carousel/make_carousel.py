"""make_carousel.py spec.json outdir  -> slide-01.png ... (1080x1350, ORONORTE look)"""
import json, sys, os, html
from playwright.sync_api import sync_playwright
spec = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
STAR = '<svg viewBox="0 0 100 100" width="{s}" height="{s}"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9A6E22"/><stop offset=".5" stop-color="#FFF3C4"/><stop offset="1" stop-color="#D9AE4E"/></linearGradient></defs><path d="M50 0 C54 38 62 46 100 50 C62 54 54 62 50 100 C46 62 38 54 0 50 C38 46 46 38 50 0Z" fill="url(#g)"/></svg>'
CSS = """*{margin:0;box-sizing:border-box}body{width:1080px;height:1350px;background:radial-gradient(ellipse at 50% 18%,#1d1608 0%,#0a0906 45%,#050505 100%);font-family:Inter,sans-serif;color:#fff;position:relative;overflow:hidden}
.wrap{position:absolute;inset:110px 96px 150px 96px;display:flex;flex-direction:column;justify-content:center}
.k{color:#D9AE4E;font-size:30px;letter-spacing:.22em;font-weight:700;text-transform:uppercase;margin-bottom:26px}
.t{font-size:92px;line-height:1.02;font-weight:800;letter-spacing:-.025em;white-space:pre-line}
.gold{background:linear-gradient(100deg,#9A6E22,#FFF3C4 45%,#D9AE4E);-webkit-background-clip:text;color:transparent}
.b{margin-top:34px;font-size:38px;line-height:1.38;color:#d8d2c4;white-space:pre-line}
.cards{margin-top:44px;display:flex;flex-direction:column;gap:22px}
.c{border:1.5px solid #5a4318;border-radius:22px;padding:28px 34px;background:linear-gradient(180deg,rgba(217,174,78,.08),rgba(217,174,78,.02))}
.c h3{font-size:40px;font-weight:800;letter-spacing:.04em}.c h3 span{color:#D9AE4E;font-weight:600;font-size:28px;letter-spacing:.14em;margin-left:14px}
.c p{margin-top:10px;font-size:31px;line-height:1.38;color:#cfc8b8}
.foot{position:absolute;left:96px;right:96px;bottom:70px;display:flex;justify-content:space-between;align-items:center;color:#8d846f;font-size:24px;letter-spacing:.2em;font-weight:600}
.foot b{display:flex;align-items:center;gap:14px;color:#cfc8b8}
.star{position:absolute;right:96px;top:96px;opacity:.9}"""
def slide(s, i, n):
    cards = "".join(f'<div class="c"><h3>{html.escape(c["name"])}<span>{html.escape(c.get("role",""))}</span></h3><p>{html.escape(c["text"])}</p></div>' for c in s.get("cards", []))
    t = html.escape(s.get("title","")); 
    if s.get("gold"): t = f'<span class="gold">{t}</span>'
    return f"""<html><head><style>{CSS}</style></head><body><div class="star">{STAR.format(s=64)}</div><div class="wrap">
<div class="k">{html.escape(s.get('kicker',''))}</div><div class="t">{t}</div>{f'<div class="b">{html.escape(s["body"])}</div>' if s.get('body') else ''}<div class="cards">{cards}</div></div>
<div class="foot"><b>{STAR.format(s=26)} ORONORTE</b><span>{i:02d} / {n:02d}</span></div></body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1080,"height":1350})
    for i, s in enumerate(spec["slides"], 1):
        pg.set_content(slide(s, i, len(spec["slides"]))); pg.wait_for_timeout(120)
        pg.screenshot(path=os.path.join(out, f"slide-{i:02d}.png"))
    b.close()
print("ok", len(spec["slides"]))
