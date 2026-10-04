// Page des anomalies : les graphiques d'une fiche sont tracés à son ouverture
// et libérés à sa fermeture (chaque nuage est un contexte WebGL, le navigateur
// en limite le nombre).
(function () {
  "use strict";

  var config = JSON.parse(document.getElementById("config-nuage").textContent);
  var nuages = Array.prototype.map.call(document.querySelectorAll(".nuage-base"), function (s) {
    return s.textContent;
  });
  var ROUGE = "#c9352b", ENCRE = "#1f1f1c";

  function lire(fiche, nom) {
    var script = fiche.querySelector("script[data-figure='" + nom + "']");
    return script && JSON.parse(script.textContent);
  }

  // La commune sur le nuage de l'objet, et, si la correction la déplace, où elle la ramène.
  function poser(base, point) {
    var traces = [{
      type: "scattergl", x: [point.x], y: [point.y], mode: "markers", hoverinfo: "skip",
      marker: { size: 10, color: ROUGE, line: { width: 1.5, color: "#fff" } },
    }];
    if (point.corrige !== null) {
      traces.unshift({
        type: "scattergl", x: [point.x, point.x], y: [point.y, point.corrige], mode: "lines", hoverinfo: "skip",
        line: { color: ENCRE, width: 1, dash: "dot" },
      });
      traces.push({
        type: "scattergl", x: [point.x], y: [point.corrige], mode: "markers", hoverinfo: "skip",
        marker: { size: 11, symbol: "circle-open", color: ENCRE, line: { width: 2 } },
      });
    }
    base.data = base.data.concat(traces);
    return base;
  }

  function ouvrir(fiche) {
    var points = JSON.parse(fiche.querySelector("script:not([data-figure])").textContent);
    fiche.querySelectorAll(".nuage-objet .figure").forEach(function (div, i) {
      var figure = poser(JSON.parse(nuages[i]), points[i]);
      Plotly.newPlot(div, figure.data, figure.layout, config);
    });
    ["bulletins", "semblables", "historique"].forEach(function (nom) {
      var figure = lire(fiche, nom);
      if (figure) Plotly.newPlot(fiche.querySelector(".figure." + nom), figure.data, figure.layout, config);
    });
  }

  function fermer(fiche) {
    fiche.querySelectorAll(".js-plotly-plot").forEach(function (div) { Plotly.purge(div); });
  }

  document.querySelectorAll("details.fiche").forEach(function (fiche) {
    fiche.addEventListener("toggle", function () {
      if (fiche.open) ouvrir(fiche); else fermer(fiche);
    });
  });
})();
