// Réglages de design des maquettes : le brouillon de scrutin/charte.py.
//
// `CHARTE` porte les valeurs par défaut (palette validée, PLAN_MODERNISATION.md
// Partie 7). Chaque variante passe sa propre surcharge à `appliquerCharte` :
// c'est là que se comparent les partis pris graphiques.
//
// On ne touche jamais aux données des figures — figures.js est généré.
window.CHARTE = {
  surface: "#fcfcfb",     // fond de la figure
  encre1: "#1f1f1c",      // texte principal
  encre2: "#5f5e58",      // texte secondaire, axes
  grille: "#e1e0d9",      // grille hairline
  bleu: "#2a78d6",        // oui / confirmé
  bleuClair: "#86b6ef",   // extrapolé (même teinte, plus clair = estimé)
  rouge: "#c9352b",       // non
  neutre: "#f0efec",      // milieu de l'échelle divergente, ancré à 50 %
  fonte: "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  carte: {
    demiEtendue: 20,      // bornes symétriques autour de 50 : 30 % … 70 %
    zoom: null,           // Mapbox seulement : null = garder le zoom de la figure
    opacite: 0.95,
    contour: 0.2,         // filet entre communes, dans la couleur du fond
    hauteur: 420,
    barreCouleur: true,
  },
  histogramme: {
    hauteur: 360,
    ligneMajorite: true,
  },
};

window.CONFIG_PLOTLY = { displayModeBar: false, responsive: true, displaylogo: false };

// Applique la charte par-dessus une figure exportée par construire.py.
// `genre` : "histogramme", "carte" (Mapbox) ou "carte_svg" (projection SVG).
// `surcharge` : les valeurs propres à la variante.
window.appliquerCharte = function (fig, genre, surcharge) {
  const s = surcharge || {};
  const c = Object.assign({}, window.CHARTE, s);
  c.carte = Object.assign({}, window.CHARTE.carte, s.carte);
  c.histogramme = Object.assign({}, window.CHARTE.histogramme, s.histogramme);

  const data = JSON.parse(JSON.stringify(fig.data));
  const layout = JSON.parse(JSON.stringify(fig.layout));

  layout.font = { family: c.fonte, color: c.encre1, size: c.taillePolice || 14 };
  layout.paper_bgcolor = c.surface;
  layout.plot_bgcolor = c.surface;
  layout.margin = { l: 8, r: 8, t: 8, b: 8 };

  if (genre === "histogramme") {
    // Deux traces : « Déja dépouillés », puis « Extrapolés ».
    const couleurs = c.couleursSeries || [c.bleu, c.bleuClair];
    data.forEach((trace, i) => {
      trace.marker = Object.assign({}, trace.marker, { color: couleurs[i] });
      trace.textposition = "outside";
      trace.textfont = { color: c.encre2 };
    });
    layout.height = c.histogramme.hauteur;
    layout.margin = { l: 48, r: 8, t: 16, b: 40 };
    layout.legend = { orientation: "h", y: -0.18, title: { text: "" } };
    layout.xaxis = Object.assign({}, layout.xaxis, { title: { text: "" }, showgrid: false });
    layout.yaxis = Object.assign({}, layout.yaxis, {
      title: { text: "" }, tickformat: ".0%", gridcolor: c.grille, zeroline: false, range: [0, 1],
    });
    if (c.histogramme.ligneMajorite) {
      // L'information n°1 d'une votation : le seuil qu'il faut franchir.
      layout.shapes = [{
        type: "line", xref: "paper", x0: 0, x1: 1, y0: 0.5, y1: 0.5,
        line: { color: c.encre2, width: 1, dash: "dot" },
      }];
      layout.annotations = [{
        xref: "paper", x: 1, y: 0.5, xanchor: "right", yanchor: "bottom",
        text: "majorité", showarrow: false, font: { size: 12, color: c.encre2 },
      }];
    }
  }

  if (genre === "carte" || genre === "carte_svg") {
    // Les contours sont stockés une fois pour toutes (voir construire.py).
    data.forEach((trace) => { if (!trace.geojson) trace.geojson = window.GEOJSON; });

    const d = c.carte.demiEtendue;
    layout.coloraxis = Object.assign({}, layout.coloraxis, {
      // Divergente ancrée à 50 % : « penche non » ← neutre → « penche oui ».
      colorscale: [[0, c.rouge], [0.5, c.neutre], [1, c.bleu]],
      cmin: 50 - d, cmid: 50, cmax: 50 + d,
      showscale: c.carte.barreCouleur,
      colorbar: {
        title: { text: "" }, ticksuffix: " %", thickness: 8, len: 0.7, x: 1,
        outlinewidth: 0, tickfont: { color: c.encre2, size: 11 },
      },
    });
    data.forEach((trace) => {
      trace.marker = Object.assign({}, trace.marker, {
        opacity: c.carte.opacite,
        line: { width: c.carte.contour, color: c.surface },
      });
    });
    layout.height = c.carte.hauteur;
    layout.margin = { l: 0, r: 0, t: 0, b: 0 };
    if (genre === "carte_svg") {
      layout.geo = Object.assign({}, layout.geo, {
        bgcolor: "rgba(0,0,0,0)", showframe: false, showcoastlines: false,
      });
    } else {
      layout.mapbox = Object.assign({}, layout.mapbox, {
        // Pas de tuiles externes : un simple aplat, à la couleur de la page.
        style: { version: 8, sources: {}, layers: [{ id: "fond", type: "background", paint: { "background-color": c.surface } }] },
      });
      // Contrairement à la projection SVG (`fitbounds`), Mapbox garde le zoom
      // figé à la construction : c'est à la page de le recalculer.
      if (c.carte.zoom) layout.mapbox.zoom = c.carte.zoom;
      if (c.carte.centre) layout.mapbox.center = c.carte.centre;
    }
  }

  return { data, layout };
};

// Raccourci : dessine une figure de figures.js dans un conteneur.
window.tracer = function (cible, fig, genre, surcharge) {
  const p = window.appliquerCharte(fig, genre, surcharge);
  return Plotly.newPlot(cible, p.data, p.layout, window.CONFIG_PLOTLY);
};
