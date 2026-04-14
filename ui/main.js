// ============================================================
// ADS Manager – main.js
// ============================================================

// ── NAVIGATION ──────────────────────────────────────────────
const PAGES = { login:'login.html', dashboard:'dashboard.html', campaigns:'campaigns.html', customers:'customers.html', reports:'reports.html' };
function goTo(p){ window.location.href = PAGES[p] || p; }

// ── MODAL ────────────────────────────────────────────────────
function openModal(id){ document.getElementById(id).classList.add('show'); }
function closeModal(id){ document.getElementById(id).classList.remove('show'); }
document.addEventListener('click', e => { if(e.target.classList.contains('overlay')) e.target.classList.remove('show'); });

// ── TOAST ────────────────────────────────────────────────────
function toast(msg, type='ok'){
  const a = document.getElementById('toast-area');
  if(!a) return;
  const t = document.createElement('div');
  t.className = 'toast'+(type==='err'?' err':'');
  t.innerHTML = `<span>${type==='err'?'❌':'✅'}</span>${msg}`;
  a.appendChild(t);
  setTimeout(()=>t.remove(), 3400);
}

// ── SEARCH ───────────────────────────────────────────────────
function filterTable(inputId, tableId){
  const q = document.getElementById(inputId).value.toLowerCase();
  document.querySelectorAll(`#${tableId} tbody tr`).forEach(r=>{
    r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

// ── CONFIRM DELETE ─────────────────────────────────────────
function confirmDel(name, btn){
  if(confirm(`Xóa "${name}"?\nThao tác này không thể hoàn tác!`)){
    const row = btn.closest('tr');
    if(row){ row.style.opacity='0'; row.style.transition='.3s'; setTimeout(()=>row.remove(),300); }
    toast(`Đã xóa "${name}"`);
  }
}

// ── PROGRESS BAR COLOR ───────────────────────────────────────
document.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('.prog-fill[data-pct]').forEach(el=>{
    const p = +el.dataset.pct;
    el.style.width = p+'%';
    el.style.background = p>=90?'#EF4444': p>=70?'#F59E0B':'#10B981';
  });
  document.querySelectorAll('.dist-fill[data-w]').forEach(el=>{
    setTimeout(()=>{ el.style.width = el.dataset.w; }, 200);
  });
  // topbar date
  const d = document.getElementById('topbar-date');
  if(d) d.textContent = new Date().toLocaleString('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit',year:'numeric'});
});

// ── SIDEBAR ACTIVE STATE ─────────────────────────────────────
(function(){
  const cur = location.pathname.split('/').pop();
  document.querySelectorAll('.sb-item[data-page]').forEach(el=>{
    if(el.dataset.page === cur) el.classList.add('active');
  });
})();
