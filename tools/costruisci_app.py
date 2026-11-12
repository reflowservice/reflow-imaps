"""REFLOW iMAPS - passo 3: costruisce l'app REFLOW iMAPS (un solo artefatto per tutti gli impianti).

Uso:
    python costruisci_app.py <cartella REFLOW iMAPS> [--solo <id impianto>]

Legge ogni sottocartella di impianti/ che contiene impianto.json e scrive in app/:
    index.html                    l'app (pagina iniziale per cliente + visualizzatore)
    mappe/catalogo.json           elenco impianti mostrato nella pagina iniziale
    mappe/<id>/dati.json          testi, vele (geometria) e attività con i moduli
    mappe/<id>/seriali.json       seriali da registro per posizione (se presente)
Si pubblica SOLO index.html sullo stesso artefatto (publish_files, modalità patch): catalogo
e dati di tutti gli impianti sono incorporati nella pagina, perché la piattaforma artefatti non
serve i file JSON alla pagina (verificato l'11/11/2026). I file in mappe/ restano come copia
leggibile dei dati. Limite pratico: pagina fino a 16 MiB, circa 250 KB per impianto da ~12.000 moduli.

impianto.json (vedi impianti/<impianto pilota>):
  id            identificativo stabile, solo minuscole, cifre e trattini (diventa #id nell'URL
                e il percorso nel database: impianti/<id>/moduli/...). Non cambiarlo mai dopo
                la pubblicazione, o le schede compilate restano sotto il vecchio id.
  cliente       nome del cliente come va raggruppato nella pagina iniziale
  impianto      nome dell'impianto mostrato in testata e nella scheda
  localita, potenza, codice   facoltativi (non inventare: lasciare vuoti se non verificati)
  modulo_installato  {marca, modello, potenza_w, fonte}: modulo dell'impianto, da registro seriali
                e/o SUF/datasheet; se c'è modelli.json (abbina_registro --out-modelli) i moduli
                diversi dal tipo prevalente vengono presi da lì, posizione per posizione
  sottotitolo, nota_orientamento
  attivita      elenco delle attività sulla mappa (es. una campagna di sostituzione moduli):
                id, titolo, data_dati, file_moduli (CSV), file_csv (nome export), fonti
                {codice: {lab, breve, c}}

CSV moduli (separatore ;):
  n;fila;tavolo;colonna;posizione;seriale;fonte;danno;note;registro_da_correggere
Controlli stampati per ogni attività: fila incoerente col tavolo, colonna fuori misura,
fonte non definita, seriale diverso dal registro in quella posizione, conteggi per fonte.
"""
import argparse, base64, csv, json, os, re, sys, collections

def carica_moduli(path, V, reg, fonti):
    mods, problemi = [], []
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            n = int(r["n"]); t = int(r["tavolo"]); col = int(r["colonna"]); pos = r["posizione"].strip().upper()
            if t not in V: sys.exit(f"{path} riga {n}: tavolo {t} inesistente nel layout.")
            v = V[t]
            if int(r["fila"]) != v["fila"]: problemi.append(f"riga {n}: fila {r['fila']} ma il tavolo {t} è nella fila {v['fila']}")
            if col > v["ncol"]: problemi.append(f"riga {n}: colonna {col} oltre le {v['ncol']} del tavolo {t}")
            if r["fonte"] not in fonti: problemi.append(f"riga {n}: fonte '{r['fonte']}' non definita")
            ser = r["seriale"].strip()
            if reg:
                rs = reg.get(str(t), [[], []])[0 if pos == "A" else 1]
                rs = rs[col - 1] if col - 1 < len(rs) else ""
                if rs and rs != ser: problemi.append(f"riga {n}: seriale {ser} ma il registro in T{t} C{col} {pos} riporta {rs}")
            mods.append(dict(n=n, fila=v["fila"], tav=t, vela=v["vela"], col=col, pos=pos, ser=ser, src=r["fonte"],
                             causa=r.get("danno", "") or "", note=r.get("note", "") or "",
                             dub=str(r.get("registro_da_correggere", "0")).strip().lower() in ("1", "si", "sì", "true")))
    return mods, problemi

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("radice"); ap.add_argument("--solo")
    a = ap.parse_args()
    R = lambda *p: os.path.join(a.radice, *p)
    out = R("app"); os.makedirs(os.path.join(out, "mappe"), exist_ok=True)
    catalogo = []
    for nome in sorted(os.listdir(R("impianti"))):
        cart = R("impianti", nome)
        if not os.path.exists(os.path.join(cart, "impianto.json")): continue
        cfg = json.load(open(os.path.join(cart, "impianto.json"), encoding="utf-8"))
        iid = cfg["id"]
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", iid): sys.exit(f"{nome}: id '{iid}' non valido (solo minuscole, cifre, trattini)")
        vele = json.load(open(os.path.join(cart, "vele.json")))
        sp = os.path.join(cart, "seriali.json")
        reg = json.load(open(sp)) if os.path.exists(sp) else {}
        V = {v["t"]: v for v in vele}
        mp = os.path.join(cart, "modelli.json")
        mods_reg = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {"tipi": [], "eccezioni": {}}
        dich = cfg.get("modulo_installato")
        if not dich and not mods_reg["tipi"]: print(f"[{iid}] CONTROLLA modello modulo non indicato (né modulo_installato in impianto.json né registro)")
        tipi = [{"marca": t[0], "modello": t[1], "potenza_w": t[2]} for t in mods_reg["tipi"]]
        if dich:
            if tipi and (dich["modello"].replace(" ", "").upper() != tipi[0]["modello"].replace(" ", "").upper() or int(dich["potenza_w"]) != int(tipi[0]["potenza_w"])):
                print(f"[{iid}] CONTROLLA modulo_installato {dich['modello']} {dich['potenza_w']} W diverso dal registro {tipi[0]['modello']} {tipi[0]['potenza_w']} W")
            tipi = [{"marca": dich["marca"], "modello": dich["modello"], "potenza_w": dich["potenza_w"]}] + tipi[1:]
        attivita = []; tot = 0; data = ""
        for att in cfg["attivita"]:
            mods, problemi = carica_moduli(os.path.join(cart, att["file_moduli"]), V, reg, att["fonti"])
            cnt = collections.Counter(m["src"] for m in mods)
            print(f"[{iid}] {att['titolo']}: {len(mods)} moduli, per fonte {dict(cnt)}")
            for p in problemi: print(f"[{iid}] CONTROLLA {p}")
            attivita.append(dict(id=att["id"], titolo=att["titolo"], data_dati=att["data_dati"],
                                 file_csv=att.get("file_csv", ""), fonti=att["fonti"], mods=mods))
            tot = len(mods); data = att["data_dati"]
        catalogo.append(dict(id=iid, cliente=cfg["cliente"], impianto=cfg["impianto"], localita=cfg.get("localita", ""),
                             potenza=cfg.get("potenza", ""), attivita=cfg["attivita"][0]["titolo"],
                             moduli_in_lista=tot, data_dati=data))
        if a.solo and a.solo != iid: continue
        dati = dict(id=iid, cliente=cfg["cliente"], impianto=cfg["impianto"], sottotitolo=cfg["sottotitolo"] + " · Dati al " + data,
                    nota_orientamento=cfg.get("nota_orientamento", ""), attivita=attivita,
                    moduli_tipo=tipi, moduli_eccezioni=mods_reg["eccezioni"],
                    vele=[[v["t"], v["fila"], v["vela"], v["ncol"], round(v["x0"], 1), round(v["x1"], 1), round(v["y0"], 1), round(v["y1"], 1)] for v in vele])
        d = os.path.join(out, "mappe", iid); os.makedirs(d, exist_ok=True)
        json.dump(dati, open(os.path.join(d, "dati.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        json.dump(reg, open(os.path.join(d, "seriali.json"), "w"), separators=(",", ":"))
    ids = [c["id"] for c in catalogo]
    if len(ids) != len(set(ids)): sys.exit("Due impianti hanno lo stesso id.")
    json.dump(catalogo, open(os.path.join(out, "mappe", "catalogo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    S = os.path.dirname(os.path.abspath(__file__))
    html = open(os.path.join(S, "app_template.html"), encoding="utf-8").read()
    # I dati sono incorporati nella pagina: la piattaforma artefatti non serve i file JSON alla pagina via fetch.
    blocchi = ['<script id="catalogo" type="application/json">' + json.dumps(catalogo, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"]
    for c in catalogo:
        d = os.path.join(out, "mappe", c["id"])
        dj = open(os.path.join(d, "dati.json"), encoding="utf-8").read().replace("</", "<\\/")
        sj = open(os.path.join(d, "seriali.json"), encoding="utf-8").read()
        blocchi.append(f'<script type="application/json" data-dati="{c["id"]}">{dj}</script>')
        blocchi.append(f'<script type="application/json" data-seriali="{c["id"]}">{sj}</script>')
    html = html.replace("__MAPPE__", "\n".join(blocchi))
    for k, f in (("__LOGO_W__", "logo_w.png"), ("__LOGO_C__", "logo_c.png")):
        html = html.replace(k, base64.b64encode(open(os.path.join(S, f), "rb").read()).decode())
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)
    print(f"app scritta in {out}: {len(catalogo)} impianti nel catalogo")

if __name__ == "__main__":
    main()
