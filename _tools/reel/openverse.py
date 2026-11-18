"""Find and download a music bed from Openverse that is safe for ORONORTE brand posts.

Only CC0 / Public Domain Mark (no credit needed) or CC BY (credit in the caption) audio that
allows commercial use. Never NC (non-commercial), ND (no derivatives) or SA. Openverse itself
says it does not verify licenses, so every pick is logged with its source page for a human check.

  python openverse.py "calm ambient pad" out_dir [--max-seconds 60] [--allow-by]

Writes out_dir/<id>.<ext> and out_dir/<id>.license.json (feed both to make_reel.py).
Needs network access to api.openverse.org and the audio host (works on Diego's laptop; in the
cloud workspace only if those domains are allowed in claude.ai Settings > Capabilities).
"""
import argparse
import json
import os
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1/audio/"
UA = {"User-Agent": "ORONORTE-LYRA/1.0 (+https://oronorte.com)"}


def search(query, allow_by=False, max_seconds=90, page_size=20, opener=urllib.request.urlopen):
    lic = "cc0,pdm" + (",by" if allow_by else "")
    q = urllib.parse.urlencode({"q": query, "license": lic, "license_type": "commercial,modification",
                                "page_size": page_size, "length": "short,medium"})
    data = json.loads(opener(urllib.request.Request(f"{API}?{q}", headers=UA), timeout=20).read())
    out = []
    for r in data.get("results", []):
        license_ = (r.get("license") or "").lower()
        if license_ not in (("cc0", "pdm", "by") if allow_by else ("cc0", "pdm")):
            continue                                       # belt and braces: never NC / ND / SA
        dur = (r.get("duration") or 0) / 1000
        if not r.get("url") or (dur and dur > max_seconds * 4):
            continue
        out.append({"id": r["id"], "title": r.get("title"), "creator": r.get("creator"),
                    "license": license_, "license_version": r.get("license_version"),
                    "license_url": r.get("license_url"), "source_page": r.get("foreign_landing_url"),
                    "provider": r.get("provider"), "url": r["url"], "seconds": dur,
                    "attribution": r.get("attribution")})
    return out


def download(pick, folder, opener=urllib.request.urlopen):
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(urllib.parse.urlparse(pick["url"]).path)[1] or ".mp3"
    path = os.path.join(folder, pick["id"] + ext)
    with opener(urllib.request.Request(pick["url"], headers=UA), timeout=60) as r, open(path, "wb") as f:
        f.write(r.read(25 * 1024 * 1024))                  # 25 MB cap
    lic_path = os.path.join(folder, pick["id"] + ".license.json")
    json.dump(dict(pick, needs_caption_credit=pick["license"] == "by",
                   note="Openverse does not verify licenses: open source_page and confirm before posting."),
              open(lic_path, "w"), indent=2)
    return path, lic_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query"); ap.add_argument("folder")
    ap.add_argument("--max-seconds", type=float, default=60); ap.add_argument("--allow-by", action="store_true")
    a = ap.parse_args()
    picks = search(a.query, a.allow_by, a.max_seconds)
    if not picks:
        raise SystemExit("no CC0 / public-domain audio found for that search; try other words")
    path, lic = download(picks[0], a.folder)
    print(json.dumps({"audio": path, "license_file": lic, "pick": picks[0]}, indent=2))
