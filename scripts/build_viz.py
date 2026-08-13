"""
Assemble the self-contained visualization.

Reads viz/template.html, injects the vendored d3 bundle and a columnar-packed copy of
the analysis JSON, and writes viz/index.html. Published artifacts cannot fetch anything
across the network, so everything has to live in the one file.

Records are packed columnar (one array per field, plus a shared string table) because the
row-of-objects form repeats every key thousands of times and roughly triples the payload.
"""
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
         "outcome_mix", "btype_gap"]


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
    body = tpl.replace("/*__D3__*/", d3).replace('"__DATA__"', payload)

    args = sys.argv[1:]
    target = "site" if "--site" in args else "artifact"
    if target == "artifact":
        # The artifact host supplies <!doctype>, <head> and <body> itself, so the
        # template is published exactly as-is.
        out = ROOT / "viz" / "index.html"
    else:
        out = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT / "viz" / "site.html"
        body = wrap_document(body)
        out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(body)
    print(f"\nwrote {out} [{target}] ({out.stat().st_size/1024/1024:.2f} MB)")


SITE_NAV = """
<nav class="sitebar">
  <a class="sitebar-back" href="https://morris-labs.dev/lab/xba-blind-spot">&#8592; Morris Labs</a>
  <span class="sitebar-sep">/</span>
  <span class="sitebar-here">The xBA blind spot</span>
</nav>
"""

SITE_CSS = """
/* Served inside morris-labs, which commits to a single dark ground, so the
   theme-aware palette is pinned dark and the page background is matched to the
   site's ink rather than left to the viewer's OS setting. */
:root{ --ground:#0B1210; }
.sitebar{
  display:flex; align-items:center; gap:10px;
  padding:11px 24px; border-bottom:1px solid var(--rule);
  background:var(--surface); font-family:var(--mono);
  font-size:.7rem; letter-spacing:.11em; text-transform:uppercase;
}
.sitebar-back{ color:var(--accent); text-decoration:none }
.sitebar-back:hover{ text-decoration:underline }
.sitebar-sep,.sitebar-here{ color:var(--ink-3) }
"""


def wrap_document(body: str) -> str:
    """Turn the artifact fragment into a standalone page for static hosting."""
    title = re.search(r"<title>(.*?)</title>", body, re.S)
    title_text = title.group(1).strip() if title else "The xBA Blind Spot"
    body = body.replace(title.group(0), "", 1) if title else body

    # Lift the template's <style> into <head> so it is parsed before first paint.
    style = re.search(r"<style>.*?</style>", body, re.S)
    style_text = style.group(0) if style else ""
    body = body.replace(style_text, "", 1) if style else body

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
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
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
