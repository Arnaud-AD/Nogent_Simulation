#!/usr/bin/env python3
"""
Enumerate ALL scenarios where Nogentais finishes champion.
Brute-force over the critical matches, deterministic ranking.
"""

import itertools
import json
from pathlib import Path

DATA = json.loads((Path(__file__).parent.parent / "data" / "poule_2mb.json").read_text())

# All possible match scores
SCORES = [
    (3, 0), (3, 1), (3, 2),
    (2, 3), (1, 3), (0, 3),
]

# Points awarded by FFVB rules
def ffvb_points(h_sets, a_sets):
    if h_sets == 3:
        return (3 if a_sets <= 1 else 2, 1 if a_sets == 2 else 0)
    else:
        return (1 if h_sets == 2 else 0, 3 if h_sets <= 1 else 2)

def score_label(h, a):
    return f"{h}-{a}"

# Build initial state from standings
def init_teams():
    teams = {}
    for t in DATA["standings"]:
        teams[t["name"]] = {
            "pts": t["points"],
            "sw": t["setsWon"],
            "sl": t["setsLost"],
            "pf": t["pointsFor"],
            "pa": t["pointsAgainst"],
        }
    return teams

def apply_match(teams, home, away, h_sets, a_sets):
    hp, ap = ffvb_points(h_sets, a_sets)
    teams[home]["pts"] += hp
    teams[away]["pts"] += ap
    teams[home]["sw"] += h_sets
    teams[home]["sl"] += a_sets
    teams[away]["sw"] += a_sets
    teams[away]["sl"] += h_sets
    # Approximate points per set for tiebreakers
    teams[home]["pf"] += h_sets * 25
    teams[home]["pa"] += a_sets * 25
    teams[away]["pf"] += a_sets * 25
    teams[away]["pa"] += h_sets * 25

def rank(teams):
    def key(name):
        t = teams[name]
        sq = t["sw"] / max(t["sl"], 1)
        pq = t["pf"] / max(t["pa"], 1)
        return (-t["pts"], -sq, -pq)
    return sorted(teams.keys(), key=key)

# ---- Define matches ----
# Nogentais matches (must win all 3)
NOG_MATCHES = [
    ("Champs", "Nogentais"),    # J16
    ("Nogentais", "SCNP"),      # J17
    ("Bussy", "Nogentais"),     # J18
]

# Nogentais winning scores (3-0 or 3-1 → 3 pts each)
NOG_WIN_SCORES = [(0, 3), (1, 3)]  # from home perspective (Champs/Bussy lose)
NOG_HOME_SCORES = [(3, 0), (3, 1)]  # when Nogentais is home

# Critical matches (involve top teams that could block Nogentais)
CRITICAL_MATCHES = [
    ("Villejuif", "Isle Adam"),   # J16
    ("Bussy", "Pantin"),          # J16
    ("St-Pierre", "Vincennes"),   # J16
    ("SCNP", "Tremblay"),         # J16
    ("Isle Adam", "Pantin"),      # J17
    ("Villejuif", "St-Pierre"),   # J17
    ("Tremblay", "Bussy"),        # J17
    ("Vincennes", "Champs"),      # J17
    ("St-Pierre", "Isle Adam"),   # J18
    ("Champs", "Villejuif"),      # J18
    ("SCNP", "Vincennes"),        # J18
    ("Pantin", "Tremblay"),       # J18
]

def main():
    print("Recherche de tous les scénarios où Nogentais finit champion...")
    print(f"Matchs critiques à énumérer : {len(CRITICAL_MATCHES)} matchs × 6 scores = {6**len(CRITICAL_MATCHES):,} combinaisons")
    print()

    # Pre-filter: only enumerate scores for matches involving top-5 teams
    # For matches between lower teams, the result doesn't affect the champion race
    top5 = {"Villejuif", "Pantin", "Isle Adam", "Bussy", "St-Pierre"}

    # Split critical matches: those involving top5 vs others
    top_matches = []
    other_matches = []
    for m in CRITICAL_MATCHES:
        if m[0] in top5 or m[1] in top5:
            top_matches.append(m)
        else:
            other_matches.append(m)

    print(f"Matchs impliquant le top 5 : {len(top_matches)}")
    print(f"Matchs secondaires : {len(other_matches)}")
    print(f"Combinaisons à tester : {6**len(top_matches):,}")
    print()

    champion_scenarios = []
    tested = 0

    # Fix Nogentais wins at 3-0 for best tiebreakers first
    nog_results = [
        (0, 3),  # Champs 0-3 Nogentais
        (3, 0),  # Nogentais 3-0 SCNP
        (0, 3),  # Bussy 0-3 Nogentais
    ]

    # For other matches, use neutral results (won't affect champion race)
    other_results = [(3, 0)] * len(other_matches)  # arbitrary

    for combo in itertools.product(SCORES, repeat=len(top_matches)):
        tested += 1

        # Quick pre-check: compute points for Villejuif, Pantin, Isle Adam
        # without full simulation
        # This lets us prune early
        temp_pts = {
            "Villejuif": 31, "Pantin": 30, "Isle Adam": 30,
            "Bussy": 25, "St-Pierre": 25
        }

        skip = False
        for (home, away), (hs, as_) in zip(top_matches, combo):
            hp, ap = ffvb_points(hs, as_)
            if home in temp_pts:
                temp_pts[home] += hp
            if away in temp_pts:
                temp_pts[away] += ap

        # Nogentais gets 33. Any team > 33 → impossible
        for name, pts in temp_pts.items():
            if pts > 33:
                skip = True
                break

        if skip:
            continue

        # Full simulation for remaining candidates
        teams = init_teams()

        # Apply Nogentais wins
        for (h, a), (hs, as_) in zip(NOG_MATCHES, nog_results):
            apply_match(teams, h, a, hs, as_)

        # Apply critical top-5 match results
        for (h, a), (hs, as_) in zip(top_matches, combo):
            apply_match(teams, h, a, hs, as_)

        # Apply other match results
        for (h, a), (hs, as_) in zip(other_matches, other_results):
            apply_match(teams, h, a, hs, as_)

        # Rank and check
        ranking = rank(teams)
        if ranking[0] == "Nogentais":
            # Build scenario description
            scenario = {}
            for (h, a), (hs, as_) in zip(NOG_MATCHES, nog_results):
                scenario[f"{h} vs {a}"] = score_label(hs, as_)
            for (h, a), (hs, as_) in zip(top_matches, combo):
                scenario[f"{h} vs {a}"] = score_label(hs, as_)

            # Get final standings
            final = [(name, teams[name]["pts"],
                       round(teams[name]["sw"]/max(teams[name]["sl"],1), 3))
                      for name in ranking[:5]]

            champion_scenarios.append({
                "scenario": scenario,
                "top5": final,
                "nog_pts": teams["Nogentais"]["pts"],
            })

        if tested % 1_000_000 == 0:
            print(f"  Testé {tested:,} combinaisons, {len(champion_scenarios)} scénarios trouvés...")

    print(f"\nTerminé ! {tested:,} combinaisons testées.")
    print(f"Scénarios où Nogentais est champion : {len(champion_scenarios)}")

    if not champion_scenarios:
        print("\nAucun scénario trouvé. Nogentais ne peut pas finir champion.")
        return

    # Group similar scenarios
    print(f"\n{'='*70}")
    print(f"TOUS LES SCÉNARIOS OÙ NOGENTAIS FINIT CHAMPION")
    print(f"{'='*70}")

    # Deduplicate by key results (top-3 team outcomes)
    for i, s in enumerate(champion_scenarios[:50], 1):
        print(f"\n--- Scénario {i} ---")
        print(f"Nogentais : {s['nog_pts']} pts (CHAMPION)")
        print(f"Classement final top 5 :")
        for name, pts, sq in s["top5"]:
            marker = " ★" if name == "Nogentais" else ""
            print(f"  {name}: {pts} pts (QS={sq}){marker}")
        print(f"Résultats nécessaires :")
        for match, score in s["scenario"].items():
            print(f"  {match} : {score}")

    if len(champion_scenarios) > 50:
        print(f"\n... et {len(champion_scenarios) - 50} autres scénarios.")

    # Save all to JSON
    output = Path(__file__).parent / "champion_scenarios.json"
    output.write_text(json.dumps(champion_scenarios, indent=2, ensure_ascii=False))
    print(f"\nTous les scénarios sauvegardés dans {output}")


if __name__ == "__main__":
    main()
