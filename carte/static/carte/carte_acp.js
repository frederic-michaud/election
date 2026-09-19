// Les deux cartes des pages ACP : chaque commune colorée par sa coordonnée sur
// l'axe horizontal (en haut) et vertical (en bas) choisis dans le nuage. Les six
// axes sont dans `layout.meta.axes` (carte.API.figure_carte_acp).
// À appeler après `tracerNuage`, qui règle les menus d'après l'adresse.
//
// Sur la page des communes (`data-communes`), cartes et nuage se répondent par les
// événements décrits dans nuage.js : noms, survol, clic.
(function () {
  "use strict";

  var RAYON = 18;          // px autour du clic
  var MAX_PROPOSES = 6;
  var VIDE = { type: "FeatureCollection", features: [] };

  function annoncer(nom, detail) {
    document.dispatchEvent(new CustomEvent(nom, { detail: detail }));
  }

  function colorer(figure, axe) {
    figure.data[0].z = axe.valeurs;
    figure.data[0].text = axe.survol;
    figure.layout.coloraxis.cmin = -axe.etendue;
    figure.layout.coloraxis.cmax = axe.etendue;
  }

  // Par commune : contour, boîte englobante, nom, et où l'écrire (le centre de
  // gravité de son plus grand polygone).
  function indexer(geojson) {
    var index = {};
    geojson.features.forEach(function (entite) {
      var g = entite.geometry;
      var polygones = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
      var repere = null, plusGrande = 0, boite = [Infinity, Infinity, -Infinity, -Infinity];
      polygones.forEach(function (polygone) {
        var anneau = polygone[0], aire = 0, cx = 0, cy = 0;
        for (var i = 0; i < anneau.length - 1; i++) {
          var p = anneau[i], q = anneau[i + 1], c = p[0] * q[1] - q[0] * p[1];
          aire += c; cx += (p[0] + q[0]) * c; cy += (p[1] + q[1]) * c;
          boite = [Math.min(boite[0], p[0]), Math.min(boite[1], p[1]), Math.max(boite[2], p[0]), Math.max(boite[3], p[1])];
        }
        if (Math.abs(aire) > plusGrande) {
          plusGrande = Math.abs(aire);
          repere = [cx / (3 * aire), cy / (3 * aire)];
        }
      });
      index[entite.properties.vogeId] = {
        entite: entite, polygones: polygones, boite: boite, repere: repere, nom: entite.properties.vogeName,
      };
    });
    return index;
  }

  function dansAnneau(point, anneau) {
    var dedans = false;
    for (var i = 0, j = anneau.length - 1; i < anneau.length; j = i++) {
      var a = anneau[i], b = anneau[j];
      if ((a[1] > point[1]) !== (b[1] > point[1]) &&
          point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]) dedans = !dedans;
    }
    return dedans;
  }

  function Vue(div, index) {
    var carte = div._fullLayout.map._subplot.map;

    // Noms en HTML par-dessus la carte : le style de fond n'a pas de polices.
    var calque = document.createElement("div");
    calque.className = "etiquettes-carte";
    div.parentNode.appendChild(calque);
    var places = [], survolee = null;

    function placer() {
      places.concat(survolee ? [survolee] : []).forEach(function (place) {
        var p = carte.project(place.lonlat);
        place.element.style.transform = "translate(" + p.x + "px," + p.y + "px)";
      });
    }
    carte.on("move", placer);
    carte.on("resize", placer);

    function etiquette(nom, lonlat, classe) {
      var element = document.createElement("span");
      element.className = "etiquette" + (classe ? " " + classe : "");
      element.textContent = nom;
      calque.appendChild(element);
      return { element: element, lonlat: lonlat };
    }

    function contour(cle) {
      if (!carte.getSource("acp-survol")) {
        carte.addSource("acp-survol", { type: "geojson", data: VIDE });
        carte.addLayer({ id: "acp-survol", type: "line", source: "acp-survol",
                         paint: { "line-color": "#1f1f1c", "line-width": 2.5 } });
      }
      carte.getSource("acp-survol").setData(index[cle]
        ? { type: "FeatureCollection", features: [index[cle].entite] } : VIDE);
      carte.moveLayer("acp-survol");
    }

    this.nommer = function (selection) {
      places.forEach(function (place) { place.element.remove(); });
      places = [];
      selection.cles.forEach(function (cle, k) {
        if (index[cle]) places.push(etiquette(selection.noms[k], index[cle].repere));
      });
      placer();
    };

    this.survoler = function (cle) {
      contour(cle);
      if (survolee) survolee.element.remove();
      survolee = index[cle] ? etiquette(index[cle].nom, index[cle].repere, "survol") : null;
      placer();
    };

    div.on("plotly_hover", function (evenement) {
      var cle = evenement.points[0].location;
      if (cle !== undefined) annoncer("acp:survol", { cle: +cle, source: "carte" });
    });
    div.on("plotly_unhover", function () { annoncer("acp:survol", { cle: null, source: "carte" }); });

    // Un clic propose la commune cliquée, puis celles dont le centre est tout proche :
    // sur une petite commune, on tombe facilement à côté.
    carte.on("click", function (evenement) {
      var lonlat = [evenement.lngLat.lng, evenement.lngLat.lat];
      var cliquees = [], proches = [];
      Object.keys(index).forEach(function (cle) {
        var commune = index[cle], b = commune.boite;
        if (lonlat[0] >= b[0] && lonlat[0] <= b[2] && lonlat[1] >= b[1] && lonlat[1] <= b[3] &&
            commune.polygones.some(function (polygone) { return dansAnneau(lonlat, polygone[0]); })) {
          cliquees.push(+cle);
        } else if (commune.repere) {
          var p = carte.project(commune.repere);
          var d = Math.pow(p.x - evenement.point.x, 2) + Math.pow(p.y - evenement.point.y, 2);
          if (d <= RAYON * RAYON) proches.push([d, +cle]);
        }
      });
      proches.sort(function (a, b) { return a[0] - b[0]; });
      var cles = cliquees.concat(proches.map(function (p) { return p[1]; })).slice(0, MAX_PROPOSES);
      if (cles.length) {
        annoncer("acp:proposer", { cles: cles, x: evenement.originalEvent.clientX, y: evenement.originalEvent.clientY });
      }
    });
  }

  window.tracerCartesACP = function () {
    var config = JSON.parse(document.getElementById("config-carte").textContent);
    var source = document.getElementById("carte-acp").textContent;
    var traces = [];

    ["x", "y"].forEach(function (sens) {
      var choix = document.getElementById("axe-" + sens);
      var cadre = document.getElementById("carte-" + sens);
      var nom = document.querySelector("[data-axe='" + sens + "']");
      var variance = document.querySelector("[data-variance='" + sens + "']");
      var figure = JSON.parse(source);          // une copie par carte : Plotly la modifie
      var axes = figure.layout.meta.axes;

      function legender() {
        var option = choix.options[choix.selectedIndex];
        nom.textContent = option.textContent;
        variance.textContent = option.dataset.variance;
      }

      colorer(figure, axes[choix.value]);
      traces.push(tracerCarte(cadre, config, figure).then(function () {
        return { div: cadre.querySelector(".figure"), geojson: figure.data[0].geojson };
      }));
      legender();

      choix.addEventListener("change", function () {
        var axe = axes[choix.value];
        Plotly.update(cadre.querySelector(".figure"), { z: [axe.valeurs], text: [axe.survol] },
                      { "coloraxis.cmin": -axe.etendue, "coloraxis.cmax": axe.etendue });
        legender();
      });
    });

    if (!document.querySelector(".cartes-axes").hasAttribute("data-communes")) return;

    // Calques et étiquettes attendent que le style des cartes soit chargé. Les
    // contours sont déjà en cache : plotly.js les a téléchargés.
    function chargee(c) {
      var carte = c.div._fullLayout.map._subplot.map;
      return new Promise(function (ok) { if (carte._loaded) ok(); else carte.once("load", ok); });
    }
    var vues = Promise.all(traces).then(function (cartes) {
      return Promise.all(cartes.map(chargee).concat(fetch(cartes[0].geojson).then(function (r) { return r.json(); })))
        .then(function (resultats) {
          var index = indexer(resultats[cartes.length]);
          return cartes.map(function (c) { return new Vue(c.div, index); });
        });
    });
    document.addEventListener("acp:selection", function (evenement) {
      var selection = evenement.detail;
      vues.then(function (liste) { liste.forEach(function (vue) { vue.nommer(selection); }); });
    });
    document.addEventListener("acp:survol", function (evenement) {
      var cle = evenement.detail.cle;
      vues.then(function (liste) { liste.forEach(function (vue) { vue.survoler(cle); }); });
    });
  };
})();
