export function api(p){return fetch(p).then(function(r){return r.json()}).catch(function(){return []})}
export function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
export function blobUrl(b){return b?'/blobs/'+b.replace(/^.*blobs\//,''):''}
export function fmtTs(ts){var d=new Date(ts*1000);return d.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'})+'.'+String(d.getMilliseconds()).padStart(3,'0')}
export function fmtHM(ts){return new Date(ts*1000).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})}
export function fmtDate(d){return d.toLocaleDateString('en-US',{weekday:'short',month:'long',day:'numeric',year:'numeric'})}
export function fmtDuration(s){if(s<1)return'<1s';if(s<60)return Math.round(s)+'s';if(s<3600)return Math.floor(s/60)+'m '+Math.round(s%60)+'s';return Math.floor(s/3600)+'h '+Math.round((s%3600)/60)+'m'}
export function fmtCount(n){return n>=1000?(n/1000).toFixed(1)+'k':String(n)}
export function openLightbox(src){document.getElementById('lbImg').src=src;document.getElementById('lightbox').classList.add('open')}
window.openLightbox = openLightbox;

export var KIND_COL={window:'#FF9500',keyboard:'#FFCC00',mouse:'#FF2D55',clipboard:'#AF52DE',idle:'#8E8E93',notification:'#FF3B30',sysaudio:'#5AC8FA',screen:'#FF3B30',audio:'#5856D6',video:'#30D158'};
export var TRACKS=['window','keyboard','mouse','clipboard','idle'];

var _toastContainer=null;
export function showToast(msg,type){
  type=type||'info';
  if(!_toastContainer){_toastContainer=document.createElement('div');_toastContainer.className='toast-container';document.body.appendChild(_toastContainer)}
  var t=document.createElement('div');t.className='toast';
  t.innerHTML='<span style="font-size:15px;flex-shrink:0">'+(type==='warn'?'\u26A0':'\u2139')+'</span><span class="toast-body">'+msg+'</span><button class="toast-close" onclick="this.parentElement.remove()">&times;</button>';
  _toastContainer.appendChild(t);setTimeout(function(){if(t.parentElement)t.remove()},12000);
}
