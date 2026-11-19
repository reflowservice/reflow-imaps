/* REFLOW iMAPS — strato cloud.
   Sostituisce le capacità dell'artefatto Claude (window.claude: db, user, downloads, assets)
   con login Microsoft (MSAL) e file JSON su SharePoint via Microsoft Graph.

   Dati condivisi: un file JSON per impianto in <BASE>/dati/<id impianto>.json
     { "versione": 1, "docs": { "moduli/<chiave>": {...}, "rilevazioni/<rid>": {...}, "fonti/<id>": {...} } }
   Richieste di nuovi impianti: <BASE>/richieste/richieste.json, stessa forma.
   Scritture con controllo di versione (eTag + If-Match): in caso di conflitto il file
   si ricarica e si riapplicano solo le modifiche in sospeso. */
(function () {
  'use strict';
  const CLIENT_ID = 'ef16e670-e362-4954-a912-b628afde91a0';   // registrazione condivisa "Reflow Planner" (consenso admin già concesso)
  const TENANT_ID = 'd53a79c7-2449-4eca-be76-4bd4b7482c96';
  const SITE_HOST = 'reflowservice.sharepoint.com';
  const SITE_PATH = '/sites/ReflowArchive';
  const BASE = '3_CONTROL ROOM/8 - FILE DI CONTESTO AI/REFLOW iMAPS';
  const SCOPES = ['User.Read', 'Sites.ReadWrite.All', 'Files.ReadWrite.All'];
  const PAGES_URL = 'https://reflowservice.github.io/reflow-imaps/';
  const POLL_MS = 15000;

  const redirectUri = location.hostname.endsWith('github.io') ? PAGES_URL : location.origin + location.pathname;
  const pca = new msal.PublicClientApplication({
    auth: { clientId: CLIENT_ID, authority: `https://login.microsoftonline.com/${TENANT_ID}`, redirectUri },
    cache: { cacheLocation: 'localStorage' }
  });

  const IM = window.IMAPS = { account: null, ready: null };

  IM.login = () => pca.loginRedirect({ scopes: SCOPES, prompt: 'select_account' });
  IM.logout = () => pca.logoutRedirect({ account: IM.account, postLogoutRedirectUri: redirectUri });

  async function token() {
    try {
      return (await pca.acquireTokenSilent({ scopes: SCOPES, account: IM.account })).accessToken;
    } catch (e) {
      if (e instanceof msal.InteractionRequiredAuthError) { await pca.acquireTokenRedirect({ scopes: SCOPES, account: IM.account }); }
      throw e;
    }
  }
  async function graph(path, opt = {}) {
    const t = await token();
    const headers = Object.assign({ Authorization: 'Bearer ' + t }, opt.headers || {});
    return fetch('https://graph.microsoft.com/v1.0' + path, Object.assign({}, opt, { headers }));
  }
  let siteId = null;
  async function site() {
    if (siteId) return siteId;
    const r = await graph(`/sites/${SITE_HOST}:${SITE_PATH}?$select=id`);
    if (!r.ok) throw new Error('Sito SharePoint non raggiungibile (' + r.status + ')');
    return siteId = (await r.json()).id;
  }
  const item = rel => `/sites/${siteId}/drive/root:/${encodeURI(BASE + '/' + rel).replace(/#/g, '%23')}:`;

  async function getFile(rel, asText) {
    await site();
    const r = await graph(item(rel) + '/content', { cache: 'no-store' });
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`Lettura di ${rel} non riuscita (${r.status})`);
    return { body: asText ? await r.text() : await r.json(), etag: r.headers.get('ETag') };
  }
  async function etagOf(rel) {
    await site();
    const r = await graph(item(rel) + '?$select=eTag', { cache: 'no-store' });
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`Lettura di ${rel} non riuscita (${r.status})`);
    return (await r.json()).eTag;
  }
  async function putFile(rel, obj, etag) {
    await site();
    const h = { 'Content-Type': 'application/json' };
    if (etag) h['If-Match'] = etag; else h['If-None-Match'] = '*';
    const r = await graph(item(rel) + '/content', { method: 'PUT', headers: h, body: JSON.stringify(obj) });
    if (r.status === 412 || r.status === 409) { const e = new Error('conflict'); e.code = 'conflict'; throw e; }
    if (!r.ok) { const e = new Error(`Salvataggio non riuscito (${r.status})`); e.code = 'save_failed'; throw e; }
    return (await r.json()).eTag;
  }

  // ---------- archivio a documenti, un file per impianto ----------
  const FILES = {};      // rel -> { data, etag, loaded }
  const LIS = {};        // rel -> Set(callback)
  function where(path) {
    const p = path.split('/');
    if (p[0] === 'impianti') return { rel: `dati/${p[1]}.json`, key: p.slice(2).join('/') };
    if (p[0] === 'richieste') return { rel: 'richieste/richieste.json', key: p.join('/') };
    return { rel: 'dati/_altro.json', key: path };
  }
  async function load(rel, force) {
    const f = FILES[rel];
    if (f && f.loaded && !force) return f;
    const got = await getFile(rel);
    const data = got && got.body && got.body.docs ? got.body : { versione: 1, docs: {} };
    return FILES[rel] = { data, etag: got ? got.etag : null, loaded: true };
  }
  function notify(rel) { (LIS[rel] || []).forEach(cb => { try { cb(); } catch (e) { console.error(e); } }); }

  // coda di scrittura per file: le modifiche ravvicinate partono insieme in un solo salvataggio
  const Q = {};
  let FAILS = 0;   // salvataggi falliti (per IM.idle)
  function mutate(rel, fn) {
    if (!IM.canEdit) { const e = new Error('Accesso in sola lettura'); e.code = 'invalid_argument'; return Promise.reject(e); }
    return new Promise((res, rej) => {
      const q = Q[rel] = Q[rel] || { fns: [], timer: null, busy: false };
      q.fns.push({ fn, res, rej });
      if (!q.timer && !q.busy) q.timer = setTimeout(() => flush(rel), 250);
    });
  }
  async function flush(rel) {
    const q = Q[rel]; q.timer = null; if (!q.fns.length) return;
    q.busy = true; const batch = q.fns.splice(0);
    try {
      for (let tent = 0; ; tent++) {
        const f = await load(rel, tent > 0);
        const next = JSON.parse(JSON.stringify(f.data));
        batch.forEach(b => b.fn(next.docs));
        next.versione = 1; next.aggiornato = new Date().toISOString();
        try { f.etag = await putFile(rel, next, f.etag); f.data = next; break; }
        catch (e) { if (e.code !== 'conflict' || tent >= 4) throw e; }
      }
      batch.forEach(b => b.res()); notify(rel);
    } catch (e) { FAILS++; batch.forEach(b => b.rej(e)); }
    finally { q.busy = false; if (q.fns.length) q.timer = setTimeout(() => flush(rel), 50); }
  }
  // attende che tutte le code di scrittura siano vuote (usato da "Aggiorna" prima di ricaricare la pagina);
  // errore con code 'timeout' se non si svuotano in tempo, 'save_failed' se un salvataggio è fallito nell'attesa
  IM.idle = async (maxMs = 20000) => {
    const busy = () => Object.values(Q).some(q => q.busy || q.timer || q.fns.length);
    const f0 = FAILS, t0 = Date.now();
    while (busy()) {
      if (Date.now() - t0 > maxMs) { const e = new Error('timeout'); e.code = 'timeout'; throw e; }
      await new Promise(r => setTimeout(r, 100));
    }
    if (FAILS > f0) { const e = new Error('save_failed'); e.code = 'save_failed'; throw e; }
    return true;
  };
  const clone = o => JSON.parse(JSON.stringify(o));
  function snapshot(rel, prefix) {
    const docs = FILES[rel] ? FILES[rel].data.docs : {};
    return { docs: Object.keys(docs).filter(k => k.startsWith(prefix) && !k.slice(prefix.length).includes('/'))
      .map(k => ({ id: k.slice(prefix.length), exists: true, data: () => clone(docs[k]) })) };
  }
  // controllo periodico: se il file è cambiato su SharePoint lo si ricarica e si avvisano le viste aperte
  setInterval(async () => {
    for (const rel of Object.keys(LIS)) {
      if (!LIS[rel].size || (Q[rel] && (Q[rel].busy || Q[rel].fns.length))) continue;
      try { const et = await etagOf(rel); const f = FILES[rel];
        if (f && et !== f.etag) { await load(rel, true); notify(rel); } } catch (e) { /* rete assente: si riprova al giro dopo */ }
    }
  }, POLL_MS);

  const db = {
    collection(path) {
      const { rel, key } = where(path + '/x'); const prefix = key.slice(0, -1);
      return {
        async get() { await load(rel, true); return snapshot(rel, prefix); },
        onSnapshot(cb, err) {
          const fire = () => cb(snapshot(rel, prefix));
          (LIS[rel] = LIS[rel] || new Set()).add(fire);
          load(rel, true).then(fire, e => err && err(e));
          return () => LIS[rel].delete(fire);
        }
      };
    },
    doc(path) {
      const { rel, key } = where(path);
      return {
        async get() { const f = await load(rel); const v = f.data.docs[key]; return { id: key.split('/').pop(), exists: v !== undefined, data: () => clone(v) }; },
        set(body) { const b = clone(body); return mutate(rel, docs => { docs[key] = b; }); },
        delete() { return mutate(rel, docs => { delete docs[key]; }); }
      };
    }
  };
  const user = {
    id: async () => IM.account ? (IM.account.name || IM.account.username) : null,
    profiles: async ids => Object.fromEntries((ids || []).map(i => [i, { name: i }])),
    can: async () => !!IM.canEdit
  };
  window.claude = {
    async use(name) {
      const ok = await IM.ready;
      if (!ok) return null;
      if (name === 'db') return db;
      if (name === 'user') return user;
      return null;   // downloads: la pagina salva i PDF da sé; assets: aggiunta impianti non ancora disponibile
    }
  };

  // ---------- ruoli ----------
  // ruoli.json nella cartella di iMAPS (non nel codice: il repository è pubblico):
  //   { dominio, amministratori: [...], editori: [...] }   voce = email oppure nome (tutte le sue parole nel nome dell'account)
  // amministratori ed editori modificano tutto; chiunque altro del dominio vede in sola lettura.
  // Senza ruoli.json leggibile: sola lettura per tutti.
  const norm = t => String(t || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9@.]+/g, ' ').trim();
  const words = t => norm(t).replace(/[@.]/g, ' ').split(' ').filter(w => w.length > 1);
  function matches(v, me) {
    v = norm(v); if (!v) return false;
    if (v.includes('@')) return v === me.email;
    const w = words(v); return w.length > 0 && w.every(x => me.tok.has(x));
  }
  async function resolveRole() {
    let me = {};
    try { const r = await graph('/me?$select=displayName,mail,userPrincipalName'); if (r.ok) me = await r.json(); } catch (e) { /* si usa l'account MSAL */ }
    const email = String(me.mail || me.userPrincipalName || IM.account.username || '').toLowerCase();
    const who = { email, tok: new Set(words(me.displayName || IM.account.name || '')) };
    let R = null; try { const f = await getFile('ruoli.json'); R = f && f.body; } catch (e) { R = null; }
    const has = k => !!(R && Array.isArray(R[k]) && R[k].some(v => matches(v, who)));
    if (R && R.dominio && !email.endsWith('@' + String(R.dominio).toLowerCase())) throw new Error('Accesso riservato agli account aziendali.');
    IM.role = has('amministratori') ? 'amministratore' : has('editori') ? 'editore' : 'lettura';
    IM.canEdit = IM.role !== 'lettura';
  }

  // ---------- avvio: login, poi catalogo e dati base degli impianti nella pagina ----------
  function inject(attr, id, text) {
    const s = document.createElement('script'); s.type = 'application/json'; s.setAttribute(attr, id);
    s.textContent = text; document.body.appendChild(s);
  }
  IM.ready = (async () => {
    await pca.initialize();
    const r = await pca.handleRedirectPromise();
    IM.account = (r && r.account) || pca.getAllAccounts()[0] || null;
    if (!IM.account) return false;
    await site(); await resolveRole();
    const cat = await getFile('app/mappe/catalogo.json', true);
    if (!cat) throw new Error('Catalogo degli impianti non trovato su SharePoint.');
    const list = JSON.parse(cat.body);
    inject('id', 'catalogo', cat.body);
    await Promise.all(list.map(async c => {
      const [d, s] = await Promise.all([getFile(`app/mappe/${c.id}/dati.json`, true), getFile(`app/mappe/${c.id}/seriali.json`, true)]);
      if (d) inject('data-dati', c.id, d.body);
      if (s) inject('data-seriali', c.id, s.body);
    }));
    return true;
  })();
})();
