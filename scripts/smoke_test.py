"""Smoke test: confirm which Savant CSV params plyball can drive, and what columns come back."""
import pandas as pd
from plyball.statcast import StatCast

sc = StatCast()

# Build params from scratch -- plyball's defaults pin hfPT='FT' (two-seamers only)
# and hfSea='2019|', which we do not want.
params = {
    "all": "true",
    "type": "details",
    "hfGT": "R|",  # regular season
    "hfBBT": "fly_ball|ground_ball|line_drive|popup|",  # balls in play only
    "player_type": "batter",
    "game_date_gt": "2025-06-01",
    "game_date_lt": "2025-06-03",
    "min_pitches": "0",
    "min_results": "0",
    "group_by": "name",
    "sort_col": "pitches",
    "player_event_sort": "api_p_release_speed",
    "sort_order": "desc",
    "min_pas": "0",
}

url = sc.urls["search"].format("&".join(f"{k}={v}" for k, v in params.items()))
print("URL:", url, "\n")

df = sc.statcast_request(url, encoding="utf-8")
print("shape:", df.shape)
print("\ncolumns:\n", sorted(df.columns.tolist()))

for c in ["game_date", "launch_speed", "launch_angle", "estimated_ba_using_speedangle",
          "hc_x", "hc_y", "hit_distance_sc", "events", "home_team", "bb_type", "description"]:
    print(f"\n--- {c} ---")
    if c in df.columns:
        print(df[c].head(5).tolist(), "| nulls:", int(df[c].isna().sum()), "/", len(df))
    else:
        print("MISSING")

df.to_parquet("data/smoke.parquet")
print("\nunique dates:", sorted(df["game_date"].dropna().unique().tolist()))
print("unique parks (home_team):", sorted(df["home_team"].dropna().unique().tolist()))
