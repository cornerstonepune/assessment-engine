// The spine page's thread view, search and sections. Its data is the page-data block that research/spine_page.py
// builds: the items (each named by its place in the list), each item's thread through the five steps
// (research/spine_thread.py) and the plan (research/plan_build.py). This script only draws. Every link and every
// number is worked out in Python, where packages/engine/tests/test_spine_page.py checks them.
const D = JSON.parse(document.getElementById('page-data').textContent);
const ITEMS = D.items, PLAN = D.plan, DS = PLAN.design;
const AT = {};
ITEMS.forEach((it, n) => { AT[it.id] = n; });
const ESC = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '\x22': '&quot;'};
const esc = s => String(s ?? '').replace(/[&<>\x22]/g, c => ESC[c]);
const fmt = (x, d = 0) => Number(x).toLocaleString('en-IN', {maximumFractionDigits: d, minimumFractionDigits: d});
const $ = id => document.getElementById(id);
const cap1 = s => s ? s[0].toUpperCase() + s.slice(1) : '';
const short = s => s.length > 48 ? s.slice(0, 46) + '…' : s;
const calm = () => matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
const STEP = {
  why: ['Why', 'The capabilities it builds, and the words they show'],
  asks: ['What NCF-SE asks', 'The competencies behind it, under their curricular goals'],
  grade: ['In the grade', 'What NCERT expects, and what we teach'],
  when: ['When', 'The fortnights of the year it is taught in'],
  check: ['How we check', "The engine's skills, and the rungs that test them"]
};
const TYPE = {word: 'Graduate word', capability: 'Capability', behaviour: 'What an educator sees', goal: 'Curricular goal',
  competency: 'Competency', outcome: 'NCERT outcome', unit: 'Our unit', skill: 'Engine skill', rung: 'Rung', grade: 'Grade'};
const NOUN = {word: ['word', 'words'], capability: ['capability', 'capabilities'], behaviour: ['observation', 'observations'],
  goal: ['goal', 'goals'], competency: ['competency', 'competencies'], outcome: ['NCERT outcome', 'NCERT outcomes'],
  unit: ['unit', 'units'], skill: ['skill', 'skills'], rung: ['rung', 'rungs']};
const SRC = {school: "the school's map", proposed: 'proposed link, not signed', inferred: 'inferred link'};
const NF = PLAN.scenarios[0].calendar.days.length;
const LIMIT = 6;
const trail = [];
let current = null;

const subject = s => D.subjects[s] || cap1(String(s || '').replace(/-/g, ' '));
const gradeName = g => g ? 'Grade ' + String(g).replace(/^G/, '') : '';
function sub(it) {
  const L = it.layer;
  if (L === 'capability') return it.words ? 'mostly shows: ' + it.words.join(', ') : '';
  if (L === 'behaviour') return [cap1(it.stage), it.from_age ? 'from age ' + it.from_age : '', it.setting ? 'in ' + it.setting : ''].filter(Boolean).join(' · ');
  if (L === 'goal' || L === 'competency') return [it.code, cap1(it.stage), subject(it.subject), it.area].filter(Boolean).join(' · ');
  if (L === 'outcome') return [gradeName(it.grade), subject(it.subject)].filter(Boolean).join(' · ');
  if (L === 'unit') return [subject(it.subject), (it.bands || []).map(gradeName).join(', ')].filter(Boolean).join(' · ');
  if (L === 'skill') return [it.domain, it.id.replace(/^skill\./, '')].filter(Boolean).join(' · ');
  if (L === 'word') return it.text || '';
  return '';
}
function srcLabel(g) {
  if (g.k !== 'official') return SRC[g.k] || '';
  return /NCERT/.test(ITEMS[g.head != null ? g.head : g.ids[0]].src || '') ? 'NCERT' : 'NCF-SE 2023';
}
function ranges(fs) {
  const out = [];
  fs.forEach(f => { const r = out[out.length - 1]; if (r && f === r[1] + 1) r[1] = f; else out.push([f, f]); });
  return out.map(([a, b]) => a === b ? String(a) : `${a}–${b}`).join(', ');
}
function row(n, g) {
  const it = ITEMS[n], s = sub(it);
  return `<button class="it" data-n="${n}"${g != null ? ` data-g="${g}"` : ''}><span class="nm">${esc(it.label)}</span>` +
    (s ? `<span class="sub">${esc(s)}</span>` : '') + '</button>';
}

function card(t) {
  const it = ITEMS[t.id], facts = [];
  if (it.counter) facts.push('<b>Not evidence when:</b> ' + esc(it.counter));
  if (it.capture) facts.push(`Recorded as ${esc(it.capture.replace('_', ' '))}${it.setting ? ', in ' + esc(it.setting) : ''}${it.from_age ? ', from age ' + esc(it.from_age) : ''}.`);
  if (it.focus) facts.push('<b>Focus:</b> ' + esc(it.focus));
  if (it.concepts) facts.push('<b>Key concepts:</b> ' + esc(it.concepts));
  if (it.samples) facts.push('<b>Its objectives include:</b> ' + it.samples.map(esc).join('; '));
  if (it.relabelled) facts.push('<b>Moved:</b> ' + esc(it.relabelled));
  const own = t.steps.grade.find(g => g.k === 'self' && g.ids.includes(t.id));
  const also = own && own.grades && own.grades.length ? `<div class="also"><span class="muted">Also taught in</span>${own.grades.map(x => `<button data-n="${t.id}" data-g="${x}">Grade ${x}</button>`).join('')}</div>` : '';
  const inYear = t.g >= 1 && t.g <= 7 && (it.layer === 'unit' || it.layer === 'outcome') ? `<button class="link" data-year="${t.g}" data-mark="${t.id}">See it in Grade ${t.g}'s year</button>` : '';
  const tag = [TYPE[it.layer], it.layer === 'unit' && own ? own.t : ''].filter(Boolean).join(' · ');
  return `<div class="card"><div class="tag">${esc(tag)}</div><div class="big">${esc(it.label)}</div>` +
    (it.text ? `<p>${esc(it.text)}</p>` : '') + (facts.length ? `<ul>${facts.map(f => `<li>${f}</li>`).join('')}</ul>` : '') +
    also + inYear + `<p class="mono muted">${esc([it.code, it.src].filter(Boolean).join(' · '))}${it.src || it.code ? ' · ' : ''}${esc(it.id)}</p></div>`;
}

function whenGroup(g) {
  const on = new Set(g.f), marks = (g.on || []).join(',');
  const cells = Array.from({length: NF}, (_, i) => `<span class="${on.has(i + 1) ? 'on' : ''}">${i + 1}</span>`).join('');
  return `<div class="grp ${g.k}"><div class="gt"><b>${esc(g.t)}</b><span class="src ${g.k}">${esc(srcLabel(g))}</span></div>` +
    `<div class="strip" style="--n:${NF}" role="img" aria-label="${esc(g.t)}: fortnights ${ranges(g.f)} of ${NF}">${cells}</div>` +
    `<button class="link" data-year="${g.g}" data-mark="${marks}">Fortnights ${ranges(g.f)}: see them in Grade ${g.g}'s year</button></div>`;
}

function group(g, t, compact) {
  if (g.note) return `<p class="note">${esc(g.note)}</p>`;
  if (g.f) return whenGroup(g);
  const ctx = g.g != null ? g.g : t.g;
  const ids = (g.ids || []).includes(t.id) ? [t.id, ...g.ids.filter(n => n !== t.id)] : (g.ids || []);
  const rows = ids.map(n => n === t.id ? card(t) : row(n, ctx));
  // a crowded step folds each long group to its title and a count; a short group always shows
  const lim = compact && !ids.includes(t.id) && rows.length > 3 ? 0 : LIMIT;
  const rest = rows.length > lim ? `<div class="rest" hidden>${rows.slice(lim).join('')}</div>` : '';
  const more = rows.length > lim ? `<button class="more" data-more>${lim ? 'Show all ' + rows.length : 'Show ' + rows.length}</button>` : '';
  const list = rows.slice(0, lim).join('') + (lim ? more + rest : rest);
  let head = '';
  if (g.head != null) {
    const h = ITEMS[g.head];
    head = g.head === t.id ? card(t) : `<button class="it head" data-n="${g.head}"><span class="nm">${esc(h.label)}</span><span class="sub">${esc(TYPE.goal)} · ${esc(sub(h))}</span></button>`;
  }
  const label = (g.t ? `<b>${esc(g.t)}</b>` : '') + (g.k !== 'self' ? `<span class="src ${g.k}">${esc(srcLabel(g))}</span>` : '') + (lim ? '' : more);
  return `<div class="grp ${g.k}">${label ? `<div class="gt">${label}</div>` : ''}${head}${head && ids.length ? `<div class="nest">${list}</div>` : list}</div>`;
}

function tally(t, s) {
  const seen = new Set(), by = {};
  t.steps[s].forEach(g => [...(g.head != null ? [g.head] : []), ...(g.ids || [])].forEach(n => {
    if (n === t.id || seen.has(n)) return;
    seen.add(n);
    by[ITEMS[n].layer] = (by[ITEMS[n].layer] || 0) + 1;
  }));
  return Object.entries(by).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([L, k]) => `${k} ${NOUN[L][k === 1 ? 0 : 1]}`).join(' · ');
}
function whenText(t) {
  const gs = t.steps.when.filter(g => g.f);
  const grades = [...new Set(gs.map(g => g.g))];
  if (!gs.length) return '';
  return grades.length === 1 ? `Grade ${grades[0]}, fortnights ${ranges([...new Set(gs.flatMap(g => g.f))].sort((a, b) => a - b))}` : `Grades ${grades.join(', ')}`;
}

function drawThread(t) {
  const here = D.home[ITEMS[t.id].layer];
  const many = s => t.steps[s].length > 8 || t.steps[s].reduce((a, g) => a + (g.ids ? g.ids.length : 0), 0) > 24;
  $('spine').innerHTML = D.steps.map(s => `<li class="step${s === here ? ' here' : ''}" id="step-${s}">` +
    '<div class="rail" aria-hidden="true"><span class="dot"></span></div>' +
    `<div class="sh"><h2>${esc(STEP[s][0])}</h2><p>${esc(STEP[s][1])}</p></div>` +
    `<div class="sb">${t.steps[s].map(g => group(g, t, many(s))).join('')}</div></li>`).join('');
  $('glance').innerHTML = `<span class="nowname">${esc(ITEMS[t.id].label)}</span>` + D.steps.map(s =>
    `<button data-jump="${s}"><b>${esc(STEP[s][0])}</b> ${esc((s === 'when' ? whenText(t) : tally(t, s)) || '–')}</button>`).join('');
  const prev = trail[trail.length - 1];
  $('back').hidden = !prev;
  if (prev) $('back').textContent = 'Back to ' + short(ITEMS[D.threads[prev].id].label);
}

function show(v) {
  ['thread', 'year', 'day'].forEach(x => {
    $(x).hidden = x !== v;
    $('t-' + x).setAttribute('aria-pressed', String(x === v));
  });
}
function remember(hash) {
  try { history.pushState(null, '', '#' + hash); } catch (_) { /* a frame may refuse; the page works without it */ }
}
function openKey(k, push) {
  const t = D.threads[k];
  if (!t) return;
  if (push && current && current !== k) trail.push(current);
  current = k;
  drawThread(t);
  show('thread');
  if (push) remember(k);
  window.scrollTo({top: 0});
}
function openItem(n, g) {
  const it = ITEMS[n];
  if (it.layer === 'grade') {
    const x = Number(it.id.split('.G')[1]);
    if (x >= 1 && x <= 7) openYear(x);
    return;
  }
  const k = g != null && D.threads[it.id + '~' + g] ? it.id + '~' + g : D.open[n];
  if (k) openKey(k, true);
}

// search: every item that has a thread, and each grade's year
const q = $('q'), hits = $('hits');
const INDEX = ITEMS.map((it, n) => (D.open[n] || (it.layer === 'grade' && /\.G[1-7]$/.test(it.id))) ? [n, (it.label + ' ' + (it.code || '') + ' ' + it.id).toLowerCase()] : null).filter(Boolean);
q.addEventListener('input', () => {
  const v = q.value.trim().toLowerCase();
  if (v.length < 2) { hits.hidden = true; return; }
  const found = INDEX.filter(([, s]) => s.includes(v)).sort((a, b) => Number(!ITEMS[a[0]].label.toLowerCase().startsWith(v)) - Number(!ITEMS[b[0]].label.toLowerCase().startsWith(v))).slice(0, 40);
  hits.innerHTML = found.map(([n]) => {
    const it = ITEMS[n];
    return `<button class="it" data-n="${n}"><span class="nm">${esc(it.label)}${it.layer === 'grade' ? "'s year" : ''}</span><span class="sub">${esc([TYPE[it.layer], sub(it)].filter(Boolean).join(' · '))}</span></button>`;
  }).join('') || '<p class="note" style="padding:8px 12px">Nothing matches. Try a subject word, a code such as C-1.3, or a grade.</p>';
  hits.hidden = false;
});
q.addEventListener('keydown', e => {
  if (e.key === 'Escape') { hits.hidden = true; q.blur(); }
  if (e.key === 'Enter') { const first = hits.querySelector('[data-n]'); if (first) first.click(); }
});

document.addEventListener('click', e => {
  if (!e.target.closest('.find')) hits.hidden = true;
  const b = e.target.closest('[data-n],[data-year],[data-jump],[data-more],[data-scen]');
  if (!b) return;
  if (b.closest('#hits')) { hits.hidden = true; q.value = ''; }
  if (b.dataset.n != null) openItem(Number(b.dataset.n), b.dataset.g != null ? Number(b.dataset.g) : null);
  else if (b.dataset.year) openYear(Number(b.dataset.year), (b.dataset.mark || '').split(',').filter(Boolean).map(Number));
  else if (b.dataset.jump) {
    const el = $('step-' + b.dataset.jump);
    el.scrollIntoView({behavior: calm(), block: 'start'});
    el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
  } else if (b.hasAttribute('data-more')) { b.closest('.grp').querySelectorAll('.rest').forEach(x => { x.hidden = false; }); b.remove(); }
  else if (b.dataset.scen) { scen = Number(b.dataset.scen); drawDay(); }
});
$('back').onclick = () => { const k = trail.pop(); if (k) { current = null; openKey(k, false); remember(k); } };
$('t-thread').onclick = () => { show('thread'); if (current) remember(current); };
$('t-year').onclick = () => openYear(yearGrade);
$('t-day').onclick = () => openDay();

$('starts').innerHTML = '<span class="muted">Start from a word:</span>' +
  ['word.capable', 'word.kind', 'word.unafraid'].filter(id => AT[id] != null).map(id => `<button data-n="${AT[id]}">${esc(ITEMS[AT[id]].label)}</button>`).join('') +
  '<span class="muted">or a grade’s year:</span>' + [1, 2, 3, 4, 5, 6, 7].map(g => `<button data-year="${g}">${g}</button>`).join('');
const notes = Object.entries(D.notes || {}).filter(([, v]) => v && v.length);
$('notes').innerHTML = `<summary>What the mapping found: ${notes.reduce((a, [, v]) => a + v.length, 0)} notes for the curriculum team</summary>` +
  notes.map(([k, v]) => `<p class="muted" style="margin:10px 0 0"><b>${esc(cap1(k))}</b></p><ul>${v.map(x => `<li>${esc(x)}</li>`).join('')}</ul>`).join('');
$('notes').hidden = !notes.length;
$('foot').innerHTML = `Spine built ${esc(D.built)} from ${D.sources.map(esc).join(' · ')}. The files behind this page are <span class="mono">docs/spine/spine.json</span> and <span class="mono">docs/spine/plan.json</span>; <span class="mono">research/spine_page.py</span> builds it, and <span class="mono">packages/engine/tests/test_spine_page.py</span> checks it.`;

function route() {
  const h = decodeURIComponent((location.hash || '').slice(1));
  const y = /^year-([1-7])$/.exec(h);
  if (h === 'day' || h === 'plan') openDay(false);
  else if (y) openYear(Number(y[1]), [], false);
  else if (D.threads[h]) openKey(h, false);
  else if (AT[h] != null && D.open[AT[h]]) openKey(D.open[AT[h]], false);
  else openKey(D.start, false);
}
window.addEventListener('popstate', route);
