// Réglages de design de la maquette : le brouillon de scrutin/charte.py.
// On change une valeur ici, on recharge la page. On ne touche jamais aux
// données des figures (figures.js est généré).
//
// Palette : celle validée dans PLAN_MODERNISATION.md Partie 7
// (validate_palette.js, surface #fcfcfb).
window.CHARTE = {
  surface: "#fcfcfb",
  encre1: "#1f1f1c",
  encre2: "#5f5e58",
  grille: "#e1e0d9",
  bleu: "#2a78d6",       // confirmé
  bleuClair: "#86b6ef",  // extrapolé (même teinte, plus clair = estimé)
  orange: "#eb6834",     // alternative validée pour « extrapolé »
  gris: "#f0efec",       // milieu neutre de l'échelle de carte
  rouge: "#c9352b",      // « penche non »
  fonte: "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  carte: {
    // Divergente ancrée à 50 % : non ← gris neutre → oui, bornes symétriques.
    demiEtendue: 20,     // 30 % … 70 %
    opacite: 0.95,
    hauteur: 420,
  },
  histogramme: {
    hauteur: 360,
  },
};

// Options passées à Plotly.newPlot : pas de barre d'outils, largeur fluide.
window.CONFIG_PLOTLY = { displayModeBar: false, responsive: true, displaylogo: false };

// Applique la charte par-dessus une figure exportée par construire.py.
// `genre` vaut "histogramme" ou "carte". Renvoie {data, layout}.
window.appliquerCharte = function (fig, genre) {
  const c = window.CHARTE;
  const data = JSON.parse(JSON.stringify(fig.data));
  const layout = JSON.parse(JSON.stringify(fig.layout));

  layout.font = { family: c.fonte, color: c.encre1, size: 14 };
  layout.paper_bgcolor = c.surface;
  layout.plot_bgcolor = c.surface;
  layout.margin = { l: 8, r: 8, t: 8, b: 8 };

  if (genre === "histogramme") {
    // Deux traces : « Déja dépouillés » puis « Extrapolés » (même teinte, plus clair).
    const couleurs = [c.bleu, c.bleuClair];
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
    // La ligne de majorité : l'information n°1 d'une votation.
    layout.shapes = [{
      type: "line", xref: "paper", x0: 0, x1: 1, y0: 0.5, y1: 0.5,
      line: { color: c.encre2, width: 1, dash: "dot" },
    }];
    layout.annotations = [{
      xref: "paper", x: 1, y: 0.5, xanchor: "right", yanchor: "bottom",
      text: "majorité", showarrow: false, font: { size: 12, color: c.encre2 },
    }];
  }

  if (genre === "carte") {
    const d = c.carte.demiEtendue;
    layout.coloraxis = Object.assign({}, layout.coloraxis, {
      colorscale: [[0, c.rouge], [0.5, c.gris], [1, c.bleu]],
      cmin: 50 - d, cmid: 50, cmax: 50 + d,
      colorbar: {
        title: { text: "% oui" }, ticksuffix: " %", thickness: 10, len: 0.6,
        outlinewidth: 0, tickfont: { color: c.encre2 },
      },
    });
    data.forEach((trace) => {
      trace.marker = Object.assign({}, trace.marker, { opacity: c.carte.opacite, line: { width: 0.2, color: c.surface } });
    });
    layout.height = c.carte.hauteur;
    layout.margin = { l: 0, r: 0, t: 0, b: 0 };
  }

  return { data, layout };
};
