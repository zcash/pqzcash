(function (DATA) {
if (!DATA) { document.getElementById('selfcheck').textContent = 'The page\'s data, pareto-data.js, did not load.'; return; }
const COLORS = { pedersen: 'var(--c-pedersen)', fp128: 'var(--c-fp128)', goldilocks: 'var(--c-gold)', pasta_q64: 'var(--c-q64)', pasta_sis: 'var(--c-sis)', pasta: 'var(--c-pasta)', whir: 'var(--c-whir)', whir_gold: 'var(--c-whirgold)', whir_hybrid: 'var(--c-whirhybrid)', plonky3: 'var(--c-plonky3)', flock: 'var(--c-flock)',
  whir_rec: 'var(--c-whirrec)', whir_gold_rec: 'var(--c-whirgoldrec)', whir_hybrid_rec: 'var(--c-whirhybridrec)', plonky3_rec: 'var(--c-plonky3rec)', flock_rec: 'var(--c-flockrec)', bitz: 'var(--c-bitz)', bitz_rec: 'var(--c-bitzrec)', bits_q64: 'var(--c-bitsq64)', bits_q64_poseidon: 'var(--c-bitsq64pos)', bits_akita: 'var(--c-bitsakita)' };
const css = getComputedStyle(document.querySelector('#pareto .top'));  // the plot's theme, live; in the book the plot and controls keep the dark one
const color = f => css.getPropertyValue(COLORS[f].slice(4, -1)).trim();
let plotResizer = null;
const OFF_BY_DEFAULT = ['whir', 'whir_gold', 'whir_hybrid', 'plonky3', 'whir_rec', 'whir_gold_rec', 'whir_hybrid_rec', 'plonky3_rec'];
// The family list's sections, each under its heading: the pre-quantum scheme; the lattice-based
// schemes; the hash-based ones.
const GROUPS = [  // heading, the section it links to, families
  ['Pre-quantum', '#pedersen-ipa', ['pedersen']],
  ['Lattice-based', '#lattice-based-families', ['fp128', 'goldilocks', 'pasta_q64', 'pasta_sis', 'pasta', 'bits_q64', 'bits_q64_poseidon', 'bits_akita']],
  ['Hash-based', '#hash-based-families', ['bitz', 'bitz_rec', 'flock', 'flock_rec', 'whir', 'whir_rec', 'whir_gold', 'whir_gold_rec', 'whir_hybrid', 'whir_hybrid_rec', 'plonky3', 'plonky3_rec']],
];
const order = GROUPS.flatMap(([, , fams]) => fams);
const famBox = document.getElementById('families');
// Each family's swatch uses the marker shapes its points have in the plot: a
// circle for configurations needing parameter changes only, a square for the
// rest, both where a family has both.
GROUPS.forEach(([heading, href, group], i) => {
  const h = document.createElement('a');
  h.className = 'eyebrow';
  h.href = href;
  h.textContent = heading;
  h.style.display = 'block';
  if (i) h.style.marginTop = '6px';
  famBox.appendChild(h);
  for (const f of group) {
    const l = document.createElement('label');
    const shapes = [...new Set(DATA.points.filter(p => p.family === f).map(p => p.change === 'none' ? 'circle' : 'square'))].sort();
    const swatches = shapes.map(s => `<span class="swatch ${s}" style="background:${COLORS[f]}"></span>`).join('');
    // The WHIR-type families and Plonky3 start unticked: Akita beats them on every measure,
    // and their many rows crowd the picture; the families list turns them on.
    const on = OFF_BY_DEFAULT.includes(f) ? '' : 'checked';
    l.innerHTML = `<input type="checkbox" class="fam" value="${f}" id="fam-${f}" ${on}><span class="swatches">${swatches}</span>${DATA.labels[f]}`;
    famBox.appendChild(l);
  }
});
// The transaction prover may be chosen as the second measure, the third, or both, each side with
// its own application list; the third's list is a copy of the second's.
const SIDES = ['second', 'third'];
const txSelect = side => document.getElementById(side === 'second' ? 'txapp2' : 'txapp3');
txSelect('third').innerHTML = txSelect('second').innerHTML;
const measureOf = side => document.querySelector(`input[name=${side}]:checked`).value;
// The point property that a side's measure reads: the transaction prover's value differs by
// side, since each side has its own application.
const measureKey = side => { const m = measureOf(side); return m === 'transaction' ? `transaction_${side}` : m; };
const txSides = () => SIDES.filter(side => measureOf(side) === 'transaction');
// With neither measure the transaction prover, the second's list stands for both: the third
// follows it, so that choosing the measure on either side afterwards starts from that choice.
txSelect('second').addEventListener('change', () => { if (txSides().length === 0) txSelect('third').value = txSelect('second').value; });
// The selected option's text, shortened for an axis title.
function txShort(side) {
  const text = txSelect(side).selectedOptions[0].textContent.replace(/\s*\(.*$/, '').replace(/:.*$/, '');
  return text.length > 44 ? text.slice(0, 42).trimEnd() + '…' : text;
}
// A Tachyon transaction as the application needs Tachyon's header of nine elements, and so
// does the recovery circuit, whose primary input is the anchor, rk, the nullifier and SigHash.
let userHeader = 2, lastForced = false;  // the header chosen on the control, kept through a forced spell
function forcedHeader() {
  return txSides().some(side => { const app = txSelect(side).value; return app.startsWith('tachyon') || app.startsWith('recovery'); });
}
function selected() {
  const fams = [...document.querySelectorAll('.fam:checked')].map(e => e.value);
  const ranks = [...document.querySelectorAll('.rank:checked')].map(e => +e.value);
  const packings = [...document.querySelectorAll('.packing:checked')].map(e => e.value);
  const paramsOnly = document.getElementById('paramsonly').checked;
  const zk = document.getElementById('zk').checked;
  const floor = +document.querySelector('input[name=floor]:checked').value;
  const grind = document.getElementById('grind').value;
  const hashes = document.querySelector('input[name=hashes]:checked').value;
  return DATA.points.filter(p => fams.includes(p.family) && (p.rank === null || ranks.includes(p.rank))    && (p.packing === null || packings.includes(p.packing ? 'packed' : 'today')) && (!paramsOnly || p.change === 'none')
    && (p.zk === null || p.zk === zk) && (p.floor === null || p.floor === floor)
    && (p.hashes === 'any' || p.hashes === 'blake3' || hashes === 'poseidon')  // the option adds the Poseidon-priced rows to the BLAKE3 ones
    && (p.grind === undefined || p.grind === null || String(p.grind) === grind));
}
const ASSUMPTION = { pedersen: 'discrete log on Pasta', fp128: 'Module-SIS, random oracle', goldilocks: 'Module-SIS, random oracle', pasta_q64: 'Module-SIS, random oracle', pasta_sis: 'Module-SIS, random oracle', pasta: 'Module-SIS, random oracle', bits_q64: 'Module-SIS, random oracle', bits_q64_poseidon: 'Module-SIS, random oracle', bits_akita: 'Module-SIS, random oracle; security ledger open',
  whir: 'random oracle', whir_gold: 'random oracle', whir_hybrid: 'random oracle', plonky3: 'random oracle', flock: 'random oracle', bitz: 'random oracle',
  whir_rec: 'random oracle', whir_gold_rec: 'random oracle', whir_hybrid_rec: 'random oracle', plonky3_rec: 'random oracle', flock_rec: 'random oracle', bitz_rec: 'random oracle' };
const SYMBOL = { none: 'circle', code: 'square', design: 'square' };
const CHANGE = { none: 'parameters only', code: 'code changes', design: 'design changes' };
// Pareto dominance on six axes: bytes, the chosen second and third measures, native support for
// the Pasta base field (more is better), the security assumption, and the changes needed (both
// less is better). The assumption ranks a random oracle alone below Module-SIS with a random
// oracle, below the open security ledger; the changes rank parameters only below code below
// design. A configuration is dominated by one at least as good on every axis and better on one.
function frontierAmong(pts, second, third) {
  const level = p => DATA.change_level[p.change];
  return pts.filter(p => !pts.some(q => q !== p && q.bytes <= p.bytes && q[second] <= p[second] && q[third] <= p[third] && q.pasta >= p.pasta && q.assumption <= p.assumption && level(q) <= level(p) && (q.bytes !== p.bytes || q[second] !== p[second] || q[third] !== p[third] || q.pasta !== p.pasta || q.assumption !== p.assumption || q.change !== p.change)));
}
const second = () => measureOf('second');
// The swap button exchanges the second and third measures, with their applications; render()
// then greys out the mirrored choice on each side again.
document.getElementById('swapmeasures').addEventListener('click', () => {
  const s = second(), t = third();
  for (const box of document.querySelectorAll('input[name=second]')) { box.disabled = false; box.checked = box.value === t; }
  for (const box of document.querySelectorAll('input[name=third]')) { box.disabled = false; box.checked = box.value === s; }
  const a2 = txSelect('second').value, a3 = txSelect('third').value;
  txSelect('second').value = a3;
  txSelect('third').value = a2;
  render();
});
// The 3D view opens from the low corner, bytes receding to the right and the second measure
// to the left, so that the best configurations are nearest the viewer; a constant uirevision
// keeps whatever the viewer turns it to.
const DEFAULT_CAMERA = { eye: { x: -1.25, y: -1.25, z: 1.0 }, up: { x: 0, y: 0, z: 1 } };
// The default eye fits the scene in a plot CAMERA_REF_WIDTH pixels wide. The vertical field of
// view is fixed, so a narrower plot crops the scene at the sides; the eye moves out in
// proportion, at the first render and when the plot's width changes.
const CAMERA_REF_WIDTH = 600;
const plotWidth = () => document.getElementById('plot').clientWidth || CAMERA_REF_WIDTH;
const cameraScale = w => Math.max(1, CAMERA_REF_WIDTH / w);
const scaledEye = (eye, k) => ({ x: eye.x * k, y: eye.y * k, z: eye.z * k });
let plotWidthRendered = 0;
// Toggling the projection carries the live camera into the next render, so that only the
// projection changes and not the view direction.
let carryCamera = false;
document.getElementById('ortho').addEventListener('change', () => { carryCamera = true; });
const third = () => measureOf('third');
// The measures in work units, which the unit option converts.
const WORK_MEASURES = ['prover', 'accumulation_prover', 'verify', 'transaction_second', 'transaction_third'];
// Prover and decider work are stored in 64-bit word multiplications; the
// unit option shows them as milliseconds at 3e9 per second on one core, to three
// significant figures, or to the nearest millisecond from a second up.
const unit = () => document.querySelector('input[name=unit]:checked').value;
const unitFactor = () => unit() === 'ms' ? 1 / 3e6 : 1;
const unitName = () => unit() === 'ms' ? 'ms' : '64‑bit muls';
const fmtMs = v => v >= 1000 ? fmt(Math.round(v)) : v.toPrecision(3);  // keeps a trailing zero: 8.90
const fmtWork = v => unit() === 'ms' ? fmtMs(v) : fmt(Math.round(v));
const val = (p, key) => WORK_MEASURES.includes(key) ? p[key] * unitFactor() : p[key];
const measureTitle = m => m.startsWith('transaction_') ? `transaction prover ${unitName()}<br>${txShort(m.slice('transaction_'.length))}` : ({ prover: `prover commitment work, ${unitName()} per step`, accumulation_prover: `accumulation prover ${unitName()} per step: the merge's commitments and the fold's sum-checks`, gates: 'merge gates', accumulation: 'accumulation atoms per merge', verify: `decider ${unitName()}`, memory: 'accumulator bytes', peak_memory: 'peak fuse memory, bytes' })[m];
function fmt(n) { return n.toLocaleString('en-GB'); }
// The transaction measure's steps: the application's units in the row's arithmetization,
// hashed under the row's own policy, or under the selected one for a row priced under either,
// in as many steps as the row's step holds, rounded up. A Tachyon transaction is a list of
// proof-tree nodes, re-packed for the step size at each rank: a node larger than a step takes
// whole steps and its remainder joins the rest, which fill steps first-fit decreasing; a
// Tachyon tree's last nodes, Ragu's two rerandomization fuses, are steps of their own. The
// model's tx_steps is the same function.
function txStepsFor(p, kind, count, policy) {
  const units = DATA.applications[kind][p.arith][p.hashes === 'any' ? policy : p.hashes];
  if (!Array.isArray(units)) return Math.ceil(units * count / p.step_units);
  const cap = p.step_units;
  const own = DATA.own_last_steps[kind] || 0;
  let steps = own;
  const items = [];
  for (const node of own ? units.slice(0, -own) : units) {
    steps += Math.floor(node / cap);
    if (node % cap) items.push(node % cap);
  }
  items.sort((a, b) => b - a);
  const bins = [];
  for (const item of items) {
    const bin = bins.findIndex(b => b + item <= cap);
    if (bin < 0) bins.push(item); else bins[bin] += item;
  }
  return steps + bins.length;
}
// Kishu's rows add their application's constraint PIOP, priced per application by route.
// The masking fold covers the user chain's accumulator, or the leaf alone for an application
// whose user hands over a bare leaf without a fuse (DATA.leaf_handoff).
const txWork = (p, kind, count, policy) => { const steps = txStepsFor(p, kind, count, policy); return steps * (p.step_prover + p.accumulation_prover) + (DATA.has_mults[kind] ? steps * (p.route_step || 0) : 0) + (DATA.leaf_handoff.includes(kind) ? p.fold_leaf : p.fold) + ((DATA.piop[kind] || {})[p.arith] || 0) * count; };
// The text quotes transaction figures that the model computes with its own copy of this
// measure; the two copies are checked against each other here, on the rows the text quotes.
{
  const bad = DATA.tx_checks.filter(c => {
    const p = DATA.points.find(q => q.family === c.family && q.label === c.label);
    return !p || Math.abs(txWork(p, c.app, c.count, c.policy) - c.transaction) > 0.5;
  });
  if (bad.length) document.getElementById('selfcheck').textContent = `The transaction figures in the text were computed by the model and do not match this page's measure for: ${bad.map(c => `${c.family}, ${c.label}, ${c.app}`).join('; ')}.`;
}
// A padded axis range over the points' values of one key, in log10 units for a
// log axis, as Plotly expects.
function padded(basis, key, logAxis) {
  const v = basis.map(p => val(p, key));
  if (!v.length) return undefined;
  let lo = Math.min(...v), hi = Math.max(...v);
  if (logAxis) { lo = Math.log10(lo); hi = Math.log10(hi); }
  const pad = Math.max(0.05 * (hi - lo), logAxis ? 0.15 : 0.05 * Math.abs(hi) || 1);
  return [lo - pad, hi + pad];
}
// The held view: the scale and view it was captured in, and the axis ranges.
let held = null;
// Ticking the hold box freezes the view as it is, from the ranges the plot is
// showing, without re-rendering; unticking it rescales the axes to the plotted
// points at once, keeping the camera for that render.
let keepCameraOnce = false;
document.getElementById('holdcamera').addEventListener('change', e => {
  if (!e.target.checked) { held = null; keepCameraOnce = true; render(); return; }
  const fl = document.getElementById('plot')._fullLayout || {};
  const view = document.querySelector('input[name=view]:checked').value;
  const scale = document.querySelector('input[name=scale]:checked').value;
  const r = a => a && a.range ? a.range.slice() : undefined;
  const sc = fl.scene || {};
  const s = measureKey('second'), t = measureKey('third'), u = unit();
  held = view === '2d'
    ? { scale, view, second: s, third: t, unit: u, x: r(fl.xaxis), y: r(fl.yaxis), z: padded(selected(), t, t !== 'accumulation' && scale === 'log') }
    : { scale, view, second: s, third: t, unit: u, x: r(sc.xaxis), y: r(sc.yaxis), z: r(sc.zaxis) };
});
function wrapLabel(label, width = 60) {
  const lines = [];
  let line = '';
  for (const part of label.split(', ')) {
    if (line && line.length + part.length + 2 > width) { lines.push(line); line = part; }
    else line = line ? `${line}, ${part}` : part;
  }
  if (line) lines.push(line);
  return lines.join('<br>');
}
function hover(p) {
  return `${DATA.labels[p.family]}<br>${wrapLabel(p.label)}<br>bytes ${fmt(p.bytes)}<br>prover commitments ${fmtWork(val(p, 'prover'))} ${unitName()}<br>accumulation prover ${fmtWork(val(p, 'accumulation_prover'))} ${unitName()}<br>decider ${fmtWork(val(p, 'verify'))} ${unitName()}<br>accumulation atoms ${p.accumulation}<br>merge gates ${fmt(p.gates)}<br>accumulator bytes ${fmt(p.memory)}<br>peak fuse bytes ${fmt(p.peak_memory)}${txSides().map(side => p[`transaction_${side}`] === null ? '' : `<br>transaction prover, ${side} measure: ${fmtWork(val(p, `transaction_${side}`))} ${unitName()}`).join('')}<br>${CHANGE[p.change]}`;
}
function render() {
  // Each class, pre-quantum (Pedersen-IPA) and post‑quantum (Akita), has its
  // own frontier, taken among the selected configurations of that class, so
  // that fixing a rank or a header size gives the frontier at that circuit
  // shape. A collapse box keeps only that class's frontier in the plot; the
  // table always lists both frontiers. The changes a configuration needs are
  // an axis of the dominance test, so the best parameter-only configurations
  // stay on the frontier beside what code or design changes buy.
  const s = measureKey('second'), t = measureKey('third');
  // The two measures are chosen independently; the one chosen on either side is greyed out
  // on the other, except the transaction prover, which both sides may take with their own
  // applications. The application list of each side that has it is shown, one at full width
  // or both side by side; with neither, the second's list shows alone, without naming a measure.
  for (const box of document.querySelectorAll('input[name=second]')) box.disabled = box.value === third() && box.value !== 'transaction';
  for (const box of document.querySelectorAll('input[name=third]')) box.disabled = box.value === second() && box.value !== 'transaction';
  const sides = txSides();
  document.getElementById('txapps').classList.toggle('both', sides.length === 2);
  document.getElementById('txapp2-group').hidden = sides.length > 0 && !sides.includes('second');
  document.getElementById('txapp3-group').hidden = !sides.includes('third');
  // Alone, the list names no measure; side by side, the two eyebrows name only their measures.
  document.querySelector('#txapp2-group .side').hidden = sides.length === 0;
  for (const e of document.querySelectorAll('#txapps .proves')) e.hidden = sides.length === 2;
  // The transaction measure: the selected application, costed in each arithmetization's
  // unit under the hash policy (DATA.applications), in as many steps as its step holds
  // (step_units, the same unit), rounded up, at the family's per-step commitment cost; one
  // merge per step at the row's prover; and, for the zero-knowledge rows, the masking work
  // at the handoff to the public aggregator (Akita's masking fold; the hash-based families'
  // masked prover extra).
  const txPolicy = document.querySelector('input[name=hashes]:checked').value;
  // The PCD header is the application's choice and applies to every row alike: the rows are
  // priced without one, and the selected header adds its elements at 64 bytes each. A Tachyon
  // transaction or the recovery circuit forces Tachyon's nine; the radio is greyed out
  // meanwhile, and the user's own choice comes back afterwards. The recursive rows' accumulator
  // memory, which is their proof, is left without the header: at most 576 bytes of hundreds of kbytes.
  const forced = forcedHeader();
  const radios = [...document.querySelectorAll('.header')];
  let header;
  if (forced) header = DATA.tachyon_header;
  else if (lastForced) header = userHeader;
  else header = userHeader = +radios.find(r => r.checked).value;
  lastForced = forced;
  for (const r of radios) { r.disabled = forced; r.checked = +r.value === header; }
  for (const p of DATA.points) {
    if (p.bytes0 === undefined) p.bytes0 = p.bytes;
    p.bytes = p.bytes0 + header * DATA.header_element_bytes;
  }
  for (const side of SIDES) {
    const [txKind, txCount] = txSelect(side).value.split(':');
    for (const p of DATA.points) p[`transaction_${side}`] = p.step_prover === null ? null : txWork(p, txKind, txCount ? +txCount : 1, txPolicy);
  }
  const all = selected().filter(p => sides.length === 0 || p.step_prover !== null);
  // With the per-family box ticked, each family's frontier is taken on its own,
  // so that a family dominated by another still shows its best configurations.
  const perFamily = document.getElementById('perfamily').checked;
  const classFrontiers = pq => {
    const cls = all.filter(p => p.pq === pq);
    const groups = perFamily ? [...new Set(cls.map(p => p.family))].map(f => cls.filter(p => p.family === f)) : [cls];
    const front = new Set();
    for (const g of groups) frontierAmong(g, s, t).forEach(p => front.add(p));
    return front;
  };
  const frontPre = classFrontiers(false), frontPost = classFrontiers(true);
  const front = new Set([...frontPre, ...frontPost]);
  // The table also lists every family's own frontier, so that a family
  // dominated within its class still shows its best configurations there.
  const familyOnly = new Set();
  for (const f of order) {
    const fam = all.filter(p => p.family === f);
    frontierAmong(fam, s, t).forEach(p => { if (!front.has(p)) familyOnly.add(p); });
  }
  const collapsePre = document.getElementById('collapse-pre').checked;
  const collapsePost = document.getElementById('collapse-post').checked;
  const pts = all.filter(p => p.pq ? (!collapsePost || frontPost.has(p)) : (!collapsePre || frontPre.has(p)));
  const view = document.querySelector('input[name=view]:checked').value;
  const scale = document.querySelector('input[name=scale]:checked').value;
  const ink = css.getPropertyValue('--ink').trim(), muted = css.getPropertyValue('--muted').trim(), rule = css.getPropertyValue('--rule').trim(), surface = css.getPropertyValue('--surface').trim();
  const traces = [];
  // Marker size in the 2D view: the logarithm of the third measure over the
  // plotted points, from 5 to 22 pixels, so that the sizes read across any
  // selection and the largest merges do not swamp the plot.
  const logv = p => Math.log10(Math.max(1, p[t]));
  let lo = Infinity, hi = -Infinity;
  for (const p of pts) { const v = logv(p); if (v < lo) lo = v; if (v > hi) hi = v; }
  const markerSize = p => hi > lo ? 5 + 17 * Math.min(1, Math.max(0, (logv(p) - lo) / (hi - lo))) : 10;
  const u = unit(), uname = unitName();
  // The families list's swatches follow the plot's marker sizes: each is the
  // family's median marker size among its plotted points under the current
  // third measure, capped so that the list stays legible.
  for (const f of order) {
    const sizes = pts.filter(p => p.family === f).map(markerSize).sort((a, b) => a - b);
    const px = Math.min(18, Math.round(sizes[Math.floor(sizes.length / 2)] || 10));
    document.querySelectorAll(`#fam-${f} ~ .swatches .swatch`).forEach(s => { s.style.width = px + 'px'; s.style.height = px + 'px'; });
  }
  for (const f of order) {
    const sub = pts.filter(p => p.family === f);
    const base = { name: DATA.labels[f], text: sub.map(hover), hoverinfo: 'text', marker: { color: color(f), opacity: f === 'pedersen' ? 0.55 : 0.9 } };
    if (view === '2d') {
      traces.push({ ...base, type: 'scatter', mode: 'markers', x: sub.map(p => p.bytes), y: sub.map(p => val(p, s)),
        marker: { ...base.marker, symbol: sub.map(p => SYMBOL[p.change]), size: sub.map(markerSize), line: { width: sub.map(p => front.has(p) ? 2 : 0), color: css.getPropertyValue('--accent').trim() } } });
    } else {
      traces.push({ ...base, type: 'scatter3d', mode: 'markers', x: sub.map(p => p.bytes), y: sub.map(p => val(p, s)), z: sub.map(p => val(p, t)),
        marker: { ...base.marker, symbol: sub.map(p => SYMBOL[p.change]), size: sub.map(p => front.has(p) ? 7 : 4), line: { width: sub.map(p => front.has(p) ? 2 : 0), color: css.getPropertyValue('--accent').trim() } } });
    }
  }
  // A small cross marks the centre of each large marker in the 2D view, so
  // that it can be read against the axes; black on light markers, and the
  // background colour on the near-black family.
  if (view === '2d') {
    const big = pts.filter(p => markerSize(p) > 16);
    if (big.length) {
      const crossColor = big.map(p => p.family === 'plonky3' ? surface : '#000');
      traces.push({ type: 'scatter', mode: 'markers', x: big.map(p => p.bytes), y: big.map(p => val(p, s)), hoverinfo: 'skip', showlegend: false,
        marker: { symbol: 'cross-thin', size: 5, color: crossColor, line: { width: 0.8, color: crossColor } } });
    }
  }
  const axis = t => ({ title: { text: t }, gridcolor: rule, zerolinecolor: rule, color: muted, tickfont: { family: 'IBM Plex Mono, monospace' } });
  const layout = { paper_bgcolor: surface, plot_bgcolor: surface, font: { family: 'IBM Plex Sans, system-ui, sans-serif', color: ink, size: 13 },
    // No in-plot legend: the families list beside the plot carries the colour
    // swatches, and a legend inside the plot changes the plot area whenever it
    // reflows.
    margin: { l: 70, r: 20, t: 20, b: 90 }, showlegend: false, hoverlabel: { font: { family: 'IBM Plex Mono, monospace', size: 12 } } };
  // Holding the view freezes the axis ranges, so that a selection only adds
  // or removes points, and a constant uirevision keeps the camera and any
  // zoom across re-renders. The ranges are captured when the box is ticked
  // (see below), so ticking it moves nothing; a change of scale or of view
  // needs new ranges, taken from the plotted points. Without the hold, the
  // ranges follow the plotted points and a fresh uirevision resets the
  // camera. The 3D scene cannot autorange a single point, or equal values on
  // a log axis, so its ranges are always set explicitly, with padding.
  const hold = document.getElementById('holdcamera').checked;
  // With the hold on, the 3D camera is read from the live figure and passed back
  // explicitly, so that it stays put whatever Plotly's own persistence decides
  // when the traces change under it.
  const live = document.getElementById('plot')._fullLayout || {};
  const camera = (hold || carryCamera) && live.scene && live.scene.camera ? JSON.parse(JSON.stringify(live.scene.camera)) : undefined;
  carryCamera = false;
  const log = scale === 'log';
  // Prover work, gates and decider work span orders of magnitude; atoms do not.
  const logFor = m => m !== 'accumulation' && log;
  const ylog = logFor(s), zlog = logFor(t);
  if (hold) {
    if (held && held.scale === scale && held.view === view && held.second === s && held.third === t && held.unit !== u) {
      // A change of work unit multiplies an axis in work units (prover,
      // decider or transaction) by a constant. Carry the held ranges across
      // it, so that the picture does not move: in log scale the ranges are
      // log10 values, so the constant adds.
      const f = (u === 'ms' ? 1 / 3e6 : 1) / (held.unit === 'ms' ? 1 / 3e6 : 1);
      const carry = (r, isLog) => r && (isLog ? r.map(v => v + Math.log10(f)) : r.map(v => v * f));
      held = { ...held, unit: u, y: WORK_MEASURES.includes(s) ? carry(held.y, ylog) : held.y, z: WORK_MEASURES.includes(t) ? carry(held.z, zlog) : held.z };
    }
    if (!held || held.scale !== scale || held.view !== view || held.second !== s || held.third !== t || held.unit !== u) {
      held = { scale, view, second: s, third: t, unit: u, x: padded(pts, 'bytes', log), y: padded(pts, s, ylog), z: padded(pts, t, zlog) };
    }
  } else {
    held = null;
  }
  // Without the hold, every axis takes a padded range over the plotted points, in
  // both views: Plotly's own autorange gives a point at the edge of the data no
  // margin, so a lone frontier point at the far right could be lost or clipped.
  const rx = held ? held.x : padded(pts, 'bytes', log);
  const ry = held ? held.y : padded(pts, s, ylog);
  const rz = held ? held.z : padded(pts, t, zlog);
  // A constant uirevision keeps the camera and any zoom across re-renders;
  // the untick render keeps it for one more render so that the camera stays
  // while the axes rescale.
  layout.uirevision = hold || keepCameraOnce ? 'hold' : String(Date.now());
  if (view === '2d') {
    layout.xaxis = { ...axis('compressed proof bytes'), type: scale, range: rx, autorange: false };
    layout.yaxis = { ...axis(measureTitle(s)), type: ylog ? 'log' : 'linear', range: ry, autorange: false };
  } else {
    layout.scene = { xaxis: { ...axis('proof bytes'), type: scale, range: rx }, yaxis: { ...axis(measureTitle(s)), type: ylog ? 'log' : 'linear', range: ry }, zaxis: { ...axis(measureTitle(t)), type: zlog ? 'log' : 'linear', range: rz }, aspectmode: 'cube', bgcolor: surface, camera: { ...(camera || { ...DEFAULT_CAMERA, eye: scaledEye(DEFAULT_CAMERA.eye, cameraScale(plotWidth())) }), projection: { type: document.getElementById('ortho').checked ? 'orthographic' : 'perspective' } } };
    layout.margin = { l: 0, r: 0, t: 0, b: 0 };
  }
  keepCameraOnce = false;
  Plotly.react('plot', traces, layout, { responsive: true, displaylogo: false });
  plotWidthRendered = plotWidth();
  // The plot's box changes width without a window resize when the book's sidebar opens or
  // closes; the responsive option watches the window only, so watch the box itself, and move
  // the camera's eye with the width.
  if (!plotResizer) {
    let frame;
    plotResizer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const w = plotWidth(), fl = document.getElementById('plot')._fullLayout;
        const live = fl && fl.scene && fl.scene.camera;
        if (live && plotWidthRendered && w !== plotWidthRendered) {
          const f = cameraScale(w) / cameraScale(plotWidthRendered);
          if (f !== 1) Plotly.relayout('plot', { 'scene.camera.eye': scaledEye(live.eye, f) });
        }
        plotWidthRendered = w;
        Plotly.Plots.resize('plot');
      });
    });
    plotResizer.observe(document.getElementById('plot'));
  }
  const tbody = document.querySelector('#table tbody');
  tbody.innerHTML = '';
  const rows = [...front, ...familyOnly].sort((a, b) => a.bytes - b.bytes);
  for (const p of rows) {
    const tr = document.createElement('tr'); tr.className = 'frontier';
    tr.innerHTML = `<td><span class="swatch ${SYMBOL[p.change]}" style="background:${COLORS[p.family]}"></span> ${DATA.labels[p.family]}</td><td>${p.label}</td><td class="num">${fmt(p.bytes)} bytes</td><td class="num">${fmtWork(val(p, 'prover'))} ${uname}</td><td class="num">${fmtWork(val(p, 'accumulation_prover'))} ${uname}</td><td class="num">${fmtWork(val(p, 'verify'))} ${uname}</td><td class="num">${p.step_prover === null ? '' : sides.map(side => `${fmtWork(val(p, `transaction_${side}`))} ${uname}`).join(' / ')}</td><td class="num">${fmt(p.memory)} bytes</td><td class="num">${fmt(p.peak_memory)} bytes</td><td class="num">${p.accumulation} atoms</td><td class="num">${fmt(p.gates)} gates</td><td class="num">${p.folded}</td><td>${p.pasta_arith}</td><td>${ASSUMPTION[p.family]}</td><td>${CHANGE[p.change]}</td><td>${front.has(p) ? 'overall' : 'family'}</td>`;
    tbody.appendChild(tr);
  }
  if (!rows.length) tbody.innerHTML = '<tr><td colspan="16">No family selected.</td></tr>';
  const table = document.getElementById('table');
  if (table.dataset.sortCol !== undefined) sortTable(table, +table.dataset.sortCol, table.dataset.sortDir);
}
// Every table sorts by a clicked column, numerically where the cells start with a
// number (the unit that follows it, such as "bytes" or "ms", is ignored); a second click on the
// same column reverses the order.
function sortTable(table, col, dir) {
  const tbody = table.tBodies[0];
  const text = r => (r.cells[col] ? r.cells[col].textContent : '').trim();
  const num = s => { const m = s.match(/^-?(?:\d[\d,]*)?(?:\.\d+)?(?:e[+-]?\d+)?/i); const n = m && m[0] !== '' && m[0] !== '-' ? Number(m[0].replace(/,/g, '')) : NaN; return isNaN(n) ? null : n; };
  const rows = [...tbody.rows];
  rows.sort((a, b) => {
    const sa = text(a), sb = text(b), na = num(sa), nb = num(sb);
    const c = na !== null && nb !== null ? na - nb : sa.localeCompare(sb);
    return dir === 'desc' ? -c : c;
  });
  rows.forEach(r => tbody.appendChild(r));
  [...table.tHead.rows[0].cells].forEach((th, i) => {
    th.classList.toggle('sorted-asc', i === col && dir === 'asc');
    th.classList.toggle('sorted-desc', i === col && dir === 'desc');
  });
}
document.querySelectorAll('table').forEach(table => {
  [...table.tHead.rows[0].cells].forEach((th, i) => th.addEventListener('click', () => {
    const dir = table.dataset.sortCol === String(i) && table.dataset.sortDir === 'asc' ? 'desc' : 'asc';
    table.dataset.sortCol = String(i);
    table.dataset.sortDir = dir;
    sortTable(table, i, dir);
  }));
});
document.querySelectorAll('.fam, .rank, .header, .packing, #paramsonly, #zk, #ortho, input[name=hashes], input[name=second], input[name=third], input[name=view], input[name=scale], input[name=floor], #grind, #txapp2, #txapp3, input[name=unit], #collapse-pre, #collapse-post, #perfamily').forEach(e => e.addEventListener('change', render));
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);
// The book switches themes by changing the root element's class.
new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
render();
})(window.PARETO_DATA);
