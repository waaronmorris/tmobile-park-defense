"""
Pull league-wide Statcast data via plyball, chunked and resumable.

Two streams:
  bip    -- every ball in play (has launch_speed, launch_angle, xBA, hc_x/hc_y, hit_distance_sc)
  nonbip -- strikeouts / walks / HBP, so plate-appearance denominators are complete

Each chunk lands in data/raw/<stream>/<start>.parquet, so re-running skips what is
already on disk and only fetches the gaps.
"""
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from plyball.statcast import StatCast

RAW = Path("data/raw")
CHUNK_DAYS = 7

# Generous bounds; hfGT=R| drops spring training and playoffs, empty chunks are skipped.
SEASONS = {
    2021: (date(2021, 4, 1), date(2021, 10, 3)),
    2022: (date(2022, 4, 7), date(2022, 10, 5)),
    2023: (date(2023, 3, 30), date(2023, 10, 1)),
    2024: (date(2024, 3, 20), date(2024, 9, 30)),
    2025: (date(2025, 3, 18), date(2025, 9, 28)),
    2026: (date(2026, 3, 25), date(2026, 8, 12)),
}

STREAMS = {
    "bip": {"hfBBT": "fly_ball|ground_ball|line_drive|popup|"},
    "nonbip": {"hfAB": "strikeout|strikeout_double_play|walk|intent_walk|hit_by_pitch|"},
}

BASE = {
    "all": "true",
    "type": "details",
    "hfGT": "R|",
    "player_type": "batter",
    "min_pitches": "0",
    "min_results": "0",
    "group_by": "name",
    "sort_col": "pitches",
    "sort_order": "desc",
    "min_pas": "0",
}


def fetch(sc, stream, start, end, attempts=4):
    params = {**BASE, **STREAMS[stream],
              "game_date_gt": start.isoformat(), "game_date_lt": end.isoformat()}
    url = sc.urls["search"].format("&".join(f"{k}={v}" for k, v in params.items()))
    for i in range(attempts):
        try:
            df = sc.statcast_request(url, encoding="utf-8")
            if "error" in df.columns:
                raise RuntimeError(f"savant error: {df['error'].iloc[0] if len(df) else 'empty'}")
            return df
        except Exception as e:  # noqa: BLE001 -- transient scrape failures, back off and retry
            if i == attempts - 1:
                print(f"  FAILED {stream} {start}..{end}: {e}", flush=True)
                return None
            time.sleep(5 * (i + 1))
    return None


def main():
    sc = StatCast()
    sc.logger.setLevel("ERROR")
    years = [int(a) for a in sys.argv[1:]] or list(SEASONS)

    for year in years:
        season_start, season_end = SEASONS[year]
        for stream in STREAMS:
            outdir = RAW / stream / str(year)
            outdir.mkdir(parents=True, exist_ok=True)
            cur = season_start
            while cur <= season_end:
                end = min(cur + timedelta(days=CHUNK_DAYS - 1), season_end)
                dest = outdir / f"{cur.isoformat()}.parquet"
                if dest.exists():
                    cur = end + timedelta(days=1)
                    continue
                df = fetch(sc, stream, cur, end)
                if df is not None and len(df):
                    df.to_parquet(dest)
                    print(f"  {stream} {year} {cur}..{end}: {len(df):,} rows", flush=True)
                elif df is not None:
                    dest.touch()  # empty range, mark done so reruns skip it
                cur = end + timedelta(days=1)
                time.sleep(1)
        print(f"[{year}] done", flush=True)


if __name__ == "__main__":
    main()
