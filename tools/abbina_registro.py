"""REFLOW MAPS - passo 2: abbina le vele del layout al registro seriali dell'impianto.

Uso:
    python abbina_registro.py <registro.xlsx> <righe_layout.json> <vele.json> <seriali.json>
                              [--foglio "aggiornamento sostituzioni"] [--ovest 31]

Registro atteso (come "registro seriali" dell'impianto pilota): una riga per
modulo con colonne Fila, Vela, Riga (1/2), Colonna, Seriale e, facoltativa, una colonna
"Seriali sostituiti" (indice --col-sost, 0-based) con il seriale montato dopo una
sostituzione. Il seriale "attuale" è quello sostituito se presente, altrimenti l'originale.

Numerazione: "tavolo" = numero progressivo della vela su tutto l'impianto, fila per fila
(fila 1 vela 1 = tavolo 1). È la convenzione verificata sull'impianto pilota: va riverificata
su ogni impianto nuovo confrontando 2-3 righe della tabella moduli con il registro.

Abbinamento righe visive -> file:
  --ovest 0  (default) ogni riga visiva contiene file consecutive, nell'ordine;
  --ovest N  le file 1..N sono il blocco di sinistra (fila i+1 = prime vele della riga
             visiva i), le file da N+1 in poi riempiono in sequenza il resto delle righe.
             impianto pilota: --ovest 31.
Lo script si ferma se il numero di vele di una fila non torna e segnala dove; una
differenza di colonne (es. 7 disegnate, 6 nel registro) è solo segnalata, vale il registro.

Dipendenze: openpyxl.
"""
import argparse, json, collections, sys
import openpyxl

def norm(v):
    if v is None: return ""
    if isinstance(v, float): v = int(v)
    return str(v).strip().lstrip("'")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("registro"); ap.add_argument("righe"); ap.add_argument("out_vele"); ap.add_argument("out_seriali")
    ap.add_argument("--out-modelli", help="modelli.json: marca/modello/potenza per posizione (colonne 6-8 del registro)")
    ap.add_argument("--foglio", default="aggiornamento sostituzioni")
    ap.add_argument("--col-sost", type=int, default=8)
    ap.add_argument("--ovest", type=int, default=0)
    a = ap.parse_args()

    wb = openpyxl.load_workbook(a.registro, data_only=True, read_only=True)
    ws = wb[a.foglio] if a.foglio in wb.sheetnames else wb.worksheets[0]
    cols = collections.defaultdict(set); ser = {}; mod = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        f, v, rg, c = r[:4]
        if not isinstance(f, int): continue
        cols[(f, v)].add(c)
        cur = (norm(r[a.col_sost]) if len(r) > a.col_sost else "") or norm(r[4])
        ser[(f, v, rg, c)] = cur
        if len(r) > 7 and r[6]: mod[(f, v, rg, c)] = (norm(r[5]), norm(r[6]), r[7])
    chiavi = sorted(cols)
    tav = {k: i + 1 for i, k in enumerate(chiavi)}
    per_fila = collections.defaultdict(list)
    for (f, v) in chiavi: per_fila[f].append(v)
    file = sorted(per_fila)
    righe = json.load(open(a.righe))["righe"]

    assegnate = []  # (fila, [vele layout])
    coda = [f for f in file if f > a.ovest] if a.ovest else list(file)
    qi = 0
    for i, rv in enumerate(righe):
        rest = list(rv["vele"])
        if a.ovest and i + 1 <= a.ovest:
            f = i + 1; n = len(per_fila[f]); assegnate.append((f, rest[:n], rv)); rest = rest[n:]
        while rest:
            if qi >= len(coda): sys.exit(f"Riga visiva {i}: avanzano {len(rest)} vele senza fila da assegnare.")
            f = coda[qi]; n = len(per_fila[f]); assegnate.append((f, rest[:n], rv)); rest = rest[n:]; qi += 1
    vele = []; avvisi = []
    for f, lv, rv in assegnate:
        if len(lv) != len(per_fila[f]):
            sys.exit(f"Fila {f}: {len(lv)} vele nel layout, {len(per_fila[f])} nel registro. Rivedere --ovest o le soglie del passo 1.")
        for v, l in zip(sorted(per_fila[f]), lv):
            nc = len(cols[(f, v)])
            if nc != l["n"]: avvisi.append(f"fila {f} vela {v}: {l['n']} moduli disegnati, {nc} nel registro (vale il registro)")
            vele.append({"t": tav[(f, v)], "fila": f, "vela": v, "ncol": nc,
                         "x0": l["x0"], "x1": l["x1"], "y0": rv["y0"], "y1": rv["y1"]})
    mancanti = set(per_fila) - {f for f, _, _ in assegnate}
    if mancanti: sys.exit(f"File del registro non trovate nel layout: {sorted(mancanti)}")
    out_ser = {}
    for (f, v) in chiavi:
        nc = max(cols[(f, v)])
        out_ser[str(tav[(f, v)])] = [[ser.get((f, v, rg, c), "") for c in range(1, nc + 1)] for rg in (1, 2)]
    json.dump(sorted(vele, key=lambda x: x["t"]), open(a.out_vele, "w"))
    if a.out_modelli:
        cnt = collections.Counter(mod.values())
        tipi = [list(k) for k, _ in cnt.most_common()]
        idx = {tuple(k): i for i, k in enumerate(tipi)}
        ecc = {f"T{tav[(f, v)]}-C{c}-{'A' if rg == 1 else 'B'}": idx[m] for (f, v, rg, c), m in mod.items() if idx[m] != 0}
        json.dump({"tipi": tipi, "eccezioni": ecc}, open(a.out_modelli, "w"), ensure_ascii=False)
        print("modelli nel registro:", {f"{k[0]} {k[1]} {k[2]} W": n for k, n in cnt.items()})
    json.dump(out_ser, open(a.out_seriali, "w"), separators=(",", ":"))
    print(f"vele abbinate {len(vele)} su {len(chiavi)} del registro; moduli nel registro {len(ser)}")
    for x in avvisi: print("AVVISO", x)

if __name__ == "__main__":
    main()
