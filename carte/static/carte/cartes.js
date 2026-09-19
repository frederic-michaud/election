// Trace les cartes de la page. Chaque `.carte` contient un `<div class="figure">`
// et le JSON de sa figure (carte.API.figure_carte).
//
// En plus du tracé : centre et zoom d'après la taille du cadre, et gestes
// coopératifs (deux doigts, ou Ctrl/⌘ + molette) pour ne pas bloquer le
// défilement de la page. Ces gestes passent par l'objet MapLibre interne de
// plotly.js : à revérifier quand plotly.js change de version.
(function () {
  "use strict";

  var TUILE = 512;
  var TEXTES = {
    "CooperativeGesturesHandler.WindowsHelpText": "Ctrl + molette pour zoomer sur la carte",
    "CooperativeGesturesHandler.MacHelpText": "⌘ + molette pour zoomer sur la carte",
    "CooperativeGesturesHandler.MobileHelpText": "Deux doigts pour déplacer la carte",
  };

  function mercator(lat) {
    return Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360));
  }

  // Centre et zoom qui font tenir l'emprise [[lon, lat], [lon, lat]] dans le cadre.
  function cadrage(emprise, largeur, hauteur) {
    var x0 = emprise[0][0], y0 = emprise[0][1], x1 = emprise[1][0], y1 = emprise[1][1];
    var marge = 1.02;
    var zoomLargeur = Math.log2(largeur * 360 / ((x1 - x0) * marge * TUILE));
    var zoomHauteur = Math.log2(hauteur * 2 * Math.PI / ((mercator(y1) - mercator(y0)) * marge * TUILE));
    var yCentre = (mercator(y0) + mercator(y1)) / 2;
    return {
      "map.center": { lon: (x0 + x1) / 2, lat: (2 * Math.atan(Math.exp(yCentre)) - Math.PI / 2) * 180 / Math.PI },
      "map.zoom": Math.min(zoomLargeur, zoomHauteur),
    };
  }

  // Sans `figure`, trace le JSON rangé dans le cadre.
  function tracer(cadre, config, figure) {
    var div = cadre.querySelector(".figure");
    figure = figure || JSON.parse(cadre.querySelector("script[type='application/json']").textContent);
    var emprise = figure.layout.meta.emprise;
    var vue = cadrage(emprise, div.clientWidth, div.clientHeight);
    figure.layout.map.center = vue["map.center"];
    figure.layout.map.zoom = vue["map.zoom"];
    var deplacee = false;

    return Plotly.newPlot(div, figure.data, figure.layout, config).then(function () {
      var map = div._fullLayout.map && div._fullLayout.map._subplot && div._fullLayout.map._subplot.map;
      if (!map) return;
      if (map._locale) Object.assign(map._locale, TEXTES);
      if (map.cooperativeGestures) map.cooperativeGestures.enable();
      map.on("movestart", function (e) { if (e.originalEvent) deplacee = true; });

      // Recadre quand le cadre change de taille, tant que le visiteur n'a pas bougé la carte.
      var attente;
      new ResizeObserver(function () {
        clearTimeout(attente);
        attente = setTimeout(function () {
          if (!deplacee && div.clientWidth) Plotly.relayout(div, cadrage(emprise, div.clientWidth, div.clientHeight));
        }, 150);
      }).observe(div);
    });
  }

  window.tracerCarte = tracer;

  window.tracerCartes = function () {
    var config = JSON.parse(document.getElementById("config-carte").textContent);
    document.querySelectorAll(".carte").forEach(function (cadre) { tracer(cadre, config); });
  };
})();
