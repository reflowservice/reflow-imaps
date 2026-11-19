/* REFLOW iMAPS — pulsante "Aggiorna" in testata e schermata di aggiornamento.
   Modello: REFLOW STATUS (bReload, segnale in sessionStorage, chiusura a fine battito), con una differenza:
   iMAPS salva le schede con una coda di scritture (cloud.js), quindi prima di ricaricare si salva la scheda aperta
   e si aspetta che la coda sia vuota; altrimenti le modifiche in sospeso andrebbero perse.
   Dopo il ricaricamento la schermata (#gate, già visibile grazie allo script in testa al body) resta per almeno
   3 battiti dei moduli che si accendono (3 secondi) e si chiude da sola alla fine di un battito, a dati caricati. */
(function () {
  'use strict';
  const KEY = 'imaps_refresh';
  const BEAT_MS = 1000;   // deve coincidere con --beat nel CSS di #gate/.gate-pulse (1s; senza --beat il CSS usa 1s)
  const BEATS = 3;
  const $ = id => document.getElementById(id);
  let busy = false;

  function show(text) {
    const g = $('gate'); if (!g) return;
    $('gate-msg').textContent = text;
    g.classList.remove('out'); g.hidden = false;
  }
  function hide() {
    const g = $('gate'); if (!g || g.hidden) return;
    g.classList.add('out');
    setTimeout(() => { g.hidden = true; }, 500);
  }
  // chiude alla fine del battito in cui si superano i 3 battiti dall'apertura della schermata
  function ready() {
    const g = $('gate'); if (!g || g.hidden || !window.IMAPS_REFRESH) return;
    $('gate-msg').textContent = 'Dati aggiornati';
    const path = g.querySelector('.gate-pulse rect');
    const an = path && path.getAnimations ? path.getAnimations()[0] : null;
    const t = an && an.currentTime != null ? an.currentTime : performance.now();
    const fine = Math.ceil(Math.max(t, BEATS * BEAT_MS - 1) / BEAT_MS) * BEAT_MS;
    setTimeout(hide, fine - t);
  }
  const avviso = t => { if (typeof alertBox === 'function') alertBox(t); else console.warn(t); };

  async function run() {
    if (busy) return; busy = true;
    const btn = $('b-reload'); if (btn) btn.disabled = true;
    const annulla = t => { hide(); busy = false; if (btn) btn.disabled = false; avviso(t); };
    show('Salvataggio delle modifiche…');
    try {
      // 1) la scheda aperta: salva subito (nessuna attesa dei 1,2 s); false = non salvabile (seriale non valido, ecc.)
      const ok = typeof flushAuto === 'function' ? await flushAuto() : true;
      if (ok === false) return annulla('Aggiornamento annullato: la scheda aperta non è stata salvata, controlla il messaggio nella scheda.');
      // 2) tutte le altre scritture in coda (rilevazioni, spostamenti, selezione multipla…)
      await IMAPS.idle(25000);
    } catch (e) {
      return annulla(e && e.code === 'timeout'
        ? 'Aggiornamento annullato: il salvataggio è ancora in corso, riprova tra qualche istante.'
        : 'Aggiornamento annullato: un salvataggio non è riuscito, riprova.');
    }
    try { sessionStorage.setItem(KEY, '1'); } catch (e) {}
    location.reload();
  }

  window.IMAPSREFRESH = { run, ready };
})();
