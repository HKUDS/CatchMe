import { api, showToast } from './utils.js';
import { renderDashboard, dashboardCleanup } from './pages/dashboard.js';
import { renderGarden, gardenCleanup } from './pages/garden.js';
import { renderModels, modelsCleanup } from './pages/models.js';
import { renderRecall } from './pages/recall.js';
import { renderExplorer, explorerCleanup } from './pages/explorer.js';
import { renderSystem, systemCleanup } from './pages/system.js';
import { renderChat, renderChatMain, toggleChatPanel } from './pages/chat.js';
import { closeTreeDetail } from './pages/tree.js';

/* ── State ── */
var page = 'home';

/* ── Theme ── */
function toggleTheme() {
  var dark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('catchme-theme', dark ? 'dark' : 'light');
  document.getElementById('themeIcon').innerHTML = dark
    ? '<circle cx="9" cy="9" r="4.5"/><path d="M9 2v1.5M9 14.5V16M2 9h1.5M14.5 9H16M4.05 4.05l1.06 1.06M12.89 12.89l1.06 1.06M4.05 13.95l1.06-1.06M12.89 5.11l1.06-1.06"/>'
    : '<path d="M13.5 10.5a5.5 5.5 0 01-7.8-6.4A6.5 6.5 0 1013.5 10.5z"/>';
}
(function() {
  var s = localStorage.getItem('catchme-theme');
  if (s === 'dark' || (!s && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
    document.getElementById('themeIcon').innerHTML = '<circle cx="9" cy="9" r="4.5"/><path d="M9 2v1.5M9 14.5V16M2 9h1.5M14.5 9H16M4.05 4.05l1.06 1.06M12.89 12.89l1.06 1.06M4.05 13.95l1.06-1.06M12.89 5.11l1.06-1.06"/>';
  }
})();
window.toggleTheme = toggleTheme;

/* ── Language ── */
var _summaryLang = 'en';
function toggleLangMenu() { document.getElementById('langMenu').classList.toggle('open'); }
function setLang(lang) {
  _summaryLang = lang;
  document.querySelectorAll('.lang-opt').forEach(function(b) { b.classList.toggle('active', b.dataset.lang === lang); });
  document.getElementById('langMenu').classList.remove('open');
  fetch('/api/config/summarize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language: lang }) })
    .then(function(r) { return r.json(); })
    .then(function() { showToast('Summary language set to ' + (lang === 'zh' ? '中文' : 'English')); })
    .catch(function(e) { showToast('Failed to save: ' + e, 'warn'); });
}
(function() {
  fetch('/api/config/summarize').then(function(r) { return r.json(); }).then(function(cfg) {
    _summaryLang = cfg.language || 'en';
    document.querySelectorAll('.lang-opt').forEach(function(b) { b.classList.toggle('active', b.dataset.lang === _summaryLang); });
  }).catch(function() {});
  document.addEventListener('click', function(e) { if (!e.target.closest('.lang-select-wrap')) document.getElementById('langMenu').classList.remove('open'); });
})();
window.toggleLangMenu = toggleLangMenu;
window.setLang = setLang;

/* ── Navigation ── */
var navFns = {
  home: renderGarden,
  activity: renderDashboard,
  recall: renderRecall,
  explorer: renderExplorer,
  chat: renderChatMain,
  models: renderModels,
  system: renderSystem
};

var navKeys = ['home', 'recall', 'explorer', 'chat', 'system'];

function nav(p) {
  if (page === 'models') modelsCleanup();
  if (page === 'home') gardenCleanup();
  if (page === 'activity') dashboardCleanup();
  if (page === 'explorer') explorerCleanup();
  if (page === 'system') systemCleanup();
  if (page === 'chat' && p !== 'chat') renderChat();
  closeTreeDetail();

  page = p;
  document.querySelectorAll('.nav-btn[data-page]').forEach(function(b) { b.classList.toggle('active', b.dataset.page === p); });
  if (navFns[p]) navFns[p]();
}
window.nav = nav;

document.querySelectorAll('.nav-btn[data-page]').forEach(function(b) {
  b.addEventListener('click', function() { nav(b.dataset.page); });
});


/* ── Keyboard Shortcuts ── */
document.addEventListener('keydown', function(e) {
  var tag = e.target.tagName;
  var inInput = tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable;

  if ((e.metaKey || e.ctrlKey) && e.key === '/') {
    e.preventDefault();
    toggleChatPanel();
    return;
  }

  if (e.key === 'Escape') {
    var chatPanel = document.getElementById('chatPanel');
    if (chatPanel && chatPanel.classList.contains('open')) { toggleChatPanel(); return; }
    closeTreeDetail();
    return;
  }

  if (inInput) return;

  if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '5') {
    e.preventDefault();
    var idx = parseInt(e.key) - 1;
    if (navKeys[idx]) nav(navKeys[idx]);
  }
});

/* ── LLM Budget Monitor ── */
var _llmBudgetWarned = false;
function _checkLLMBudget() {
  api('/api/llm/status').then(function(s) {
    if (s.exhausted && !_llmBudgetWarned) {
      _llmBudgetWarned = true;
      showToast('LLM call limit reached (' + s.count + ' calls). Auto-summarization paused. Increase <code>llm.max_calls</code> in config or set to 0 for unlimited.', 'warn');
    }
  }).catch(function() {});
}
_checkLLMBudget();
setInterval(_checkLLMBudget, 60000);

/* ── Init ── */
renderChat();
nav('home');
