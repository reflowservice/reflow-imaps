"""Genera index.html dell'app web REFLOW iMAPS a partire dal modello del prototipo.

Uso:  python tools/costruisci_web.py
Legge prototipo/app_template.html e scrive index.html nella radice del repository:
- i loghi diventano file in assets/ invece che immagini incorporate;
- nessun dato di impianto nella pagina: catalogo, dati e seriali li carica cloud.js da SharePoint dopo il login;
- window.claude (db, user) è fornito da cloud.js con login Microsoft e file JSON su SharePoint;
- il pulsante della schermata iniziale diventa "Accedi" finché non si è entrati; in alto compare "Esci".
"""
import os, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(R, "prototipo", "app_template.html"), encoding="utf-8").read()


def sost(vecchio, nuovo, volte=1):
    global html
    n = html.count(vecchio)
    if n != volte:
        sys.exit(f"Modello cambiato: atteso {volte}x, trovato {n}x -> {vecchio[:70]!r}")
    html = html.replace(vecchio, nuovo)


sost("data:image/png;base64,__LOGO_W__", "assets/logo_w.png", 2)
sost("data:image/png;base64,__LOGO_C__", "assets/logo_c.png", 2)
sost("__MAPPE__", "")
sost('<link rel="preconnect" href="https://fonts.googleapis.com">',
     '<link rel="manifest" href="manifest.json">\n<link rel="icon" href="assets/icon-192.png">\n'
     '<link rel="apple-touch-icon" href="assets/icon-192.png">\n<meta name="theme-color" content="#18063c">\n'
     '<link rel="preconnect" href="https://fonts.googleapis.com">')
sost("</header>",
     '  <button class="back" id="b-out" title="Esci dall\'account Microsoft" style="margin-left:auto">Esci</button>\n</header>')
sost("$('b-enter').onclick=()=>{location.hash='impianti';};",
     "$('b-enter').onclick=()=>{if(!IMAPS.account)IMAPS.login();else location.hash='impianti';};\n"
     "$('b-out').onclick=()=>IMAPS.logout();")
sost("\nroute();\n</script>",
     "\nIMAPS.ready.then(ok=>{\n"
     "  if(!ok){const b=$('b-enter');b.firstChild.textContent='Accedi';b.setAttribute('aria-label','Accedi con l\\'account Microsoft aziendale');location.hash='';}\n"
     "  route();\n"
     "}).catch(e=>{console.error(e);route();$('sp-count').textContent='Errore: '+(e&&e.message||e);});\n</script>")
sost("<script>\nconst $=id=>",
     '<script src="https://cdn.jsdelivr.net/npm/@azure/msal-browser@2.38.3/lib/msal-browser.min.js"></script>\n'
     '<script src="cloud.js"></script>\n<script>\nconst $=id=>')
sost("<title>REFLOW iMAPS</title>", "<title>REFLOW iMAPS (beta)</title>")

open(os.path.join(R, "index.html"), "w", encoding="utf-8").write(html)
print("index.html scritto,", len(html), "caratteri")
