import { esc } from '../utils.js';

let epoch = 0, timer, apps = [], category = 'all', search = '', selected = null, next = null, collecting = false;
let monitor = {}, activityKind = 'all', activityQuery = '', activitySession = '', activityRequest = 0, searchTimer;
const $ = id => document.getElementById(id);
const groups = {all:'全部应用', following:'已开启', office:'办公', ai:'AI 助手', social:'沟通', development:'编程', creative:'创作', browser:'浏览器'};
const icon = (app, cls='') => `<img class="app-icon ${cls}" src="/img/apps/${app.id}.png" alt="" width="64" height="64">`;
async function api(path, data) {
  const res = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const value = await res.json();
  if (!res.ok) throw new Error(value.error || '暂时没能完成，请再试一次');
  return value;
}
function notify(text, error=false) {
  if ($('gardenNotice')) { $('gardenNotice').textContent=text; $('gardenNotice').classList.toggle('is-error',error); }
}
function relative(ts) {
  if (!ts) return '等待第一段记忆';
  const seconds = Math.max(0, Date.now()/1000-ts);
  if (seconds<60) return '刚刚';
  if (seconds<3600) return `${Math.floor(seconds/60)} 分钟前`;
  if (seconds<86400) return `${Math.floor(seconds/3600)} 小时前`;
  if (seconds<86400*7) return `${Math.floor(seconds/86400)} 天前`;
  return new Date(ts*1000).toLocaleDateString('zh-CN',{month:'short',day:'numeric'});
}
function updateStatus() {
  const count=apps.filter(a=>a.enabled).length;
  if ($('gardenSummary')) $('gardenSummary').textContent=`${count} 个应用已开启 · 记忆保存在这台电脑`;
}
function renderCards() {
  if (!$('gardenCards')) return;
  const visible=apps.filter(a=>(category==='all'||(category==='following'?a.enabled:a.category===category)) && `${a.name} ${a.description}`.toLowerCase().includes(search.toLowerCase()));
  $('gardenCards').innerHTML=visible.length ? visible.map(a=>`<article class="garden-card" style="--app-tint:${a.color}">
    <button class="garden-card-open" data-open="${a.id}" aria-label="查看 ${esc(a.name)} 最近活动">
      <div class="garden-card-top">${icon(a)}<span class="garden-availability">${a.available?'本机可用':'尚未发现'}</span></div>
      <h2>${esc(a.name)}</h2><p>${esc(a.description)}</p>
      <div class="garden-card-preview">${(a.session_count??a.count) ? `<span class="garden-count">${(a.session_count??a.count).toLocaleString()}</span> ${a.session_count!==null&&a.session_count!==undefined?'个会话':'条记录'} <span class="garden-last">${relative(a.last)}</span>` : '开启后，最近活动会出现在这里'}</div>
    </button>
    <div class="garden-card-foot"><span class="garden-state ${a.enabled?'on':''}"><i></i>${a.enabled?(a.mode==='full'?'完整监控':'基础记录'):'未开启'}</span>
    <button role="switch" aria-checked="${a.enabled}" aria-label="监测 ${esc(a.name)}" class="garden-switch" data-toggle="${a.id}" ${!a.available&&!a.enabled?'disabled':''}><span></span></button></div>
    </article>`).join('') : '<div class="garden-empty"><h3>还没找到这样的应用</h3><p>换个关键词，或看看全部应用。</p></div>';
  $('gardenCards').querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>openApp(b.dataset.open));
  $('gardenCards').querySelectorAll('[data-toggle]').forEach(b=>b.onclick=()=>toggle(b.dataset.toggle,b));
  $('gardenResultCount').textContent=`${visible.length} 个应用`;
  updateStatus();
}
async function refresh() {
  const e=epoch;
  const data=await api('/api/library/apps');
  if (e!==epoch) return;
  apps=data.apps;monitor=data.monitor||{};
  if (!selected&&!catalogOpen) renderCards();
  else updateDetailHeader();
}
async function toggle(id, button) {
  const app=apps.find(a=>a.id===id), enabled=!app.enabled, e=epoch;
  button.disabled=true;
  try {
    await api(`/api/library/apps/${id}/monitor`,{enabled});
    if(e!==epoch) return;
    app.enabled=enabled;
    notify(enabled?`已为 ${app.name} 开启记录`:`已暂停 ${app.name}，已有记忆仍可查看`);
    if (selected) updateDetailHeader(); else renderCards();
    if(enabled) collect();
  } catch(err) { notify(err.message,true); button.disabled=false; }
}
async function collect() {
  if(collecting) return;
  collecting=true;
  const e=epoch;
  try {
    await api('/api/activity/collect',{});
    if(e!==epoch) return;
    await refresh();
    // Preserve expanded records and pagination while the user reads; detail refresh is explicit.
    if($('gardenSync')) $('gardenSync').textContent='刚刚更新';
  } catch(err) { if(e===epoch) notify('暂时无法更新活动，请稍后重试。',true); }
  finally { collecting=false; }
}
function updateDetailHeader() {
  const a=apps.find(a=>a.id===selected);
  if(!a||!$('appDetailControl')) return;
  $('appDetailControl').innerHTML=`<span class="garden-state ${a.enabled?'on':''}"><i></i>${a.enabled?'记录已开启':'记录已暂停'}</span><button role="switch" aria-checked="${a.enabled}" aria-label="监测 ${esc(a.name)}" class="garden-switch" ${!a.available&&!a.enabled?'disabled':''}><span></span></button>`;
  $('appDetailControl').querySelector('button').onclick=e=>toggle(a.id,e.currentTarget);
  $('appMemoryCount').textContent=a.count.toLocaleString();
  renderModePanel(a);
  if($('appModeSummary'))$('appModeSummary').textContent=`${a.enabled?(a.mode==='full'?'完整监控':'基础记录'):'记录已暂停'} · 记录设置`;
}
function renderModePanel(app) {
  if(!$('appModePanel'))return;
  const full=app.mode==='full';
  let status=monitor.running?'本地采集正在运行，关闭网页后也会继续。':'本地采集未运行，请通过 catchme web 启动服务。';
  if(monitor.error)status='采集暂时不可用，请重新启动本地服务后查看。';
  if(app.id==='wechat'&&app.enabled&&!monitor.accessibility)status='微信文件索引可用；确认文件是否打开还需要辅助功能权限。';
  if(full&&app.enabled&&!monitor.accessibility)status='等待辅助功能权限：系统设置 → 隐私与安全性 → 辅助功能，允许启动 CatchMe 的终端或 Python，然后重新启动服务。';
  if(full&&app.enabled&&monitor.input==='permission_required')status='界面采集可用；操作记录仍需输入监控权限。请在系统设置中允许启动 CatchMe 的终端或 Python。';
  if(full&&app.enabled&&monitor.accessibility&&monitor.foreground_app===app.id&&!monitor.readable_text)status='正在监测此应用，但当前窗口没有提供可读取的正文。仍可记录可用的窗口和操作信息。';
  if(monitor.platform!=='macos')status='完整监控与文件打开追踪目前仅支持 macOS。';
  $('appModePanel').innerHTML=`<div><span class="garden-eyebrow">记录方式</span><h2>${full?'完整监控':'基础记录'}${!app.enabled?' · 已暂停':''}</h2><p>${full?(['claude','codex'].includes(app.id)?'读取本地对话、项目与工具记录，并补充前台界面及操作。':'记录前台窗口中可读取的内容、输入变化和应用操作。'):'保留使用情况、最近文档和应用已有的本地记录。'}</p><small>${esc(status)}</small>${app.source_issues?`<small>${app.source_issues} 项本地记录暂时无法读取，可在高级设置中查看原因。</small>`:''}</div><div class="garden-mode-controls">${app.full_supported?`<button class="garden-secondary" id="appModeChange">${full?'切回基础记录':'了解完整监控'}</button>`:'<span class="garden-muted">此应用目前支持基础记录</span>'}</div>`;
  if($('appModeChange'))$('appModeChange').onclick=()=>full?changeMode(app,'basic'):showFullMode(app);
}
async function changeMode(app,mode) {
  const e=epoch;
  try {
    await api(`/api/library/apps/${app.id}/mode`,{mode,consent:mode==='full'});
    if(mode==='full')await api(`/api/library/apps/${app.id}/monitor`,{enabled:true});
    if(e!==epoch)return;
    $('fullModeDialog')?.close();$('fullModeDialog')?.remove();
    await refresh();if(selected===app.id)openApp(app.id);notify(mode==='full'?`已为 ${app.name} 开启完整监控`:'已切回基础记录，历史记录保留');
  } catch(err){if(e===epoch){const target=$('fullModeError');if(target)target.textContent=err.message;else notify(err.message,true);}}
}
function showFullMode(app) {
  $('fullModeDialog')?.remove();
  const dialog=document.createElement('dialog');dialog.id='fullModeDialog';dialog.className='garden-consent';
  dialog.innerHTML=`<form method="dialog"><button class="garden-dialog-close" aria-label="关闭">×</button></form>${icon(app)}<span class="garden-eyebrow">由你决定记录多少</span><h2>为 ${esc(app.name)} 开启完整监控</h2><p>切换后将开启此应用的记录，并保存：</p>${['claude','codex'].includes(app.id)?'<p>此应用还会直接读取本地会话中已有的工具调用、参数和结果，包括历史记录。</p>':''}<ul><li>当前窗口中可读取的文字，包括界面上呈现的消息、文档或代码。</li><li>输入框内容的变化，包括已输入或粘贴的文字。</li><li>窗口切换、点击、滚动、快捷键，以及可确认的文件打开记录。</li></ul><div class="garden-consent-note">仅采集此应用的前台窗口。这不是完整聊天备份：后台或未显示的消息、快速变化的内容和未开放辅助功能的界面可能无法捕获。输入文字不等于发送成功；不会猜测消息收发方向。系统标记的密码框会跳过。<br><br>内容保存在这台电脑，本功能不会自动发给 LLM。可随时暂停或切回基础记录，历史内容仍保留。仅支持 macOS，需要辅助功能权限，操作记录还可能需要输入监控权限。</div><label class="garden-consent-check"><input type="checkbox" id="fullModeConsent">我了解以上范围，同意为 ${esc(app.name)} 开启完整监控</label><p id="fullModeError" role="alert"></p><button id="fullModeConfirm" class="garden-primary" disabled>开启完整监控</button>`;
  $('gardenBody').append(dialog);
  $('fullModeConsent').onchange=e=>$('fullModeConfirm').disabled=!e.target.checked;
  $('fullModeConfirm').onclick=async e=>{e.currentTarget.disabled=true;await changeMode(app,'full');if($('fullModeConfirm'))$('fullModeConfirm').disabled=false;};
  dialog.showModal();
}
const actions={bookmark:'保存的书签',download:'下载列表记录',capture_gap:'部分记录无法读取',attachment_available:'微信文件已保存',document_opened:'打开了微信文件',window_context:'切换了窗口',visible_content:'界面内容变化',input_changed:'输入框内容变化',app_action:'应用操作',tool_call:'AI 调用了工具',tool_result:'工具返回了结果',document_recent:'最近使用的文档',workspace_recent:'发现最近工作区',conversation_index:'更新了对话主题',conversation:'留下了一段对话',project_recent:'最近的创作工程',browser_visit:'浏览了网页',file_metadata:'本地文件有变化',foreground_sample:'应用出现在前台'};
function eventMarkup(event,app) {
  const when=new Date(event.ts*1000), data=event.payload;
  const title=event.kind==='foreground_sample'?app.name:event.title || app.name;
  const subtitle=event.kind==='conversation' ? (/^<(local-command|command-name|system-reminder)/.test((data.text||'').trimStart())?'会话上下文':data.role==='user'?'你说':'AI 回复') : (actions[event.kind]||'一段应用活动');
  return `<article class="garden-memory"><div class="garden-memory-time">${when.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})}</div>
    <div class="garden-memory-main"><span class="garden-memory-type">${esc(subtitle)}</span><h3>${esc(title)}</h3>
    <details><summary>查看记录</summary><div class="garden-record-content">${data.text!==undefined?`<p>${esc(data.text)||'（输入框已清空）'}</p>`:''}${data.project?`<p>项目：${esc(data.project)}</p>`:''}${data.session_id?`<p>会话：${esc(data.session_id)}</p>`:''}${data.model?`<p>模型：${esc(data.model)}</p>`:''}${data.folder?`<p>书签文件夹：${esc(data.folder)}</p>`:''}${data.viewing_app?`<p>打开应用：${esc(data.viewing_app)}</p>`:''}${data.size!==undefined?`<p>文件大小：${Number(data.size).toLocaleString()} 字节</p>`:''}${data.truncated?'<p>内容较长，这是一段截取记录。</p>':''}${data.file||data.uri||data.url||data.draft_fold_path?`<p>${esc(data.file||data.uri||data.url||data.draft_fold_path)}</p>`:''}<p class="garden-muted">${esc(data.meaning || app.note || (event.kind==='workspace_recent'?'这是最近工作区列表中的一条记录，时间为首次发现时间。':event.kind==='file_metadata'?'这条记录表示文件发生变化，不代表一次用户操作。':event.kind==='foreground_sample'?'这条记录表示采样时应用位于前台，不代表持续使用时长。':'来自应用保存在本机的活动记录。'))}</p></div></details></div></article>`;
}
let detailTab = '', chatEvents = [], currentSession = null, catalogOpen = false;
function sessionApp(app) { return app.presentation?.type === 'sessions'; }
function detailTabs(app) { return [...(sessionApp(app)?[{id:'sessions',label:'对话会话',placeholder:'搜索会话、项目或聊天内容…'}]:[]), ...(app.presentation?.tabs||[])]; }
function displayDate(ts) { return ts ? new Date(ts*1000).toLocaleString('zh-CN',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '时间未知'; }
function safeWeb(url) { try {const u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:'';}catch{return '';} }
function sourcePath(data) {return data.file||data.uri||data.draft_fold_path||data.url||'';}
function collectionMarkup(event,app,layout) {
  const data=event.payload,path=sourcePath(data),ext=(event.title.split('.').pop()||'FILE').slice(0,5).toUpperCase();
  const url=safeWeb(data.url),domain=url?new URL(url).hostname:'';
  const title=url?`<a href="${esc(url)}" target="_blank" rel="noreferrer noopener">${esc(event.title||domain)}</a>`:esc(event.title||app.name);
  const badge=layout==='projects'?(data.entry_type==='file'?ext:data.entry_type==='folder'?'文件夹':data.entry_type==='workspace'?'工作区':'项目'):layout==='topics'?'对话':layout==='web'||layout==='bookmarks'?'网页':ext;
  return `<article class="garden-collection-item ${layout}"><span class="garden-file-badge">${esc(badge)}</span><div class="garden-collection-main"><h3>${title}</h3><div class="garden-item-meta"><span>${displayDate(event.ts)}</span>${data.profile?`<span>${esc(data.profile)}</span>`:''}${data.size!=null?`<span>${Number(data.size).toLocaleString()} 字节</span>`:''}${data.folder?`<span>${esc(data.folder)}</span>`:''}${data.tm_draft_removed?'<span>已移除的工程</span>':''}${layout==='topics'?'<span>目前可读取主题索引</span>':''}${event.observations>1?`<span>${event.observations} 次记录</span>`:''}</div>${domain?`<p class="garden-item-path">${esc(domain)}</p>`:''}${path&&!url?`<p class="garden-item-path" title="${esc(path)}">${esc(path)}</p>`:''}<details><summary>记录详情</summary><div class="garden-record-content">${path?`<p>${esc(path)}</p>`:''}${data.viewing_app?`<p>查看应用：${esc(data.viewing_app)}</p>`:''}<p>${esc(data.meaning||data.evidence||app.note||'来自应用保存在本机的记录。')}</p></div></details></div></article>`;
}
function chatText(text) {
  return String(text||'').split(/(```[\s\S]*?```)/g).map(part=>part.startsWith('```')?`<pre>${esc(part.replace(/^```[^\n]*\n?/,'').replace(/```$/,''))}</pre>`:`<div class="garden-chat-prose">${esc(part)}</div>`).join('');
}
function renderChat() {
  const results=new Map(),calls=new Set(chatEvents.filter(e=>e.kind==='tool_call').map(e=>e.payload.call_id));
  chatEvents.filter(e=>e.kind==='tool_result'&&e.payload.call_id).forEach(e=>{const key=e.payload.call_id;if(!results.has(key))results.set(key,[]);results.get(key).push(e);});
  const expanded=new Set([...document.querySelectorAll('.garden-tool[open],.garden-context[open],.garden-chat-message details[open]')].map(n=>n.dataset.event));
  $('appTimeline').innerHTML=chatEvents.map(e=>{
    const p=e.payload,text=p.text||'',context=/^<(local-command|command-name|system-reminder)/.test(text.trimStart());
    if(e.kind==='tool_result'&&calls.has(p.call_id))return '';
    if(e.kind==='tool_call'||e.kind==='tool_result'){
      const matches=results.get(p.call_id)||[];
      return `<details class="garden-tool" data-event="${e.id}" ${expanded.has(String(e.id))?'open':''}><summary><span>${e.kind==='tool_call'?'工具 · '+esc(p.tool||e.title):'工具返回结果'}</span><time>${displayDate(e.ts)}</time></summary><div class="garden-tool-body">${chatText(text)}${matches.map(r=>`<h4>${r.payload.is_error?'返回错误':'返回结果'}</h4>${chatText(r.payload.text)}`).join('')}</div></details>`;
    }
    if(context||e.kind==='capture_gap')return `<details class="garden-context" data-event="${e.id}" ${expanded.has(String(e.id))?'open':''}><summary>${e.kind==='capture_gap'?'有一条未导入的记录':'会话上下文'} · ${displayDate(e.ts)}</summary>${chatText(text||p.meaning)}</details>`;
    const role=p.role==='user'?'user':'assistant',body=chatText(text);
    return `<article class="garden-chat-message ${role}"><div class="garden-chat-meta"><strong>${role==='user'?'你':esc(apps.find(a=>a.id===selected)?.name||'AI')}</strong><time>${displayDate(e.ts)}</time>${p.model?`<span>${esc(p.model)}</span>`:''}</div><div class="garden-chat-bubble">${text.length>6000?`<details data-event="${e.id}" ${expanded.has(String(e.id))?'open':''}><summary>${esc(text.slice(0,180))}… · 展开完整消息（${text.length.toLocaleString()} 字）</summary>${body}</details>`:body}${p.truncated?'<p class="garden-muted">这条历史记录的正文尚未完整导入，后台回填后可刷新。</p>':''}</div></article>`;
  }).join('');
}
async function loadActivity(append=false) {
  const id=selected,e=epoch,request=++activityRequest,app=apps.find(a=>a.id===id);
  if(!app)return;
  if(!append){$('appTimeline').innerHTML='<p class="garden-muted" role="status">正在读取记录…</p>';$('appMore').hidden=true;}
  const guard=()=>e===epoch&&selected===id&&request===activityRequest&&$('appTimeline');
  if(sessionApp(app)&&detailTab==='sessions') {
    if(activitySession) {
      const params=new URLSearchParams({session:activitySession});if(append&&next)params.set('after',next);
      const result=await api(`/api/library/apps/${id}/transcript?${params}`);if(!guard())return;
      chatEvents=append?[...chatEvents,...result.events]:result.events;next=result.next;
      $('appReaderHeading').innerHTML=`<h3>${esc(currentSession?.title||'聊天历史')}</h3><p>${esc(result.project||'未提供项目目录')} · 已展示 ${chatEvents.length} / ${result.total} 条记录</p>`;
      renderChat();$('appMore').textContent='继续阅读后续对话';$('appMore').hidden=!next;
      return;
    }
    const params=new URLSearchParams({q:activityQuery});if(append&&next)params.set('before',next);
    const result=await api(`/api/library/apps/${id}/sessions?${params}`);if(!guard())return;
    const markup=result.sessions.map(s=>`<button class="garden-session-card" data-session="${esc(s.session_id)}"><div class="garden-session-card-top"><span>${esc((s.project||'本地会话').replace(/\\/g,'/').split('/').pop()||'本地会话')}</span><time>${displayDate(s.updated)}</time></div><h3>${esc(s.title||'本地对话')}</h3><p>${esc(s.project||'这个会话未提供项目目录')}</p><div class="garden-session-counts"><span>${s.messages} 条消息</span>${s.tools?`<span>${s.tools} 条工具记录</span>`:''}${s.gaps?'<span>含部分未完整导入的记录</span>':''}<span>阅读聊天历史 →</span></div></button>`).join('');
    if(append)$('appTimeline').insertAdjacentHTML('beforeend',markup);else $('appTimeline').innerHTML=markup||emptyMarkup(app,'没有找到符合条件的会话');
    const byId=new Map(result.sessions.map(s=>[s.session_id,s]));
    $('appTimeline').querySelectorAll('[data-session]').forEach(button=>{if(byId.has(button.dataset.session))button.onclick=()=>openConversation(byId.get(button.dataset.session));});
    $('appFeedCount').textContent=`${result.total.toLocaleString()} 个已采集会话`;
    next=result.next;$('appMore').textContent='查看更多会话';$('appMore').hidden=!next;
    return;
  }
  const params=new URLSearchParams({tab:detailTab,q:activityQuery});if(append&&next)params.set('before',next);
  const result=await api(`/api/library/apps/${id}/content?${params}`);if(!guard())return;
  const markup=result.layout==='timeline'?result.events.map(event=>eventMarkup(event,app)).join(''):result.events.map(event=>collectionMarkup(event,app,result.layout)).join('');
  if(append)$('appTimeline').insertAdjacentHTML('beforeend',markup);else $('appTimeline').innerHTML=markup||emptyMarkup(app,'这里暂时没有记录');
  $('appFeedCount').textContent=`${result.total.toLocaleString()} 项`;
  next=result.next;$('appMore').textContent='再看一些';$('appMore').hidden=!next;
}
function emptyMarkup(app,title) {
  return `<div class="garden-empty compact"><h3>${title}</h3><p>${activityQuery?'试试其他关键词。':app.enabled?'采集到这一类记录后，会显示在这里。':'开启这个应用的记录后，可以在这里查看。'}</p>${app.needs_permission?'<p>部分数据尚需系统访问权限，详见下方数据位置。</p>':''}</div>`;
}
function openConversation(session) {
  currentSession=session;activitySession=session.session_id;next=null;chatEvents=[];
  $('appActivityTools').hidden=true;$('appReaderHeader').hidden=false;$('appFeedCount').textContent='';
  $('appTimeline').innerHTML='<p class="garden-muted">正在读取聊天历史…</p>';
  $('appReaderHeading').innerHTML=`<h3>${esc(session.title)}</h3>`;
  loadActivity().catch(err=>notify(err.message,true));
  $('appReaderHeader').scrollIntoView({block:'start',behavior:'smooth'});
}
function changeDetailTab(tab) {
  detailTab=tab;activitySession='';activityQuery='';next=null;chatEvents=[];
  $('appActivityTools').hidden=false;$('appReaderHeader').hidden=true;$('appSearch').value='';
  const app=apps.find(a=>a.id===selected),active=detailTabs(app).find(t=>t.id===tab);
  $('appSearch').placeholder=active?.placeholder||'搜索记录…';
  $('appKinds').querySelectorAll('button').forEach(b=>{b.classList.toggle('active',b.dataset.kind===tab);b.setAttribute('aria-pressed',String(b.dataset.kind===tab));});
  loadActivity().catch(err=>notify(err.message,true));
}
async function loadLocations(app) {
  const e=epoch;
  try {
    const data=await api(`/api/library/apps/${app.id}/locations`);
    if(e!==epoch||selected!==app.id||!$('appLocations'))return;
    $('appLocations').innerHTML=data.locations.length?`<p>默认位置会自动发现。如果应用使用了其他目录，可在这里补充；保存后重新扫描，不会改变监测开关。</p>${data.locations.map((location,i)=>`<label class="garden-location-field"><strong>${esc(location.name)}</strong><span>${({available:'已发现',partial:'部分位置可读',permission_required:'需要访问权限',error:'读取失败',missing:'尚未发现'})[location.status]||location.status}</span><details><summary>已检查的默认位置</summary>${location.detected.map(p=>`<code>${esc(p)}</code>`).join('')||'<p>没有默认位置</p>'}</details><span>${['claude','codex'].includes(location.reader)?'补充会话目录或 JSONL 文件（每行一个）':['wechat_files','metadata'].includes(location.reader)?'补充数据目录（每行一个）':'补充索引文件的完整路径（每行一个）'}</span><textarea data-location-index="${i}" rows="2" placeholder="~/…">${esc(location.custom.join('\n'))}</textarea></label>`).join('')}<button class="garden-secondary" id="saveAppLocations">保存位置并重新发现</button><p role="status" id="appLocationStatus"></p>`:'此应用目前通过系统界面记录，无需指定本地数据目录。';
    if($('saveAppLocations'))$('saveAppLocations').onclick=async event=>{
      const button=event.currentTarget;button.disabled=true;
      const locations={};$('appLocations').querySelectorAll('textarea').forEach(input=>locations[data.locations[Number(input.dataset.locationIndex)].id]=input.value.split('\n').map(p=>p.trim()).filter(Boolean));
      try {await api(`/api/library/apps/${app.id}/locations`,{locations});if(e!==epoch||selected!==app.id)return;await refresh();await loadLocations(app);$('appLocationStatus').textContent='位置已保存，已重新检查可用性。';}
      catch(err){if($('appLocationStatus'))$('appLocationStatus').textContent=err.message;}
      finally{button.disabled=false;}
    };
  }catch(err){if(e===epoch&&$('appLocations'))$('appLocations').textContent=err.message;}
}
function openApp(id) {
  selected=id;catalogOpen=false;next=null;activityQuery='';activitySession='';chatEvents=[];clearTimeout(searchTimer);
  const a=apps.find(app=>app.id===id),tabs=detailTabs(a);detailTab=tabs[0]?.id||'usage';
  $('gardenBody').innerHTML=`<button class="garden-back" id="appBack">← 返回应用乐园</button><section class="garden-detail-hero" style="--app-tint:${a.color}">${icon(a,'large')}<div><span class="garden-eyebrow">我的应用</span><h1>${esc(a.name)}</h1><p>${esc(a.description)}</p></div><div id="appDetailControl"></div></section>
  <details class="garden-mode-disclosure"><summary><span id="appModeSummary">记录设置</span><span>查看与切换记录方式</span></summary><section id="appModePanel" class="garden-mode-panel"></section></details>
  <section class="garden-app-feed"><div class="garden-section-title"><div><h2>${esc(a.presentation?.heading||'应用记录')}</h2><p id="appFeedCount"></p></div><button class="garden-secondary" id="appRefresh">更新记录</button></div>
  <div class="garden-activity-tools" id="appActivityTools"><div class="garden-categories" id="appKinds">${tabs.map(t=>`<button data-kind="${t.id}" class="${t.id===detailTab?'active':''}" aria-pressed="${t.id===detailTab}">${esc(t.label)}</button>`).join('')}</div><input type="search" id="appSearch" aria-label="搜索${sessionApp(a)?'会话':'记录'}" placeholder="${esc(tabs[0]?.placeholder||'搜索记录…')}"></div>
  <div id="appReaderHeader" class="garden-reader-header" hidden><button class="garden-back" id="appSessionBack">← 所有会话</button><div id="appReaderHeading"></div></div><div id="appTimeline"></div><button id="appMore" class="garden-secondary" hidden>再看一些</button></section>
  <footer class="garden-app-foot"><p>${esc(a.note||'记录来自应用保存在本机的数据。你可以随时暂停，历史记录会继续保留。')}</p><span>已保存 <strong id="appMemoryCount">${a.count}</strong> 条记录</span></footer>
  <details class="garden-locations"><summary>数据位置与采集状态</summary><div id="appLocations">正在检查…</div></details>`;
  $('appBack').onclick=()=>{selected=null;renderBody();};
  $('appKinds').querySelectorAll('button').forEach(b=>b.onclick=()=>changeDetailTab(b.dataset.kind));
  $('appSessionBack').onclick=()=>{activitySession='';chatEvents=[];next=null;$('appReaderHeader').hidden=true;$('appActivityTools').hidden=false;loadActivity().catch(err=>notify(err.message,true));};
  $('appSearch').oninput=event=>{activityQuery=event.target.value;next=null;clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadActivity().catch(err=>notify(err.message,true)),300);};
  $('appRefresh').onclick=async event=>{const button=event.currentTarget,e=epoch;button.disabled=true;try{await collect();if(e===epoch&&selected===id)await loadActivity();}catch(err){notify(err.message,true);}finally{button.disabled=false;}};
  $('appMore').onclick=async event=>{const button=event.currentTarget;button.disabled=true;try{await loadActivity(true);}catch(err){notify(err.message,true);}finally{button.disabled=false;}};
  updateDetailHeader();loadLocations(a);loadActivity().catch(err=>notify(err.message,true));$('content').scrollTo({top:0,behavior:'smooth'});
}
async function openCatalog() {
  selected=null;catalogOpen=true;const e=epoch;
  $('gardenBody').innerHTML='<p class="garden-muted">正在整理支持的应用…</p>';
  try {
    const result=await api('/api/library/catalog');if(e!==epoch||!catalogOpen)return;
    $('gardenBody').innerHTML=`<button class="garden-back" id="catalogBack">← 返回我的应用</button><section class="garden-catalog-head"><span class="garden-eyebrow">APP DIRECTORY</span><h1>支持的应用</h1><p>目前有 ${result.apps.length} 个应用提供专属入口。查看每个应用能记录什么，再选择是否开启。</p></section><input class="garden-catalog-search" id="catalogSearch" type="search" aria-label="搜索支持的应用" placeholder="搜索应用或记录能力…"><div id="catalogApps"></div><details class="garden-other-apps"><summary>本机另外发现 ${result.discovered.length} 个应用</summary><p>这些应用尚未提供专属展示。部分应用可在高级数据设置中读取通用记录。</p><div>${result.discovered.map(a=>`<span>${esc(a.name)}</span>`).join('')}</div><button class="garden-secondary" onclick="nav('activity')">查看高级数据设置</button></details>`;
    const draw=()=>{const q=$('catalogSearch').value.toLowerCase();$('catalogApps').innerHTML=result.apps.filter(a=>(a.name+' '+a.capabilities.join(' ')).toLowerCase().includes(q)).map(a=>`<article class="garden-catalog-row">${icon(a)}<div><h2>${esc(a.name)}</h2><p>${a.capabilities.map(esc).join(' · ')}</p><small>${esc(a.note||'读取应用本地记录；具体可用性取决于本机安装、版本及访问权限。')}</small></div><div class="garden-catalog-status"><span>${a.available?'本机可用':'本机尚未发现'}</span><span>${a.full_supported?'支持完整监控':'基础记录'}</span><button class="garden-secondary" data-catalog-app="${a.id}">查看应用</button></div></article>`).join('');$('catalogApps').querySelectorAll('[data-catalog-app]').forEach(b=>b.onclick=()=>openApp(b.dataset.catalogApp));};
    $('catalogSearch').oninput=draw;$('catalogBack').onclick=()=>{catalogOpen=false;renderBody();};draw();$('content').scrollTo({top:0,behavior:'smooth'});
  }catch(err){notify(err.message,true);}
}

function renderBody() {
  selected=null;catalogOpen=false;
  $('gardenBody').innerHTML=`<section class="garden-welcome"><div class="garden-welcome-copy"><span class="garden-eyebrow">YOUR EVERYDAY, REMEMBERED</span><h1>你的应用，<br>都有迹可循<span>。</span></h1><p>把熟悉的应用放在一起，<br>让那些文档、对话和灵感，都有自己的记忆。</p><div class="garden-welcome-note"><i></i><span id="gardenSummary"></span></div></div>
    <div class="garden-welcome-apps" aria-hidden="true"><img src="/img/apps/excel.png" alt=""><img src="/img/apps/claude.png" alt=""><img src="/img/apps/wechat.png" alt=""><img src="/img/apps/word.png" alt=""><span>一点一滴，都是你。</span></div></section>
    <div class="garden-section-title garden-gallery-title"><div><h2>选择你的日常伙伴</h2><p>开启记录，点击应用看看最近发生了什么。</p></div><label class="garden-search"><span class="sr-only">搜索应用</span><input id="gardenSearch" type="search" placeholder="搜索应用…" value="${esc(search)}"></label></div>
    <div class="garden-filter-row"><div class="garden-categories">${Object.entries(groups).map(([id,name])=>`<button class="${category===id?'active':''}" data-category="${id}">${name}</button>`).join('')}</div><span id="gardenResultCount"></span></div>
    <div class="garden-grid" id="gardenCards"></div><footer class="garden-footer"><span>由你选择，为你记住。本地服务运行时持续记录，退出服务即停止。</span><button class="garden-text-button" onclick="nav('activity')">高级数据设置</button></footer>`;
  $('gardenSearch').oninput=e=>{search=e.target.value;renderCards();};
  $('gardenBody').querySelectorAll('[data-category]').forEach(b=>b.onclick=()=>{category=b.dataset.category;renderBody();});
  renderCards();
}
export function gardenCleanup() { epoch++; clearTimeout(timer); clearTimeout(searchTimer); document.body.classList.remove('garden-mode'); selected=null; }
export async function renderGarden() {
  gardenCleanup(); const e=epoch; document.body.classList.add('garden-mode');
  $('content').innerHTML=`<div class="app-garden"><header class="garden-topbar"><span class="garden-breadcrumb">我的空间 <span>/</span> 应用乐园</span><div><span id="gardenSync">只属于你的记忆</span><button class="garden-secondary" id="gardenCatalog">支持的应用</button><button class="garden-secondary" id="gardenDiscover">刷新应用</button></div></header><div id="gardenNotice" role="status"></div><div id="gardenBody"></div></div>`;
  renderBody();
  $('gardenCatalog').onclick=openCatalog;
  $('gardenDiscover').onclick=async ev=>{
    const button=ev.currentTarget;button.disabled=true;notify('正在看看这台电脑上的应用…');
    try {await api('/api/activity/scan',{});await refresh();await collect();notify('应用已更新');}catch(err){notify(err.message,true);}finally{button.disabled=false;}
  };
  try {
    await refresh();
    if(e!==epoch)return;
    if(!apps.some(a=>a.available)){await api('/api/activity/scan',{});await refresh();}
    collect();
  } catch(err) {notify('暂时无法加载应用，请点击“刷新应用”重试。',true);}
  async function tick(){if(e!==epoch)return;await collect();if(e===epoch)timer=setTimeout(tick,15000);}
  if(e===epoch)timer=setTimeout(tick,15000);
}
