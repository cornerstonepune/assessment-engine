// The spine page's Plan view: each grade's syllabus laid onto the school year. Data: docs/spine/plan.json, built by
// research/plan_build.py from the school's map, NCERT's outcomes, NCF-SE's checked hours and the school's proposed day
// (docs/spine/plan_design.json). Uses the page's N (spine nodes) and its data-go links into the explorer.
(function () {
  const P = JSON.parse(document.getElementById('plan-data').textContent);
  const DS = P.design, CAL = DS.calendar, MODES = DS.modes;
  const ORDER = ['concept', 'practice', 'check', 'application', 'arts', 'sport', 'community'];
  const ACADS = ['concept', 'practice', 'check'];
  const MATCH = {eng: 'R1', math: 'Maths', evs: 'TWAU', sci: 'Science', sst: 'SS'};
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const fmt = (x, d = 0) => Number(x).toLocaleString('en-IN', {maximumFractionDigits: d, minimumFractionDigits: d});
  const SCEN = [
    {id: 'plan', label: 'Mon–Fri, NCF-SE’s 20 test days', sat: false, tests: CAL.test_days},
    {id: 'sat', label: '+ alternate Saturday half-days', sat: true, tests: CAL.test_days},
    {id: 'both', label: '+ Saturdays, 8 test days', sat: true, tests: 8}
  ];
  let scen = SCEN[0], grade = 3, cellKey = null;

  function cal(s) {
    const weeks = 52 - CAL.summer_weeks - CAL.diwali_weeks, work = weeks * 5 - CAL.weekday_holidays;
    const teach = work - s.tests - CAL.event_days, sats = s.sat ? Math.floor(weeks / 2) : 0, days = [];
    for (let left = teach; left > 0; left -= CAL.fortnight_days) days.push(Math.min(CAL.fortnight_days, left));
    return {weeks, work, teach, sats, days};
  }
  const bandOf = g => g <= 2 ? 'G1-2' : g <= 5 ? 'G3-5' : 'G6-7';
  function week(band) { // {slot: {mode: minutes a week}}
    const out = {};
    for (const [slot, mode, min] of DS.bands[band].week) (out[slot] = out[slot] || {})[mode] = ((out[slot] || {})[mode] || 0) + min;
    return out;
  }
  function hours(band, c) { // hours a year per slot
    const sat = DS.bands[band].saturday || {}, out = {};
    for (const [slot, modes] of Object.entries(week(band))) {
      const min = Object.values(modes).reduce((a, b) => a + b, 0);
      out[slot] = min / 60 * c.teach / 5 + (sat[slot] || 0) * c.sats * CAL.saturday_minutes / 60;
    }
    out.Community = DS.day.community / 60 * c.teach;
    return out;
  }
  function composition(band) { // minutes a weekday per mode
    const an = DS.bands[band].anatomy, out = Object.fromEntries(ORDER.map(m => [m, 0]));
    out.community = DS.day.community;
    for (const [, mode, min] of DS.bands[band].week) {
      if (mode === 'acads') ACADS.forEach(k => { out[k] += min / 5 * an[k]; });
      else out[mode] += min / 5;
    }
    return out;
  }
  const items = (g, slot) => { const s = P.grades[g].slots[slot]; return !s ? 0 : s.units ? s.units.reduce((a, u) => a + u[2], 0) : s.outcomes.length; };
  function spread(g, slot, c) { // fortnight -> [{id, label, n}], paced by teaching days, in the syllabus's order
    const s = P.grades[g].slots[slot], out = c.days.map(() => []);
    if (!s) return out;
    const flat = s.units ? s.units.flatMap(u => Array(u[2]).fill(u)) : s.outcomes.map(id => [id, (N[id] && N[id].label) || id, 1]);
    const total = c.days.reduce((a, b) => a + b, 0), cum = [];
    c.days.reduce((a, d, i) => (cum[i] = a + d), 0);
    flat.forEach((u, i) => {
      let k = cum.findIndex(x => (i + 0.5) / flat.length * total < x);
      if (k < 0) k = out.length - 1;
      const cell = out[k], last = cell[cell.length - 1];
      if (last && last.id === u[0] && last.label === u[1]) last.n++; else cell.push({id: u[0], label: u[1], n: 1});
    });
    return out;
  }
  function load(g, c) { // NCERT outcomes against the hours of the slots that teach them
    const h = hours(bandOf(g), c), used = new Set();
    let n = 0, hrs = 0;
    for (const [subj, k] of Object.entries(P.grades[g].ncert_counts)) {
      const slot = MATCH[subj];
      if (h[slot] == null) continue;
      n += k;
      if (!used.has(slot)) { hrs += h[slot]; used.add(slot); }
    }
    return {n, per: n ? hrs / n : null, school: P.grades[g].school_objectives || null};
  }
  const seg = (m, min, max) => `<span class="pl-seg m-${m}" style="width:${min / max * 100}%" title="${esc(MODES[m].label)}: ${fmt(min)} min a day">${min / max > 0.075 ? fmt(min) : ''}</span>`;

  function renderComp(c) {
    const max = DS.day.instruction + DS.day.community;
    let h = '';
    for (let g = 1; g <= 7; g++) {
      const comp = composition(bandOf(g)), L = load(g, c);
      h += `<div class="pl-row"><button class="pl-g" data-pgrade="${g}" aria-pressed="${g === grade}">Grade ${g}</button>` +
        `<div class="pl-bar">${ORDER.filter(m => comp[m] > 0.5).map(m => seg(m, comp[m], max)).join('')}</div>` +
        `<div class="pl-load"><b>${fmt(L.n)}</b> NCERT outcomes · <b>${L.per ? fmt(L.per, 1) : '–'} h</b> each${L.school ? ` · ${fmt(L.school)} school objectives` : ''}</div></div>`;
    }
    document.getElementById('pl-comp').innerHTML = h;
    document.getElementById('pl-legend').innerHTML = ORDER.map(m => `<div class="pl-leg"><span class="pl-sw m-${m}"></span><b>${esc(MODES[m].label)}</b><span class="pl-what">${esc(MODES[m].what)} <i>${esc(MODES[m].group)}.</i></span>` +
      `<span class="pl-caps">${MODES[m].caps.filter(id => N[id]).map(id => `<button class="pl-cap" data-go="${esc(id)}">${esc(N[id].label)}</button>`).join('')}</span></div>`).join('');
  }
  function renderAnatomy() {
    document.getElementById('pl-anat').innerHTML = Object.values(DS.bands).map(b => `<div class="pl-an"><div><b>${esc(b.stage)}</b> · Grades ${b.grades[0]}–${b.grades[b.grades.length - 1]} · ${esc(b.arc)}</div>` +
      `<div class="pl-bar small">${ACADS.map(k => `<span class="pl-seg m-${k}" style="width:${b.anatomy[k] * 100}%">${esc(MODES[k].label)} ${fmt(b.anatomy[k] * 60)}′</span>`).join('')}</div></div>`).join('') +
      `<p class="meta">${esc(DS.anatomy_note)}</p>`;
  }
  function renderGrade(c) {
    const band = bandOf(grade), h = hours(band, c), ncf = P.ncf_hours[band] || {}, w = week(band), G = P.grades[grade];
    const slots = Object.keys(w).concat('Community');
    let t = '<table class="pl-t"><thead><tr><th>Slot</th><th>How it is taught</th><th class="num">Hours a year</th><th class="num">NCF-SE</th><th class="num">Syllabus items</th><th class="num">Hours each</th></tr></thead><tbody>';
    for (const s of slots) {
      const modes = s === 'Community' ? {community: 1} : w[s], n = items(grade, s), ref = ncf[s], pct = ref ? h[s] / ref * 100 : null;
      const dots = Object.keys(modes).flatMap(m => m === 'acads' ? ACADS : [m]).map(m => `<span class="pl-dot m-${m}" title="${esc(MODES[m].label)}"></span>`).join('');
      t += `<tr><td>${esc(DS.slot_names[s] || s)}</td><td>${dots}</td><td class="num">${fmt(h[s])}</td>` +
        `<td class="num">${ref ? `${fmt(ref)} <span class="${pct >= 97 ? 'ok' : pct >= 80 ? 'mid' : 'low'}">${fmt(pct)}%</span>` : '–'}</td>` +
        `<td class="num">${n || '–'}</td><td class="num">${n ? fmt(h[s] / n, 1) : '–'}</td></tr>`;
    }
    const intro = G.syllabus === 'school' ? `Grade ${grade} follows the school's own map: ${fmt(G.school_objectives)} objectives, in the map's order, grouped by unit.` : `Grade ${grade} has no school map yet, so NCERT's learning outcomes stand in.`;
    document.getElementById('pl-hours').innerHTML = `<p class="meta">${esc(intro)}</p><div class="pl-scroll">${t}</tbody></table></div>`;
    let f = `<table class="pl-f"><thead><tr><th>Slot</th>${c.days.map((d, i) => `<th title="${d} teaching days">F${i + 1}${d < CAL.fortnight_days ? `<small>${d} days</small>` : ''}</th>`).join('')}</tr></thead><tbody>`;
    for (const s of slots) {
      if (!items(grade, s)) continue;
      f += `<tr><td>${esc(DS.slot_names[s] || s)}</td>` + spread(grade, s, c).map((cell, i) => {
        const n = cell.reduce((a, x) => a + x.n, 0), key = `${grade}|${s}|${i}`;
        return `<td><button class="pl-cell${key === cellKey ? ' on' : ''}" data-pcell="${key}" aria-label="${esc(s)}, fortnight ${i + 1}: ${n} items">${n || ''}</button></td>`;
      }).join('') + '</tr>';
    }
    f += `<tr class="pl-check"><td>Customised check</td>${c.days.map(() => '<td title="A personal paper from the engine on the fortnight’s last day">✎</td>').join('')}</tr></tbody></table>`;
    document.getElementById('pl-fort').innerHTML = `<div class="pl-scroll">${f}</div><p class="meta">Each cell is the number of syllabus items that fortnight, in the syllabus's order and paced by teaching days. ✎ marks a personal paper from the engine on each fortnight's last day. Pick a cell to see what it holds.</p>`;
    renderCell(c);
  }
  function renderCell(c) {
    const box = document.getElementById('pl-cell');
    const [g, s, i] = (cellKey || '').split('|');
    if (!cellKey || Number(g) !== grade) { box.innerHTML = ''; return; }
    const cell = spread(Number(g), s, c)[Number(i)] || [], unit = P.grades[g].syllabus === 'school';
    box.innerHTML = `<div class="grp"><div class="h"><span>Grade ${g} · ${esc(DS.slot_names[s] || s)} · fortnight ${Number(i) + 1} · ${c.days[Number(i)] || 0} days</span></div>` +
      (cell.map(x => `<button class="row" ${x.id && N[x.id] ? `data-go="${esc(x.id)}"` : 'disabled'}><span class="l">${esc(x.label)}</span><span class="s">${unit ? `${x.n} objective${x.n > 1 ? 's' : ''} of this unit` : 'NCERT outcome'}</span></button>`).join('') || '<div class="row meta">nothing planned</div>') + '</div>';
  }
  function renderSays(c) {
    const L5 = load(5, c), L6 = load(6, c), L7 = load(7, c), best = cal(SCEN[2]);
    const ac = b => ACADS.reduce((a, k) => a + composition(b)[k], 0), h1 = hours('G1-2', c), n1 = items(1, 'Discover');
    const cards = [
      ['Academic time holds steady; the load does not', `Academic time is about ${fmt(ac('G1-2'))} minutes a day in Grades 1–2, ${fmt(ac('G3-5'))} in 3–5 and ${fmt(ac('G6-7'))} in 6–7. The NCERT outcomes it must carry go from ${L5.n} in Grade 5 to ${L6.n} in Grade 6 and ${L7.n} in Grade 7, so hours per outcome fall from ${fmt(L5.per, 1)} to ${fmt(L7.per, 1)}.`],
      ['So each academic hour has to do more', 'Concept time stays short and creative. Practice happens at each child’s own level. A customised check ends every block and regroups the children, and a personal paper closes every fortnight. The engine already writes those papers, so time goes to what a child has not learnt yet.'],
      ['Studio carries outcomes in groups', 'From Grade 3, 64 minutes a day of studio carry The World Around Us, and later Science, Social Science and vocational work, through projects. By Grades 6–7 there is too little time to teach outcomes one at a time.'],
      ['Grade 1 has a studio squeeze', `The Grade 1 map has ${n1} studio objectives (science, Global Perspectives, computing, home science). Discover time gives them ${fmt(h1.Discover)} hours, about ${fmt(h1.Discover * 60 / n1)} minutes each. NCERT teaches these concerns inside language and maths in Classes I and II; the school can do the same, or give Discover more time.`],
      ['Fluid levels need shared bells', 'Maths and R1 run at the same hour for every section of a grade. Across Grades 3–5 the bells line up, so children can regroup by level across ages, with one educator per level group in that hour.'],
      ['Levers', `${c.teach} teaching days at present. Alternate Saturday half-days and 8 test days instead of 20 give ${best.teach} days plus ${best.sats} Saturdays. NCF-SE plans 180 teaching days in a 220-day year.`]
    ];
    document.getElementById('pl-says').innerHTML = cards.map(([t, p]) => `<div class="pl-card"><b>${esc(t)}</b><p>${esc(p)}</p></div>`).join('');
  }
  function renderSources() {
    const off = Object.values(P.official).map(o => `<li>“${esc(o.quote)}” <span class="mono">${esc(o.doc)} · PDF p.${o.pdf_page}${o.printed_page ? ' · printed p.' + o.printed_page : ''}</span></li>`).join('');
    document.getElementById('pl-src').innerHTML = `<details class="notes"><summary>Where the numbers come from</summary><ul>${off}` +
      '<li>The day, the seven modes, the shape of an academic hour and the weekly minutes are the school’s proposal (docs/spine/plan_design.json), drafted for discussion.</li>' +
      '<li>Grades 1–4 follow the school’s learning-objective map. Its order is taken as the teaching order, which is an assumption. Units relabelled by the subject seats go to their corrected slot. Grade 4’s signal tags differ from Grades 1–3 (62% “Foundational”), so modes come from the design, not from tags.</li>' +
      '<li>Grades 5–7 use NCERT’s outcomes (2017) until the school writes its own map. Cambridge Primary and Lower Secondary are not counted yet.</li>' +
      '<li>Built by research/plan_build.py; the official quotes are checked on their page by research/timetable_data.py.</li></ul></details>';
  }
  function renderPlan() {
    const c = cal(scen);
    document.getElementById('pl-scen').innerHTML = SCEN.map(s => `<button data-pscen="${s.id}" aria-pressed="${s === scen}">${esc(s.label)}</button>`).join('') +
      `<span class="meta">${c.teach} teaching days${c.sats ? ` + ${c.sats} Saturdays` : ''} · ${c.days.length} fortnights · 8:30–2:30</span>`;
    document.getElementById('pl-gtitle').textContent = `Grade ${grade}: hours and fortnights`;
    renderComp(c); renderSays(c); renderAnatomy(); renderGrade(c);
  }
  const WHERE = {};
  (function () {
    const c = cal(SCEN[0]);
    for (let g = 1; g <= 7; g++) for (const s of Object.keys(P.grades[g].slots)) spread(g, s, c).forEach((cell, i) => cell.forEach(x => {
      if (!x.id) return;
      const k = `Grade ${g} · ${DS.slot_names[s] || s}`, w = WHERE[x.id] = WHERE[x.id] || {};
      if (!(w[k] = w[k] || []).includes(i + 1)) w[k].push(i + 1);
    }));
  })();
  window.PLAN_WHERE = id => Object.entries(WHERE[id] || {}).map(([k, fs]) => `${k}, fortnight${fs.length > 1 ? 's' : ''} ${fs[0]}${fs.length > 1 ? '–' + fs[fs.length - 1] : ''}`).join('; ');
  document.body.addEventListener('click', e => {
    const s = e.target.closest('[data-pscen]'), g = e.target.closest('[data-pgrade]'), k = e.target.closest('[data-pcell]');
    if (s) { scen = SCEN.find(x => x.id === s.dataset.pscen); renderPlan(); }
    else if (g) { grade = Number(g.dataset.pgrade); cellKey = null; renderPlan(); }
    else if (k) { cellKey = k.dataset.pcell; renderGrade(cal(scen)); }
  });
  window.renderPlan = renderPlan;
  renderSources();
})();
