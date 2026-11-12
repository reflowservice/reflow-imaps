# REFLOW iMAPS – specifica tecnica dell'applicativo

Versione 0.1 – 12/11/2026. Proprietario e manutentore: Luca Alberton (PM O&M, Reflow S.r.l.).

## 1. Scopo

REFLOW iMAPS è l'applicativo delle planimetrie interattive degli impianti fotovoltaici in O&M di Reflow: mappa dei moduli per impianto, rilevazioni dei moduli danneggiati, schede di sostituzione con seriali vecchio/nuovo, estrazioni PDF per i tecnici in campo e per l'Ufficio Pratiche.

Nasce come artefatto Claude (prototipo funzionante, 11-12/11/2026, impianto pilota impianto pilota da 11.986 moduli) e diventa un applicativo web aziendale sul modello di REFLOW PLANNER: utilizzabile senza Claude, con accesso tramite account Microsoft aziendale.

## 2. Decisioni di architettura (12/11/2026)

| Tema | Decisione | Motivo / alternativa scartata |
|---|---|---|
| Forma | PWA statica (HTML + JS, nessun server applicativo), come `reflow-planner` | Stesso modello già in uso; installabile su telefono |
| Repository e hosting | `reflowservice/reflow-imaps`, pubblico, GitHub Pages | Scelta di Luca, coerente con il Planner. Gli ID Azure nel codice non sono segreti; nessun dato aziendale nel repository |
| Accesso | MSAL.js (msal-browser), tenant Reflow, stessa app registration del Planner o una dedicata (da decidere, §9) | Login con mail aziendale, nessuna password gestita dall'app |
| Dati condivisi | Liste SharePoint sul sito `ReflowArchive`, via Microsoft Graph | Una riga per scheda: salvataggi indipendenti e controllo delle modifiche concorrenti (eTag). Scartati i file JSON interi del Planner: con più persone che compilano in parallelo l'ultimo salvataggio cancella gli altri |
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

Implementazione: gruppi Microsoft 365 / Entra ID letti con Graph (`/me/memberOf`) oppure lista SharePoint `iMAPS_Ruoli` (mail → ruolo). Da decidere (§9). I permessi effettivi di scrittura restano quelli di SharePoint: i ruoli nell'app nascondono le funzioni, i permessi delle liste le proteggono.

## 4. Modello dati

Il modello è quello già in uso nel prototipo (database dell'artefatto), trasposto in liste SharePoint. Chiave posizione modulo: `T{tavolo}-C{colonna}-{A|B}`.

### 4.1 Lista `iMAPS_Schede` (una riga per modulo segnalato o compilato)
| Colonna | Tipo | Note |
|---|---|---|
| Title | testo | `<impianto>|<attività>|<chiave>` (univoca) |
| Impianto | testo | id impianto, es. `cliente-codice-localita` |
| Attivita | testo | id attività, es. `sostituzione-moduli-2026` |
| Chiave | testo | posizione; per i moduli da file = posizione trascritta sulla carta |
| Stato | scelta | da_sostituire, sostituito, ok |
| SerialeLetto, SerialeNuovo | testo | 14-18 cifre |
| MarcaNuova, ModelloNuovo | testo | solo moduli sostituiti |
| PotenzaNuovaW | numero | |
| DataSostituzione | data | |
| Note, Danno | testo multiriga / testo | |
| Rilevazione | testo | id rilevazione creata in app (vuoto per moduli da file) |
| Numero | numero | progressivo dopo i moduli da file |
| SpostatoA, SpostatoDa | testo | correzioni di trascrizione |
| Created/Modified/Author/Editor | sistema | sostituiscono `by`/`at` |

### 4.2 Lista `iMAPS_Rilevazioni`
Impianto, Attivita, Titolo, Data, Note, Colore (hex).

### 4.3 Lista `iMAPS_Fonti` (correzioni alle rilevazioni da file)
Impianto, Attivita, Fonte (codice, es. R, MP), Titolo, Data, Note, Colore, Eliminata (sì/no).

### 4.4 Lista `iMAPS_Richieste` (impianti in preparazione)
Cliente, Impianto, Codice, Localita, PotenzaKWp, ModuloMarca, ModuloModello, ModuloPotenzaW, Note, Cartella (percorso dei documenti), Stato (in_preparazione, pubblicato), ImpiantoId.

## 5. Funzioni da portare dal prototipo (tutte già realizzate e provate nell'artefatto)

1. Schermata di avvio (REFLOW iMAPS in Syncopate, sottotitolo, pulsante Impianti), elenco impianti per cliente con anteprime.
2. Mappa: zoom/pan, filtri da contatori in testata, legenda, elenco e filtri con "Resetta filtri", scheda modulo.
3. Rilevazioni: create in app, sommate a quelle da file, colore scelto, modifica ed eliminazione (da file: reversibile).
4. Selezione multipla (tocco e area) con applicazione di stato/danno/data/note.
5. Spostamento di un modulo per errori di trascrizione (trascinamento o "Sposta"), con ritorno alla posizione della carta.
6. "Ripristina modifiche" (ultimo minuto, dispositivo corrente).
7. Estrai layout (PDF tecnici) ed Estrazione seriali (PDF PM / Ufficio Pratiche).
8. Aggiungi impianto (caricamento documenti, stato "In preparazione"). Excel caricato così com'è nella libreria (non serve più la conversione in CSV del prototipo).

## 6. Migrazione dal prototipo

1. Creazione delle liste (§4) sul sito `ReflowArchive`.
2. Esportazione dei dati dal database dell'artefatto (schede, rilevazioni, fonti, richieste) e caricamento nelle liste: a cura di Luca con Claude.
3. Periodo di prova in parallelo; poi l'artefatto resta solo come prototipo/demo.

## 7. Aggiunta di un impianto (fase 1)

1. Ufficio tecnico: "Aggiungi impianto" → dati + layout as built (PDF vettoriale), SUF, registro seriali, altri documenti → riga in `iMAPS_Richieste`, file in `REFLOW iMAPS/richieste/<id>/`.
2. Luca (con Claude, skill `reflow-imaps`): estrazione geometria, abbinamento registro, verifica dei dubbi, generazione `dati.json`/`seriali.json`, aggiornamento `catalogo.json` nella cartella `app/mappe/`, stato richiesta → pubblicato.
3. L'impianto compare nell'app senza ripubblicarla.

## 8. Fuori perimetro (per ora)

Inverter (serve abbinamento stringhe-inverter), modalità offline completa, elaborazione automatica dei layout (fase 2).

## 9. Decisioni aperte

- App registration Azure: riuso di quella del Planner o una dedicata a iMAPS.
- Ruoli: gruppi Entra ID o lista SharePoint.
- Creazione delle liste: manuale da SharePoint o tramite script (richiede permesso Sites.Manage.All).
- Chi compone l'ufficio tecnico e chi tra i tecnici usa l'app dal telefono.
