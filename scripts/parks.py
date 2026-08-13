"""Park identity by (home_team, season).

Savant reports the home TEAM, not the ballpark, and three clubs have not been in
their usual building over this window. Anything not listed here is assumed to have
played the whole span in one park.
"""

# (team, season) -> (park_id, park_name)
PARK_OVERRIDES = {
    ("ATH", 2025): ("SUTTER", "Sutter Health Park (Sacramento)"),
    ("ATH", 2026): ("SUTTER", "Sutter Health Park (Sacramento)"),
    ("OAK", 2025): ("SUTTER", "Sutter Health Park (Sacramento)"),
    ("TB", 2025): ("STEIN", "George M. Steinbrenner Field (Tampa)"),
}

PARK_NAMES = {
    "AZ": "Chase Field", "ATL": "Truist Park", "ATH": "Oakland Coliseum",
    "OAK": "Oakland Coliseum", "BAL": "Oriole Park at Camden Yards",
    "BOS": "Fenway Park", "CHC": "Wrigley Field", "CIN": "Great American Ball Park",
    "CLE": "Progressive Field", "COL": "Coors Field", "CWS": "Rate Field",
    "DET": "Comerica Park", "HOU": "Daikin Park", "KC": "Kauffman Stadium",
    "LAA": "Angel Stadium", "LAD": "Dodger Stadium", "MIA": "loanDepot park",
    "MIL": "American Family Field", "MIN": "Target Field", "NYM": "Citi Field",
    "NYY": "Yankee Stadium", "PHI": "Citizens Bank Park", "PIT": "PNC Park",
    "SD": "Petco Park", "SEA": "T-Mobile Park", "SF": "Oracle Park",
    "STL": "Busch Stadium", "TB": "Tropicana Field", "TEX": "Globe Life Field",
    "TOR": "Rogers Centre", "WSH": "Nationals Park",
    "SUTTER": "Sutter Health Park (Sacramento)",
    "STEIN": "George M. Steinbrenner Field (Tampa)",
}

# Teams whose Savant abbreviation changed; fold onto one park id.
TEAM_ALIAS = {"OAK": "ATH", "ARI": "AZ", "CHW": "CWS", "KCR": "KC",
              "SDP": "SD", "SFG": "SF", "TBR": "TB", "WSN": "WSH", "ANA": "LAA", "WAS": "WSH"}


def park_id(home_team: str, season: int) -> str:
    team = TEAM_ALIAS.get(home_team, home_team)
    if (home_team, season) in PARK_OVERRIDES:
        return PARK_OVERRIDES[(home_team, season)][0]
    if (team, season) in PARK_OVERRIDES:
        return PARK_OVERRIDES[(team, season)][0]
    return team


def park_name(pid: str) -> str:
    return PARK_NAMES.get(pid, pid)
