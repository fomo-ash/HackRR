const backtests = [
  { year: '2025', role: 'BATTERS', cohort: 25, legacy: 27.950, state: 22.497, consensus: 28.901 },
  { year: '2025', role: 'BOWLERS', cohort: 38, legacy: 19.029, state: 8.803, consensus: 18.003 },
  { year: '2026', role: 'BATTERS', cohort: 33, legacy: 7.717, state: 8.275, consensus: 14.260 },
  { year: '2026', role: 'BOWLERS', cohort: 45, legacy: -14.804, state: 11.893, consensus: -5.746 },
];

let rankings = [];
let currentRole = 'batting';
let selectedName = null;

const list = document.getElementById('rank-list');
const detail = document.getElementById('player-detail');
const search = document.getElementById('player-search');
const roleButtons = [...document.querySelectorAll('.role-btn')];
const exploreChart = document.getElementById('explore-chart');
const exploreInsight = document.getElementById('explore-insight');
const exploreView = document.getElementById('explore-view');
const exploreFilterButtons = [...document.querySelectorAll('.filter-chip')];
const backtestFilter = document.getElementById('backtest-filter');
let exploreRole = 'all';

const dec = (value, places = 1) => Number(value).toFixed(places);
const impact = value => `${value >= 0 ? '+' : ''}${dec(value, 1)}`;
const percent = value => `${dec(value * 100, 1)}%`;

function reasoning(player) {
  const difference = Math.abs(player.legacy_rank - player.state_rank);
  const agreement = difference <= 2
    ? `Both methods place ${player.player_name} close together: #${player.legacy_rank} legacy and #${player.state_rank} state.`
    : `The methods differ by ${difference} places (#${player.legacy_rank} legacy, #${player.state_rank} state); the final place reflects their combined rank, not either model alone.`;
  const exposure = `${dec(player.state_effective_balls)} effective state-pressure balls across ${player.state_pressure_matches} matches support the estimate.`;
  const share = player.state_positive_match_share < 0.5
    ? `Positive impact appears in ${percent(player.state_positive_match_share)} of those matches. The overall positive score is driven by the size of better performances, so consistency is a caution.`
    : `Positive impact appears in ${percent(player.state_positive_match_share)} of those matches; this share is shown as evidence, not used as a hidden ranking weight.`;
  return [agreement, exposure, share];
}

function reasoningList(player) {
  return reasoning(player).map(item => `<li>${item}</li>`).join('');
}

function renderDetail(player) {
  if (!player) {
    detail.innerHTML = '<p class="detail-kicker">PLAYER PROFILE</p><h3 class="detail-name">No match</h3><p class="detail-subtitle">Try another player name.</p>';
    return;
  }
  const roleLabel = player.role === 'batting' ? 'BATTER' : 'BOWLER';
  const roleNoun = player.role === 'batting' ? 'batting' : 'bowling';
  const legacyWidth = Math.max(5, (21 - player.legacy_rank) * 5);
  const stateWidth = Math.max(5, (21 - player.state_rank) * 5);
  detail.innerHTML = `
    <span class="detail-kicker">${roleLabel} / PLAYER PROFILE</span>
    <h3 class="detail-name">${player.player_name}</h3>
    <div class="detail-subtitle">A final top-ten ${roleNoun} selection based on two conservative pressure views.</div>
    <div class="detail-rank"><strong>#${String(player.rank).padStart(2, '0')}</strong><span>FINAL ${roleLabel} RANK</span></div>
    <div class="detail-consensus">
      <div class="detail-consensus-title"><span>MODEL AGREEMENT</span><b>RANK SUM ${player.rank_sum}</b></div>
      <div class="rank-bars">
        <div class="rank-bar"><span>LEGACY</span><div class="rank-bar-track"><div class="rank-bar-fill" style="width:${legacyWidth}%"></div></div><b>${player.legacy_rank}</b></div>
        <div class="rank-bar state"><span>STATE</span><div class="rank-bar-track"><div class="rank-bar-fill" style="width:${stateWidth}%"></div></div><b>${player.state_rank}</b></div>
      </div>
    </div>
    <div class="detail-stats">
      <div class="detail-stat"><span>STATE CONSERVATIVE SCORE</span><strong>${impact(player.state_conservative_score)}</strong></div>
      <div class="detail-stat"><span>STATE PRESSURE BALLS</span><strong>${dec(player.state_effective_balls)}</strong></div>
      <div class="detail-stat"><span>PRESSURE MATCHES</span><strong>${player.state_pressure_matches}</strong></div>
      <div class="detail-stat"><span>POSITIVE MATCH SHARE</span><strong>${percent(player.state_positive_match_share)}</strong></div>
    </div>
    <div class="reasoning-panel"><h4>Why this player made the list</h4><ol>${reasoningList(player)}</ol></div>
    <p class="detail-note">State-model whole-match bootstrap 10th–90th percentile: ${impact(player.state_bootstrap_p10)} to ${impact(player.state_bootstrap_p90)} runs per 100 effective balls. The range is for impact, not rank.</p>
  `;
}

function renderList() {
  const query = search.value.trim().toLocaleLowerCase();
  const visible = rankings.filter(player => player.role === currentRole && player.player_name.toLocaleLowerCase().includes(query));
  if (!visible.some(player => player.player_name === selectedName)) selectedName = visible[0]?.player_name ?? null;
  list.innerHTML = '<div class="rank-list-head"><span>RANK</span><span>PLAYER</span><span>LEGACY</span><span>STATE</span><span>SUM</span></div>';
  if (!visible.length) list.insertAdjacentHTML('beforeend', '<p class="no-results">No players match that search.</p>');
  visible.forEach(player => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `rank-row${player.player_name === selectedName ? ' active' : ''}`;
    button.setAttribute('aria-label', `${player.rank}. ${player.player_name}, legacy rank ${player.legacy_rank}, state rank ${player.state_rank}, rank sum ${player.rank_sum}`);
    button.setAttribute('aria-pressed', player.player_name === selectedName ? 'true' : 'false');
    button.innerHTML = `<span class="rank-num">${String(player.rank).padStart(2, '0')}</span><span class="rank-name"></span><span class="rank-cell">${player.legacy_rank}</span><span class="rank-cell">${player.state_rank}</span><span class="rank-sum">${player.rank_sum}</span>`;
    button.querySelector('.rank-name').textContent = player.player_name;
    button.addEventListener('click', () => { selectedName = player.player_name; renderList(); });
    list.append(button);
  });
  renderDetail(visible.find(player => player.player_name === selectedName));
  renderExplore();
}

roleButtons.forEach(button => button.addEventListener('click', () => {
  currentRole = button.dataset.role;
  selectedName = null;
  search.value = '';
  roleButtons.forEach(item => { item.classList.toggle('active', item === button); item.setAttribute('aria-pressed', item === button ? 'true' : 'false'); });
  renderList();
}));
search.addEventListener('input', renderList);

const svgNS = 'http://www.w3.org/2000/svg';
function svgElement(tag, attrs = {}, parent) {
  const element = document.createElementNS(svgNS, tag);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, String(value)));
  if (parent) parent.append(element);
  return element;
}

function svgText(parent, value, attrs) {
  const element = svgElement('text', attrs, parent);
  element.textContent = value;
  return element;
}

function renderExplore() {
  if (!rankings.length) return;
  const mode = exploreView.value;
  const players = rankings.filter(player => exploreRole === 'all' || player.role === exploreRole);
  const selected = players.find(player => player.player_name === selectedName) || players[0];
  const agreement = mode === 'agreement';
  document.getElementById('explore-chart-title').textContent = agreement ? 'Where the models agree' : 'Impact against exposure';
  document.getElementById('explore-chart-description').textContent = agreement
    ? 'Closer to the diagonal means the two methods rank a player similarly. Lower ranks are better.'
    : 'Higher conservative impact and more effective pressure balls move a player up and right.';

  const svg = svgElement('svg', { viewBox: '0 0 720 430', 'aria-label': agreement ? 'Scatter plot of legacy and state model rank for final selections' : 'Scatter plot of state conservative impact against pressure balls for final selections' });
  const left = 64, right = 686, top = 28, bottom = 362;
  const xValue = player => agreement ? player.legacy_rank : player.state_effective_balls;
  const yValue = player => agreement ? player.state_rank : player.state_conservative_score;
  const xMin = agreement ? 1 : 0, xMax = agreement ? 18 : 800;
  const yMin = agreement ? 1 : 0, yMax = agreement ? 18 : 40;
  const x = value => left + (value - xMin) / (xMax - xMin) * (right - left);
  const y = value => bottom - (value - yMin) / (yMax - yMin) * (bottom - top);
  const ticksX = agreement ? [1, 5, 10, 15, 18] : [0, 200, 400, 600, 800];
  const ticksY = agreement ? [1, 5, 10, 15, 18] : [0, 10, 20, 30, 40];

  ticksX.forEach(tick => {
    svgElement('line', { x1: x(tick), y1: top, x2: x(tick), y2: bottom, class: 'scatter-grid' }, svg);
    svgText(svg, String(tick), { x: x(tick), y: bottom + 22, class: 'scatter-tick', 'text-anchor': 'middle' });
  });
  ticksY.forEach(tick => {
    svgElement('line', { x1: left, y1: y(tick), x2: right, y2: y(tick), class: 'scatter-grid' }, svg);
    svgText(svg, String(tick), { x: left - 15, y: y(tick) + 4, class: 'scatter-tick', 'text-anchor': 'end' });
  });
  if (agreement) svgElement('line', { x1: x(1), y1: y(1), x2: x(18), y2: y(18), class: 'agreement-line' }, svg);
  svgText(svg, agreement ? 'LEGACY RANK →' : 'EFFECTIVE PRESSURE BALLS →', { x: (left + right) / 2, y: 414, class: 'scatter-axis-label', 'text-anchor': 'middle' });
  svgText(svg, agreement ? 'STATE RANK →' : 'STATE CONSERVATIVE IMPACT →', { x: 15, y: (top + bottom) / 2, class: 'scatter-axis-label', transform: `rotate(-90 15 ${(top + bottom) / 2})`, 'text-anchor': 'middle' });

  players.forEach(player => {
    const circle = svgElement('circle', {
      cx: x(xValue(player)), cy: y(yValue(player)), r: 5 + Math.sqrt(player.state_effective_balls / 800) * 6,
      class: `scatter-point ${player.role === 'batting' ? 'batter' : 'bowler'}${player.player_name === selected.player_name ? ' selected' : ''}`,
      tabindex: 0, role: 'button', 'aria-label': `${player.player_name}: legacy rank ${player.legacy_rank}, state rank ${player.state_rank}, ${dec(player.state_effective_balls)} effective balls`
    }, svg);
    svgElement('title', {}, circle).textContent = `${player.player_name} · #${player.rank} ${player.role} · legacy ${player.legacy_rank} / state ${player.state_rank}`;
    const choose = () => {
      currentRole = player.role;
      selectedName = player.player_name;
      search.value = '';
      roleButtons.forEach(button => { const active = button.dataset.role === currentRole; button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active)); });
      renderList();
    };
    circle.addEventListener('click', choose);
    circle.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(); } });
  });
  exploreChart.replaceChildren(svg);
  exploreInsight.innerHTML = `<span class="insight-kicker">SELECTED / #${String(selected.rank).padStart(2, '0')} ${selected.role === 'batting' ? 'BATTER' : 'BOWLER'}</span><h3>${selected.player_name}</h3><div class="insight-metrics"><div><span>LEGACY RANK</span><b>${selected.legacy_rank}</b></div><div><span>STATE RANK</span><b>${selected.state_rank}</b></div><div><span>RANK SUM</span><b>${selected.rank_sum}</b></div></div><h4>Selection reasoning</h4><ol>${reasoningList(selected)}</ol><a href="#selections">VIEW FULL PROFILE ↗</a>`;
  exploreInsight.querySelector('a').addEventListener('click', () => {
    currentRole = selected.role;
    selectedName = selected.player_name;
    search.value = '';
    roleButtons.forEach(button => { const active = button.dataset.role === currentRole; button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active)); });
    renderList();
  });
}

exploreFilterButtons.forEach(button => button.addEventListener('click', () => {
  exploreRole = button.dataset.filter;
  exploreFilterButtons.forEach(item => { const active = item === button; item.classList.toggle('active', active); item.setAttribute('aria-pressed', String(active)); });
  renderExplore();
}));
exploreView.addEventListener('change', renderExplore);

function renderChart() {
  const chart = document.getElementById('backtest-chart');
  const colors = { legacy: 'var(--gold)', state: 'var(--cyan)', consensus: 'var(--pink)' };
  chart.innerHTML = backtests.filter(group => backtestFilter.value === 'all' || group.role === backtestFilter.value).map(group => {
    const rows = ['legacy', 'state', 'consensus'].map(model => {
      const value = group[model];
      const zero = 40; // Domain: -20 to +30 runs per 100 balls.
      const reach = Math.abs(value) * 2;
      const left = value >= 0 ? zero : zero - reach;
      return `<div class="chart-row" title="${model}: ${value.toFixed(3)}"><div class="bar-track"><span class="bar-zero"></span><span class="chart-bar" style="left:${left}%;width:${reach}%;background:${colors[model]}"></span></div><span class="chart-value">${impact(value)}</span></div>`;
    }).join('');
    return `<div class="chart-group"><div class="chart-group-label">${group.year} ${group.role}<small>${group.cohort} EVALUABLE</small></div><div class="bar-stack">${rows}</div></div>`;
  }).join('');
}

renderChart();
backtestFilter.addEventListener('change', renderChart);
fetch('rankings.json')
  .then(response => { if (!response.ok) throw Error('Rankings unavailable'); return response.json(); })
  .then(data => { rankings = data; renderList(); })
  .catch(() => { list.innerHTML = '<p class="no-results">The rankings could not load. Please use the downloadable methodology report.</p>'; });
