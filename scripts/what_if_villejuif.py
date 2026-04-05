#!/usr/bin/env python3
"""
What if Nogentais had won 3-1 vs Villejuif (J14) instead of losing 1-3?
Run Monte Carlo with modified standings.
"""

import json
import sys
from pathlib import Path

# Add parent to path for importing simulation logic
sys.path.insert(0, str(Path(__file__).parent.parent))

data = json.loads((Path(__file__).parent.parent / "data" / "poule_2mb.json").read_text())

# --- Modify the J14 match result ---
# Original: Villejuif 3-1 Nogentais → Villejuif +3pts, Nogentais +0pts
# New:      Villejuif 1-3 Nogentais → Villejuif +0pts, Nogentais +3pts

# Original match scores: 25:20, 25:21, 23:25, 25:21
# Villejuif scored 98, Nogentais scored 87

for t in data["standings"]:
    if t["name"] == "Villejuif":
        t["points"] -= 3        # Remove the 3 pts from win
        t["setsWon"] -= 3       # Remove 3 sets won
        t["setsLost"] -= 1      # Remove 1 set lost
        t["setsWon"] += 1       # Add 1 set won (from losing 1-3)
        t["setsLost"] += 3      # Add 3 sets lost
        t["pointsFor"] -= 98    # Remove points scored
        t["pointsFor"] += 87    # Add points as if they scored less
        t["pointsAgainst"] -= 87
        t["pointsAgainst"] += 98
        print(f"Villejuif: {t['points']} pts, SW={t['setsWon']}, SL={t['setsLost']}")

    elif t["name"] == "Nogentais":
        t["points"] += 3        # Add the 3 pts from win
        t["setsWon"] -= 1       # Remove 1 set won (from losing)
        t["setsLost"] -= 3      # Remove 3 sets lost
        t["setsWon"] += 3       # Add 3 sets won
        t["setsLost"] += 1      # Add 1 set lost
        t["pointsFor"] -= 87
        t["pointsFor"] += 98
        t["pointsAgainst"] -= 98
        t["pointsAgainst"] += 87
        print(f"Nogentais: {t['points']} pts, SW={t['setsWon']}, SL={t['setsLost']}")

# Also update the played match record
for m in data["playedMatches"]:
    if m["home"] == "Villejuif" and m["away"] == "Nogentais" and m["journee"] == 14:
        m["homeSets"] = 1
        m["awaySets"] = 3
        print(f"Match J14 modifié: Villejuif {m['homeSets']}-{m['awaySets']} Nogentais")
        break

# Print new standings
print("\n--- CLASSEMENT MODIFIÉ ---")
standings_sorted = sorted(data["standings"], key=lambda t: -t["points"])
for i, t in enumerate(standings_sorted, 1):
    sq = t["setsWon"] / max(t["setsLost"], 1)
    print(f"  {i}. {t['name']:12s} {t['points']} pts  (QS={sq:.3f})")

# --- Run simulation using the JS engine logic ported to Python ---
import itertools
from collections import defaultdict
import random

def ffvb_points(h_sets, a_sets):
    if h_sets == 3:
        return (3 if a_sets <= 1 else 2, 1 if a_sets == 2 else 0)
    else:
        return (1 if h_sets == 2 else 0, 3 if h_sets <= 1 else 2)

def compute_strengths(standings):
    stats = {}
    for t in standings:
        wr = (t["points"] / 3.0) / max(t["matchesPlayed"], 1)
        pd = t["pointsFor"] - t["pointsAgainst"]
        stats[t["name"]] = {"wr": wr, "pd": pd}

    wrs = [s["wr"] for s in stats.values()]
    pds = [s["pd"] for s in stats.values()]
    min_wr, max_wr = min(wrs), max(wrs)
    min_pd, max_pd = min(pds), max(pds)

    strengths = {}
    for name, s in stats.items():
        norm_wr = (s["wr"] - min_wr) / (max_wr - min_wr) if max_wr > min_wr else 0.5
        norm_pd = (s["pd"] - min_pd) / (max_pd - min_pd) if max_pd > min_pd else 0.5
        combined = 0.7 * norm_wr + 0.3 * norm_pd
        strengths[name] = 0.5 + combined * 1.5
    return strengths

def simulate_match(home_str, away_str, rng):
    p_home = home_str / (home_str + away_str)
    p_home = max(0.01, min(0.99, p_home))
    home_wins = rng.random() < p_home

    closeness = abs(p_home - 0.5) * 2
    p30, p31, p32 = 0.25, 0.40, 0.35
    if closeness > 0.6:
        p30 *= 1.4; p32 *= 0.6
    elif closeness < 0.3:
        p32 *= 1.5; p30 *= 0.5
    total = p30 + p31 + p32
    p30 /= total; p31 /= total; p32 /= total

    r = rng.random()
    if r < p30: w_sets, l_sets = 3, 0
    elif r < p30 + p31: w_sets, l_sets = 3, 1
    else: w_sets, l_sets = 3, 2

    if home_wins:
        return w_sets, l_sets
    else:
        return l_sets, w_sets

NUM_SIMS = 100_000
strengths = compute_strengths(data["standings"])

print(f"\n--- SIMULATION MONTE CARLO ({NUM_SIMS:,} itérations) ---")
print(f"Forces: {', '.join(f'{k}={v:.3f}' for k, v in sorted(strengths.items(), key=lambda x: -x[1]))}")

team_names = [t["name"] for t in data["standings"]]
n = len(team_names)
position_counts = {name: [0]*n for name in team_names}

for sim in range(NUM_SIMS):
    rng = random.Random(sim + 42)

    # Copy states
    teams = {}
    for t in data["standings"]:
        teams[t["name"]] = {
            "pts": t["points"],
            "sw": t["setsWon"],
            "sl": t["setsLost"],
            "pf": t["pointsFor"],
            "pa": t["pointsAgainst"],
        }

    # Simulate remaining matches
    for m in data["remainingMatches"]:
        h, a = m["home"], m["away"]
        hs, as_ = simulate_match(strengths[h], strengths[a], rng)

        hp, ap = ffvb_points(hs, as_)
        teams[h]["pts"] += hp
        teams[a]["pts"] += ap
        teams[h]["sw"] += hs
        teams[h]["sl"] += as_
        teams[a]["sw"] += as_
        teams[a]["sl"] += hs
        teams[h]["pf"] += hs * 25
        teams[h]["pa"] += as_ * 25
        teams[a]["pf"] += as_ * 25
        teams[a]["pa"] += hs * 25

    # Rank
    def key(name):
        t = teams[name]
        sq = t["sw"] / max(t["sl"], 1)
        pq = t["pf"] / max(t["pa"], 1)
        return (-t["pts"], -sq, -pq)

    ranking = sorted(team_names, key=key)
    for pos, name in enumerate(ranking):
        position_counts[name][pos] += 1

# Results
print("\n--- RÉSULTATS ---")
print(f"{'Équipe':15s} {'Pts':>4s}  {'1er':>6s}  {'2e':>6s}  {'3e':>6s}  {'4e':>6s}  {'5e':>6s}  {'6e':>6s}  {'7e':>6s}  {'Maint.':>7s}  {'Releg.':>7s}")
print("-" * 100)

standings_sorted = sorted(data["standings"], key=lambda t: -t["points"])
for t in standings_sorted:
    name = t["name"]
    counts = position_counts[name]
    row = [round(100 * c / NUM_SIMS, 1) for c in counts]
    maint = sum(row[:7])
    releg = sum(row[7:])
    is_nog = " ★" if name == "Nogentais" else ""
    print(f"{name+is_nog:15s} {t['points']:>4d}  {row[0]:>5.1f}%  {row[1]:>5.1f}%  {row[2]:>5.1f}%  {row[3]:>5.1f}%  {row[4]:>5.1f}%  {row[5]:>5.1f}%  {row[6]:>5.1f}%  {maint:>6.1f}%  {releg:>6.1f}%")
