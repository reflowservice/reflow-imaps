"""REFLOW MAPS - passo 1: estrae le vele (tavoli) da un layout PDF vettoriale.

Uso:
    python estrai_vele_layout.py <layout.pdf> <righe_layout.json> [opzioni]

Cosa fa:
  - legge i disegni vettoriali del PDF (PyMuPDF) e tiene i rettangoli che hanno la
    dimensione di un modulo (default 12-14 x 5-7 unità PDF, colori blu/rosso/verde/nero);
  - porta i centri nel sistema della pagina ruotata, come la vede chi apre il PDF;
  - raggruppa i moduli in righe visive (distanza verticale > --gap-righe);
  - dentro ogni riga visiva spezza le vele dove la distanza orizzontale tra moduli
    supera --gap-vele.
Output: elenco di righe visive dall'alto verso il basso; per ogni riga le vele da
sinistra a destra con x0, x1 (centri del primo/ultimo modulo), y0, y1 (centri delle due
file di moduli) e n (moduli disegnati per fila).

Le soglie di default sono quelle verificate su l'impianto pilota (layout generale as built).
Su un layout nuovo vanno SEMPRE controllate: stampare il riepilogo (--riepilogo) e
confrontarlo con il numero di vele per fila del registro seriali.

Dipendenze: pymupdf (pip install pymupdf).
"""
import argparse, json, sys
import numpy as np
import pymupdf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("out")
    ap.add_argument("--pagina", type=int, default=0)
    ap.add_argument("--w", default="12,14", help="larghezza modulo min,max (unità PDF non ruotate)")
    ap.add_argument("--h", default="5,7", help="altezza modulo min,max")
    ap.add_argument("--colori", default="0,0,1;1,0,0;0,1,0;0,0,0",
                    help="colori tratto ammessi, RGB 0-1 separati da ;")
    ap.add_argument("--gap-righe", type=float, default=20.0)
    ap.add_argument("--gap-vele", type=float, default=7.25)
    ap.add_argument("--doppia", type=int, default=52,
                    help="un tratto di N moduli senza stacco si spezza in due vele da N/2 (0 = mai)")
    ap.add_argument("--riepilogo", action="store_true")
    a = ap.parse_args()

    wmin, wmax = map(float, a.w.split(",")); hmin, hmax = map(float, a.h.split(","))
    colori = {tuple(round(float(x), 2) for x in c.split(",")) for c in a.colori.split(";")}
    doc = pymupdf.open(a.pdf); p = doc[a.pagina]; M = p.rotation_matrix
    pts = {}
    for d in p.get_drawings():
        r = d["rect"]; col = tuple(round(v, 2) for v in (d["color"] or ()))
        if wmin < r.width < wmax and hmin < r.height < hmax and col in colori:
            c = (r.tl + r.br) / 2 * M
            pts[(round(c.x * 2) / 2, round(c.y * 2) / 2)] = 1
    if not pts:
        sys.exit("Nessun modulo trovato: controllare --w/--h/--colori sul layout.")
    P = np.array(list(pts))
    ys = np.sort(np.unique(P[:, 1]))
    gruppi = np.split(ys, np.where(np.diff(ys) > a.gap_righe)[0] + 1)
    righe = []
    for g in gruppi:
        sel = P[(P[:, 1] >= g[0] - 1) & (P[:, 1] <= g[-1] + 1)]
        top = sel[np.abs(sel[:, 1] - g[0]) < 1.5]
        xs = np.sort(np.unique(top[:, 0]))
        runs = np.split(xs, np.where(np.diff(xs) > a.gap_vele)[0] + 1)
        out = []
        for r in runs:
            if a.doppia and len(r) == a.doppia:
                h = a.doppia // 2; out += [r[:h], r[h:]]
            else:
                out.append(r)
        ylines = sorted(set(np.round(sel[:, 1])))
        righe.append({"y0": float(min(ylines)), "y1": float(max(ylines)),
                      "vele": [{"x0": float(r[0]), "x1": float(r[-1]), "n": int(len(r))} for r in out]})
    json.dump({"pdf": a.pdf, "moduli_trovati": len(P), "righe": righe}, open(a.out, "w"), indent=1)
    print(f"moduli trovati {len(P)}, righe visive {len(righe)}, vele {sum(len(r['vele']) for r in righe)}")
    if a.riepilogo:
        for i, r in enumerate(righe):
            print(i, int(r["y0"]), [v["n"] for v in r["vele"]])

if __name__ == "__main__":
    main()
