/**
 * Scenario module (V3) — Interactive score selection for remaining matches
 */

const SCORES = [
  { label: '3-0', homeSets: 3, awaySets: 0 },
  { label: '3-1', homeSets: 3, awaySets: 1 },
  { label: '3-2', homeSets: 3, awaySets: 2 },
  { label: '2-3', homeSets: 2, awaySets: 3 },
  { label: '1-3', homeSets: 1, awaySets: 3 },
  { label: '0-3', homeSets: 0, awaySets: 3 },
];

// Current forced results: { "home|away": { homeSets, awaySets } }
let forcedResults = {};
let onChangeCallback = null;

function getForcedResultsArray() {
  return Object.entries(forcedResults).map(([key, val]) => {
    const [home, away] = key.split('|');
    return { home, away, homeSets: val.homeSets, awaySets: val.awaySets };
  });
}

function renderScenarios(remainingMatches, onChange) {
  onChangeCallback = onChange;
  const container = document.getElementById('scenarioContainer');
  container.innerHTML = '';

  if (!remainingMatches || remainingMatches.length === 0) {
    container.innerHTML = '<p style="color:#555;font-size:0.75rem;">Tous les matchs ont été joués.</p>';
    return;
  }

  // Group by journee
  const byJournee = {};
  remainingMatches.forEach(m => {
    const j = m.journee || '?';
    if (!byJournee[j]) byJournee[j] = [];
    byJournee[j].push(m);
  });

  const resetBtn = document.getElementById('scenarioResetBtn');
  resetBtn.disabled = Object.keys(forcedResults).length === 0;
  resetBtn.onclick = () => {
    forcedResults = {};
    renderScenarios(remainingMatches, onChange);
    onChange(getForcedResultsArray());
  };

  Object.entries(byJournee).sort((a, b) => a[0] - b[0]).forEach(([journee, matches]) => {
    const group = document.createElement('div');
    group.className = 'journee-group';

    const label = document.createElement('div');
    label.className = 'journee-label';
    label.textContent = `Journée ${journee}`;
    group.appendChild(label);

    matches.forEach(match => {
      const key = match.home + '|' + match.away;
      const row = document.createElement('div');
      row.className = 'match-row' + (forcedResults[key] ? ' has-selection' : '');

      const homeName = Heatmap.FULL_NAMES[match.home] || match.home;
      const awayName = Heatmap.FULL_NAMES[match.away] || match.away;

      const teams = document.createElement('div');
      teams.className = 'match-teams';
      teams.innerHTML = `<span class="home">${homeName}</span><span class="vs">vs</span><span class="away">${awayName}</span>`;
      if (match.date) {
        teams.innerHTML += `<span class="date-info">${match.date}</span>`;
      }
      row.appendChild(teams);

      const btns = document.createElement('div');
      btns.className = 'score-buttons';

      SCORES.forEach(score => {
        const btn = document.createElement('button');
        btn.className = 'score-btn';
        btn.textContent = score.label;

        // Color code: home win = green tint, away win = red tint
        if (score.homeSets > score.awaySets) {
          btn.classList.add('home-win');
        } else {
          btn.classList.add('away-win');
        }

        // Check if this score is currently selected
        const current = forcedResults[key];
        if (current && current.homeSets === score.homeSets && current.awaySets === score.awaySets) {
          btn.classList.add('selected');
        }

        btn.addEventListener('click', () => {
          // Toggle: if same score clicked, deselect
          if (current && current.homeSets === score.homeSets && current.awaySets === score.awaySets) {
            delete forcedResults[key];
          } else {
            forcedResults[key] = { homeSets: score.homeSets, awaySets: score.awaySets };
          }
          renderScenarios(remainingMatches, onChange);
          onChange(getForcedResultsArray());
        });

        btns.appendChild(btn);
      });

      row.appendChild(btns);
      group.appendChild(row);
    });

    container.appendChild(group);
  });
}

window.Scenario = { renderScenarios, getForcedResultsArray };
