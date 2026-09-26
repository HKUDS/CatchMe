import { esc } from '../utils.js';

let version = 0;
export function modelsCleanup() { version++; }
export async function renderModels() {
  modelsCleanup();
  const token = version;
  const content = document.getElementById('content');
  content.innerHTML = `<div class="page-enter activity-dashboard provider-page">
    <div class="activity-heading"><div><div class="activity-eyebrow">MODEL CONNECTIONS</div><h1>Providers & models</h1><p>Connect your own services, discover models, and verify generation before using them.</p></div><button id="providerNew">New provider</button></div>
    <p id="providerActive"></p><div class="provider-layout"><section class="activity-panel"><h2>Saved providers</h2><div id="providerList"></div></section>
    <section class="activity-panel"><form id="providerForm"><fieldset id="providerFields">
    <h2>1. Configure provider</h2><div class="activity-model-form">
    <label>Service name<input name="name" required placeholder="my-deepseek"></label>
    <label>Provider preset<select name="provider" id="providerPreset"><option value="custom">Custom OpenAI-compatible</option></select></label>
    <label class="wide">API base URL<input name="api_url" required type="url" placeholder="https://api.deepseek.com/v1"></label>
    <label>Protocol<select name="wire_api"><option value="completions">OpenAI Chat Completions</option><option value="responses">OpenAI Responses</option></select></label>
    <label>API key<input name="api_key" type="password" autocomplete="new-password" placeholder="Blank keeps a saved key"></label>
    <label>Credential environment variable<input name="api_key_env" placeholder="DEEPSEEK_API_KEY"></label>
    <div id="providerCredential" class="provider-hint"></div></div>
    <div class="activity-actions"><button type="button" id="providerTest">Test provider</button><button type="button" id="providerFetch">Fetch model list</button><button type="submit">Save provider</button></div>
    <div class="provider-result" id="providerResult" role="status">Provider tests query the model catalog; they do not generate text.</div>
    <h2>2. Discover & configure models</h2><p>Fetch the catalog, select models to add, or enter IDs manually if the provider does not expose a catalog.</p>
    <input id="providerSearch" aria-label="Filter discovered models" placeholder="Filter model catalog…"><div id="providerCatalog" class="provider-catalog"></div><button type="button" id="providerAdd">Add selected models</button>
    <div class="activity-model-form"><label class="wide">Configured model IDs (one per line)<textarea name="models" rows="4" placeholder="deepseek-chat"></textarea></label>
    <label class="wide">Model to test / activate<input name="model" list="providerModelOptions" placeholder="Choose or enter a model ID"><datalist id="providerModelOptions"></datalist></label></div>
    <div class="activity-actions"><button type="button" id="providerModelTest">Test model</button><button type="button" class="primary" id="providerActivate">Save & use this model</button></div>
    <p>A model test sends only “Reply with OK.” to this provider and may incur a small charge.</p>
    <div class="provider-result" id="providerModelResult" role="status">No model test yet.</div>
    </fieldset></form><p class="provider-hint">OpenAI-compatible protocols only. Native Anthropic/Gemini APIs need a compatible gateway. Environment references are resolved by the CatchMe server. Saved credentials are not returned to this page.</p></section></div></div>`;
  const $ = id => document.getElementById(id);
  const form = $('providerForm');
  let config = {services: {}, selection: {}}, presets = [], catalog = [], chosen = new Set();
  async function api(path, data) {
    const response = await fetch(path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Request failed');
    return result;
  }
  function result(id, text, error = false) {
    if (version !== token) return;
    $(id).textContent = text; $(id).classList.toggle('error', error);
  }
  function configured() { return [...new Set(form.elements.models.value.split('\n').map(x => x.trim()).filter(Boolean))]; }
  function payload() {
    return {name: form.elements.name.value.trim(), service: {
      provider: form.elements.provider.value, api_url: form.elements.api_url.value.trim(),
      wire_api: form.elements.wire_api.value, api_key: form.elements.api_key.value.trim(),
      api_key_env: form.elements.api_key_env.value.trim(), models: configured()
    }};
  }
  function options() {
    $('providerModelOptions').innerHTML = [...new Set([...configured(), ...catalog])].map(m => `<option value="${esc(m)}"></option>`).join('');
  }
  function showCatalog() {
    const query = $('providerSearch').value.toLowerCase();
    const visible = catalog.filter(m => m.toLowerCase().includes(query));
    $('providerCatalog').innerHTML = visible.map(m => `<label><input type="checkbox" value="${esc(m)}" ${chosen.has(m) ? 'checked' : ''}>${esc(m)}</label>`).join('') || '<p>No models found. Fetch a list or enter model IDs below.</p>';
    $('providerCatalog').querySelectorAll('input').forEach(input => input.onchange = () => input.checked ? chosen.add(input.value) : chosen.delete(input.value));
    options();
  }
  function list() {
    $('providerActive').textContent = config.selection.service ? `Active: ${config.selection.service} / ${config.selection.model}` : `Active: legacy provider configuration / ${config.selection.model || 'not set'}`;
    $('providerList').innerHTML = Object.entries(config.services).map(([name, s]) => `<button type="button" class="provider-card" data-name="${esc(name)}"><b>${esc(name)}</b><small>${esc(s.provider || 'custom')} · ${s.models?.length || 0} models</small><small>${config.selection.service === name ? 'Active service' : 'Click to edit'}</small></button>`).join('') || '<p>No saved providers yet. Configure your first connection.</p>';
    $('providerList').querySelectorAll('button').forEach(b => b.onclick = () => edit(b.dataset.name));
  }
  function edit(name) {
    const service = config.services[name] || {};
    form.reset();
    form.elements.name.value = name || '';
    for (const key of ['provider','api_url','api_key_env','wire_api']) form.elements[key].value = service[key] || ({provider:'custom', wire_api:'completions'}[key] || '');
    if (!form.elements.provider.value) form.elements.provider.value = 'custom';
    form.elements.api_url.value ||= presets.find(p => p.id === service.provider)?.api_url || '';
    form.elements.models.value = (service.models || []).join('\n');
    form.elements.model.value = name && config.selection.service === name ? config.selection.model : (service.models || [])[0] || '';
    $('providerCredential').textContent = service.has_api_key ? 'Saved credential available. Leave the key blank to retain it.' : 'No saved credential. Local providers may work without a key.';
    catalog = []; chosen.clear(); showCatalog();
    result('providerResult','Ready to test this connection.'); result('providerModelResult','No model test yet.');
  }
  async function action(callback, target='providerResult') {
    if (!form.reportValidity()) return;
    $('providerFields').disabled = true;
    $('providerNew').disabled = true;
    $('providerList').querySelectorAll('button').forEach(b => b.disabled = true);
    result(target,'Working…');
    try { await callback(); } catch(e) { result(target,e.message,true); }
    finally {
      if (version === token) {
        $('providerFields').disabled = false; $('providerNew').disabled = false;
        $('providerList').querySelectorAll('button').forEach(b => b.disabled = false);
      }
    }
  }
  async function save(activate) {
    const data = payload(), model = form.elements.model.value.trim();
    if (activate) {
      if (!model) throw new Error('Enter a model ID to activate.');
      data.service.models = [...new Set([...data.service.models, model])]; data.model = model;
    }
    const saved = await api('/api/activity/models', data);
    if (version !== token) return;
    config = saved; list();
    form.elements.models.value = data.service.models.join('\n');
    form.elements.api_key.value = ''; options();
    $('providerCredential').textContent = config.services[data.name].has_api_key ? 'Credential saved.' : 'No saved credential.';
    result('providerResult', activate ? `Saved and activated ${data.name} / ${model}.` : 'Provider and configured models saved. Active selection preserved.');
  }
  form.onsubmit = e => { e.preventDefault(); action(() => save(false)); };
  $('providerNew').onclick = () => edit('');
  $('providerPreset').onchange = () => {
    const preset = presets.find(p => p.id === form.elements.provider.value);
    if (preset) form.elements.api_url.value = preset.api_url;
    form.elements.api_key.value = ''; form.elements.api_key_env.value = '';
    result('providerResult','Provider changed. Enter credentials for this endpoint before testing.');
  };
  $('providerTest').onclick = () => action(async () => {
    const r = await api('/api/activity/providers/test', payload());
    result('providerResult',r.ok ? `Connected · ${r.latency_ms} ms · ${r.model_count} catalog models. Test a model to verify generation.` : r.error,!r.ok);
  });
  $('providerFetch').onclick = () => action(async () => {
    const r = await api('/api/activity/providers/models', payload());
    if (!r.ok) throw new Error(r.error);
    if (version !== token) return;
    catalog = r.models; chosen.clear(); showCatalog();
    result('providerResult',`Fetched ${catalog.length} models in ${r.latency_ms} ms. Select models to add below.`);
  });
  $('providerSearch').oninput = showCatalog;
  form.elements.models.oninput = options;
  $('providerAdd').onclick = () => { form.elements.models.value = [...new Set([...configured(),...chosen])].join('\n'); options(); result('providerResult',`Added ${chosen.size} selected models. Save to persist.`); };
  $('providerActivate').onclick = () => action(() => save(true));
  $('providerModelTest').onclick = () => action(async () => {
    const model = form.elements.model.value.trim();
    if (!model) throw new Error('Enter a model ID to test.');
    const r = await api('/api/activity/models/test', {...payload(), model});
    result('providerModelResult', r.ok ? `${r.model} · ${r.latency_ms} ms\n${r.response}` : (r.error || r.message), !r.ok);
  }, 'providerModelResult');
  try {
    const [saved, choices] = await Promise.all([api('/api/activity/models'),api('/api/activity/providers/presets')]);
    if (version !== token) return;
    config = saved; presets = choices;
    $('providerPreset').insertAdjacentHTML('beforeend', presets.map(p => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join(''));
    list(); edit(config.selection.service || Object.keys(config.services)[0] || '');
  } catch(e) { result('providerResult', e.message, true); }
}
