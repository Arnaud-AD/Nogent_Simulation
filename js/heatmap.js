/**
 * Heatmap rendering module
 */

// Highlight team is set dynamically from data
let highlightTeam = 'Nogentais';

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

function setHighlightTeam(name) {
  highlightTeam = name;
}

/**
 * Render the heatmap table and update metric cards
 */
function renderHeatmap(results) {
  const tbody = document.getElementById('heatmapBody');
  tbody.innerHTML = '';

  const globalMax = Math.max(...results.probabilityMatrix.flat());

  // Update highlight team metrics
  const detail = results.teamDetails.find(t => t.name === highlightTeam);
  if (detail) {
    document.getElementById('nogChamp').textContent = detail.championPct.toFixed(1) + '%';
    document.getElementById('nogMaint').textContent = detail.maintenancePct.toFixed(1) + '%';
    document.getElementById('nogMedian').textContent = detail.medianPosition + (detail.medianPosition === 1 ? 'er' : 'e');
    document.getElementById('nogPoints').textContent = detail.currentPoints + ' pts';

    const champEl = document.getElementById('nogChamp');
    champEl.className = detail.championPct > 10 ? 'value orange' : detail.championPct > 0 ? 'value green' : 'value red';
  }

  // Build rows
  results.teamDetails.forEach((td, teamIdx) => {
    const probs = td.probabilities;
    const isHighlight = td.name === highlightTeam;
    const isLastSafe = teamIdx === 6;

    const tr = document.createElement('tr');
    if (isLastSafe) tr.classList.add('relegation-line');

    const teamTd = document.createElement('td');
    teamTd.className = 'team-cell' + (isHighlight ? ' nogentais' : '');
    teamTd.innerHTML = `${isHighlight ? '★ ' : ''}${td.name} <span class="pts">${td.currentPoints}</span>`;
    tr.appendChild(teamTd);

    probs.forEach(prob => {
      const cell = document.createElement('td');
      cell.style.backgroundColor = getColor(prob, globalMax);
      cell.style.color = getTextColor(prob, globalMax);
      cell.style.borderRadius = '3px';
      if (prob > 0) {
        if (prob >= 1) {
          cell.textContent = Math.round(prob);
        } else if (prob >= 0.1) {
          cell.textContent = prob.toFixed(1);
        }
      }
      if (isHighlight) cell.style.fontWeight = '700';
      tr.appendChild(cell);
    });

    tbody.appendChild(tr);
  });
}

window.Heatmap = { renderHeatmap, setHighlightTeam };
