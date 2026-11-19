# REFLOW iMAPS

Planimetrie interattive degli impianti fotovoltaici in O&M di Reflow S.r.l.: mappa dei moduli, rilevazioni dei moduli danneggiati, schede di sostituzione con seriale vecchio e nuovo, estrazioni PDF per i tecnici in campo e per l'Ufficio Pratiche.

Applicativo web (PWA) con accesso tramite account Microsoft aziendale; i dati stanno su SharePoint, non in questo repository.

## Struttura

| File / cartella | Contenuto |
|---|---|
| `prototipo/app_template.html` | **Sorgente della pagina** (HTML, CSS, logica della mappa, schermata di aggiornamento). Si modifica qui. |
| `tools/costruisci_web.py` | Genera `index.html` dal modello (loghi in `assets/`, login, pulsanti "Aggiorna" ed "Esci"). |
| `index.html` | Pagina pubblicata su GitHub Pages. **Generata da `costruisci_web.py`, non va modificata a mano.** |
| `cloud.js` | Login Microsoft (MSAL) e lettura/scrittura dei dati su SharePoint via Graph, con controllo di versione (eTag + `If-Match`) e aggiornamento automatico ogni 15 s. |
| `aggiorna.js` | Pulsante "Aggiorna": salva la scheda aperta, attende i salvataggi in corso, ricarica. |
| `manifest.json`, `assets/` | PWA (nome, icone, loghi). |
| `tools/` (altri script) | Preparazione di un impianto: estrazione della geometria dal layout PDF vettoriale, abbinamento al registro seriali, griglia schematica, generazione dei file `app/mappe/` (`costruisci_app.py`). |
| `docs/SPEC.md` | Specifica tecnica: architettura, ruoli, modello dati. |

## Dati

Nessun dato di impianto, seriale o documento tecnico va inserito in questo repository: il `.gitignore` esclude Excel, PDF e le cartelle degli impianti. I dati vivono nella libreria SharePoint aziendale.

## Manutenzione

Responsabile dell'applicativo: Luca Alberton (PM O&M, Reflow S.r.l.). Modifiche strutturali, correzioni e nuove funzioni passano dal responsabile.
