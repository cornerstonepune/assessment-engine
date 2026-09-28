// The spine page's year and day views: a grade's syllabus fortnight by fortnight, and the school day across the
// grades. Every number comes from docs/spine/plan.json (research/plan_build.py); this only draws it. Uses the
// helpers and data of research/spine_view.js, which comes first in the page.
const MODES = DS.modes, ORDER = Object.keys(MODES);
const GRADES = [1, 2, 3, 4, 5, 6, 7];
let yearGrade = 3, scen = 0;

const clock = t => { const [h, m] = t.split(':').map(Number); return `${h > 12 ? h - 12 : h}:${String(m).padStart(2, '0')}`; };
function modesOf(band, slot) {
  if (slot === 'Community') return ['community'];
  return band.week.filter(([s]) => s === slot).map(([, m]) => MODES[m] ? m : 'academic');
}
// The day in five parts: academic time as one block (its concept, practice and check are the same in every grade of
// a stage, and have their own chart), then studio, arts, sport, and circle and close.
const partName = m => m === 'academic' ? 'Academic' : MODES[m].label;
function day(b) {
  const c = PLAN.composition[b], hour = Object.keys(DS.bands[b].anatomy);
  return [['academic', hour.reduce((a, k) => a + c[k], 0)], ...ORDER.filter(m => !hour.includes(m)).map(m => [m, c[m]])];
}
function slotsOf(g) {
  const order = [];
  DS.bands[PLAN.grades[g].band].week.forEach(([s]) => { if (!order.includes(s)) order.push(s); });
  return order.concat('Community').filter(s => PLAN.year[g][s]);
}
function segs(b) {
  const parts = day(b).filter(([, x]) => x > 0.5), total = parts.reduce((a, [, x]) => a + x, 0);
  return parts.map(([m, x]) => `<span class="seg m-${m}" style="width:${x / total * 100}%" title="${esc(partName(m))}: ${fmt(x)} minutes a day">${x / total > 0.06 ? fmt(x) : ''}</span>`).join('');
}
const said = b => 'Minutes a day: ' + day(b).filter(([, x]) => x > 0.5).map(([m, x]) => `${partName(m)} ${fmt(x)}`).join(', ');
const bar = (b, cls) => `<div class="${cls}" role="img" aria-label="${esc(said(b))}">${segs(b)}</div>`;

function openYear(g, marks = [], push = true) {
  yearGrade = g;
  show('year');
  drawYear(g, new Set(marks));
  if (push) remember('year-' + g);
  const first = document.querySelector('#ygrid .mark');
  if (first) first.scrollIntoView({behavior: calm(), block: 'center', inline: 'center'});
  else window.scrollTo({top: 0});
}
function drawYear(g, marks) {
  const G = PLAN.grades[g], band = DS.bands[G.band], S = PLAN.scenarios[0], cal = S.calendar;
  const hrs = S.hours[G.band], ncf = PLAN.ncf_hours[G.band] || {}, slots = slotsOf(g);
  const outcomes = Object.values(G.ncert_counts).reduce((a, b) => a + b, 0);
  $('picker').innerHTML = GRADES.map(x => `<button data-year="${x}" aria-pressed="${x === g}">Grade ${x}</button>`).join('');
  $('ysum').innerHTML = `<b>Grade ${g}</b> · ${esc(band.stage)} stage · ` + (G.syllabus === 'school'
    ? `the school's own map: ${fmt(G.school_objectives)} objectives, taught in the map's order`
    : `no school map yet, so NCERT's ${fmt(outcomes)} learning outcomes stand in, in NCERT's order`) +
    ` · ${cal.teach} teaching days in ${cal.days.length} fortnights. The bar is Grade ${g}'s day, in minutes, by how children learn.`;
  $('ybar').innerHTML = segs(G.band);
  $('ybar').setAttribute('aria-label', said(G.band));
  const head = '<thead><tr><th>Fortnight</th>' + slots.map(s => {
    const dots = modesOf(band, s).map(m => `<i class="m-${m}" title="${esc(partName(m))}"></i>`).join('');
    return `<th>${esc(DS.slot_names[s] || s)}<small>${fmt(hrs[s])} hours a year${ncf[s] ? ` · NCF-SE ${fmt(ncf[s])}` : ''}</small><span class="mdots">${dots}</span></th>`;
  }).join('') + '</tr></thead>';
  const body = cal.days.map((d, i) => `<tr><th>F${i + 1}${d < DS.calendar.fortnight_days ? `<small>${d} days</small>` : ''}</th>` +
    slots.map(s => `<td>${cell(g, s, i, marks)}</td>`).join('') + '</tr>').join('');
  $('ygrid').innerHTML = `<table class="year">${head}<tbody>${body}</tbody></table>`;
}
function cell(g, s, i, marks) {
  const cells = PLAN.year[g][s], here = cells[i], before = i ? cells[i - 1] : [];
  return here.map(([n, k], j) => {
    const it = ITEMS[n], cls = ['cell'];
    if (j === 0 && before.length && before[before.length - 1][0] === n) cls.push('cont');
    if (it.layer === 'outcome') cls.push('clamp');
    if (it.why) cls.push('routine');
    if (marks.has(n)) cls.push('mark');
    const count = it.layer === 'unit' ? `<span class="n">${k}</span>` : '';
    return `<button class="${cls.join(' ')}" data-n="${n}" data-g="${g}" title="${esc(it.label)}">${esc(it.label)}${count}</button>`;
  }).join('');
}

function openDay(push = true) {
  show('day');
  drawDay();
  if (push) remember('day');
  window.scrollTo({top: 0});
}
function drawDay() {
  const S = PLAN.scenarios[scen], cal = S.calendar, C = PLAN.composition;
  const academic = b => Object.keys(DS.bands[b].anatomy).reduce((a, m) => a + C[b][m], 0);
  $('scen').innerHTML = PLAN.scenarios.map((s, i) => `<button data-scen="${i}" aria-pressed="${i === scen}">${esc(s.label)}</button>`).join('') +
    `<span class="muted" style="font-size:13px">${cal.teach} teaching days${cal.saturdays ? ` and ${cal.saturdays} Saturday half-days` : ''} · ${cal.days.length} fortnights · ${clock(DS.day.start)} to ${clock(DS.day.end)}</span>`;
  $('dchart').innerHTML = GRADES.map(g => {
    const b = PLAN.grades[g].band, L = S.load[g];
    return `<div class="drow"><button class="gb" data-year="${g}">Grade ${g}</button>${bar(b, 'bar2')}` +
      `<div class="dl"><b>${fmt(academic(b))}</b> academic minutes a day · <b>${fmt(L.outcomes)}</b> NCERT outcomes at <b>${L.hours_each ? fmt(L.hours_each, 1) : '–'}</b> hours each` +
      (L.school_objectives ? ` · ${fmt(L.school_objectives)} objectives in our map` : '') + '</div></div>';
  }).join('');
  const hour = Object.keys(DS.bands['G1-2'].anatomy);
  $('dkeys').innerHTML = '<div class="key" style="grid-column:1/-1"><i class="m-academic"></i><b>Academic</b><span>Every academic hour has three parts. ' +
    hour.map(m => `<b>${esc(MODES[m].label)}:</b> ${esc(MODES[m].what)} ${esc(MODES[m].group)}.`).join(' ') + '</span></div>' +
    ORDER.filter(m => !hour.includes(m)).map(m => `<div class="key"><i class="m-${m}"></i><b>${esc(MODES[m].label)}</b><span>${esc(MODES[m].what)} ${esc(MODES[m].group)}.</span></div>`).join('');
  const L5 = S.load[5], L6 = S.load[6], L7 = S.load[7], best = PLAN.scenarios[PLAN.scenarios.length - 1].calendar;
  const n1 = PLAN.year[1].Discover.reduce((a, c) => a + c.reduce((x, [, k]) => x + k, 0), 0), h1 = S.hours['G1-2'].Discover;
  const cards = [
    ['Academic time holds steady; the load does not', `Academic time is about ${fmt(academic('G1-2'))} minutes a day in Grades 1–2, ${fmt(academic('G3-5'))} in Grades 3–5 and ${fmt(academic('G6-7'))} in Grades 6–7. The NCERT outcomes it carries go from ${L5.outcomes} in Grade 5 to ${L6.outcomes} in Grade 6 and ${L7.outcomes} in Grade 7, so the hours for each fall from ${fmt(L5.hours_each, 1)} to ${fmt(L7.hours_each, 1)}.`],
    ['So each academic hour has to do more', 'Concept time stays short and creative. Practice happens at each child’s own level. A customised check ends every block and regroups the children, and a personal paper closes every fortnight. The engine already writes those papers, so time goes to what a child has not learnt yet.'],
    ['Studio carries outcomes in groups', `From Grade 3, ${fmt(C['G3-5'].application)} minutes a day of studio carry The World Around Us, and later Science, Social Science and vocational work, through projects. By Grades 6–7 there is too little time to teach outcomes one at a time.`],
    ['Grade 1 has a studio squeeze', `The Grade 1 map puts ${n1} objectives in Discover (science, Global Perspectives, computing, home science). Discover time gives them ${fmt(h1)} hours, about ${fmt(h1 * 60 / n1)} minutes each. NCERT teaches these concerns inside language and maths in Classes I and II; the school can do the same, or give Discover more time.`],
    ['Fluid levels need shared bells', 'Maths and English run at the same hour for every section of a grade. Across Grades 3–5 the bells line up, so children can regroup by level across ages, with one educator for each level group in that hour.'],
    ['Levers', `${cal.teach} teaching days in this calendar. Alternate Saturday half-days and 8 test days instead of 20 give ${best.teach} days and ${best.saturdays} Saturdays. NCF-SE plans ${PLAN.official.instruction_days.value.days} teaching days in a ${PLAN.official.working_days.value.days}-day year.`]
  ];
  $('dcards').innerHTML = cards.map(([t, p]) => `<div class="fcard"><b>${esc(t)}</b><p>${esc(p)}</p></div>`).join('');
  $('danat').innerHTML = Object.values(DS.bands).map(b => `<div class="anat"><div><b>${esc(b.stage)}</b> · Grades ${b.grades[0]}–${b.grades[b.grades.length - 1]} · ${esc(b.arc)}</div>` +
    `<div class="daybar" role="img" aria-label="${esc(Object.entries(b.anatomy).map(([m, x]) => `${MODES[m].label} ${fmt(x * 60)} minutes`).join(', '))}">${Object.entries(b.anatomy).map(([m, x]) => `<span class="seg m-${m}" style="width:${x * 100}%" title="${esc(MODES[m].label)}">${esc(cap1(MODES[m].label.split(' ').pop()))} ${fmt(x * 60)} min</span>`).join('')}</div></div>`).join('') +
    `<p class="muted" style="font-size:13px">${esc(DS.anatomy_note)}</p>`;
  $('dsrc').innerHTML = '<summary>Where the numbers come from</summary><ul>' +
    Object.values(PLAN.official).map(o => `<li>“${esc(o.quote)}” <span class="mono muted">${esc(o.doc)} · PDF page ${o.pdf_page}${o.printed_page ? ', printed page ' + o.printed_page : ''}</span></li>`).join('') +
    '<li>The day, the seven modes, the shape of an academic hour and the weekly minutes are the school’s proposal (docs/spine/plan_design.json), drafted for discussion and not agreed.</li>' +
    '<li>Grades 1–4 follow the school’s learning-objective map, and its order is taken as the teaching order, which is an assumption. Units the subject reviewers relabelled go to their corrected subject.</li>' +
    '<li>Grades 5–7 use NCERT’s learning outcomes (2017) until the school writes its own map. Cambridge Primary and Lower Secondary are not counted yet.</li>' +
    '<li>research/plan_build.py works out every number here; research/timetable_data.py finds each official quote on its page.</li></ul>';
}
