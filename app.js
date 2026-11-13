/* REFLOW iMAPS – applicativo (scheletro v0.1, 13/11/2026)
   Login Microsoft (MSAL, redirect) e lettura dei dati da SharePoint via Microsoft Graph.
   Specifica: docs/SPEC.md */
'use strict';

// ---------- configurazione ----------
const CLIENT_ID = 'ef16e670-e362-4954-a912-b628afde91a0';          // registrazione condivisa "Reflow Planner" (consenso admin già concesso)
const TENANT_ID = 'd53a79c7-2449-4eca-be76-4bd4b7482c96';          // tenant REFLOW SRL
const SITE_HOST = 'reflowservice.sharepoint.com';
const SITE_PATH = '/sites/ReflowArchive';
const BASE = '3_CONTROL ROOM/8 - FILE DI CONTESTO AI/REFLOW iMAPS';
const SCOPES = ['User.Read', 'Sites.ReadWrite.All', 'Files.ReadWrite.All'];
const PAGES_URL = 'https://reflowservice.github.io/reflow-imaps/';
const VERSIONE = 'v0.1';

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// ---------- login ----------
const redirectUri = location.hostname.endsWith('github.io') ? PAGES_URL : location.origin + location.pathname;
const msalApp = new msal.PublicClientApplication({
  auth: { clientId: CLIENT_ID, authority: `https://login.microsoftonline.com/${TENANT_ID}`, redirectUri },
  cache: { cacheLocation: 'localStorage' }
});
let account = null;

async function initAuth() {
  const r = await msalApp.handleRedirectPromise();
  if (r && r.account) msalApp.setActiveAccount(r.account);
  account = msalApp.getActiveAccount() || msalApp.getAllAccounts()[0] || null;
  if (account) msalApp.setActiveAccount(account);
  return account;
}
function login() { msalApp.loginRedirect({ scopes: SCOPES, prompt: 'select_account' }); }
function logout() { msalApp.logoutRedirect({ account, postLogoutRedirectUri: redirectUri }); }

async function token() {
  try {
    return (await msalApp.acquireTokenSilent({ scopes: SCOPES, account })).accessToken;
  } catch (e) {
    if (e instanceof msal.InteractionRequiredAuthError) { msalApp.acquireTokenRedirect({ scopes: SCOPES, account }); }
    throw e;
  }
}

// ---------- Microsoft Graph ----------
async function graph(path, opt = {}) {
  const res = await fetch('https://graph.microsoft.com/v1.0' + path, {
    ...opt, headers: { Authorization: 'Bearer ' + await token(), ...(opt.headers || {}) }
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Graph ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res;
}
let siteId = null;
async function site() {
  if (!siteId) siteId = (await (await graph(`/sites/${SITE_HOST}:${SITE_PATH}?$select=id`)).json()).id;
  return siteId;
}
// legge un JSON della cartella REFLOW iMAPS; null se il file non esiste
async function leggiJson(rel) {
  const r = await graph(`/sites/${await site()}/drive/root:/${encodeURI(BASE + '/' + rel)}:/content`);
  return r ? r.json() : null;
}

// ---------- stato ----------
let CAT = [];            // catalogo impianti (app/mappe/catalogo.json)
const DATI = {};         // dati di base per impianto (app/mappe/<id>/dati.json)
const STAT = {};         // avanzamento per impianto (dati/<id>.json)

// ---------- interfaccia ----------
function toast(t, ms = 3500) { const el = $('toast'); el.textContent = t; el.hidden = false; clearTimeout(toast._t); toast._t = setTimeout(() => el.hidden = true, ms); }

function showSplash() {
  $('splash').hidden = false; $('home').hidden = true; document.querySelector('header').hidden = true;
  document.title = 'REFLOW iMAPS';
  const n = CAT.length, nc = new Set(CAT.map(c => c.cliente)).size;
  $('sp-count').textContent = n ? `${n} ${n === 1 ? 'impianto' : 'impianti'} di ${nc} ${nc === 1 ? 'cliente' : 'clienti'}` : '';
  $('b-enter').firstChild.textContent = account ? 'Impianti' : 'Accedi';
  if (CAT[0] && DATI[CAT[0].id] && !$('sp-art').innerHTML) $('sp-art').innerHTML = lineArt(DATI[CAT[0].id]);
}
function showHome() {
  $('splash').hidden = true; $('home').hidden = false; document.querySelector('header').hidden = false;
  document.title = 'Impianti · REFLOW iMAPS';
  drawHome();
}
function route() {
  const id = decodeURIComponent(location.hash.slice(1));
  if (!account) return showSplash();
  if (id === 'impianti') return showHome();
  if (id && CAT.find(c => c.id === id)) { showHome(); toast('La mappa interattiva arriva nel prossimo rilascio dell\'app. Per ora usa il prototipo.'); history.replaceState(null, '', '#impianti'); return; }
  showSplash();
}

function bounds(d) {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  d.vele.forEach(v => { x0 = Math.min(x0, v[4]); x1 = Math.max(x1, v[5]); y0 = Math.min(y0, v[6]); y1 = Math.max(y1, v[7]); });
  return { x0, y0, x1, y1 };
}
function modXY(d, vt, m) {
  const v = vt[m.tav]; if (!v) return null;
  const nd = Math.round((v[5] - v[4]) / 6.5) + 1, st = nd > 1 ? (v[5] - v[4]) / (nd - 1) : 6.5;
  return [v[4] + (m.col - 1) * st, m.pos === 'A' ? v[6] : v[7]];
}
function lineArt(d) {
  const { x0, y0, x1, y1 } = bounds(d), p = 30, X = x => (x - x0 + p).toFixed(1), Y = y => (y - y0 + p).toFixed(1), vt = {};
  d.vele.forEach(v => vt[v[0]] = v);
  let s = `<svg viewBox="0 0 ${(x1 - x0 + 2 * p).toFixed(0)} ${(y1 - y0 + 2 * p).toFixed(0)}" preserveAspectRatio="xMidYMid meet">`;
  s += d.vele.map(v => `<rect x="${X(v[4] - 4)}" y="${Y(v[6] - 7)}" width="${(v[5] - v[4] + 8).toFixed(1)}" height="${(v[7] - v[6] + 14).toFixed(1)}" fill="rgba(255,255,255,.035)" stroke="rgba(206,198,245,.32)" stroke-width="1.2" vector-effect="non-scaling-stroke"/>`).join('');
  s += (d.attivita[0]?.mods || []).map(m => { const q = modXY(d, vt, m); return q ? `<circle cx="${X(q[0])}" cy="${Y(q[1])}" r="9" fill="#17b3e8" opacity=".85"/>` : ''; }).join('');
  return s + '</svg>';
}
function miniMap(d) {
  const { x0, y0, x1, y1 } = bounds(d), p = 40, X = x => (x - x0 + p).toFixed(1), Y = y => (y - y0 + p).toFixed(1), vt = {};
  d.vele.forEach(v => vt[v[0]] = v);
  const a = d.attivita[0] || { mods: [], fonti: {} };
  let s = `<svg viewBox="0 0 ${(x1 - x0 + 2 * p).toFixed(0)} ${(y1 - y0 + 2 * p).toFixed(0)}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">`;
  s += d.vele.map(v => `<rect x="${X(v[4] - 4)}" y="${Y(v[6] - 7)}" width="${(v[5] - v[4] + 8).toFixed(1)}" height="${(v[7] - v[6] + 14).toFixed(1)}" fill="#eceaf4" stroke="#c9c5da" stroke-width="1"/>`).join('');
  s += a.mods.map(m => { const q = modXY(d, vt, m); const c = (a.fonti[m.src] || {}).c || '#17b3e8';
    return q ? `<circle cx="${X(q[0])}" cy="${Y(q[1])}" r="14" fill="${c.startsWith('var(') ? '#17b3e8' : c}" stroke="#fff" stroke-width="3"/>` : ''; }).join('');
  return s + '</svg>';
}
function drawHome() {
  const q = $('hq').value.trim().toLowerCase();
  const list = CAT.filter(c => !q || (c.cliente + ' ' + c.impianto + ' ' + (c.localita || '')).toLowerCase().includes(q));
  const el = $('clienti');
  if (!CAT.length) { el.innerHTML = '<p class="empty">Nessun impianto pubblicato.</p>'; return; }
  if (!list.length) { el.innerHTML = '<p class="empty">Nessun cliente o impianto corrisponde alla ricerca.</p>'; return; }
  const by = {}; list.forEach(c => (by[c.cliente] = by[c.cliente] || []).push(c));
  el.innerHTML = Object.keys(by).sort((a, b) => a.localeCompare(b, 'it')).map(cl => {
    const imps = by[cl].sort((a, b) => a.impianto.localeCompare(b.impianto, 'it'));
    return `<section class="cliente"><div class="cliente-h"><h3>${esc(cl)}</h3><span>${imps.length} ${imps.length === 1 ? 'impianto' : 'impianti'}</span></div>
      <div class="cards">${imps.map(c => {
        const tot = c.moduli_in_lista || 0, st = STAT[c.id], done = st ? st.done : null, pct = tot && done !== null ? Math.round(done / tot * 100) : 0;
        return `<button class="card" data-id="${esc(c.id)}"><span class="thumb">${DATI[c.id] ? miniMap(DATI[c.id]) : ''}</span><span class="card-b">
          <span class="nm">${esc(c.impianto)}</span>
          <span class="loc">${esc(c.localita || '')}${c.potenza ? ', ' + esc(c.potenza) : ''}</span>
          <span class="cp">${esc(c.attivita || '')}</span>
          <span class="bar" aria-hidden="true"><i style="width:${pct}%"></i></span>
          <span class="stat"><span><b>${done === null ? '–' : done}</b> sostituiti su ${tot}</span><span>dati al ${esc(c.data_dati || '')}</span></span></span></button>`;
      }).join('')}</div></section>`;
  }).join('');
  el.querySelectorAll('.card').forEach(b => b.onclick = () => { location.hash = b.dataset.id; });
}

// ---------- caricamento dati ----------
async function caricaTutto() {
  CAT = (await leggiJson('app/mappe/catalogo.json')) || [];
  await Promise.all(CAT.map(async c => {
    try { DATI[c.id] = await leggiJson(`app/mappe/${c.id}/dati.json`); } catch (e) { console.warn('dati', c.id, e); }
    try {
      const f = await leggiJson(`dati/${c.id}.json`);
      STAT[c.id] = { done: f && f.schede ? Object.values(f.schede).filter(s => s && s.stato === 'sostituito').length : 0 };
    } catch (e) { console.warn('stato', c.id, e); }
  }));
}

// ---------- avvio ----------
$('b-enter').onclick = () => { if (!account) login(); else location.hash = 'impianti'; };
$('b-start').onclick = () => { location.hash = ''; };
$('b-logout').onclick = logout;
$('hq').addEventListener('input', drawHome);
window.addEventListener('hashchange', route);

(async () => {
  try {
    await initAuth();
  } catch (e) { console.error(e); $('sp-msg').textContent = 'Accesso non riuscito: ' + e.message; }
  if (!account) { showSplash(); return; }
  $('who-name').textContent = account.name || account.username;
  showSplash(); $('sp-msg').textContent = 'Carico gli impianti…';
  try { await caricaTutto(); $('sp-msg').textContent = ''; }
  catch (e) { console.error(e); $('sp-msg').textContent = 'Non riesco a leggere i dati su SharePoint: ' + e.message; }
  route();
})();
