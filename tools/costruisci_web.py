"""Genera index.html dell'app web REFLOW iMAPS a partire dal modello del prototipo.

Uso:  python tools/costruisci_web.py
Legge prototipo/app_template.html e scrive index.html nella radice del repository:
- i loghi diventano file in assets/ invece che immagini incorporate;
- nessun dato di impianto nella pagina: catalogo, dati e seriali li carica cloud.js da SharePoint dopo il login;
- window.claude (db, user) è fornito da cloud.js con login Microsoft e file JSON su SharePoint;
- in testata "Aggiorna" (aggiorna.js: attende la coda di scrittura e ricarica con la schermata di aggiornamento) ed "Esci";
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


sost("data:image/png;base64,__LOGO_W__", "assets/logo_w.png", 3)
sost("data:image/png;base64,__LOGO_C__", "assets/logo_c.png", 2)
sost("__MAPPE__", "")
sost('<link rel="preconnect" href="https://fonts.googleapis.com">',
     '<link rel="manifest" href="manifest.json">\n<script>/* Finestra a tutto schermo quando l\'app installata si apre su PC (una volta per finestra, non dopo Aggiorna) */(function(){try{var m=function(q){return matchMedia(q).matches};if(!(m(\'(display-mode: standalone)\')||m(\'(display-mode: window-controls-overlay)\'))||!m(\'(pointer: fine)\')||sessionStorage.getItem(\'reflow_maxwin\'))return;sessionStorage.setItem(\'reflow_maxwin\',\'1\');var s=screen,w=s.availWidth,h=s.availHeight;if(outerWidth>=w-8&&outerHeight>=h-8)return;moveTo(s.availLeft||0,s.availTop||0);resizeTo(w,h)}catch(e){}})();</script>\n<link rel="icon" href="assets/icon-192.png">\n'
     '<link rel="apple-touch-icon" href="assets/icon-192.png">\n<meta name="theme-color" content="#18063c">\n'
     '<link rel="preconnect" href="https://fonts.googleapis.com">')
sost("</header>",
     '  <div class="hact">\n'
     '    <button class="back" id="b-reload" aria-label="Aggiorna" title="Salva le modifiche in sospeso e ricarica i dati da SharePoint">'
     '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13.5 8a5.5 5.5 0 1 1-1.7-4M13.5 2.5v3h-3"/></svg><span class="tx">Aggiorna</span></button>\n'
     '    <button class="back" id="b-out" title="Esci dall\'account Microsoft">Esci</button>\n'
     '  </div>\n</header>')
sost("$('b-enter').onclick=()=>{location.hash='impianti';};",
     "$('b-enter').onclick=()=>{if(!IMAPS.account)IMAPS.login();else location.hash='impianti';};\n"
     "$('b-out').onclick=()=>IMAPS.logout();\n"
     "$('b-reload').onclick=()=>IMAPSREFRESH.run();")
sost("\nroute();\n</script>",
     "\nIMAPS.ready.then(ok=>{\n"
     "  if(!ok){const b=$('b-enter');b.firstChild.textContent='Accedi';b.setAttribute('aria-label','Accedi con l\\'account Microsoft aziendale');location.hash='';}\n"
     "  route();IMAPSREFRESH.ready();\n"
     "}).catch(e=>{console.error(e);route();$('sp-count').textContent='Errore: '+(e&&e.message||e);IMAPSREFRESH.ready();});\n</script>")
sost("<script>\nconst $=id=>",
     '<script src="https://cdn.jsdelivr.net/npm/@azure/msal-browser@2.38.3/lib/msal-browser.min.js"></script>\n'
     '<script src="cloud.js"></script>\n<script src="aggiorna.js"></script>\n<script>\nconst $=id=>')
sost("<title>REFLOW iMAPS</title>", "<title>REFLOW iMAPS (beta)</title>")
sost("</style>\n</head>",
     ".hact{margin-left:auto;display:flex;gap:8px;flex:none}\n"
     ".hact .back{padding:0 14px}\n"
     "#b-reload{padding:0 14px 0 11px}\n"
     ".hact .back:disabled{opacity:.55;cursor:default}\n"
     "@media (max-width:820px){.hact{position:absolute;top:12px;right:12px;margin:0}.hact .back{height:32px;padding:0 11px}#b-reload{padding:0 9px}#b-reload .tx{display:none}}\n"
     "@media (max-width:480px){.hsep{display:none}.hact{right:8px;gap:6px}.hact .back{padding:0 9px}}\n"
     "</style>\n</head>")

open(os.path.join(R, "index.html"), "w", encoding="utf-8").write(html)
print("index.html scritto,", len(html), "caratteri")
