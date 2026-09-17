// La carte des axes de l'ACP. `cartes.js` la trace ; le menu déroulant échange
// ensuite l'axe affiché sans la redessiner — les six coordonnées de chaque
// commune sont déjà dans `layout.meta.axes` (carte.API.figure_carte_acp).
(function () {
  "use strict";

  window.tracerCarteACP = function () {
    tracerCartes();
    var cadre = document.querySelector(".carte");
    var figure = JSON.parse(cadre.querySelector("script[type='application/json']").textContent);
    var axes = figure.layout.meta.axes;
    document.getElementById("axe").addEventListener("change", function () {
      var axe = axes[this.value];
      Plotly.update(cadre.querySelector(".figure"),
                    { z: [axe.valeurs], text: [axe.survol] },
                    { "coloraxis.cmin": -axe.etendue, "coloraxis.cmax": axe.etendue });
    });
  };
})();
