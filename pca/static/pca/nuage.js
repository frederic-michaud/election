// Les nuages ACP : communes et objets de votation dans le plan de deux axes.
//
// La figure servie par Django porte les six coordonnées dans `layout.meta.nuage` :
// changer de plan ou chercher un nom ne redemande donc rien au serveur.
// Trois traces, toujours dans cet ordre : tous les points, les étiquettes
// d'office (points les plus excentrés), les résultats de la recherche.
(function () {
  "use strict";

  function sansAccent(texte) {
    return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  window.tracerNuage = function (config) {
    var cadre = document.querySelector(".nuage");
    var div = cadre.querySelector(".figure");
    var figure = JSON.parse(cadre.querySelector("script[type='application/json']").textContent);
    var nuage = figure.layout.meta.nuage;
    var normalises = nuage.noms.map(sansAccent);
    var champ = document.getElementById("recherche");
    var compte = document.getElementById("compte");
    var unite = champ.dataset.unite;

    // Les points les plus loin de l'origine : ceux qui donnent leur sens aux axes.
    function extremes(x, y) {
      if (!nuage.extremes) return [];
      var rangs = nuage.noms.map(function (_, i) { return i; });
      rangs.sort(function (a, b) { return (x[b] * x[b] + y[b] * y[b]) - (x[a] * x[a] + y[a] * y[a]); });
      return rangs.slice(0, nuage.extremes);
    }

    // D'abord les noms qui commencent par la saisie — « Lau » doit donner Lausanne,
    // pas les vingt communes qui contiennent ces lettres. Sinon, on élargit.
    function trouves() {
      var q = sansAccent(champ.value.trim());
      if (!q) return [];
      var debut = [], dedans = [];
      normalises.forEach(function (nom, i) {
        var ou = nom.indexOf(q);
        if (ou === 0) debut.push(i);
        else if (ou !== -1) dedans.push(i);
      });
      return debut.length ? debut : dedans;
    }

    // { x, y, text, textposition, hovertext } d'une sélection ; `noms` écrit les étiquettes.
    //
    // Dans le cercle des corrélations, l'étiquette part vers l'intérieur : posée
    // dessous, elle sortirait du cadre pour les points collés au bord.
    function selection(indices, x, y, noms) {
      return {
        x: indices.map(function (i) { return x[i]; }),
        y: indices.map(function (i) { return y[i]; }),
        text: indices.map(function (i) { return noms ? nuage.etiquettes[i] : ""; }),
        textposition: indices.map(function (i) {
          if (!nuage.fixe) return "bottom center";
          return x[i] > 0 ? "middle left" : "middle right";
        }),
        hovertext: indices.map(function (i) { return nuage.survol[i]; }),
      };
    }

    function redessiner() {
      var ax = +document.getElementById("axe-x").value;
      var ay = +document.getElementById("axe-y").value;
      var x = nuage.axes[ax], y = nuage.axes[ay];
      var marques = trouves();
      var haut = selection(extremes(x, y), x, y, true);
      var cherches = selection(marques, x, y, marques.length > 0 && marques.length < nuage.seuil_noms);

      if (compte) {
        compte.textContent = champ.value.trim()
          ? marques.length + " " + unite + (marques.length < nuage.seuil_noms ? "" : " — trop pour les nommer")
          : "";
      }
      var miseAJour = {
        x: [x, haut.x, cherches.x],
        y: [y, haut.y, cherches.y],
        text: [[], haut.text, cherches.text],
        textposition: ["bottom center", haut.textposition, cherches.textposition],
        hovertext: [nuage.survol, haut.hovertext, cherches.hovertext],
      };
      var cadrage = {
        "xaxis.title.text": "Axe " + (ax + 1),
        "yaxis.title.text": "Axe " + (ay + 1),
      };
      if (!nuage.fixe) {
        cadrage["xaxis.autorange"] = true;
        cadrage["yaxis.autorange"] = true;
      }
      Plotly.update(div, miseAJour, cadrage);
    }

    // ?q=Lau&x=1&y=3 — l'état de la page tient dans son adresse, donc se partage.
    var parametres = new URLSearchParams(location.search);
    if (parametres.get("q")) champ.value = parametres.get("q");
    ["x", "y"].forEach(function (nom) {
      var axe = parseInt(parametres.get(nom), 10);
      if (axe >= 1 && axe <= nuage.axes.length) document.getElementById("axe-" + nom).value = String(axe - 1);
    });

    Plotly.newPlot(div, figure.data, figure.layout, config).then(redessiner);
    document.getElementById("axe-x").addEventListener("change", redessiner);
    document.getElementById("axe-y").addEventListener("change", redessiner);
    champ.addEventListener("input", redessiner);
  };
})();
