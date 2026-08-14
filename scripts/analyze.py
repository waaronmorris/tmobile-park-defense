"""
Build the analysis tables behind the T-Mobile Park question.

Core idea: Statcast's expected stats are functions of exit velocity and launch angle
ONLY. They are computed at the moment of contact, so they are blind to two things that
decide what the batted ball actually becomes:

  1. WHERE the ball went (spray angle vs. that park's fence distance and defense)
  2. HOW FAR it carried (air density, which happens after contact)

So (BA - xBA) at a park is the residual xBA cannot explain, and we can split that
residual along both axes.

The same residual is computed against xwOBA, which weights each outcome by its run
value instead of scoring every hit alike. That matters here because the hit types a
park removes are not drawn evenly: T-Mobile takes half the league's triples, and a
triple is worth 1.6 in wOBA against a single's 0.9. wOBA - xwOBA therefore prices the
park effect, where BA - xBA only counts it.

Carry residual is the cleanest park-only signal in here: defensive positioning cannot
change how far a ball travels for a given exit velocity and launch angle. If the method
is sound, Coors Field must come out strongly positive.

Outputs JSON into viz/data/ for the d3 front end.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from parks import park_id, park_name, park_short
from stats import wilson, ratio_ci, moe_for_proportion, n_needed, Z95


def add_ba_ci(df, ba="ba", n="n"):
    """Attach a Wilson interval to a table holding a batting average and its count."""
    lo, hi = wilson(df[ba] * df[n], df[n])
    df[ba + "_lo"], df[ba + "_hi"] = lo.round(4), hi.round(4)
    df["moe"] = moe_for_proportion(df[ba], df[n]).round(4)
    return df


# Both metrics are read off the same bins so the page can switch between them, but they
# do not share an error model: batting average is a proportion and takes a Wilson
# interval, while wOBA is a mean of weighted outcomes and takes the ordinary standard
# error. Using Wilson on wOBA would be wrong twice over -- it is not bounded in [0,1],
# and its per-ball variance is not p(1-p).
METRIC_AGG = {
    "n": ("is_hit", "count"), "ba": ("is_hit", "mean"), "xba": ("xba", "mean"),
    "wn": ("woba", "count"), "woba": ("woba", "mean"), "xwoba": ("xwoba", "mean"),
    "wsem": ("woba", "sem"),
}


def add_woba_ci(df):
    """Attach the wOBA margin of error to a table already carrying wsem."""
    df["wmoe"] = (Z95 * df["wsem"]).round(4)
    return df.drop(columns=["wsem"])


def binning_frame(df, scale):
    """
    One frame for every binned chart, carrying both metrics on their own valid rows.

    The two populations differ by sacrifice flies: they have an xwOBA and count in the
    wOBA denominator, but carry no xBA and are not at-bats. Masking is_hit to null
    wherever xBA is null makes a single groupby produce each metric over exactly its own
    rows -- pandas skips nulls per column -- so the bins line up for a toggle without
    either metric borrowing the other's population. n and wn travel separately for the
    same reason.
    """
    df = df.copy()
    df["is_hit"] = df["is_hit"].where(df["xba"].notna())
    # Same masking on the other side: a row outside the wOBA denominator carries a
    # woba_value that must not reach a mean, and null is how the groupby is told to skip it.
    in_woba = (df["woba_denom"] == 1) & df["xwoba"].notna()
    df["woba"] = df["woba"].where(in_woba)
    df["xwoba"] = df["xwoba"].where(in_woba)
    df["gap_row"] = df["is_hit"] - df["xba"]
    df["wgap_row"] = df["woba"] - df["xwoba"]
    df["hc_dist"] = df["hc_r"] * scale
    return df

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "viz" / "data"
OUT.mkdir(parents=True, exist_ok=True)

HITS = {"single", "double", "triple", "home_run"}

# Statcast hit coordinates: home plate sits at (125.42, 198.27), y decreasing toward the outfield.
HOME_X, HOME_Y = 125.42, 198.27

KEEP = ["game_date", "game_year", "home_team", "away_team", "inning_topbot", "events",
        "description", "bb_type", "launch_speed", "launch_angle",
        "estimated_ba_using_speedangle", "estimated_woba_using_speedangle",
        "woba_value", "woba_denom",
        "hc_x", "hc_y", "hit_distance_sc", "batter", "pitcher", "stand", "p_throws", "game_pk"]

# Every event that carries wOBA credit. Outs weigh zero and drop out of the sum, so this
# is the whole of the decomposition below. Weights are read off woba_value rather than
# hardcoded, because the league re-fits them every season.
WOBA_EVENTS = ["single", "double", "triple", "home_run", "field_error", "fielders_choice"]


def load(stream, required=True):
    files = sorted(RAW.glob(f"{stream}/*/*.parquet"))
    frames = []
    for f in files:
        if f.stat().st_size == 0:
            continue
        df = pd.read_parquet(f)
        frames.append(df[[c for c in KEEP if c in df.columns]])
    if not frames:
        if required:
            raise SystemExit(f"no data for stream {stream}")
        return None
    out = pd.concat(frames, ignore_index=True)
    # Overlapping season workers can refetch a chunk; drop exact dupes.
    return out.drop_duplicates()


def prep_bip(df):
    """
    Shared preparation. The two expected-stat comparisons do not run over the same rows,
    so this stops short of choosing a population; ba_population and woba_population cut
    it two ways.
    """
    df = df.copy()
    df["season"] = df["game_year"].astype(int)
    df["park"] = [park_id(t, s) for t, s in zip(df["home_team"], df["season"])]
    df = df[df["events"].notna()]
    df = df[~df["events"].isin(["sac_bunt", "sac_bunt_double_play", "catcher_interf"])]
    df = df[df["launch_speed"].notna() & df["launch_angle"].notna()]

    df["is_hit"] = df["events"].isin(HITS).astype(float)
    df["xba"] = df["estimated_ba_using_speedangle"].astype(float)
    df["xwoba"] = df["estimated_woba_using_speedangle"].astype(float)
    df["woba"] = df["woba_value"].astype(float)
    df["ev"] = df["launch_speed"].astype(float)
    df["la"] = df["launch_angle"].astype(float)
    # Visiting team bats in the top of the inning.
    df["batting_side"] = np.where(df["inning_topbot"] == "Top", "away", "home")

    dx = df["hc_x"] - HOME_X
    dy = HOME_Y - df["hc_y"]
    df["spray"] = np.degrees(np.arctan2(dx, dy))          # negative = left field
    df["hc_r"] = np.sqrt(dx ** 2 + dy ** 2)               # scaled below to feet
    df.loc[(df["spray"].abs() > 50), "spray"] = np.nan    # foul-territory coordinate noise
    return df


def ba_population(df):
    """
    Rows the BA - xBA comparison runs over: at-bats carrying an xBA.

    The denominator lands correctly by itself because Savant assigns no xBA to sacrifice
    flies, so they drop out exactly as they drop out of at-bats, while errors, double
    plays and fielder's choices remain -- correct, since those are at-bats and outs.
    """
    return df[df["xba"].notna()].copy()


def woba_population(df):
    """
    Rows the wOBA - xwOBA comparison runs over, which is NOT the same set.

    wOBA counts sacrifice flies in its denominator and Savant does attach an xwOBA to
    them (100% populated, against 0% for xBA), so they come back in here. Sacrifice
    bunts carry woba_denom 0 and stay out. Selecting on woba_denom == 1 reproduces the
    standard wOBA denominator without restating it.
    """
    return df[(df["woba_denom"] == 1) & df["xwoba"].notna()].copy()


def calibrate_hc_scale(df):
    """
    hc_x/hc_y are in an arbitrary unit; solve for feet per unit.

    Calibrated on balls hit in the air, where hit_distance_sc and the hit coordinate
    describe the same point. The ratio there is nearly constant (inter-quartile spread
    under 1%), which says Statcast derives both from one trajectory model. Ground balls
    are excluded: their coordinate is where a fielder picked the ball up, which has no
    fixed relationship to distance travelled.
    """
    air = df[(df["events"] == "home_run") | (df["bb_type"] == "fly_ball")]
    air = air[air["hit_distance_sc"].notna() & air["hc_r"].notna()]
    air = air[(air["hc_r"] > 40) & (air["launch_angle"] > 20) & (air["hit_distance_sc"] > 200)]
    return float((air["hit_distance_sc"] / air["hc_r"]).median())


def carry_model(df):
    """
    League-expected carry distance for a given (EV, LA), then per-park residual.

    Restricted to balls hit in the air hard enough for air density to matter. Uses the
    median within fine EV/LA cells rather than a fit, so it makes no functional-form
    assumption.
    """
    air = df[df["la"].between(15, 45) & (df["ev"] >= 85) & df["hit_distance_sc"].notna()].copy()
    air["ev_b"] = (air["ev"] // 1) * 1
    air["la_b"] = (air["la"] // 1) * 1

    cell = air.groupby(["ev_b", "la_b"])["hit_distance_sc"].agg(["median", "size"])
    cell = cell[cell["size"] >= 50]["median"].rename("exp_dist")
    air = air.join(cell, on=["ev_b", "la_b"])
    air = air[air["exp_dist"].notna()]
    air["carry_resid"] = air["hit_distance_sc"] - air["exp_dist"]
    # The per-cell reference is a median but parks are scored on the mean, and the
    # within-cell distance distribution is left-skewed, so raw residuals sit below zero
    # everywhere. Re-center on the league mean: carry is only meaningful as a park-vs-park
    # comparison anyway.
    air["carry_resid"] -= air["carry_resid"].mean()

    by_park = air.groupby("park")["carry_resid"].agg(["mean", "size", "sem"]).reset_index()
    by_park.columns = ["park", "carry_ft", "n", "sem"]

    by_park_season = (air.groupby(["park", "season"])["carry_resid"]
                      .agg(["mean", "size"]).reset_index())
    by_park_season.columns = ["park", "season", "carry_ft", "n"]

    # Carry loss is not uniform across the outfield; fences are not equidistant.
    air["spray_b"] = pd.cut(air["spray"], bins=np.arange(-45, 46, 7.5))
    by_spray = (air[air["spray"].notna()].groupby(["park", "spray_b"], observed=True)["carry_resid"]
                .agg(["mean", "size"]).reset_index())
    by_spray.columns = ["park", "spray_b", "carry_ft", "n"]
    by_spray["spray_mid"] = by_spray["spray_b"].apply(lambda b: b.mid).astype(float)
    by_spray = by_spray.drop(columns=["spray_b"])
    return by_park, by_park_season, by_spray, air


def batter_adjusted_gap(df):
    """
    Park gap with the hitter mix divided out.

    Each batted ball carries the batter's own (BA - xBA) rate computed from all his
    OTHER parks, so a park full of hitters who chronically underperform xBA does not
    get charged for it.
    """
    g = df.groupby("batter")[["is_hit", "xba"]].sum()
    g["n"] = df.groupby("batter").size()

    pk = df.groupby(["batter", "park"])[["is_hit", "xba"]].sum()
    pk["n"] = df.groupby(["batter", "park"]).size()

    tot = pk.join(g, rsuffix="_tot")
    # leave-one-park-out baseline for each batter
    out_hit = tot["is_hit_tot"] - tot["is_hit"]
    out_xba = tot["xba_tot"] - tot["xba"]
    out_n = tot["n_tot"] - tot["n"]
    baseline = ((out_hit - out_xba) / out_n.replace(0, np.nan))

    tot["exp_gap"] = baseline * tot["n"]
    res = tot.groupby("park").agg(
        hits=("is_hit", "sum"), xba=("xba", "sum"), n=("n", "sum"),
        exp_gap=("exp_gap", "sum")).reset_index()
    res["raw_gap"] = (res["hits"] - res["xba"]) / res["n"]
    res["adj_gap"] = (res["hits"] - res["xba"] - res["exp_gap"]) / res["n"]
    return res[["park", "raw_gap", "adj_gap", "n"]]


def woba_decomposition(wob):
    """
    Split each park's wOBA shortfall by which outcome went missing.

    mean(wOBA) is a weighted sum of outcome rates, so the ACTUAL side decomposes exactly:

        d mean(wOBA) = SUM over events of (rate_park - rate_league) * weight_event

    Each term is that outcome's contribution in wOBA points, which is the number the hit
    mix chart cannot give: a rate ratio says triples are down by half, but only the
    weighted contribution says what half a park's triples is worth against half its
    singles. xwOBA does not decompose this way -- it is one number per batted ball -- so
    it is carried whole, as the contact-quality baseline the outcome side is read against.
    A park whose xwOBA is level with the league but whose wOBA is not has been changed by
    the building rather than by who batted in it.
    """
    lg_n = len(wob)
    # Weights and league rates are properties of the whole population, so they are taken
    # once rather than rescanned 700,000 rows deep inside the per-park loop.
    weight = wob.groupby("events")["woba"].mean()
    lg_count = wob["events"].value_counts()
    rows = []
    for pid, g in wob.groupby("park"):
        n = len(g)
        counts = g["events"].value_counts()
        for ev in WOBA_EVENTS:
            w = float(weight.get(ev, 0.0))
            k = int(counts.get(ev, 0))
            lg_k = int(lg_count.get(ev, 0))
            rate, lg_rate = k / n, lg_k / lg_n
            rows.append({"park": pid, "event": ev, "weight": round(w, 4),
                         "k": k, "n": n, "rate": rate, "lg_rate": lg_rate,
                         "contrib": (rate - lg_rate) * w,
                         # Interval on the contribution is the interval on the rate
                         # difference, scaled by a weight that is effectively exact.
                         "moe": float(Z95 * w * np.sqrt(rate * (1 - rate) / n))})
    dec = pd.DataFrame(rows)

    # The parts must add back to the whole, or the chart is decorative. Carry both so a
    # reader can see the identity hold rather than take it on faith.
    tot = dec.groupby("park")["contrib"].sum().rename("sum_contrib")
    actual = (wob.groupby("park")["woba"].mean() - wob["woba"].mean()).rename("woba_rel")
    xw = (wob.groupby("park")["xwoba"].mean() - wob["xwoba"].mean()).rename("xwoba_rel")
    check = pd.concat([tot, actual, xw], axis=1).reset_index()
    check["resid"] = check["woba_rel"] - check["sum_contrib"]
    return dec, check


def woba_gap(wob):
    """Per-park and per-season wOBA - xwOBA, against the league rather than zero."""
    wob = wob.assign(wgap=wob["woba"] - wob["xwoba"])
    lg = float(wob["wgap"].mean())
    lg_season = wob.groupby("season")["wgap"].mean().to_dict()

    by = wob.groupby("park").agg(
        woba=("woba", "mean"), xwoba=("xwoba", "mean"),
        wgap=("wgap", "mean"), wgap_sem=("wgap", "sem"), woba_n=("wgap", "size")).reset_index()
    by["wgap_rel"] = by["wgap"] - lg
    by["wgap_z"] = by["wgap_rel"] / by["wgap_sem"]

    ps = wob.groupby(["park", "season"]).agg(
        wgap=("wgap", "mean"), wgap_sem=("wgap", "sem"), woba_n=("wgap", "size")).reset_index()
    ps["wgap_rel"] = ps["wgap"] - ps["season"].map(lg_season)
    ps["wgap_moe"] = (Z95 * ps["wgap_sem"]).round(4)
    return by, ps[["park", "season", "wgap", "wgap_rel", "wgap_moe", "woba_n"]], lg, lg_season


def park_factors(bip, nb):
    """
    Home/road park factors, which is the only honest way to ask the strikeout question.

    Raw strikeout rate at a park mostly measures the roster that plays there 81 times a
    year. Holding personnel fixed instead: take the home club's hitters and compare their
    rate in this building against their rate everywhere else, then do the same for the
    home club's pitchers. Both comparisons follow the same people in and out of the park,
    so what is left is the building.
    """
    frames = []
    for df, kind in ((bip, "bip"), (nb, "nonbip")):
        if df is None or not len(df):
            continue
        d = df[["park", "season", "home_team", "away_team", "inning_topbot", "events"]].copy()
        d["bat_team"] = np.where(d["inning_topbot"] == "Bot", d["home_team"], d["away_team"])
        d["pit_team"] = np.where(d["inning_topbot"] == "Bot", d["away_team"], d["home_team"])
        d["is_k"] = d["events"].isin(["strikeout", "strikeout_double_play"]).astype(float)
        d["is_hit"] = d["events"].isin(HITS).astype(float) if kind == "bip" else 0.0
        d["xba"] = df["xba"].values if kind == "bip" else np.nan
        d["is_bip"] = 1.0 if kind == "bip" else 0.0
        frames.append(d)
    allpa = pd.concat(frames, ignore_index=True)

    # Which club actually called each park home, season by season.
    home_of = (allpa.groupby(["park", "season"])["home_team"]
               .agg(lambda s: s.value_counts().idxmax()).to_dict())

    rows = []
    for (pid, season), team in home_of.items():
        sl = allpa[allpa["season"] == season]
        out = {"park": pid, "season": season, "team": team}
        for role, col in (("bat", "bat_team"), ("pit", "pit_team")):
            home = sl[(sl[col] == team) & (sl["park"] == pid)]
            road = sl[(sl[col] == team) & (sl["park"] != pid)]
            if len(home) < 500 or len(road) < 500:
                continue
            out[f"k_{role}_home"] = float(home["is_k"].mean())
            out[f"k_{role}_road"] = float(road["is_k"].mean())
            out[f"kn_{role}_home"] = int(len(home))
            out[f"kn_{role}_road"] = int(len(road))
            out[f"kk_{role}_home"] = int(home["is_k"].sum())
            out[f"kk_{role}_road"] = int(road["is_k"].sum())
            hb, rb = home[home["is_bip"] == 1], road[road["is_bip"] == 1]
            if len(hb) > 200 and len(rb) > 200:
                out[f"gap_{role}_home"] = float((hb["is_hit"] - hb["xba"]).mean())
                out[f"gap_{role}_road"] = float((rb["is_hit"] - rb["xba"]).mean())
        rows.append(out)

    pf = pd.DataFrame(rows)
    agg = pf.groupby("park").mean(numeric_only=True).reset_index().drop(columns=["season"])
    # Strikeouts as a ratio (1.05 = 5% more strikeouts than the same people manage elsewhere),
    # hit suppression as a difference in BA points.
    for role in ("bat", "pit"):
        agg[f"kpf_{role}"] = agg[f"k_{role}_home"] / agg[f"k_{role}_road"]
        agg[f"gapdiff_{role}"] = agg[f"gap_{role}_home"] - agg[f"gap_{role}_road"]
    agg["k_pf"] = agg[["kpf_bat", "kpf_pit"]].mean(axis=1)
    agg["gap_pf"] = agg[["gapdiff_bat", "gapdiff_pit"]].mean(axis=1)

    # Interval on the strikeout factor. Each role gives an independent home/road ratio;
    # averaging two independent estimates halves the variance, hence the /4 on the sum.
    # Seasons were summed before this point, so the counts are the whole span.
    count_cols = [c for c in pf.columns if c.startswith(("kn_", "kk_"))]
    tot = pf.groupby("park")[count_cols].sum()
    # agg holds the per-season MEAN of every numeric column, counts included; those
    # averages are meaningless and would collide with the summed totals on merge.
    agg = agg.drop(columns=[c for c in count_cols if c in agg.columns]).merge(
        tot, on="park", how="left")
    var = np.zeros(len(agg))
    have = np.zeros(len(agg))
    for role in ("bat", "pit"):
        kh, nh = agg[f"kk_{role}_home"], agg[f"kn_{role}_home"]
        kr, nr = agg[f"kk_{role}_road"], agg[f"kn_{role}_road"]
        ph, pr = kh / nh, kr / nr
        with np.errstate(divide="ignore", invalid="ignore"):
            v = (1 - ph) / (nh * ph) + (1 - pr) / (nr * pr)
        v = np.where(np.isfinite(v), v, np.nan)
        var = var + np.nan_to_num(v)
        have = have + np.isfinite(v).astype(float)
    # Var(mean of k independent estimates) = sum(Var_i) / k^2. The two roles are built
    # from disjoint plate appearances -- the home club's hitters bat in one half-inning,
    # its pitchers work the other -- so treating them as independent is fair.
    se_log = np.sqrt(np.where(have > 0, var / np.maximum(have, 1) ** 2, np.nan))
    agg["k_pf_lo"] = (agg["k_pf"] * np.exp(-Z95 * se_log)).round(4)
    agg["k_pf_hi"] = (agg["k_pf"] * np.exp(Z95 * se_log)).round(4)
    agg["k_pa"] = agg[["kn_bat_home", "kn_pit_home"]].sum(axis=1)
    return agg[["park", "k_pf", "kpf_bat", "kpf_pit", "k_pf_lo", "k_pf_hi", "k_pa",
                "gap_pf", "gapdiff_bat", "gapdiff_pit"]]


def main():
    print("loading balls in play...")
    allbip = prep_bip(load("bip"))
    bip = ba_population(allbip)
    wob = woba_population(allbip)
    print(f"  {len(bip):,} batted balls, {bip['season'].min()}-{bip['season'].max()}")
    print(f"  {len(wob):,} of them in the wOBA denominator "
          f"({len(wob) - len(bip):+,} vs the xBA set — sacrifice flies)")

    scale = calibrate_hc_scale(bip)
    bip["hc_dist"] = bip["hc_r"] * scale
    print(f"  hit-coordinate scale: {scale:.3f} ft/unit")

    print("loading strikeouts/walks...")
    nb = load("nonbip", required=False)
    if nb is None:
        print("  WARNING: nonbip stream not downloaded yet; K rates will be null")
        nb = pd.DataFrame(columns=["park", "events", "batting_side"])
    else:
        nb["season"] = nb["game_year"].astype(int)
        nb["park"] = [park_id(t, s) for t, s in zip(nb["home_team"], nb["season"])]
        nb["batting_side"] = np.where(nb["inning_topbot"] == "Top", "away", "home")
        print(f"  {len(nb):,} non-BIP plate appearances")

    # ---------- per-park summary ----------
    rows = []
    for pid, g in bip.groupby("park"):
        nbp = nb[nb["park"] == pid]
        k = int((nbp["events"].isin(["strikeout", "strikeout_double_play"])).sum())
        pa = len(g) + len(nbp)
        vis = g[g["batting_side"] == "away"]
        nbv = nbp[nbp["batting_side"] == "away"]
        k_v = int((nbv["events"].isin(["strikeout", "strikeout_double_play"])).sum())
        pa_v = len(vis) + len(nbv)
        rows.append({
            "park": pid, "name": park_name(pid), "short": park_short(pid), "bip": len(g), "pa": pa,
            # Raw totals, so the rate can always be traced back to the counts behind it.
            "hits": int(g["is_hit"].sum()), "xba_sum": float(g["xba"].sum()),
            "hits_vs_xba": float(g["is_hit"].sum() - g["xba"].sum()),
            "ba": float(g["is_hit"].mean()), "xba": float(g["xba"].mean()),
            "gap": float(g["is_hit"].mean() - g["xba"].mean()),
            "k_pct": k / pa if pa else None,
            "ba_vis": float(vis["is_hit"].mean()), "xba_vis": float(vis["xba"].mean()),
            "gap_vis": float(vis["is_hit"].mean() - vis["xba"].mean()),
            "k_pct_vis": k_v / pa_v if pa_v else None,
            "mean_ev": float(g["ev"].mean()), "mean_la": float(g["la"].mean()),
        })
    summary = pd.DataFrame(rows)

    print("carry model...")
    carry, carry_season, carry_spray, air = carry_model(bip)
    carry = carry.rename(columns={"n": "carry_n", "sem": "carry_sem"})
    carry["carry_moe"] = (Z95 * carry["carry_sem"]).round(2)
    summary = summary.merge(carry, on="park", how="left")

    print("batter-adjusted gap...")
    summary = summary.merge(batter_adjusted_gap(bip), on="park", how="left", suffixes=("", "_x"))

    print("home/road park factors...")
    summary = summary.merge(park_factors(bip, nb if len(nb) else None), on="park", how="left")

    print("wOBA - xwOBA...")
    wgap, wgap_season, lg_wgap, lg_wgap_season = woba_gap(wob)
    summary = summary.merge(wgap, on="park", how="left")
    wdecomp, wcheck = woba_decomposition(wob)
    summary = summary.merge(wcheck[["park", "woba_rel", "xwoba_rel"]], on="park", how="left")
    print(f"  league wOBA-xwOBA = {lg_wgap:+.4f}; decomposition residual max "
          f"{wcheck['resid'].abs().max():.5f}")

    # xBA is not calibrated to be unbiased on this exact population -- across every park
    # the league sits a few points ABOVE its own expected mark, and that offset drifts
    # year to year. Zero is therefore the wrong reference line; the league is. Everything
    # user-facing is reported against it, with a standard error so noise is visible.
    bip["gap_row"] = bip["is_hit"] - bip["xba"]
    lg_gap = float(bip["gap_row"].mean())
    lg_gap_season = bip.groupby("season")["gap_row"].mean().to_dict()
    se = bip.groupby("park")["gap_row"].agg(["sem", "size"]).rename(columns={"sem": "gap_sem"})
    summary = summary.merge(se[["gap_sem"]], on="park", how="left")
    summary["gap_rel"] = summary["gap"] - lg_gap
    summary["gap_z"] = summary["gap_rel"] / summary["gap_sem"]

    # The same measurement as a count rather than a rate: hits - SUM(xBA), net of the
    # league's own offset. The rate is what ranks parks fairly, since they differ in how
    # many balls they see; the count is what makes the size of the effect legible.
    summary["hits_vs_lg"] = summary["gap_rel"] * summary["bip"]
    seasons_per_park = bip.groupby("park")["season"].nunique().rename("seasons")
    summary = summary.merge(seasons_per_park, on="park", how="left")
    summary["hits_vs_lg_per_season"] = summary["hits_vs_lg"] / summary["seasons"]
    print(f"  league BA-xBA = {lg_gap:+.4f} (this, not zero, is neutral)")

    # ---------- per-park per-season ----------
    ps = bip.groupby(["park", "season"]).agg(
        bip=("is_hit", "size"), ba=("is_hit", "mean"), xba=("xba", "mean")).reset_index()
    ps["gap"] = ps["ba"] - ps["xba"]
    ps["lg_gap"] = ps["season"].map(lg_gap_season)
    ps["gap_rel"] = ps["gap"] - ps["lg_gap"]
    # A single season is a sixth of the span, so these bars need their error shown or
    # season-to-season wobble reads as a trend.
    ps_sem = bip.groupby(["park", "season"])["gap_row"].sem().rename("gap_sem").reset_index()
    ps = ps.merge(ps_sem, on=["park", "season"], how="left")
    ps["gap_moe"] = (Z95 * ps["gap_sem"]).round(4)
    ps = ps.merge(carry_season, on=["park", "season"], how="left")
    ps = ps.merge(wgap_season, on=["park", "season"], how="left")

    # ---------- EV/LA grid: the model surface, and each park's actual ----------
    # From here down every table carries both metrics on the same bins, so the page can
    # switch xBA <-> xwOBA without changing which balls it is looking at.
    binf = binning_frame(allbip, scale)
    binf["ev_bin"] = (binf["ev"] // 2.5) * 2.5
    binf["la_bin"] = (binf["la"] // 2.5) * 2.5
    grid = binf[binf["ev"].between(40, 120) & binf["la"].between(-30, 60)]
    lg_grid = grid.groupby(["ev_bin", "la_bin"]).agg(**METRIC_AGG).reset_index()
    lg_grid = lg_grid.drop(columns=["wsem"])
    pk_grid = grid.groupby(["park", "ev_bin", "la_bin"]).agg(**METRIC_AGG).reset_index()
    pk_grid = pk_grid[pk_grid["n"] >= 15].drop(columns=["wsem"])

    # ---------- the point of the whole exercise ----------
    # One xBA value hides a big spray-angle gradient. Within EV/LA cells, show how the
    # real hit probability moves with WHERE the ball was hit, league-wide and per park.
    sp = grid[grid["spray"].notna()].copy()
    sp["spray_bin"] = (sp["spray"] // 5) * 5
    # coarse contact-quality buckets so cells stay populated
    sp["ev_band"] = pd.cut(sp["ev"], [0, 80, 90, 95, 100, 105, 200],
                           labels=["<80", "80-90", "90-95", "95-100", "100-105", "105+"])
    sp["la_band"] = pd.cut(sp["la"], [-90, 0, 10, 20, 25, 30, 40, 90],
                           labels=["<0", "0-10", "10-20", "20-25", "25-30", "30-40", "40+"])
    # Median landing distance travels with each bin. Inside a narrow speed/angle cell the
    # distance is close to determined by physics, so this lets the same numbers be drawn
    # on field geometry rather than on an abstract axis.
    lg_spray = (sp.groupby(["ev_band", "la_band", "spray_bin"], observed=True)
                .agg(**METRIC_AGG, dist=("hc_dist", "median")).reset_index())
    lg_spray = add_woba_ci(add_ba_ci(lg_spray[lg_spray["n"] >= 30].copy()))
    lg_spray["dist"] = lg_spray["dist"].round(1)
    # A single park holds ~1/30th of the league's contact, so the per-park curve needs
    # wider bins. Widen the SPRAY bins only, and keep the exact same contact bands as the
    # league curve it is plotted against.
    #
    # Widening the contact bands instead is what the first version did, and it was wrong:
    # a park binned over 90-100 mph / 10-25 degrees was being drawn against a league line
    # binned over 90-95 / 10-20, which is a systematically weaker population. That put
    # every one of the thirty-two parks below the league line by construction. Spray-bin
    # width carries no such bias, because it does not change the average contact quality
    # inside the cell.
    sp["spray_c"] = (sp["spray"] // 7.5) * 7.5
    pk_spray = (sp.groupby(["park", "ev_band", "la_band", "spray_c"], observed=True)
                .agg(**METRIC_AGG, dist=("hc_dist", "median")).reset_index())
    pk_spray = add_woba_ci(add_ba_ci(pk_spray[pk_spray["n"] >= 15].copy()))
    pk_spray["dist"] = pk_spray["dist"].round(1)
    # League on the park's own spray binning, for a like-for-like reference line.
    lg_spray_c = (sp.groupby(["ev_band", "la_band", "spray_c"], observed=True)
                  .agg(**METRIC_AGG, dist=("hc_dist", "median")).reset_index())
    lg_spray_c = add_woba_ci(add_ba_ci(lg_spray_c[lg_spray_c["n"] >= 30].copy()))
    lg_spray_c["dist"] = lg_spray_c["dist"].round(1)

    # ---------- how the thirty parks spread at each spray angle ----------
    # The league mean line answers "what happens on average". It cannot answer "is this
    # park unusual", because a park sitting under the mean may still be entirely ordinary.
    # These are the percentiles ACROSS parks in each bin, so the band is the league's own
    # distribution and its asymmetry about the median is the skew, drawn rather than
    # asserted.
    # Both metrics get their own percentile band. The spread across parks is the whole
    # point of the strip, and it is not the same shape on the two scales: wOBA separates
    # the parks further down the lines, where the hit that goes missing is an extra-base
    # hit rather than a single.
    dist_rows = []
    for (evb, lab, spc), g in pk_spray.groupby(["ev_band", "la_band", "spray_c"], observed=True):
        if len(g) < 12:            # too few parks clear the per-bin floor to describe a spread
            continue
        row = {"ev_band": evb, "la_band": lab, "spray_c": spc, "parks": int(len(g))}
        for col, pre in (("ba", ""), ("woba", "w")):
            q = g[col].quantile([0.10, 0.25, 0.50, 0.75, 0.90])
            for p in (10, 25, 50, 75, 90):
                row[f"{pre}p{p}"] = round(float(q[p / 100]), 4)
        dist_rows.append(row)
    spray_dist = pd.DataFrame(dist_rows)
    if len(spray_dist):
        # Positive = the upper half of the parks is more spread out than the lower half.
        for pre in ("", "w"):
            spray_dist[pre + "skew"] = (
                (spray_dist[pre + "p90"] - spray_dist[pre + "p50"])
                - (spray_dist[pre + "p50"] - spray_dist[pre + "p10"])).round(4)

    # ---------- field map: gap by landing location ----------
    fm = binf[binf["spray"].notna() & binf["hc_dist"].notna()]
    fm = fm.assign(sb=(fm["spray"] // 4) * 4, db=(fm["hc_dist"] // 20) * 20)
    fmap = (fm.groupby(["park", "sb", "db"])
            .agg(**METRIC_AGG, gap_sem=("gap_row", "sem"),
                 wgap_sem=("wgap_row", "sem")).reset_index())
    # These are the thinnest cells anywhere in the project -- a single park, a 4-degree
    # wedge, a 20-foot ring. The floor is raised to 25 and the residual standard error
    # travels with each cell so the map can fade what it cannot support.
    fmap = fmap[fmap["n"] >= 25].drop(columns=["wsem"])
    fmap["gap_sem"] = fmap["gap_sem"].round(4)
    fmap["wgap_sem"] = fmap["wgap_sem"].round(4)

    # ---------- outcome mix ----------
    # Which hit types a park actually removes. A park that shortens fly balls but has short
    # fences can leave home runs untouched while quietly deleting doubles and triples.
    mix_rows = []
    lg_n = int(len(bip))
    for ev in ["single", "double", "triple", "home_run"]:
        lg_k = int((bip["events"] == ev).sum())
        lg_rate = lg_k / lg_n
        for pid, g in bip.groupby("park"):
            k = int((g["events"] == ev).sum())
            mix_rows.append({"park": pid, "event": ev, "k": k, "rate": k / len(g),
                             "lg_rate": lg_rate, "ratio": (k / len(g)) / lg_rate if lg_rate else None,
                             "n": int(len(g)), "lg_k": lg_k, "lg_n": lg_n})
    mix = pd.DataFrame(mix_rows)
    # Ratio of two proportions: skewed, so the interval is built on the log and comes
    # back asymmetric. Triples are the case that needs it -- a rare event over a rare
    # event, where a symmetric interval would be visibly wrong.
    r, rlo, rhi = ratio_ci(mix["k"], mix["n"], mix["lg_k"], mix["lg_n"])
    mix["ratio_lo"], mix["ratio_hi"] = rlo.round(4), rhi.round(4)
    mix["pct_lo"] = ((rlo - 1) * 100).round(1)
    mix["pct_hi"] = ((rhi - 1) * 100).round(1)

    # Same question by batted-ball type: a carry effect should bite on air balls, not grounders.
    bt_rows = []
    for bt in ["ground_ball", "line_drive", "fly_ball", "popup"]:
        lgm = float(bip[bip["bb_type"] == bt]["gap_row"].mean())
        for pid, g in bip[bip["bb_type"] == bt].groupby("park"):
            sem = float(g["gap_row"].sem())
            bt_rows.append({"park": pid, "bb_type": bt, "gap": float(g["gap_row"].mean()),
                            "lg_gap": lgm, "rel": float(g["gap_row"].mean()) - lgm,
                            "n": int(len(g)), "sem": round(sem, 5),
                            "moe": round(Z95 * sem, 4)})
    btype = pd.DataFrame(bt_rows)

    # ---------- precision ledger ----------
    # Every headline number with the sample behind it and the width of its interval,
    # so a reader can see which comparisons the data actually supports. Ordered the
    # way the charts appear.
    def prec(label, chart, est, moe, n, unit, note):
        return {"label": label, "chart": chart, "est": est, "moe": moe, "n": int(n),
                "unit": unit, "note": note,
                "lo": (None if est is None or moe is None else round(est - moe, 4)),
                "hi": (None if est is None or moe is None else round(est + moe, 4)),
                "ratio": (None if not moe or not est else round(abs(est) / moe, 2))}

    s = summary[summary["park"] == "SEA"].iloc[0]
    cell = lg_spray[(lg_spray["ev_band"] == "95-100") & (lg_spray["la_band"] == "20-25")]
    thin = cell.loc[cell["ba"].idxmin()] if len(cell) else None
    sea_carry = air[air["park"] == "SEA"]["carry_resid"]
    sea_fm = fmap[fmap["park"] == "SEA"]
    sea_mix = mix[(mix["park"] == "SEA") & (mix["event"] == "triple")].iloc[0]
    sea_bt = btype[(btype["park"] == "SEA") & (btype["bb_type"] == "fly_ball")].iloc[0]
    sea_ps = ps[(ps["park"] == "SEA")]
    sea_tri_w = wdecomp[(wdecomp["park"] == "SEA") & (wdecomp["event"] == "triple")].iloc[0]

    ledger = [
        prec("Park BA - xBA vs league", "Every park", float(s["gap_rel"]),
             round(Z95 * float(s["gap_sem"]), 4), s["bip"], "BA",
             "one park, whole span"),
        prec("Park wOBA - xwOBA vs league", "The cost", float(s["wgap_rel"]),
             round(Z95 * float(s["wgap_sem"]), 4), s["woba_n"], "wOBA",
             "the same effect, priced by run value"),
        prec("Triples, share of the wOBA loss", "The cost", float(sea_tri_w["contrib"]),
             round(float(sea_tri_w["moe"]), 4), int(sea_tri_w["k"]), "wOBA",
             "62 triples, weighted 1.6 apiece"),
        prec("Same, one season", "Season by season", float(sea_ps["gap_rel"].iloc[-1]),
             float(sea_ps["gap_moe"].iloc[-1]), sea_ps["bip"].iloc[-1], "BA",
             "a sixth of the sample"),
        prec("Carry vs league", "Carry", round(float(sea_carry.mean()), 2),
             round(Z95 * float(sea_carry.sem()), 2), len(sea_carry), "ft",
             "air balls only"),
        prec("Strikeout park factor", "Strikeouts", float(s["k_pf"]),
             round((float(s["k_pf_hi"]) - float(s["k_pf_lo"])) / 2, 4), s["k_pa"], "ratio",
             "plate appearances — the largest sample here"),
        prec("Triples vs league", "Hit types", float(sea_mix["ratio"] - 1) * 100,
             round((float(sea_mix["pct_hi"]) - float(sea_mix["pct_lo"])) / 2, 1),
             int(sea_mix["k"]), "%",
             "the smallest sample on any chart"),
        prec("Fly-ball shortfall", "Batted-ball type", float(sea_bt["rel"]),
             float(sea_bt["moe"]), sea_bt["n"], "BA", "one park, one batted-ball type"),
        prec("Spray cell, straightaway centre", "The blind spot",
             float(thin["ba"]) if thin is not None else None,
             float(thin["moe"]) if thin is not None else None,
             int(thin["n"]) if thin is not None else 0, "BA",
             "one 5° wedge of one contact cell"),
        prec("Field map cell, median", "The gradient", None, None,
             int(sea_fm["n"].median()) if len(sea_fm) else 0, "BA",
             "the thinnest bins in the project"),
    ]
    # How many balls it takes to resolve an effect of a given size at all.
    curve = [{"effect": e, "n": int(round(float(n_needed(e))))}
             for e in (0.002, 0.004, 0.006, 0.008, 0.010, 0.015, 0.020, 0.030)]

    def dump(name, obj):
        p = OUT / name
        p.write_text(json.dumps(obj, separators=(",", ":"), allow_nan=False))
        print(f"  wrote {p} ({p.stat().st_size/1024:.0f} KB)")

    r3 = lambda d: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}
    recs = lambda df: [r3(x) for x in df.replace({np.nan: None}).to_dict("records")]

    dump("meta.json", {"league_gap": round(lg_gap, 5),
                       "league_gap_by_season": {str(k): round(v, 5) for k, v in lg_gap_season.items()},
                       "league_wgap": round(lg_wgap, 5),
                       "league_wgap_by_season": {str(k): round(v, 5) for k, v in lg_wgap_season.items()},
                       "league_woba": round(float(wob["woba"].mean()), 5),
                       "league_xwoba": round(float(wob["xwoba"].mean()), 5),
                       "seasons": sorted(int(s) for s in lg_gap_season),
                       "total_bip": int(len(bip)), "total_woba": int(len(wob)),
                       "hc_scale": round(scale, 4)})
    dump("summary.json", recs(summary))
    dump("park_season.json", recs(ps))
    dump("league_grid.json", recs(lg_grid))
    dump("park_grid.json", recs(pk_grid))
    dump("league_spray.json", recs(lg_spray))
    dump("league_spray_coarse.json", recs(lg_spray_c))
    dump("park_spray.json", recs(pk_spray))
    dump("spray_dist.json", recs(spray_dist))
    dump("field_map.json", recs(fmap))
    dump("carry_spray.json", recs(carry_spray))
    dump("outcome_mix.json", recs(mix))
    dump("woba_decomp.json", recs(wdecomp))
    dump("btype_gap.json", recs(btype))
    dump("precision.json", {"ledger": [r3(r) for r in ledger], "curve": curve,
                            "z": round(Z95, 4)})

    pd.set_option("display.width", 200)
    print("\n=== park summary, sorted by BA - xBA ===")
    cols = ["park", "name", "bip", "ba", "xba", "gap", "gap_rel", "gap_z",
            "adj_gap", "carry_ft", "k_pct", "k_pf"]
    print(summary[cols].sort_values("gap").round(4).to_string(index=False))
    print("\n=== wOBA - xwOBA vs league (the same parks, priced by run value) ===")
    print(summary[["short", "woba_n", "woba", "xwoba", "wgap_rel", "wgap_z", "gap_rel"]]
          .sort_values("wgap_rel").round(4).to_string(index=False))
    print("\n=== T-Mobile's wOBA shortfall, by outcome ===")
    d = wdecomp[wdecomp["park"] == "SEA"].copy()
    d["ratio"] = d["rate"] / d["lg_rate"]
    print(d[["event", "weight", "k", "rate", "lg_rate", "ratio", "contrib", "moe"]]
          .round(5).to_string(index=False))
    print(wcheck[wcheck["park"] == "SEA"].round(5).to_string(index=False))
    print("\n=== strikeout park factor, home/road controlled (1.00 = neutral) ===")
    print(summary[["name", "k_pct", "k_pf", "kpf_bat", "kpf_pit"]]
          .sort_values("k_pf", ascending=False).round(4).to_string(index=False))
    print("\n=== T-Mobile by season ===")
    print(ps[ps["park"] == "SEA"].to_string(index=False))


if __name__ == "__main__":
    main()
