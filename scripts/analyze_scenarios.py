#!/usr/bin/env python3
"""Analyze champion scenarios to find common patterns."""

import json
from pathlib import Path
from collections import Counter

data = json.loads((Path(__file__).parent / "champion_scenarios.json").read_text())

print(f"Total scénarios : {len(data)}")
print()

# For each match, count how often each score appears
match_scores = {}
for s in data:
    for match, score in s["scenario"].items():
        if match not in match_scores:
            match_scores[match] = Counter()
        match_scores[match][score] += 1

total = len(data)

print("=" * 70)
print("RÉSULTATS OBLIGATOIRES (présents dans 100% des scénarios)")
print("=" * 70)
for match, scores in match_scores.items():
    if len(scores) == 1:
        score, count = list(scores.items())[0]
        print(f"  {match} : {score}")

print()
print("=" * 70)
print("RÉSULTATS POSSIBLES (par match)")
print("=" * 70)
for match, scores in match_scores.items():
    if len(scores) > 1:
        print(f"\n  {match} :")
        for score, count in scores.most_common():
            pct = count / total * 100
            print(f"    {score} → {pct:.1f}% des scénarios ({count})")

# Analyze who must win/lose
print()
print("=" * 70)
print("QUI DOIT GAGNER / PERDRE (résumé)")
print("=" * 70)

for match, scores in match_scores.items():
    home, away = match.split(" vs ")
    home_wins = sum(c for s, c in scores.items() if int(s[0]) == 3)
    away_wins = sum(c for s, c in scores.items() if int(s[2]) == 3)

    if home_wins == total:
        print(f"  {home} DOIT battre {away}")
    elif away_wins == total:
        print(f"  {away} DOIT battre {home}")
    elif home_wins == 0:
        print(f"  {home} DOIT perdre contre {away}")
    elif away_wins == 0:
        print(f"  {away} DOIT perdre contre {home}")
    else:
        pct = home_wins / total * 100
        print(f"  {home} vs {away} : {home} gagne dans {pct:.0f}%, {away} dans {100-pct:.0f}%")

# Points distribution for top teams
print()
print("=" * 70)
print("POINTS FINAUX DES ÉQUIPES DANS CES SCÉNARIOS")
print("=" * 70)

team_pts = {}
for s in data:
    for name, pts, sq in s["top5"]:
        if name not in team_pts:
            team_pts[name] = Counter()
        team_pts[name][pts] += 1

# Also check Nogentais
nog_pts = Counter(s["nog_pts"] for s in data)
print(f"\n  Nogentais : {dict(nog_pts)}")

for name in ["Villejuif", "Pantin", "Isle Adam", "Bussy", "St-Pierre"]:
    if name in team_pts:
        pts_dist = team_pts[name]
        print(f"  {name} : {dict(pts_dist.most_common())}")
