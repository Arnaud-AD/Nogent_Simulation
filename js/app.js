/**
 * App orchestration — loads data, runs simulation, renders UI
 */

let pouleData = null;

async function init() {
  showLoading(true);

  try {
    const response = await fetch('data/poule_2mb.json');
    if (!response.ok) throw new Error('Impossible de charger les données');
    pouleData = await response.json();

    // Update subtitle
    const remaining = pouleData.remainingMatches.length;
    const subtitle = document.querySelector('.subtitle');
    subtitle.textContent = `Matchs restants : ${remaining}`;

    // Render scenario controls (V3) — loads saved selections from localStorage
    Scenario.renderScenarios(pouleData.remainingMatches, onScenarioChange);

    // Run initial simulation with any saved scenarios
    runAndRender(Scenario.getForcedResultsArray());

  } catch (err) {
    console.error(err);
    document.getElementById('loadingIndicator').innerHTML =
      `<p style="color:#e74c3c;">Erreur : ${err.message}</p>`;
  }
}

function runAndRender(forcedResults) {
  showLoading(true);

  // Use requestAnimationFrame to let the spinner show before heavy computation
  requestAnimationFrame(() => {
    setTimeout(() => {
      const results = Simulation.runSimulation(pouleData, 10000, forcedResults);
      Heatmap.renderHeatmap(results);
      showLoading(false);
    }, 20);
  });
}

function onScenarioChange(forcedResults) {
  runAndRender(forcedResults);
}

function showLoading(show) {
  const el = document.getElementById('loadingIndicator');
  const content = document.getElementById('mainContent');
  if (show) {
    el.style.display = 'block';
    content.style.opacity = '0.4';
  } else {
    el.style.display = 'none';
    content.style.opacity = '1';
  }
}

document.addEventListener('DOMContentLoaded', init);
