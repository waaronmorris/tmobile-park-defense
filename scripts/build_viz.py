"""
Assemble the self-contained visualization.

Reads viz/template.html, injects the vendored d3 bundle and a columnar-packed copy of
the analysis JSON, and writes one standalone HTML file. Everything lives in that file --
no stylesheet, no script, no font, no data fetched at runtime -- so it can be dropped on
any static host and works offline.

    build_viz.py                      -> docs/index.html   (GitHub Pages)
    build_viz.py --out <path>         -> anywhere else

Records are packed columnar (one array per field, plus a shared string table) because the
row-of-objects form repeats every key thousands of times and roughly triples the payload.
"""
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "viz" / "data"

# park_grid is deliberately excluded: the page draws the EV/LA heatmap from the league
# grid only, and the per-park copy is ~1 MB of payload nothing reads.
FILES = ["summary", "park_season", "league_grid",
         "league_spray", "league_spray_coarse", "park_spray", "field_map", "carry_spray",
         "outcome_mix", "btype_gap", "spray_dist"]


def pack(records):
    """Rows of dicts -> {cols: {field: [values]}, n: rowcount}, strings deduped."""
    if not records:
        return {"cols": {}, "n": 0}
    fields = list(records[0].keys())
    cols = {}
    for f in fields:
        vals = [r.get(f) for r in records]
        if any(isinstance(v, str) for v in vals):
            uniq = sorted({v for v in vals if isinstance(v, str)})
            idx = {s: i for i, s in enumerate(uniq)}
            cols[f] = {"dict": uniq, "idx": [idx.get(v, -1) for v in vals]}
        else:
            cols[f] = vals
    return {"cols": cols, "n": len(records)}


def main():
    bundle = {}
    for name, key in (("meta", "_meta"), ("precision", "_precision")):
        p = DATA / f"{name}.json"
        if p.exists():
            # Single objects rather than row sets; they bypass the columnar packer.
            bundle[key] = json.loads(p.read_text())
            print(f"  passed through {name}")
    for name in FILES:
        p = DATA / f"{name}.json"
        if not p.exists():
            print(f"  skip {name} (missing)")
            continue
        bundle[name] = pack(json.loads(p.read_text()))
        print(f"  packed {name}: {bundle[name]['n']:,} rows")

    payload = json.dumps(bundle, separators=(",", ":"))
    d3 = (ROOT / "viz" / "vendor" / "d3.min.js").read_text()
    tpl = (ROOT / "viz" / "template.html").read_text()
    body = (tpl.replace("/*__D3__*/", d3)
               .replace('"__DATA__"', payload)
               .replace("/*__FONTS__*/", font_faces()))

    args = sys.argv[1:]
    out = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT / "docs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(wrap_document(body))
    print(f"\nwrote {out} ({out.stat().st_size/1024/1024:.2f} MB)")


SITE_NAV = """
<nav class="sitebar">
  <a class="sitebar-back" href="https://morris-labs.dev/lab/xba-blind-spot">&#8592; Morris Labs</a>
  <span class="sitebar-sep">/</span>
  <span class="sitebar-here">The xBA blind spot</span>
</nav>
"""

SITE_CSS = """
/* The page owns its palette outright -- no ground override here, or the board
   texture would be painted over by the host's colour. */
.sitebar{
  display:flex; align-items:center; gap:11px;
  padding:12px 26px; border-bottom:1px solid var(--rule);
  background:var(--panel); font-family:var(--mono);
  font-size:.64rem; letter-spacing:.18em; text-transform:uppercase;
}
.sitebar-back{ color:var(--led); text-decoration:none }
.sitebar-back:hover{ text-decoration:underline }
.sitebar-sep,.sitebar-here{ color:var(--faint) }
"""


FONTS = [
    ("Oswald", 500, "oswald-latin-500-normal.woff2"),
    ("Oswald", 600, "oswald-latin-600-normal.woff2"),
    ("IBM Plex Mono", 400, "ibm-plex-mono-latin-400-normal.woff2"),
    ("IBM Plex Mono", 600, "ibm-plex-mono-latin-600-normal.woff2"),
    ("IBM Plex Sans", 400, "ibm-plex-sans-latin-400-normal.woff2"),
    ("IBM Plex Sans", 500, "ibm-plex-sans-latin-500-normal.woff2"),
]


def favicon_uri() -> str:
    """
    Inline the site mark as a data URI.

    It used to be pulled from morris-labs.dev, which was the page's only remaining
    network request -- and a cross-domain one now that the app is served from GitHub
    Pages. A root-relative path is not an option either: under a project path it
    resolves against the user page and 404s.
    """
    p = ROOT / "viz" / "favicon.svg"
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:image/svg+xml;base64,{b64}"


def font_faces() -> str:
    """
    Inline the two faces as data URIs.

    The page has to work from a file:// path and from two different hosts, so a
    linked font is not an option -- a silent fallback to a system sans would take
    the condensed scoreboard lettering with it. Latin subsets only, ~64 KB total
    against a megabyte of data.
    """
    out = []
    for family, weight, fname in FONTS:
        p = ROOT / "viz" / "fonts" / fname
        if not p.exists():
            print(f"  WARNING: missing font {fname}; falling back to system stack")
            continue
        b64 = base64.b64encode(p.read_bytes()).decode()
        out.append(
            f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{weight};"
            f"font-display:swap;src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )
    return "\n".join(out)


def wrap_document(body: str) -> str:
    """Wrap the template fragment in a complete HTML document for static hosting."""
    title = re.search(r"<title>(.*?)</title>", body, re.S)
    title_text = title.group(1).strip() if title else "The xBA Blind Spot"
    body = body.replace(title.group(0), "", 1) if title else body

    # Lift the template's <style> into <head> so it is parsed before first paint.
    style = re.search(r"<style>.*?</style>", body, re.S)
    style_text = style.group(0) if style else ""
    body = body.replace(style_text, "", 1) if style else body

    favicon = favicon_uri()
    desc = ("Why T-Mobile Park suppresses offense: xBA is blind to spray angle and carry, "
            "measured across 700,000 Statcast batted balls.")
    return f"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_text} &middot; Morris Labs</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title_text}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<link rel="icon" href="{favicon}">
{style_text}
<style>{SITE_CSS}</style>
</head>
<body>
{SITE_NAV}
{body}
</body>
</html>
"""


if __name__ == "__main__":
    main()
