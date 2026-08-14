# T-Mobile Park, measured

Why Seattle is continually one of the lowest-offense parks in MLB, measured from
pitch-level Statcast data pulled with [`plyball`](https://plyball.readthedocs.io/).

**Application:** https://waaronmorris.github.io/tmobile-park-defense/
**Write-up:** https://morris-labs.dev/blog/the-xba-blind-spot

## The argument

Statcast's expected stats are functions of exit velocity and launch angle, computed at the
instant of contact. Two things decide the outcome afterward and the model can see neither:

1. **Direction.** xBA has no spray term, so every ball in a given speed/angle cell gets the
   same expected average no matter where it was hit.
2. **Carry.** xBA is fixed at contact; how far the ball actually travels depends on the air.

T-Mobile Park is unusually good at exploiting both, and it also converts an unusual number
of plate appearances into strikeouts before a ball is ever put in play.

The mechanism is not the one usually named. The marine layer is a null result in Seattle
specifically; the carry deficit is cold air plus sea level. See
[what the published work rules out](#what-the-published-work-rules-out).

## Headline findings

2021–2026 regular season, 699,693 batted balls, all 30 parks.

| Measure | T-Mobile Park | Rank | Read |
|---|---|---|---|
| BA − xBA vs league | **−.0140** (5.8σ) | 1st of 32 | Largest hit suppression in MLB |
| Same as a count | **−311 hits** (≈−52/season) | 1st | hits − ∑xBA, net of the league offset |
| Same, hitters divided out | **−.0148** | 1st | Not the Mariners roster — it's the building |
| wOBA − xwOBA vs league | **−.0155** (5.4σ) | 2nd of 32 | The same effect priced by run value |
| Carry vs league expectation | **−3.5 ft** | 4th-shortest | Physics, not defense |
| Strikeout park factor | **1.123** | 1st of 32 | 12% more Ks than the same people manage elsewhere |

Negative in **all six seasons** (−.009 to −.020 vs league), which is the "continually" part.

The one rank that moves is wOBA: Busch Stadium passes Seattle at −.0183 (6.9σ). The two
measures agree closely on the parks (r = .94) and differ where a park's losses are
concentrated in the expensive hit types, which is Seattle's case in one direction and
St. Louis's in another. Coors Field (+.0338) and Sutter Health Park (+.0420) come out
strongly positive, which is the check that the wOBA measurement works.

### It does not eat home runs

Rate of each hit type per ball in play at T-Mobile, against the league:

| Outcome | vs league | Rank (1 = lowest) |
|---|---|---|
| Triples | **−49%** | 2nd of 32 |
| Doubles | −10% | 3rd |
| Singles | −5% | 3rd |
| Home runs | **+5%** | 19th |

And by batted-ball type (BA − xBA relative to league): fly balls **−.026**, line drives
**−.023**, ground balls −.003, pop-ups +.001.

So the park is not a home-run suppressor — the fences are short enough (average 367 ft,
average wall height 7.6 ft vs an MLB mean of 9.6) that the 2013 move-in offsets the dead air.
The damage lands on balls hit in the air that need to find grass, which is exactly where the
spray-angle gradient below does its work.

### What that mix is worth

Rate ratios say triples are down by half. They cannot say what half a park's triples is
worth against half its singles, because BA scores every hit alike. wOBA does not: a triple
weighs 1.6 against a single's 0.9 and a home run's 2.0. Since mean wOBA *is* a weighted sum
of outcome rates, the shortfall splits exactly (residual 2e-5):

| Outcome | Rate vs league | Weight | wOBA cost | Share of the total |
|---|---|---|---|---|
| Singles | ×0.95 | 0.90 | **−.0101** | 53% |
| Doubles | ×0.90 | 1.25 | **−.0081** | 43% |
| Triples | ×0.51 | 1.60 | **−.0042** | **22%** |
| Home runs | ×1.05 | 2.00 | +.0049 | −26% |
| Errors, fielder's choice | — | ~0.90 | −.0015 | 8% |
| **Total wOBA vs league** | | | **−.0190** | |
| *of which contact quality (xwOBA)* | | | *−.0035* | 18% |
| ***left over — the park*** | | | **−.0155** | 82% |

Triples are 0.54% of league contact and 22% of the loss. Nothing else on the board returns
that much per ball. Home runs run the other way and give back a quarter of it, which is why
the park reads as merely below average on wOBA and worst in MLB on batting average.

### Why the triples go

62 triples in six seasons against 121 at the league rate — the lowest of any park with a
full span. Two things do it, at opposite ends of the field.

**The corners are too short.** On air balls carrying 300–420 ft down the right-field line
(+35° to +50°), T-Mobile turns **45.6%** into home runs against a league 33.5%, and 0.7%
into triples against 2.2%. A ball that caroms around the corner for a triple in a deep park
leaves this one. The same holds in the left-field corner. This is the 2013 move-in showing
up as a *cost* to the hitter's slower legs and a credit to his power.

**The middle is too dead.** From −15° to −5° in that same distance band, T-Mobile's out
rate is **78.0%** against a league 72.5% — the carry deficit and a 401-ft centre field
catching balls that reach the gap elsewhere. Only 4.07% of Seattle air balls travel 400+ ft
against a league 5.11%, and among the ones that do, the triple rate is .0021 against .0170.

A triple needs a ball that lands deep, stays in the park, and beats the throw. Seattle
squeezes it from both sides: too short at the corners for the ball to stay in, too dead in
the middle for it to get out there. The effect is far stronger for left-handed batters
(rate ratio **0.35**) than right (0.65), consistent with FanGraphs' handedness split.

Caveat: 62 triples is the smallest sample in the project. The direction is not in doubt —
the wOBA contribution is 3.9× its own margin of error — but the split between the two
mechanisms above rests on a few hundred balls per spray bin.

### The blind spot, quantified

Take the 9,025 balls hit 95–100 mph at 20–25°. Statcast assigns them all essentially the same xBA,
**.302**, across the entire field — it holds to within four points in every direction.
The actual batting average within that one cell, by 5° bin:

| Direction | Actual BA | Balls |
|---|---|---|
| Left-field line, −50° to −45° | **.990** | 104 |
| Left-centre gap, −20° to −15° | .488 | 508 |
| Straightaway centre, 0° to +5° | **.021** | 569 |
| Right-centre gap, +15° to +20° | .445 | 548 |
| Right-field line, +45° to +50° | **.971** | 140 |

A spread of **.969** in outcome that the model treats as identical contact. That gradient is
what a ballpark's geometry acts on, and it is invisible to xBA by construction.

## How much of this the sample supports

Every chart is an estimate and they are not equally solid. Batting average is a coin flip
repeated, so its uncertainty falls as 1/√n — a measurement over 22,000 balls is about a
fifth as wide as the same measurement over one season.

| Measurement | n | Estimate | 95% | ÷ MoE |
|---|---|---|---|---|
| Strikeout park factor | 33,444 PA | 1.123 | ± .031 | **36×** |
| Carry vs league | 5,705 | −3.46 ft | ± 0.52 | 6.7× |
| Triples, wOBA cost | 62 | −.0042 | ± .0011 | 3.9× |
| Triples vs league | 62 | −49% | ± 13pp | 3.8× |
| Fly-ball shortfall | 5,952 | −.0264 | ± .0076 | 3.5× |
| Park BA − xBA vs league | 22,139 | −.0140 | ± .0047 | 3.0× |
| Park wOBA − xwOBA vs league | 22,325 | −.0155 | ± .0056 | 2.8× |
| Spray cell, dead centre | 569 | .021 | ± .012 | 1.8× |
| **One season** | 2,952 | −.015 | ± .013 | **1.1×** |

Three consequences worth stating plainly:

- **Only 13 of the 32 parks clear their own error bar** on BA − xBA, and 15 on
  wOBA − xwOBA. A park sees ~23,000 balls in play over six seasons, which resolves an
  effect of about .006 of batting average — or .0055 of wOBA — and no smaller. The
  remaining parks are not neutral, they are *unmeasured*, and both ranking charts fade
  them accordingly.
- **No single T-Mobile season is strong evidence.** Four of six are individually
  significant; the interval on one season is ±.013 against an effect of ~.015. What
  carries the argument is that all six share a sign, which under a fair coin is p = 0.031.
- **The field map is the thinnest thing here** — a median of 50 balls per cell, giving a
  95% interval near ±.085. Cells whose interval spans zero are drawn faded.

The strikeout factor is by far the most certain result in the project. Triples are the
thinnest of the headline numbers — 62 over six seasons puts the true effect somewhere
between −36% and −62% — though the direction survives it comfortably either way you
score them, as a rate or as a wOBA cost.

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
- **The wOBA population is not the same rows.** wOBA counts sacrifice flies in its
  denominator and Savant *does* attach an xwOBA to them (100% populated, against 0% for
  xBA), so they come back in — 706,842 rows against 699,693. Selecting on
  `woba_denom == 1` reproduces the standard denominator without restating it: sacrifice
  bunts carry denom 0 and stay out.
- **The wOBA decomposition is an identity, not a model.** Mean wOBA is a weighted sum of
  outcome rates, so `Δ mean(wOBA) = Σ (rate_park − rate_lg) × weight` splits the shortfall
  exactly by outcome; the residual is checked every run and is 2e-5. Weights are read off
  `woba_value` rather than hardcoded, since the league re-fits them each season. xwOBA does
  not decompose this way — it is one number per batted ball — so it is carried whole, as
  the contact-quality baseline the outcome side is read against.
- **Reference frame.** Neither expected stat is unbiased on this population: league-wide
  BA − xBA is **+.0048** and wOBA − xwOBA is **+.0096**, not zero, and both drift by
  season. Every comparison is against the league, not against zero.
- **Carry residual** compares each air ball against the league median distance for its exact
  1 mph × 1° cell, re-centred so the league mean is zero. Defensive positioning cannot change
  how far a ball flies, so this isolates the park. **Validation: Coors Field comes out at
  +16.1 ft**, Chase Field +7.5, which is the check that the measurement works.
- **Strikeout park factor** holds personnel fixed: the home club's hitters are compared to
  themselves in and out of the building, the home club's pitchers likewise, and the two are
  averaged. 1.00 is neutral.
- **Hitter-adjusted gap** charges each batted ball against that batter's own record in every
  *other* park, so a lineup that chronically underperforms xBA is not mistaken for a park.
  This is computed on the xBA side only; the wOBA charts are unadjusted for hitter mix.
- **Spray angle** is derived from the Statcast hit coordinate about home plate at
  (125.42, 198.27); negative is toward left field. Coordinates are scaled to feet by
  calibrating against `hit_distance_sc` on balls hit in the air, which gives **2.487 ft/unit**
  (the widely-quoted 2.29 does not fit this data — the ratio is constant to within 1% on
  home runs and caught fly balls).
- **Park identity ≠ team.** The Athletics (Sutter Health Park, 2025–26) and Rays
  (Steinbrenner Field, 2025) are tracked as separate parks.

### External corroboration

Independent sources agree on direction and rough magnitude:

- **FanGraphs** 5-year regressed factors for Seattle: Basic 94, 2B 93, **3B 79**, **SO 104**
  (all pre-halved; unhalved ≈ 88 and 108). The SO figure corroborates the 1.123 measured
  here, and 3B 79 — unhalved ≈ 58, and regressed, so shrunk toward neutral — is the
  independent read on the triples result.
- **ESPN** 2022 single-season: runs 0.886, hits 0.915, doubles 0.891, **triples 0.407**.
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
docs/index.html      the built application, ~1.7 MB, served by GitHub Pages
viz/fonts/           Oswald + IBM Plex, inlined as data URIs at build time
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
