/**
 * Heatmap rendering module
 */

const FULL_NAMES = {
  "Villejuif": "US Villejuif",
  "Pantin": "Pantin Volley",
  "Isle Adam": "Isle Adam FVO",
  "Bussy": "Bussy Volley",
  "St-Pierre": "St-Pierre VB",
  "Nogentais": "VC Nogentais",
  "Champs": "VC Champs/Marne",
  "Tremblay": "Tremblay AC",
  "Vincennes": "Vincennes VC",
  "SCNP": "SC Nord Parisien"
};

function getColor(value, maxVal) {
  if (value === 0) return 'rgba(26, 26, 46, 0.8)';
  const ratio = Math.min(value / Math.max(maxVal, 1), 1);

  let r, g, b;
  if (ratio < 0.25) {
    const t = ratio / 0.25;
    r = Math.round(26 + (192 - 26) * t);
    g = Math.round(26 + (57 - 26) * t);
    b = Math.round(46 + (43 - 46) * t);
  } else if (ratio < 0.5) {
    const t = (ratio - 0.25) / 0.25;
    r = Math.round(192 + (230 - 192) * t);
    g = Math.round(57 + (126 - 57) * t);
    b = Math.round(43 + (34 - 43) * t);
  } else if (ratio < 0.75) {
    const t = (ratio - 0.5) / 0.25;
    r = Math.round(230 + (241 - 230) * t);
    g = Math.round(126 + (196 - 126) * t);
    b = Math.round(34 + (15 - 34) * t);
  } else {
    const t = (ratio - 0.75) / 0.25;
    r = Math.round(241 + (46 - 241) * t);
    g = Math.round(196 + (204 - 196) * t);
    b = Math.round(15 + (113 - 15) * t);
  }
  return `rgb(${r}, ${g}, ${b})`;
}

function getTextColor(value, maxVal) {
  if (value === 0) return '#444';
  const ratio = value / Math.max(maxVal, 1);
  return ratio > 0.6 ? '#1a1a2e' : '#fff';
}

/**
 * Render the heatmap table and update metric cards
 * @param {Object} results - simulation results from runSimulation
 */
function renderHeatmap(results) {
  const tbody = document.getElementById('heatmapBody');
  tbody.innerHTML = '';

  const globalMax = Math.max(...results.probabilityMatrix.flat());
  const n = results.teams.length;

  // Update Nogentais metrics
  const nogDetail = results.teamDetails.find(t => t.name === 'Nogentais');
  if (nogDetail) {
    document.getElementById('nogChamp').textContent = nogDetail.championPct.toFixed(1) + '%';
    document.getElementById('nogMaint').textContent = nogDetail.maintenancePct.toFixed(1) + '%';
    document.getElementById('nogMedian').textContent = nogDetail.medianPosition + (nogDetail.medianPosition === 1 ? 'er' : 'e');
    document.getElementById('nogPoints').textContent = nogDetail.currentPoints + ' pts';

    // Color the champion value
    const champEl = document.getElementById('nogChamp');
    if (nogDetail.championPct > 10) {
      champEl.className = 'value orange';
    } else if (nogDetail.championPct > 0) {
      champEl.className = 'value red';
    } else {
      champEl.className = 'value red';
    }
  }

  // Build rows
  results.teamDetails.forEach((detail, teamIdx) => {
    const probs = detail.probabilities;
    const champPct = detail.championPct;
    const maintPct = detail.maintenancePct;
    const isNogentais = detail.name === 'Nogentais';
    const isLastSafe = teamIdx === 6; // 7th position is last safe

    const tr = document.createElement('tr');
    if (isLastSafe) tr.classList.add('relegation-line');

    // Team name cell
    const teamTd = document.createElement('td');
    teamTd.className = 'team-cell' + (isNogentais ? ' nogentais' : '');
    const displayName = FULL_NAMES[detail.name] || detail.name;
    teamTd.innerHTML = `${isNogentais ? '★ ' : ''}${displayName} <span class="pts">(${detail.currentPoints}pts)</span>`;
    tr.appendChild(teamTd);

    // Position probabilities
    probs.forEach(prob => {
      const td = document.createElement('td');
      td.style.backgroundColor = getColor(prob, globalMax);
      td.style.color = getTextColor(prob, globalMax);
      td.style.borderRadius = '4px';
      if (prob > 0) {
        td.textContent = prob < 0.1 ? '' : prob.toFixed(1);
      }
      if (isNogentais) td.style.fontWeight = '700';
      tr.appendChild(td);
    });

    // Champion % side cell
    const champTd = document.createElement('td');
    champTd.className = 'side-cell';
    champTd.innerHTML = champPct > 0
      ? `<span class="champ">${champPct.toFixed(1)}%</span>`
      : '—';
    tr.appendChild(champTd);

    // Maintenance % side cell
    const maintTd = document.createElement('td');
    maintTd.className = 'side-cell';
    maintTd.innerHTML = `<span class="maint">${maintPct.toFixed(1)}%</span>`;
    tr.appendChild(maintTd);

    tbody.appendChild(tr);
  });
}

window.Heatmap = { renderHeatmap, FULL_NAMES };
