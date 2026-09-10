# Maquette statique de l'accueil

Le laboratoire de design de la voie Interface (`PLAN_MODERNISATION.md`,
Partie 7). Une page HTML qu'on ouvre en `file://`, avec les **vraies figures
Plotly** du site embarquées en JSON — interactives et éditables, là où un PNG
figerait ce qu'on veut faire varier.

```bash
python manage.py peupler_demo        # base fictive, une fois
python maquette/construire.py        # écrit figures.js, copie plotly.min.js
xdg-open maquette/accueil.html       # ou double-clic
```

| Fichier | Rôle | Versionné |
|---|---|---|
| `construire.py` | génère les fichiers ci-dessous depuis la base fictive, avec les fonctions du site | oui |
| `figures.js` | contrat de vue + figures en JSON (`window.VUE`, `window.FIGURES`) | **non** (généré, ~5 Mo) |
| `plotly.min.js` | plotly.js, copié du paquet Python — la version qui a produit les figures | **non** (généré) |
| `charte.js` | **les réglages de design**, appliqués par-dessus les figures au chargement | oui |
| `accueil.html` | variante 0, le squelette ; les variantes d'agencement s'appellent `accueil-a.html`, `-b.html`… | oui |
| `capture.mjs` | capture PNG d'une variante (Playwright), pour discuter par message | oui |

Pour changer l'apparence d'un graphe, on édite `charte.js` et on recharge.
On n'édite jamais `figures.js` : il sort de `graphiques.py` et `carte/`, comme
les figures du site, et c'est ce qui garantit que la maquette ne promet rien
que Django ne donnerait pas.

Largeur téléphone : `node maquette/capture.mjs maquette/accueil.html tel.png 400`.
