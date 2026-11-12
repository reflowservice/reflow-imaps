"""REFLOW MAPS - alternativa al passo 1+2 quando NON c'è un layout vettoriale utilizzabile.

Genera vele.json con una griglia schematica: una striscia per fila, vele affiancate da
ovest a est, stesse convenzioni di numerazione (tavolo = progressivo della vela).

Uso:
    python griglia_schematica.py <struttura.csv> <vele.json>

struttura.csv (separatore ;), una riga per vela:
    fila;vela;colonne
    1;1;26
    1;2;26
    ...
Se esiste un registro seriali, la struttura si ricava da lì (colonne = colonna massima per
fila/vela) e conviene usare abbina_registro.py su un layout vero; questa griglia serve per
gli impianti senza layout o senza registro. La pagina funziona uguale, ma la forma
dell'impianto non è quella reale: dirlo sempre a chi la usa.
"""
import csv, json, sys, collections

PASSO = 6.5      # distanza tra centri di colonna (stessa scala del layout dell'impianto pilota)
ALT_FILA = 52.0  # distanza tra file
GAP_VELA = 8.0

def main():
    src, out = sys.argv[1], sys.argv[2]
    righe = collections.defaultdict(list)
    with open(src, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            righe[int(r["fila"])].append((int(r["vela"]), int(r["colonne"])))
    vele = []; t = 0
    for i, f in enumerate(sorted(righe)):
        x = 0.0; y0 = i * ALT_FILA
        for v, nc in sorted(righe[f]):
            t += 1
            vele.append({"t": t, "fila": f, "vela": v, "ncol": nc, "x0": x, "x1": x + (nc - 1) * PASSO, "y0": y0, "y1": y0 + 13.0})
            x += (nc - 1) * PASSO + PASSO + GAP_VELA
    json.dump(vele, open(out, "w"))
    print(f"file {len(righe)}, vele {len(vele)}")

if __name__ == "__main__":
    main()
