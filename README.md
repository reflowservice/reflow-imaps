# REFLOW iMAPS

Planimetrie interattive degli impianti fotovoltaici in O&M di Reflow S.r.l.: mappa dei moduli, rilevazioni dei moduli danneggiati, schede di sostituzione con seriale vecchio e nuovo, estrazioni PDF per i tecnici in campo e per l'Ufficio Pratiche.

Applicativo web (PWA) con accesso tramite account Microsoft aziendale; i dati stanno su SharePoint, non in questo repository.

## Struttura

| Cartella | Contenuto |
|---|---|
| `docs/` | Specifica tecnica (`SPEC.md`): architettura, ruoli, modello dati, migrazione |
| `prototipo/` | Modello della pagina del prototipo (artefatto Claude, novembre 2026), base del porting |
| `tools/` | Strumenti Python per preparare un impianto: estrazione della geometria dal layout PDF vettoriale, abbinamento al registro seriali, griglia schematica, generazione dei file dell'impianto |

## Dati

Nessun dato di impianto, seriale o documento tecnico va inserito in questo repository: il `.gitignore` esclude Excel, PDF e le cartelle degli impianti. I dati vivono nella libreria SharePoint aziendale.

## Manutenzione

Responsabile dell'applicativo: Luca Alberton (PM O&M, Reflow S.r.l.). Modifiche strutturali, correzioni e nuove funzioni passano dal responsabile.
