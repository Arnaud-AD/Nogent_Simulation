#!/usr/bin/env python3
"""
Scrape FFVB poule data and update data/poule_2mb.json.
Designed to run via GitHub Actions every Sunday at 23:30.

Usage: python scripts/scrape_ffvb.py
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

FFVB_URL = "https://www.ffvbbeach.org/ffvbapp/resu/vbspo_calendrier.php"
DATA_FILE = Path(__file__).parent.parent / "data" / "poule_2mb.json"

# Short name mapping for teams
SHORT_NAMES = {
    "UNION SPORTIVE DE VILLEJUIF 3": "Villejuif",
    "US VILLEJUIF 3": "Villejuif",
    "PANTIN VOLLEY 1": "Pantin",
    "ISLE ADAM F.V.O. 2": "Isle Adam",
    "ISLE ADAM FVO 2": "Isle Adam",
    "BUSSY VOLLEY": "Bussy",
    "SAINT-PIERRE VOLLEY-BALL": "St-Pierre",
    "ST-PIERRE VB": "St-Pierre",
    "VOLLEY-CLUB NOGENTAIS": "Nogentais",
    "VC NOGENTAIS": "Nogentais",
    "VC CHAMPS SUR MARNE": "Champs",
    "VC CHAMPS/MARNE": "Champs",
    "TREMBLAY ATHLETIQUE CLUB 2": "Tremblay",
    "TREMBLAY AC 2": "Tremblay",
    "VINCENNES VOLLEY CLUB 3": "Vincennes",
    "VINCENNES VC 3": "Vincennes",
    "SPORTING CLUB NORD PARISIEN 2": "SCNP",
    "SC NORD PARISIEN 2": "SCNP",
}

FULL_NAMES = {
    "Villejuif": "US VILLEJUIF 3",
    "Pantin": "PANTIN VOLLEY 1",
    "Isle Adam": "ISLE ADAM F.V.O. 2",
    "Bussy": "BUSSY VOLLEY",
    "St-Pierre": "SAINT-PIERRE VOLLEY-BALL",
    "Nogentais": "VOLLEY-CLUB NOGENTAIS",
    "Champs": "VC CHAMPS SUR MARNE",
    "Tremblay": "TREMBLAY AC 2",
    "Vincennes": "VINCENNES VOLLEY CLUB 3",
    "SCNP": "SC NORD PARISIEN 2",
}


def get_short_name(full_name: str) -> str:
    """Convert a full FFVB team name to our short name."""
    name = full_name.strip()
    if name in SHORT_NAMES:
        return SHORT_NAMES[name]
    # Fuzzy match: try partial matches
    for key, short in SHORT_NAMES.items():
        if key in name or name in key:
            return short
    return name


def fetch_page(poule="2MB", saison="2025/2026", codent="LIIDF") -> str:
    """Fetch the FFVB page HTML."""
    params = {"saison": saison, "codent": codent, "poule": poule}
    r = requests.get(FFVB_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.text


def parse_standings(soup: BeautifulSoup) -> list[dict]:
    """Parse the standings table from the FFVB page."""
    standings = []

    # Find the standings table — it's the one with "Clt" or "Pts" in headers
    tables = soup.find_all("table")
    standings_table = None

    for table in tables:
        text = table.get_text()
        if "Clt" in text and "Pts" in text and "QS" in text:
            standings_table = table
            break

    if not standings_table:
        print("WARNING: Could not find standings table", file=sys.stderr)
        return standings

    rows = standings_table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 10:
            continue

        # Extract text from each cell
        values = [c.get_text(strip=True) for c in cells]

        # First cell is typically "rank.TEAM NAME" or just the team name
        team_text = values[0]
        # Remove leading rank number (e.g., "1." or "1")
        team_text = re.sub(r"^\d+\.?\s*", "", team_text)

        short_name = get_short_name(team_text)
        if short_name == team_text and len(team_text) > 20:
            # Unknown team, skip
            continue

        try:
            # Parse numeric columns — the exact column order from FFVB:
            # Clt | Equipe | Pts | J | G | P | 3-0 | 3-1 | 3-2 | 2-3 | 1-3 | 0-3 | Sets+ | Sets- | QS | Pts+ | Pts- | QP
            # But columns may shift. We look for the pattern after the team name.
            nums = []
            for v in values[1:]:
                v = v.replace(",", ".")
                try:
                    nums.append(float(v))
                except ValueError:
                    continue

            if len(nums) >= 15:
                standings.append({
                    "name": short_name,
                    "fullName": FULL_NAMES.get(short_name, team_text),
                    "points": int(nums[0]),
                    "matchesPlayed": int(nums[1]),
                    "wins": int(nums[2]),
                    "losses": int(nums[3]),
                    "setsWon": int(nums[10]),
                    "setsLost": int(nums[11]),
                    "pointsFor": int(nums[13]),
                    "pointsAgainst": int(nums[14]),
                })
        except (ValueError, IndexError) as e:
            print(f"WARNING: Could not parse row for {team_text}: {e}", file=sys.stderr)

    return standings


def parse_matches(soup: BeautifulSoup) -> tuple[list[dict], list[dict]]:
    """Parse played and remaining matches from the FFVB page."""
    played = []
    remaining = []

    text = soup.get_text()

    # Find all match lines. FFVB format in the calendar section:
    # Match code | date | home team | score | away team | details
    # Played matches have a score like "3 - 1"
    # Unplayed matches have venue info instead of score

    # Strategy: find all <tr> that contain match data
    # Match rows typically have a code like "2MBR001"
    tables = soup.find_all("table")

    current_journee = 0

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            row_text = row.get_text(strip=True)

            # Detect journee headers
            journee_match = re.search(r"Journ[ée]e\s*n[°o]?\s*(\d+)", row_text, re.IGNORECASE)
            if journee_match:
                current_journee = int(journee_match.group(1))
                continue

            # Look for match rows (contain match code pattern)
            if not re.search(r"2MB", row_text):
                continue

            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            cell_texts = [c.get_text(strip=True) for c in cells]

            # Try to find home team, score, away team
            # Score pattern: "3 - 0", "3 - 1", "3 - 2", "2 - 3", "1 - 3", "0 - 3"
            score_found = False
            home_name = None
            away_name = None

            for i, ct in enumerate(cell_texts):
                score_match = re.match(r"^(\d)\s*-\s*(\d)$", ct)
                if score_match and i >= 1:
                    h_sets = int(score_match.group(1))
                    a_sets = int(score_match.group(2))

                    # Home team is before score, away team after
                    home_name = get_short_name(cell_texts[i - 1])
                    if i + 1 < len(cell_texts):
                        away_name = get_short_name(cell_texts[i + 1])

                    if home_name and away_name and home_name != away_name:
                        played.append({
                            "home": home_name,
                            "away": away_name,
                            "homeSets": h_sets,
                            "awaySets": a_sets,
                            "journee": current_journee,
                        })
                        score_found = True
                    break

            # If no score found, it might be an unplayed match
            if not score_found and current_journee > 0:
                # Try to extract two team names
                teams_found = []
                for ct in cell_texts:
                    short = get_short_name(ct)
                    if short != ct or short in FULL_NAMES:
                        if short not in teams_found:
                            teams_found.append(short)

                # Look for date pattern
                date_str = ""
                for ct in cell_texts:
                    dm = re.search(r"(\d{2}/\d{2}/\d{2,4})", ct)
                    if dm:
                        date_str = dm.group(1)
                        break

                if len(teams_found) >= 2:
                    remaining.append({
                        "home": teams_found[0],
                        "away": teams_found[1],
                        "journee": current_journee,
                        "date": date_str,
                    })

    return played, remaining


def scrape_and_update():
    """Main entry point: scrape FFVB and update JSON file."""
    print("Fetching FFVB page...")
    html = fetch_page()
    soup = BeautifulSoup(html, "html.parser")

    print("Parsing standings...")
    standings = parse_standings(soup)
    print(f"  Found {len(standings)} teams")

    print("Parsing matches...")
    played, remaining = parse_matches(soup)
    print(f"  Found {len(played)} played matches, {len(remaining)} remaining")

    if len(standings) == 0:
        print("ERROR: No standings found, aborting update", file=sys.stderr)
        sys.exit(1)

    data = {
        "saison": "2025/2026",
        "poule": "2MB",
        "codent": "LIIDF",
        "lastUpdated": date.today().isoformat(),
        "standings": standings,
        "playedMatches": played,
        "remainingMatches": remaining,
    }

    # Validate against existing data if available
    if DATA_FILE.exists():
        existing = json.loads(DATA_FILE.read_text())
        existing_teams = {t["name"] for t in existing.get("standings", [])}
        new_teams = {t["name"] for t in standings}
        if existing_teams and not new_teams.intersection(existing_teams):
            print("ERROR: No team overlap with existing data, aborting", file=sys.stderr)
            sys.exit(1)

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Updated {DATA_FILE}")
    print(f"  Teams: {[t['name'] for t in standings]}")
    print(f"  Played: {len(played)}, Remaining: {len(remaining)}")


if __name__ == "__main__":
    scrape_and_update()
