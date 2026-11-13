# REFLOW iMAPS – specifica tecnica dell'applicativo

Versione 0.2 – 13/11/2026. Proprietario e manutentore: Luca Alberton (PM O&M, Reflow S.r.l.).

## 1. Scopo

REFLOW iMAPS è l'applicativo delle planimetrie interattive degli impianti fotovoltaici in O&M di Reflow: mappa dei moduli per impianto, rilevazioni dei moduli danneggiati, schede di sostituzione con seriali vecchio/nuovo, estrazioni PDF per i tecnici in campo e per l'Ufficio Pratiche.

Nasce come artefatto Claude (prototipo funzionante, 11-12/11/2026, impianto pilota impianto pilota da 11.986 moduli) e diventa un applicativo web aziendale sul modello di REFLOW PLANNER: utilizzabile senza Claude, con accesso tramite account Microsoft aziendale.

## 2. Decisioni di architettura (12/11/2026)

| Tema | Decisione | Motivo / alternativa scartata |
|---|---|---|
| Forma | PWA statica (HTML + JS, nessun server applicativo), come `reflow-planner` | Stesso modello già in uso; installabile su telefono |
| Repository e hosting | `reflowservice/reflow-imaps`, pubblico, GitHub Pages | Scelta di Luca, coerente con il Planner. Gli ID Azure nel codice non sono segreti; nessun dato aziendale nel repository |
| Accesso | MSAL.js (msal-browser), tenant Reflow, app registration dedicata **REFLOW iMAPS** (client ID `8ffb57e1-fbd1-4a67-baaf-b6321ffe4a85`, creata il 13/11/2026), tipo SPA, redirect `https://reflowservice.github.io/reflow-imaps/`, permessi delegati User.Read, Sites.ReadWrite.All, Files.ReadWrite.All (nessun consenso amministratore richiesto) | Login con mail aziendale; registrazione separata dal Planner: permessi e accessi revocabili indipendentemente |
| Dati condivisi | Un file JSON per impianto in `REFLOW iMAPS/dati/<id impianto>.json`, scritto via Graph con controllo di versione (eTag, `If-Match`): se un altro utente ha salvato nel frattempo, l'app ricarica il file, riapplica la sola modifica dell'utente e riprova | Decisione 13/11/2026. Le liste SharePoint (scelta iniziale) richiedono il permesso "Gestisci elenchi" sul sito `ReflowArchive`, che gli utenti non hanno. Scartati i file JSON riscritti senza controllo come nel Planner: con più persone in parallelo l'ultimo salvataggio cancella gli altri |
| Dati di base degli impianti | File JSON in `3_CONTROL ROOM/8 - FILE DI CONTESTO AI/REFLOW iMAPS/app/mappe/` (catalogo + un `dati.json` e un `seriali.json` per impianto), letti via Graph | Sono già prodotti oggi da `costruisci_app.py`; aggiungere un impianto non richiede di ripubblicare l'app |
| Documenti caricati | Libreria documenti, cartella `REFLOW iMAPS/richieste/<id richiesta>/` | Restano nell'archivio aziendale |
| Aggiunta impianti | Fase 1: l'ufficio tecnico carica i documenti dall'app ("In preparazione"); l'elaborazione (geometria, abbinamento registro, controllo dubbi) la fa Luca con gli strumenti Python e pubblica i JSON. Fase 2 (da valutare dopo 2-3 impianti veri): elaborazione automatica | Gli script usano PyMuPDF, che non gira nel browser (verificato su Pyodide 0.27.2). Alternative per la fase 2: Azure Function Python che riusa gli script, oppure estrazione riscritta in JS con pdf.js |
| PDF | jsPDF 2.5.1 + jspdf-autotable 3.8.2 nel browser | Già collaudati nel prototipo |

## 3. Ruoli

| Ruolo | Chi | Può |
|---|---|---|
| Tecnico | tecnici O&M | consultare mappe, compilare schede (seriale letto/nuovo, data sostituzione, note) |
| PM | PM O&M | come tecnico + rilevazioni (creare, modificare, eliminare), selezione multipla, spostamenti, estrazioni |
| Ufficio tecnico | da definire | come PM + "Aggiungi impianto" (caricamento documenti) |
| Amministratore | Luca Alberton | tutto + pubblicazione impianti, ripristino rilevazioni eliminate, modifiche strutturali |

Implementazione: file `REFLOW iMAPS/ruoli.json` (mail → ruolo), modificabile solo dall'amministratore, oppure gruppi Entra ID letti con Graph (`/me/memberOf`). Da decidere (§9). I permessi effettivi di scrittura restano quelli di SharePoint: i ruoli nell'app nascondono le funzioni, i permessi della cartella `REFLOW iMAPS` proteggono i dati. Limite noto: chi ha accesso in scrittura alla cartella può modificare i file anche fuori dall'app.

## 4. Modello dati

Il modello è quello già in uso nel prototipo (database dell'artefatto). Chiave posizione modulo: `T{tavolo}-C{colonna}-{A|B}`.

### 4.1 File `REFLOW iMAPS/dati/<id impianto>.json` (formato in uso dalla beta del 13/11/2026)
```json
{
  "versione": 1,
  "aggiornato": "<ISO>",
  "docs": {
    "moduli/<chiave modulo>": { "stato": "da_sostituire|sostituito|ok", "...": "campi della scheda come nel prototipo" },
    "rilevazioni/<rid>":      { "titolo": "", "data": "", "note": "", "colore": "#hex", "...": "" },
    "fonti/<attività>__<fonte>": { "titolo": "", "data": "", "colore": "", "eliminata": false }
  }
}
```
Le chiavi sono i percorsi del database del prototipo senza il prefisso `impianti/<id>/`: così la pagina del prototipo gira invariata e `cloud.js` traduce le chiamate `db.collection(...)` / `db.doc(...)` in letture e scritture del file. Le richieste di nuovi impianti stanno in `REFLOW iMAPS/richieste/richieste.json` con chiavi `richieste/<rid>`. Le modifiche ravvicinate partono in un solo salvataggio; le viste aperte controllano l'eTag ogni 15 secondi e si aggiornano se il file è cambiato.
Per i moduli da file la chiave è la posizione trascritta sulla carta. Ogni salvataggio è una modifica puntuale (una scheda, una rilevazione, una correzione) applicata all'ultima versione del file con `If-Match`; in caso di conflitto (HTTP 412) si ricarica e si riapplica. Il file resta piccolo (decine di KB anche con centinaia di schede).

### 4.2 Impianti in preparazione: `REFLOW iMAPS/richieste/<id richiesta>/`
`richiesta.json` (cliente, impianto, codice, località, kWp, modulo, note, stato in_preparazione|pubblicato, impianto_id, by, at) e i documenti caricati (layout, SUF, registro Excel così com'è, altri file).

### 4.3 Dati di base degli impianti: `REFLOW iMAPS/app/mappe/`
`catalogo.json` e, per impianto, `dati.json` (geometria, attività, moduli da file) e `seriali.json`, prodotti da `tools/costruisci_app.py`.

## 5. Funzioni da portare dal prototipo (tutte già realizzate e provate nell'artefatto)

1. Schermata di avvio (REFLOW iMAPS in Syncopate, sottotitolo, pulsante Impianti), elenco impianti per cliente con anteprime.
2. Mappa: zoom/pan, filtri da contatori in testata, legenda, elenco e filtri con "Resetta filtri", scheda modulo.
3. Rilevazioni: create in app, sommate a quelle da file, colore scelto, modifica ed eliminazione (da file: reversibile).
4. Selezione multipla (tocco e area) con applicazione di stato/danno/data/note.
5. Spostamento di un modulo per errori di trascrizione (trascinamento o "Sposta"), con ritorno alla posizione della carta.
6. "Ripristina modifiche" (ultimo minuto, dispositivo corrente).
7. Estrai layout (PDF tecnici) ed Estrazione seriali (PDF PM / Ufficio Pratiche).
8. Aggiungi impianto (caricamento documenti in `richieste/`, stato "In preparazione"). Excel caricato così com'è (non serve più la conversione in CSV del prototipo).

## 6. Migrazione dal prototipo

1. Esportazione dei dati dal database dell'artefatto (schede, rilevazioni, fonti, richieste) nei file `dati/<impianto>.json` e `richieste/`: a cura di Luca con Claude.
2. Copia dei documenti caricati nel prototipo (asset dell'artefatto) nelle cartelle `richieste/`.
3. Periodo di prova in parallelo; poi l'artefatto resta solo come prototipo/demo.

## 7. Aggiunta di un impianto (fase 1)

1. Ufficio tecnico: "Aggiungi impianto" → dati + layout as built (PDF vettoriale), SUF, registro seriali, altri documenti → `REFLOW iMAPS/richieste/<id>/` (richiesta.json + file).
2. Luca (con Claude, skill `reflow-imaps`): estrazione geometria, abbinamento registro, verifica dei dubbi, generazione `dati.json`/`seriali.json`, aggiornamento `catalogo.json` nella cartella `app/mappe/`, stato richiesta → pubblicato.
3. L'impianto compare nell'app senza ripubblicarla.

## 8. Fuori perimetro (per ora)

Inverter (serve abbinamento stringhe-inverter), modalità offline completa, elaborazione automatica dei layout (fase 2).

## 9. Decisioni aperte

- Ruoli: file `ruoli.json` o gruppi Entra ID.
- Chi compone l'ufficio tecnico e chi tra i tecnici usa l'app dal telefono.
- Redirect URI per le prove in locale (da aggiungere alla registrazione quando serve).

## 10. Registro decisioni

- 12/11/2026: applicativo sul modello del Planner; repository pubblico, GitHub Pages; aggiunta impianti fase 1 con elaborazione di Luca.
- 13/11/2026: app registration dedicata REFLOW iMAPS; dati in file JSON per impianto con eTag invece delle liste SharePoint (permesso "Gestisci elenchi" non disponibile).
