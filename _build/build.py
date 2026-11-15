"""Build the public site: prerender index.html into English (/), Spanish (/es/) and Portuguese (/pt/)
with full SEO heads (title, description, canonical, hreflang, Open Graph, JSON-LD).

Run from the site folder:  python3 _build/build.py
Source of truth: _src/index.html (folders starting with _ are not published by GitHub Pages).
"""
import html
import json
import pathlib
import re

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src" / "index.html"
SITE = "https://oronorte.com"
PATHS = {"en": "/", "es": "/es/", "pt": "/pt/"}
LOCALE = {"en": "en_US", "es": "es_MX", "pt": "pt_BR"}
META = {
    "en": ("AI Agents That Run Your Business 24/7 | ORONORTE",
           "A CEO agent and a team of AI specialists that research, sell and create content for your business 24/7, with every dollar in a live ledger. EN, ES, PT."),
    "es": ("Agentes de IA que trabajan para tu negocio 24/7 | ORONORTE",
           "Un agente CEO y un equipo de especialistas de IA que investigan, venden y crean contenido para tu negocio 24/7, con cada dólar en un libro contable en vivo."),
    "pt": ("Agentes de IA que trabalham para o seu negócio | ORONORTE",
           "Um agente CEO e uma equipe de especialistas em IA que pesquisam, vendem e criam conteúdo para o seu negócio 24/7, com cada dólar num livro-caixa ao vivo."),
}
PRICES = [("Launch", "49"), ("Syndicate", "149"), ("Empire", "399"), ("Performance", "79")]


def head(lang, faqs):
    title, desc = META[lang]
    url = SITE + PATHS[lang]
    alt = "\n".join(f'<link rel="alternate" hreflang="{l}" href="{SITE}{p}">' for l, p in PATHS.items())
    alt += f'\n<link rel="alternate" hreflang="x-default" href="{SITE}/">'
    og_alt = "\n".join(f'<meta property="og:locale:alternate" content="{LOCALE[l]}">' for l in PATHS if l != lang)
    graph = [
        {"@type": "Organization", "@id": SITE + "/#org", "name": "ORONORTE", "url": SITE + "/",
         "logo": SITE + "/icon-256.png", "email": "hello@oronorte.com",
         "founder": {"@type": "Person", "name": "Diego K. Currier"},
         "sameAs": ["https://www.instagram.com/oronorteai/"]},
        {"@type": "WebSite", "@id": SITE + "/#web", "url": SITE + "/", "name": "ORONORTE",
         "inLanguage": ["en", "es", "pt"], "publisher": {"@id": SITE + "/#org"}},
        {"@type": "SoftwareApplication", "name": "ORONORTE", "url": url, "applicationCategory": "BusinessApplication",
         "operatingSystem": "Web, Windows", "inLanguage": lang, "description": desc, "publisher": {"@id": SITE + "/#org"},
         "offers": [{"@type": "Offer", "name": n, "price": p, "priceCurrency": "USD", "url": url + "#pricing"} for n, p in PRICES]},
        {"@type": "FAQPage", "inLanguage": lang, "url": url + "#faq",
         "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
    ]
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")
    e = html.escape
    return f"""<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#04050A">
<link rel="canonical" href="{url}">
{alt}
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/icon-256.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="ORONORTE">
<meta property="og:locale" content="{LOCALE[lang]}">
{og_alt}
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="ORONORTE · Your business, pointed north">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{SITE}/og.jpg">
<script type="application/ld+json">{ld}</script>
"""


def build():
    src = SRC.read_text(encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        for lang, path in PATHS.items():
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            pg.add_init_script(f"window.__LANG = '{lang}';")
            pg.goto(SRC.as_uri())
            pg.wait_for_timeout(600)
            faqs = pg.evaluate("T[lang].faqs")
            body = pg.evaluate("document.body.innerHTML")
            browser_lang = pg.evaluate("document.documentElement.lang")
            assert browser_lang == lang, (browser_lang, lang)
            # keep the source's <body> scripts and markup, but swap in the rendered content so crawlers read real text
            start, end = src.index("<body>") + len("<body>"), src.index("</body>")
            rendered = re.sub(r'class="([^"]*?)\breveal in\b', r'class="\1reveal', body)
            rendered = rendered.replace(' class="line lit"', ' class="line"').replace(' class="line gold lit"', ' class="line gold"')
            rendered = re.sub(r"<script[\s\S]*?</script>", "", rendered)          # scripts are re-added from the source
            scripts = "".join(re.findall(r"<script[\s\S]*?</script>", src[start:end]))
            pin = "" if lang == "en" else f"<script>window.__LANG = '{lang}';</script>\n"
            out = src[:start] + rendered + "\n" + pin + scripts + "\n" + src[end:]
            out = out.replace("<!--SEO-HEAD-->", head(lang, faqs))
            out = re.sub(r'<html lang="[a-z]+"', f'<html lang="{lang}"', out, count=1)
            dest = ROOT / path.strip("/") / "index.html" if path != "/" else ROOT / "index.html"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(out, encoding="utf-8")
            print("built", dest.relative_to(ROOT), len(out))
        b.close()
    urls = []
    for lang, path in PATHS.items():
        links = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE}{p}"/>' for l, p in PATHS.items())
        urls.append(f"<url><loc>{SITE}{path}</loc>{links}<xhtml:link rel=\"alternate\" hreflang=\"x-default\" href=\"{SITE}/\"/><changefreq>weekly</changefreq><priority>1.0</priority></url>")
    for page in ("terms.html", "privacy.html"):
        urls.append(f"<url><loc>{SITE}/{page}</loc><changefreq>yearly</changefreq><priority>0.3</priority></url>")
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                                      'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")


if __name__ == "__main__":
    build()
