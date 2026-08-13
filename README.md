# T-Mobile Park: the xBA blind spot

Why Seattle is continually one of the lowest-offense parks in MLB, measured from
pitch-level Statcast data pulled with [`plyball`](https://plyball.readthedocs.io/).

**Application:** https://waaronmorris.github.io/tmobile-park-defense/
**Write-up:** https://morris-labs.dev/blog/the-xba-blind-spot

## The argument

Statcast's xBA is a function of exit velocity and launch angle, computed at the instant of
contact. Two things decide the outcome afterward and the model can see neither:

1. **Direction.** xBA has no spray term, so every ball in a given speed/angle cell gets the
   same expected average no matter where it was hit.
2. **Carry.** xBA is fixed at contact; how far the ball actually travels depends on the air.

T-Mobile Park is unusually good at exploiting both, and it also converts an unusual number
of plate appearances into strikeouts before a ball is ever put in play.

The mechanism is not the one usually named. The marine layer is a null result in Seattle
specifically; the carry deficit is cold air plus sea level. See
[what the published work rules out](#what-the-published-work-rules-out).

## Headline findings

2021–2026 regular season, 700,414 batted balls, all 30 parks.

| Measure | T-Mobile Park | Rank | Read |
|---|---|---|---|
| BA − xBA vs league | **−.0140** (5.8σ) | 1st of 32 | Largest hit suppression in MLB |
| Same as a count | **−311 hits** (≈−52/season) | 1st | hits − ∑xBA, net of the league offset |
| Same, hitters divided out | **−.0148** | 1st | Not the Mariners roster — it's the building |
| Carry vs league expectation | **−3.5 ft** | 4th-shortest | Physics, not defense |
| Strikeout park factor | **1.123** | 1st of 32 | 12% more Ks than the same people manage elsewhere |

Negative in **all six seasons** (−.009 to −.019 vs league), which is the "continually" part.

### It does not eat home runs

Rate of each hit type per ball in play at T-Mobile, against the league:

| Outcome | vs league | Rank (1 = lowest) |
|---|---|---|
| Triples | **−49%** | 2nd of 32 |
| Doubles | −10% | 3rd |
| Singles | −5% | 3rd |
| Home runs | **+4%** | 19th |

And by batted-ball type (BA − xBA relative to league): fly balls **−.027**, line drives
**−.025**, ground balls −.004, pop-ups +.001.

So the park is not a home-run suppressor — the fences are short enough (average 367 ft,
average wall height 7.6 ft vs an MLB mean of 9.6) that the 2013 move-in offsets the dead air.
The damage lands on balls hit in the air that need to find grass, which is exactly where the
spray-angle gradient below does its work.

### The blind spot, quantified

Take balls hit 95–100 mph at 20–25°. Statcast assigns them all essentially the same xBA,
**.301**, across the entire field. The actual batting average within that one cell:

| Direction | Actual BA |
|---|---|
| Down the lines (±45°) | ~.97 |
| The gaps (±15–20°) | ~.41 |
| Dead center (−10° to +5°) | **.021** |

A spread of **.969** in outcome that the model treats as identical contact. That gradient is
what a ballpark's geometry acts on, and it is invisible to xBA by construction.

## How much of this the sample supports

Every chart is an estimate and they are not equally solid. Batting average is a coin flip
repeated, so its uncertainty falls as 1/√n — a measurement over 22,000 balls is about a
fifth as wide as the same measurement over one season.

| Measurement | n | Estimate | 95% | ÷ MoE |
|---|---|---|---|---|
| Strikeout park factor | 33,442 PA | 1.123 | ± .031 | **36×** |
| Carry vs league | 5,705 | −3.46 ft | ± 0.52 | 6.7× |
| Park BA − xBA vs league | 22,139 | −.0140 | ± .0047 | 3.0× |
| Triples vs league | 62 | −49% | ± 13pp | 3.8× |
| Fly-ball shortfall | 5,952 | −.0264 | ± .0076 | 3.5× |
| Spray cell, dead centre | 569 | .021 | ± .012 | 1.8× |
| **One season** | 2,952 | −.015 | ± .013 | **1.1×** |

Three consequences worth stating plainly:

- **Only 13 of the 32 parks clear their own error bar.** A park sees ~23,000 balls in play
  over six seasons, which resolves an effect of about .006 of batting average and no
  smaller. The other 19 parks are not neutral — they are *unmeasured*, and the ranking
  chart fades them accordingly.
- **No single T-Mobile season is strong evidence.** Four of six are individually
  significant; the interval on one season is ±.013 against an effect of ~.015. What
  carries the argument is that all six share a sign, which under a fair coin is p = 0.031.
- **The field map is the thinnest thing here** — a median of 50 balls per cell, giving a
  95% interval near ±.085. Cells whose interval spans zero are drawn faded.

The strikeout factor is by far the most certain result in the project, and the
percentage on triples is the least — 62 triples over six seasons puts the true effect
somewhere between −36% and −62%.

## Method notes

- **The statistic.** `BA − mean(xBA)` is identically `(hits − ∑xBA) / n` — verified equal to
  1.6e-17. The rate form ranks parks fairly, since parks differ in how many balls they see;
  the count form (`hits_vs_lg`) makes the size legible. What actually matters is that both
  terms run over one identical row set: pairing an at-bat-denominated BA against an xBA
  summed over a wider set of batted balls would be comparing two different populations.
  The denominator lands correctly by itself because **Savant assigns no xBA to sacrifice
  flies** (0.0% populated), so they drop out exactly as they drop out of at-bats, while
  errors, double plays and fielder's choices remain — correct, since those are at-bats and
  they are outs.
- **Reference frame.** xBA is not unbiased on this population: league-wide BA − xBA is
  **+.0048**, not zero, and it drifts by season. Every comparison is against the league,
  not against zero.
- **Carry residual** compares each air ball against the league median distance for its exact
  1 mph × 1° cell, re-centred so the league mean is zero. Defensive positioning cannot change
  how far a ball flies, so this isolates the park. **Validation: Coors Field comes out at
  +16.1 ft**, Chase Field +7.5, which is the check that the measurement works.
- **Strikeout park factor** holds personnel fixed: the home club's hitters are compared to
  themselves in and out of the building, the home club's pitchers likewise, and the two are
  averaged. 1.00 is neutral.
- **Hitter-adjusted gap** charges each batted ball against that batter's own record in every
  *other* park, so a lineup that chronically underperforms xBA is not mistaken for a park.
- **Spray angle** is derived from the Statcast hit coordinate about home plate at
  (125.42, 198.27); negative is toward left field. Coordinates are scaled to feet by
  calibrating against `hit_distance_sc` on balls hit in the air, which gives **2.487 ft/unit**
  (the widely-quoted 2.29 does not fit this data — the ratio is constant to within 1% on
  home runs and caught fly balls).
- **Park identity ≠ team.** The Athletics (Sutter Health Park, 2025–26) and Rays
  (Steinbrenner Field, 2025) are tracked as separate parks.

### External corroboration

Independent sources agree on direction and rough magnitude:

- **FanGraphs** 5-year regressed factors for Seattle: Basic 94, 2B 93, 3B 79, **SO 104**
  (all pre-halved; unhalved ≈ 88 and 108). The SO figure corroborates the 1.123 measured here.
- **ESPN** 2022 single-season: runs 0.886, hits 0.915, doubles 0.891, triples 0.407.
- FanGraphs' handedness split shows the park punishes left-handed power (HR-as-LHB 93)
  notably more than right-handed (HR-as-RHB 98).
- Published **strikeout** park factors for T-Mobile run 109–122 depending on year and method
  (Ryan Blake at Lookout Landing; Pitcher List has it highest in MLB), which brackets the
  1.123 measured here. Four-seam whiff rate is 25.1% at T-Mobile versus 21.9% elsewhere.

Note the two park-factor sources use different conventions — FanGraphs halves its factors for
direct application to full-season lines, ESPN does not. Undoing the halving reconciles them.

### What the published work rules out

**It is not the marine layer.** This is the popular explanation and it is measurably wrong.
Kagan & Mitchell ([THT Annual 2017](https://physics.csuchico.edu/baseball/Pubs/MarineLayer.pdf))
regressed marine-layer conditions within each West Coast park, controlling for exit speed,
launch angle, spray angle and pitch speed:

| Park | Effect | SE | p |
|---|---|---|---|
| San Diego | −6.1 ft | ±3.0 | 0.04 |
| Oakland | −5.6 ft | ±3.2 | 0.07 |
| **Seattle** | **−1.2 ft** | **±2.3** | **0.53** |

Seattle's coefficient is indistinguishable from zero. The widely-quoted "~6 feet of marine
layer" belongs to San Diego and Oakland; the Seattle Times piece that popularized it applies
the figure to all six parks and omits Seattle's null. The physics explains why: cold air is
denser and shortens a fly ball, humid air is *less* dense and lengthens it, and the two
roughly cancel.

**It is the thermometer.** Statcast's own carry decomposition
([Savant park factors, distance view](https://baseballsavant.mlb.com/leaderboard/statcast-park-factors?type=distance))
splits T-Mobile's 2024 −5.3 ft into temperature −4.2, elevation −2.3, roof +0.6, and
"environment" — the term where humidity would live — at **+0.6**. Within Seattle's own
schedule: cool games (~57°F) lose 9.5 ft, hot games (~73°F) lose 1.0 ft. Same park, same air.

**It is not the roof.** Petriello (MLB.com, Jan 2025) measured 2022–24: the park suppressed
offense by **9% with the roof closed and 9% with it open**, closed marginally the worse for
home hitters. It is shut ~16% of the time and Statcast prices it at under a foot of carry.

**It is not foul territory.** 24,300 sq ft — 10th of 29, ~5% above median. Not an outlier.

**The strikeouts are the real anomaly, and they point at twilight.** Savant's single-season K
park factor has T-Mobile **1st in MLB in 2023, 2024 (122) and 2025**. Ryan Blake's GLMM/GAMM
work ([Swings & Takes](https://swingsandtakes.substack.com/p/t-mobile-park-factored)) measures
whiff rate at 25.1% before sunset versus 27.0% after, and removing that single effect drops
the K factor from 109 to ~101. His decomposition of the .024 wOBA park effect: sun/lighting
~50%, climate on batted balls ~33%, pitch movement ~10%. The effect is symmetric — Mariners
hitters *and* Mariners pitchers both whiff ~25% at home against ~20% on the road — which is a
visibility signature, not a roster one. Attribution to the batter's eye specifically (rebuilt
in black honeycomb in July 2003, angle never altered) remains unproven.

## Caveats

- BA − xBA blends the ballpark with the defense that plays in it. The **carry residual is the
  cleaner park-only reading**; the hitter-adjusted gap removes the batting side but not the
  fielding side.
- Seattle's gap widens from 2024 onward (−.019, −.018, −.015 vs league) against −.013, −.011,
  −.009 in 2021–23. The sign is stable but the era difference is within roughly one standard
  error per season, so treat the trend as suggestive rather than established.
- `hit_distance_sc` for home runs is a projected landing point, not a measured one.

## Layout

```
scripts/
  pull_statcast.py   chunked, resumable Savant pull via plyball -> data/raw/{bip,nonbip}/
  parks.py           park identity by (home_team, season)
  stats.py           Wilson / delta-method / mean intervals
  analyze.py         all metrics + intervals -> viz/data/*.json
  build_viz.py       inlines d3 + columnar-packed data -> one standalone file
  export_for_post.py small extracts for the write-up's server-rendered charts
viz/
  template.html      the page (placeholders for d3 and data)
  data/              aggregates, committed, so a clone can rebuild
  vendor/d3.min.js   inlined at build time
docs/index.html      the built application, ~1.1 MB, served by GitHub Pages
data/raw/            233 MB of parquet chunks, gitignored, resumable
```

## Reproducing

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e ../plyball pandas pyarrow numpy

.venv/bin/python scripts/pull_statcast.py           # all seasons, ~2h serial
.venv/bin/python scripts/pull_statcast.py 2025      # or one season at a time, in parallel

PYTHONPATH=scripts .venv/bin/python scripts/analyze.py
.venv/bin/python scripts/build_viz.py            # -> docs/index.html, served by Pages
```

The pull skips any chunk already on disk, so it is safe to interrupt and re-run, and safe to
run several seasons concurrently.

### A note on `plyball`

`StatCast.get_statcast_data()` ships defaults that pin `hfPT='FT'` (two-seam fastballs only)
and `hfSea='2019|'`. These scripts bypass that by building the parameter dict from scratch and
calling `statcast_request()` directly — worth knowing before reusing the convenience wrapper
for league-wide work.
