"""
Export small data extracts for the morris-labs write-up.

The blog post renders its charts server-side as inline SVG, so it needs a handful of
numbers rather than the megabyte the interactive application carries. Everything here
is a trimmed view of viz/data/*.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "viz" / "data"
DEST = Path("/Users/waaronmorris/Projects/morris-labs/src/data")

# The contact cell the post is built around: hard enough and high enough that xBA
# treats every one of them as the same batted ball.
EV_BAND, LA_BAND = "95-100", "20-25"


def load(name):
    return json.loads((SRC / f"{name}.json").read_text())


def main():
    DEST.mkdir(parents=True, exist_ok=True)

    spray = sorted(
        (d for d in load("league_spray") if d["ev_band"] == EV_BAND and d["la_band"] == LA_BAND),
        key=lambda d: d["spray_bin"])
    xba_level = sum(d["xba"] * d["n"] for d in spray) / sum(d["n"] for d in spray)
    out_spray = {
        "evBand": EV_BAND, "laBand": LA_BAND,
        "xbaLevel": round(xba_level, 4),
        "totalBalls": sum(d["n"] for d in spray),
        "points": [{"spray": d["spray_bin"], "ba": round(d["ba"], 4),
                    "xba": round(d["xba"], 4), "n": d["n"]} for d in spray],
    }
    (DEST / "xba-spray-gradient.json").write_text(json.dumps(out_spray, indent=1))

    summary = load("summary")
    carry = sorted((d for d in summary if d.get("carry_ft") is not None),
                   key=lambda d: -d["carry_ft"])
    out_carry = {"points": [{"park": d["park"], "name": d["name"],
                             "ft": round(d["carry_ft"], 1), "n": d["n"]} for d in carry]}
    (DEST / "xba-park-carry.json").write_text(json.dumps(out_carry, indent=1))

    sea = next(d for d in summary if d["park"] == "SEA")
    mix = [d for d in load("outcome_mix") if d["park"] == "SEA"]
    order = ["single", "double", "triple", "home_run"]
    out_facts = {
        "seasons": "2021-2026",
        "totalBip": sum(d["bip"] for d in summary),
        "sea": {k: sea[k] for k in
                ("bip", "hits", "xba_sum", "hits_vs_xba", "ba", "xba", "gap", "gap_rel",
                 "gap_z", "adj_gap", "carry_ft", "k_pct", "k_pf", "hits_vs_lg",
                 "hits_vs_lg_per_season")},
        "mix": [{"event": e,
                 "pct": round((next(m for m in mix if m["event"] == e)["ratio"] - 1) * 100, 1),
                 "hits": round((lambda m: (m["rate"] - m["lg_rate"]) * m["n"])
                               (next(m for m in mix if m["event"] == e)))}
                for e in order],
    }
    (DEST / "xba-facts.json").write_text(json.dumps(out_facts, indent=1))

    for f in ("xba-spray-gradient", "xba-park-carry", "xba-facts"):
        p = DEST / f"{f}.json"
        print(f"  wrote {p} ({p.stat().st_size/1024:.1f} KB)")
    print(f"\nspray cell {EV_BAND} mph / {LA_BAND} deg: xBA {xba_level:.3f}, "
          f"BA {min(d['ba'] for d in spray):.3f}–{max(d['ba'] for d in spray):.3f}")


if __name__ == "__main__":
    main()
