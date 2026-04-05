/**
 * Monte Carlo simulation engine (Bradley-Terry model)
 * Port from Python simulation.py to client-side JS
 */

// Seeded PRNG (xoshiro128** for reproducibility and speed)
function createRNG(seed) {
  let s = [seed, seed ^ 0xdeadbeef, seed ^ 0xcafebabe, seed ^ 0x12345678];

  function rotl(x, k) { return ((x << k) | (x >>> (32 - k))) >>> 0; }

  function next() {
    const result = (rotl((s[1] * 5) >>> 0, 7) * 9) >>> 0;
    const t = (s[1] << 9) >>> 0;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3];
    s[2] ^= t;
    s[3] = rotl(s[3], 11);
    return result / 4294967296;
  }

  function normal(mean, std) {
    const u1 = next();
    const u2 = next();
    return mean + std * Math.sqrt(-2 * Math.log(u1 || 1e-10)) * Math.cos(2 * Math.PI * u2);
  }

  return { random: next, normal };
}

/**
 * Compute Bradley-Terry strengths from standings
 * 70% win-rate + 30% point differential, normalized to [0.5, 2.0]
 */
function computeStrengths(standings) {
  const stats = standings.map(t => {
    const winRate = (t.points / 3.0) / Math.max(t.matchesPlayed, 1);
    const ptDiff = t.pointsFor - t.pointsAgainst;
    return { name: t.name, wr: winRate, pd: ptDiff };
  });

  const wrs = stats.map(s => s.wr);
  const pds = stats.map(s => s.pd);
  const minWr = Math.min(...wrs), maxWr = Math.max(...wrs);
  const minPd = Math.min(...pds), maxPd = Math.max(...pds);

  const strengths = {};
  stats.forEach(s => {
    const normWr = maxWr > minWr ? (s.wr - minWr) / (maxWr - minWr) : 0.5;
    const normPd = maxPd > minPd ? (s.pd - minPd) / (maxPd - minPd) : 0.5;
    const combined = 0.7 * normWr + 0.3 * normPd;
    strengths[s.name] = 0.5 + combined * 1.5;
  });

  return strengths;
}

/**
 * Simulate set score for the winner
 * Returns [winnerSets, loserSets]
 */
function simulateSetScore(winnerStr, loserStr, rng) {
  const winProb = winnerStr / (winnerStr + loserStr);
  const closeness = Math.abs(winProb - 0.5) * 2;

  let p30 = 0.25, p31 = 0.40, p32 = 0.35;

  if (closeness > 0.6) {
    p30 *= 1.4;
    p32 *= 0.6;
  } else if (closeness < 0.3) {
    p32 *= 1.5;
    p30 *= 0.5;
  }

  const total = p30 + p31 + p32;
  p30 /= total; p31 /= total; p32 /= total;

  const r = rng.random();
  if (r < p30) return [3, 0];
  if (r < p30 + p31) return [3, 1];
  return [3, 2];
}

/**
 * Simulate a single match, returns [homeSets, awaySets]
 */
function simulateMatch(homeStr, awayStr, rng) {
  let pHome = homeStr / (homeStr + awayStr);
  pHome = Math.max(0.01, Math.min(0.99, pHome));

  const homeWins = rng.random() < pHome;

  if (homeWins) {
    return simulateSetScore(homeStr, awayStr, rng);
  } else {
    const [wSets, lSets] = simulateSetScore(awayStr, homeStr, rng);
    return [lSets, wSets];
  }
}

/**
 * Rank teams by FFVB rules: points > set quotient > point quotient
 */
function rankTeams(teams) {
  return Object.entries(teams)
    .sort((a, b) => {
      const ta = a[1], tb = b[1];
      if (tb.points !== ta.points) return tb.points - ta.points;
      const sqA = ta.setsWon / Math.max(ta.setsLost, 1);
      const sqB = tb.setsWon / Math.max(tb.setsLost, 1);
      if (sqB !== sqA) return sqB - sqA;
      const pqA = ta.pointsFor / Math.max(ta.pointsAgainst, 1);
      const pqB = tb.pointsFor / Math.max(tb.pointsAgainst, 1);
      return pqB - pqA;
    })
    .map(e => e[0]);
}

/**
 * Apply match result to team states
 */
function applyResult(teams, home, away, hSets, aSets, rng) {
  teams[home].setsWon += hSets;
  teams[home].setsLost += aSets;
  teams[away].setsWon += aSets;
  teams[away].setsLost += hSets;

  // Approximate points scored per set
  const noise = rng ? Math.round(rng.normal(0, 3)) : 0;
  teams[home].pointsFor += hSets * 25 + noise;
  teams[home].pointsAgainst += aSets * 25 + (rng ? Math.round(rng.normal(0, 3)) : 0);
  teams[away].pointsFor += aSets * 25 + (rng ? Math.round(rng.normal(0, 3)) : 0);
  teams[away].pointsAgainst += hSets * 25 + (rng ? Math.round(rng.normal(0, 3)) : 0);

  // FFVB points
  if (hSets === 3) {
    teams[home].points += aSets <= 1 ? 3 : 2;
    teams[away].points += aSets === 2 ? 1 : 0;
  } else {
    teams[away].points += hSets <= 1 ? 3 : 2;
    teams[home].points += hSets === 2 ? 1 : 0;
  }
}

/**
 * Run Monte Carlo simulation
 * @param {Object} data - poule data (standings, playedMatches, remainingMatches)
 * @param {number} numSimulations - number of iterations
 * @param {Array} forcedResults - [{home, away, homeSets, awaySets}]
 * @returns {Object} simulation results
 */
function runSimulation(data, numSimulations = 10000, forcedResults = []) {
  const strengths = computeStrengths(data.standings);
  const teamNames = data.standings.map(t => t.name);
  const n = teamNames.length;

  // Build forced results lookup
  const forcedMap = {};
  forcedResults.forEach(f => {
    forcedMap[f.home + '|' + f.away] = [f.homeSets, f.awaySets];
  });

  // Remaining matches not in forced results that still need simulation
  const matchesToSimulate = data.remainingMatches.filter(m => {
    return !forcedMap.hasOwnProperty(m.home + '|' + m.away);
  });

  // Position counts: positionCounts[teamName][position] = count
  const positionCounts = {};
  teamNames.forEach(name => {
    positionCounts[name] = new Array(n).fill(0);
  });

  const seed = Date.now() & 0xffffffff;

  for (let sim = 0; sim < numSimulations; sim++) {
    const rng = createRNG(seed + sim);

    // Copy team states
    const simTeams = {};
    data.standings.forEach(t => {
      simTeams[t.name] = {
        points: t.points,
        setsWon: t.setsWon,
        setsLost: t.setsLost,
        pointsFor: t.pointsFor,
        pointsAgainst: t.pointsAgainst,
      };
    });

    // Apply forced results
    for (const key in forcedMap) {
      const [home, away] = key.split('|');
      const [hSets, aSets] = forcedMap[key];
      applyResult(simTeams, home, away, hSets, aSets, null);
    }

    // Simulate remaining matches
    matchesToSimulate.forEach(m => {
      const [hSets, aSets] = simulateMatch(
        strengths[m.home], strengths[m.away], rng
      );
      applyResult(simTeams, m.home, m.away, hSets, aSets, rng);
    });

    // Rank and record positions
    const ranking = rankTeams(simTeams);
    ranking.forEach((name, pos) => {
      positionCounts[name][pos]++;
    });
  }

  // Build probability matrix (sorted by current points desc)
  const sortedTeams = [...data.standings].sort((a, b) => b.points - a.points);
  const probMatrix = [];
  const teamDetails = [];

  sortedTeams.forEach(t => {
    const counts = positionCounts[t.name];
    const row = counts.map(c => Math.round(c / numSimulations * 10000) / 100);
    probMatrix.push(row);

    const champPct = row[0];
    const maintPct = row.slice(0, 7).reduce((a, b) => a + b, 0);
    const relegPct = row.slice(7).reduce((a, b) => a + b, 0);

    // Most probable position
    let maxProb = 0, maxPos = n;
    row.forEach((p, i) => { if (p > maxProb) { maxProb = p; maxPos = i + 1; } });

    teamDetails.push({
      name: t.name,
      fullName: t.fullName,
      currentPoints: t.points,
      probabilities: row,
      championPct: champPct,
      maintenancePct: Math.round(maintPct * 100) / 100,
      relegationPct: Math.round(relegPct * 100) / 100,
      medianPosition: maxPos,
    });
  });

  return {
    teams: sortedTeams.map(t => t.name),
    currentPoints: sortedTeams.map(t => t.points),
    probabilityMatrix: probMatrix,
    teamDetails,
    numSimulations,
    remainingMatches: data.remainingMatches.length,
    strengths,
  };
}

// Export for use in other modules
window.Simulation = { runSimulation, computeStrengths };
