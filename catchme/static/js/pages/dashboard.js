import { esc, fmtCount } from '../utils.js';

let timer, generation = 0, next = null, models = null, busy = false;
const $ = id => document.getElementById(id);
async function request(url, data) {
  const response = await fetch(url, data === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed');
  return result;
}
const date = ts => ts ? new Date(ts * 1000).toLocaleString() : 'Never';
function message(text, error = false) {
  if ($('activityMessage')) { $('activityMessage').textContent = text; $('activityMessage').classList.toggle('error', error); }
}
function params() {
  const until = Date.now() / 1000, days = Number($('activityRange').value);
  return new URLSearchParams({since: until - days * 86400, until,
    source: $('activitySource').value, category: $('activityCategory').value});
}
function eventRows(events) {
  return events.map(e => `<details class="activity-event"><summary>
    <span class="activity-event-time">${esc(date(e.ts))}</span>
    <span><b>${esc(e.app)}</b><small>${esc(e.kind)} · ${esc(e.source)}</small></span>
    <span class="activity-event-title">${esc(e.title)}</span>
    </summary><div class="activity-provenance">Record #${e.id} · observed ${esc(date(e.observed))}</div><pre>${esc(JSON.stringify(e.payload, null, 2))}</pre></details>`).join('');
}
async function loadEvents(append = false) {
  const token = generation;
  const p = params(); p.set('q', $('activitySearch').value); p.set('limit', '60');
  if (append && next) p.set('before', next);
  const data = await request('/api/activity/events?' + p);
  if (token !== generation || !$('activityFeed')) return;
  next = data.next;
  if (append) $('activityFeed').insertAdjacentHTML('beforeend', eventRows(data.events));
  else $('activityFeed').innerHTML = data.events.length ? eventRows(data.events) : '<div class="empty">No observations match this range. Scan sources, enable a reader, then collect.</div>';
  $('activityMore').hidden = !next;
}
async function refresh() {
  if (!$('activityStats')) return;
  const token = generation;
  const [inventory, facts, history] = await Promise.all([
    request('/api/activity/sources'), request('/api/activity/facts?' + params()), request('/api/activity/analyses')
  ]);
  if (token !== generation || !$('activityStats')) return;
  inventory.sources.sort((a, b) => Number(b.enabled) - Number(a.enabled) || Number(b.reader === 'foreground') - Number(a.reader === 'foreground') || a.name.localeCompare(b.name));
  const enabled = inventory.sources.filter(s => s.enabled).length;
  const problems = inventory.sources.filter(s => s.enabled && s.status !== 'available').length;
  $('activityStats').innerHTML = [
    ['Discovered apps', inventory.applications.length, 'Installed software inventory'],
    ['Enabled sources', enabled, problems ? `${problems} need attention` : 'Independent readers'],
    ['Observations', facts.total, 'Selected range and filters'],
    ['Observed apps', facts.apps.length, 'Up to 30 shown']
  ].map(([label, n, sub]) => `<div class="stat-card"><div class="stat-label">${label}</div><div class="stat-val">${fmtCount(n)}</div><div class="stat-sub">${sub}</div></div>`).join('');
  const selected = $('activitySource').value;
  $('activitySource').innerHTML = '<option value="">All sources</option>' + inventory.sources.map(s => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join('');
  $('activitySource').value = selected;
  $('activitySources').innerHTML = inventory.sources.length ? inventory.sources.map(s => `<div class="activity-source">
    <div><b>${esc(s.name)}</b><span class="activity-badge ${s.status === 'available' ? 'available' : ''}">${esc(s.reader === 'inventory' ? 'Foreground supported' : s.status.replaceAll('_', ' '))}</span>
    <p>${esc(s.detail)}</p><small>${esc(s.category)} · last collected ${esc(date(s.collected))}</small>
    ${s.error ? `<p class="error">${esc(s.error)}</p>` : ''}
    <details><summary>Source locations</summary><pre>${esc(s.paths.join('\n') || 'macOS foreground application API')}</pre></details></div>
    <label class="activity-switch"><input type="checkbox" aria-label="Collect ${esc(s.name)}" data-source="${esc(s.id)}" ${s.enabled ? 'checked' : ''} ${['missing','unsupported'].includes(s.status) && !s.enabled ? 'disabled' : ''}> Collect</label>
    </div>`).join('') : '<div class="empty">Scan this computer to discover apps and available traces.</div>';
  $('activitySources').querySelectorAll('input[data-source]').forEach(input => input.onchange = async () => {
    input.disabled = true;
    try { await request('/api/activity/sources/' + encodeURIComponent(input.dataset.source), {enabled: input.checked}); message('Source preference saved.'); await refresh(); }
    catch (e) { input.checked = !input.checked; message(e.message, true); }
    finally { input.disabled = false; }
  });
  $('activityApps').innerHTML = inventory.applications.map(a => `<div class="activity-app"><b>${esc(a.name)}</b><small>${esc(a.category)} · ${esc(a.version)}</small><span title="${esc(a.path)}">${esc(a.id)}</span></div>`).join('') || '<div class="empty">No app inventory yet. Discovery currently supports macOS.</div>';
  const max = Math.max(1, ...facts.apps.map(a => a.events));
  $('activityRanking').innerHTML = facts.apps.map(a => `<div class="activity-rank"><div><b>${esc(a.app)}</b><span>${fmtCount(a.events)} events · ${a.active_samples} active samples</span></div><div class="activity-bar"><i style="width:${a.events / max * 100}%"></i></div></div>`).join('') || '<div class="empty">Collect observations to see app distribution.</div>';
  const bucket = Math.max(3600, Math.ceil((facts.until - facts.since) / (48 * 3600)) * 3600);
  const start = Math.floor(facts.since / bucket) * bucket;
  const bins = Array.from({length: Math.ceil((facts.until - start) / bucket)}, (_, i) => ({ts: start + i * bucket, events: 0}));
  facts.hours.forEach(h => { const i = Math.floor((h.ts - start) / bucket); if (bins[i]) bins[i].events += h.events; });
  const hourlyMax = Math.max(1, ...bins.map(h => h.events));
  $('activityChart').innerHTML = bins.map(h => `<div title="${esc(date(h.ts))}: ${h.events} observations (${bucket / 3600}h bucket)" style="height:${h.events ? Math.max(3, h.events / hourlyMax * 100) : 0}%"><span>${h.events}</span></div>`).join('');
  $('activityChartRange').textContent = `${date(facts.since)} → ${date(facts.until)} · ${bucket / 3600}h buckets`;
  $('activityKinds').textContent = facts.kinds.map(k => `${k.kind}: ${k.events}`).join(' · ');
  $('activityAnalyses').innerHTML = history.map(a => `<details class="activity-analysis"><summary>${esc(date(a.created))} · ${esc(a.service)} / ${esc(a.model)}</summary><small>${esc(date(a.since))} → ${esc(date(a.until))}</small><pre>${esc(a.answer)}</pre><details><summary>Input aggregates / provenance</summary><pre>${esc(JSON.stringify(a.facts, null, 2))}</pre></details></details>`).join('') || '<div class="empty">No model analysis yet. Local statistics are available without an LLM.</div>';
  await loadEvents();
}
function fillModels() {
  const service = $('activityService').value;
  const list = models.services[service]?.models || [];
  $('activityModel').innerHTML = list.map(m => `<option>${esc(m)}</option>`).join('');
  if (list.includes(models.selection.model)) $('activityModel').value = models.selection.model;
}
async function loadModels() {
  const token = generation;
  const result = await request('/api/activity/models');
  if (token !== generation || !$('activityService')) return;
  models = result;
  $('activityService').innerHTML = Object.keys(models.services).map(s => `<option>${esc(s)}</option>`).join('') || '<option value="">Legacy configuration</option>';
  $('activityService').value = models.selection.service || '';
  if (!$('activityService').value && Object.keys(models.services).length) $('activityService').selectedIndex = 0;
  fillModels();
  $('activityModelNote').textContent = models.legacy ? 'Existing provider configuration remains active. Open Models to configure a named service and model.' : `Active: ${models.selection.service} / ${models.selection.model}`;
}
async function action(button, task) {
  button.disabled = true;
  try { await task(); } catch (e) { message(e.message, true); }
  finally { button.disabled = false; }
}
export function dashboardCleanup() { generation++; clearTimeout(timer); busy = false; }
export function renderDashboard() {
  dashboardCleanup();
  const token = generation;
  $('content').innerHTML = `<div class="page-enter activity-dashboard">
    <div class="activity-heading"><div><div class="activity-eyebrow">LOCAL INTELLIGENCE INFRASTRUCTURE</div><h1>Activity monitor</h1><p>Explore the traces your software leaves behind.</p></div><div class="activity-actions"><button id="activityScan">Scan computer</button><button id="activityCollect" class="primary">Collect now</button></div></div>
    <div id="activityMessage" role="status">Local statistics need no LLM. Sources collect only after you enable them.</div>
    <div class="stats-grid" id="activityStats"></div>
    <div class="activity-filters"><select id="activityRange" aria-label="Time range"><option value="1">Last 24 hours</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="365">Last year</option></select><select id="activitySource" aria-label="Source"><option value="">All sources</option></select><select id="activityCategory" aria-label="Category"><option value="">All categories</option>${['development','communication','office','creative','browser','system','other'].map(c => `<option>${c}</option>`).join('')}</select><label><input type="checkbox" id="activityLive"> Collect every 10s while this page is open</label></div>
    <div class="activity-columns"><section class="activity-panel"><h2>Activity volume</h2><p>Observed activity over the selected range</p><div class="activity-chart" id="activityChart"></div><p id="activityChartRange"></p><small id="activityKinds"></small></section><section class="activity-panel"><h2>Software distribution</h2><p>Counts are observations, not time spent or productivity.</p><div id="activityRanking"></div></section></div>
    <section class="activity-panel"><div class="activity-section-head"><div><h2>Raw observations</h2><p>Expand any record to inspect its payload and source.</p></div><input id="activitySearch" placeholder="Search app or title…" aria-label="Search observations"></div><div id="activityFeed"></div><button id="activityMore" hidden>Load more</button></section>
    <section class="activity-panel"><h2>Sources & collection</h2><p>Conversation readers contain text; history readers contain URLs. Log readers collect file metadata only. Basic secret masking is applied, but cannot detect every private value.</p><div id="activitySources"></div></section>
    <section class="activity-panel"><details><summary class="activity-summary">Installed software inventory</summary><div id="activityApps" class="activity-app-grid"></div></details></section>
    <section class="activity-panel"><div class="activity-section-head"><div><h2>Analysis</h2><p>Send the selected aggregate counts and app names to your model. Raw conversations stay out of this request.</p></div><button id="activityAnalyze" class="primary">Analyze aggregates</button></div><div class="activity-actions"><select id="activityService" aria-label="LLM service"></select><select id="activityModel" aria-label="Model"></select><button id="activitySelectModel">Use service + model</button><button id="activityEditModel">Edit service</button></div><p id="activityModelNote"></p><div id="activityAnalyses"></div>
    <button type="button" onclick="nav('models')">Manage providers & models →</button></section>
    </div>`;
  $('activityScan').onclick = e => action(e.currentTarget, async () => { message('Discovering local software and traces…'); const r = await request('/api/activity/scan', {}); message(`Found ${r.applications} apps and ${r.sources} candidate sources.`); await refresh(); });
  async function collectOnce() { const r = await request('/api/activity/collect', {}); message(r.busy ? 'Another collector is running.' : `Collected ${r.inserted} new observations.${Object.keys(r.errors || {}).length ? ' Some sources need attention; see below.' : ''}`); await refresh(); }
  $('activityCollect').onclick = e => action(e.currentTarget, collectOnce);
  ['activityRange','activitySource','activityCategory'].forEach(id => $(id).onchange = () => refresh().catch(e => message(e.message, true)));
  $('activitySearch').onchange = () => loadEvents().catch(e => message(e.message, true));
  $('activityMore').onclick = e => action(e.currentTarget, () => loadEvents(true));
  $('activityService').onchange = fillModels;
  $('activityEditModel').onclick = () => window.nav('models');
  $('activitySelectModel').onclick = e => action(e.currentTarget, async () => { await request('/api/activity/models/select', {service: $('activityService').value, model: $('activityModel').value}); await loadModels(); message('Service and model selected.'); });
  $('activityAnalyze').onclick = e => action(e.currentTarget, async () => { message('Analyzing aggregate observations…'); await request('/api/activity/analyze', {...Object.fromEntries(params()), service: $('activityService').value, model: $('activityModel').value}); message('Analysis saved with its input aggregates.'); await refresh(); });
  async function tick() {
    if (token !== generation) return;
    if ($('activityLive')?.checked && !busy) {
      busy = true;
      try { await collectOnce(); } catch (e) { message(e.message, true); } finally { busy = false; }
    }
    if (token === generation) timer = setTimeout(tick, 10000);
  }
  Promise.all([refresh(), loadModels()]).catch(e => message(e.message, true));
  timer = setTimeout(tick, 10000);
}
