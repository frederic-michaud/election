// Les nuages ACP : communes ou objets dans le plan de deux axes.
//
// Les six coordonnées sont dans `layout.meta.nuage`. Quatre traces : tous les
// points, les points nommés, la recherche, l'anneau du point survolé ailleurs.
// Un clic ouvre une bulle listant les points proches, où l'on nomme ou retire.
//
// Événements échangés avec les cartes, sur `document` :
//   acp:selection {cles, noms}  la liste des points nommés a changé
//   acp:survol    {cle, source} point survolé (cle null : aucun)
//   acp:proposer  {cles, x, y}  ouvrir la bulle sur ces points, à ces coordonnées
(function () {
  "use strict";

  var RAYON = 14;          // px autour du clic
  var MAX_PROPOSES = 8;
  var ANNEAU = 3;

  function sansAccent(texte) {
    return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function element(balise, classe, texte) {
    var e = document.createElement(balise);
    if (classe) e.className = classe;
    if (texte) e.textContent = texte;
    return e;
  }

  function bouton(classe, texte, quoi) {
    var b = element("button", classe, texte);
    b.type = "button";
    b.addEventListener("click", quoi);
    return b;
  }

  function annoncer(nom, detail) {
    document.dispatchEvent(new CustomEvent(nom, { detail: detail }));
  }

  window.tracerNuage = function (config) {
    var cadre = document.querySelector(".nuage");
    var div = cadre.querySelector(".figure");
    var figure = JSON.parse(cadre.querySelector("script[type='application/json']").textContent);
    var nuage = figure.layout.meta.nuage;
    var normalises = nuage.noms.map(sansAccent);
    var rang = {};
    nuage.cles.forEach(function (cle, i) { rang[cle] = i; });

    var champ = document.getElementById("recherche");
    var compte = document.getElementById("compte");
    var pastilles = document.getElementById("choisis");
    var choixX = document.getElementById("axe-x");
    var choixY = document.getElementById("axe-y");
    var unite = champ.dataset.unite;
    var zone = document.querySelector(".analyse");

    var parDefaut = nuage.selection.slice();
    var nommes = parDefaut.slice();
    var marques = [];
    var plan = null;

    function axes() {
      return [nuage.axes[+choixX.value], nuage.axes[+choixY.value]];
    }

    // D'abord les noms qui commencent par la saisie, sinon ceux qui la contiennent.
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

    // Près d'un bord, l'étiquette part vers l'intérieur pour ne pas sortir du cadre.
    function points(indices, x, y, noms, bornes) {
      return {
        x: indices.map(function (i) { return x[i]; }),
        y: indices.map(function (i) { return y[i]; }),
        text: indices.map(function (i) { return noms ? nuage.etiquettes[i] : ""; }),
        textposition: indices.map(function (i) {
          if (nuage.fixe) return x[i] > 0 ? "middle left" : "middle right";
          var t = (x[i] - bornes[0]) / (bornes[1] - bornes[0]);
          return t > 0.88 ? "bottom left" : t < 0.12 ? "bottom right" : "bottom center";
        }),
        hovertext: indices.map(function (i) { return nuage.survol[i]; }),
      };
    }

    function titre(choix) {
      var option = choix.options[choix.selectedIndex];
      return option.textContent + " · " + option.dataset.variance;
    }

    function etendue(valeurs) {
      if (nuage.fixe) return [-1.08, 1.08];
      var lo = Math.min.apply(null, valeurs), hi = Math.max.apply(null, valeurs);
      var marge = 0.04 * (hi - lo);
      return [lo - marge, hi + marge];
    }

    function redessiner() {
      var xy = axes(), x = xy[0], y = xy[1];
      // On ne recadre qu'en changeant d'axes, pour garder le zoom du visiteur.
      var recadrer = plan !== choixX.value + "," + choixY.value;
      plan = choixX.value + "," + choixY.value;
      var bornesX = recadrer ? etendue(x) : div._fullLayout.xaxis.range.slice();
      marques = trouves();
      var avecNoms = marques.length > 0 && marques.length < nuage.seuil_noms;
      var haut = points(nommes, x, y, true, bornesX);
      var cherches = points(marques, x, y, avecNoms, bornesX);

      compte.textContent = !champ.value.trim() ? "" :
        marques.length + " " + (marques.length > 1 ? unite : unite.replace(/s$/, "")) +
        (avecNoms ? " — Entrée pour les nommer" : marques.length ? " — trop pour les nommer" : "");

      var mise = { "xaxis.title.text": titre(choixX), "yaxis.title.text": titre(choixY) };
      if (recadrer) {
        mise["xaxis.range"] = bornesX;
        mise["yaxis.range"] = etendue(y);
      }
      Plotly.update(div, {
        x: [x, haut.x, cherches.x],
        y: [y, haut.y, cherches.y],
        text: [[], haut.text, cherches.text],
        textposition: ["bottom center", haut.textposition, cherches.textposition],
        hovertext: [nuage.survol, haut.hovertext, cherches.hovertext],
      }, mise, [0, 1, 2]);
    }

    function lister() {
      pastilles.textContent = "";
      nommes.forEach(function (i) {
        var puce = bouton("puce", nuage.etiquettes[i], function () { basculer(i); });
        puce.setAttribute("aria-label", "Retirer " + nuage.noms[i]);
        puce.addEventListener("mouseenter", function () { survoler(i, "liste"); });
        puce.addEventListener("mouseleave", function () { survoler(null, "liste"); });
        pastilles.appendChild(puce);
      });
      if (nommes.join() !== parDefaut.join()) {
        pastilles.appendChild(bouton("action", "Choix par défaut", function () { nommes = parDefaut.slice(); changer(); }));
      }
      if (nommes.length) {
        pastilles.appendChild(bouton("action", "Tout retirer", function () { nommes = []; changer(); }));
      }
    }

    function changer() {
      redessiner();
      lister();
      annoncer("acp:selection", {
        cles: nommes.map(function (i) { return nuage.cles[i]; }),
        noms: nommes.map(function (i) { return nuage.etiquettes[i]; }),
      });
    }

    function basculer(i) {
      var ou = nommes.indexOf(i);
      if (ou === -1) nommes.push(i);
      else nommes.splice(ou, 1);
      changer();
    }

    function survoler(i, source) {
      annoncer("acp:survol", { cle: i === null ? null : nuage.cles[i], source: source });
    }

    // Pas d'anneau pour un survol du nuage lui-même : Plotly montre déjà le point,
    // et redessiner sous la souris effacerait son info-bulle.
    document.addEventListener("acp:survol", function (evenement) {
      if (evenement.detail.source === "nuage") return;
      var i = rang[evenement.detail.cle], xy = axes();
      var ici = i === undefined ? [[], []] : [[xy[0][i]], [xy[1][i]]];
      Plotly.restyle(div, { x: [ici[0]], y: [ici[1]] }, [ANNEAU]);
    });

    // --- Bulle ---

    var bulle = element("div", "bulle");
    bulle.hidden = true;
    bulle.setAttribute("role", "dialog");
    bulle.setAttribute("aria-label", "Nommer ou retirer");
    zone.appendChild(bulle);

    function fermer() {
      if (bulle.hidden) return;
      bulle.hidden = true;
      survoler(null, "bulle");
    }

    function ligne(i) {
      var nomme = nommes.indexOf(i) !== -1;
      var choix = bouton("choix", "", function () { fermer(); basculer(i); });
      choix.title = nuage.survol[i];
      choix.append(
        element("span", "nom", nuage.etiquettes[i]),
        element("span", "detail", nuage.survol[i].split(" · ").slice(1).join(" · ")),
        element("span", nomme ? "geste retirer" : "geste", nomme ? "Retirer" : "Nommer"));
      choix.addEventListener("mouseenter", function () { survoler(i, "bulle"); });
      choix.addEventListener("focus", function () { survoler(i, "bulle"); });
      var li = element("li");
      li.appendChild(choix);
      return li;
    }

    // `point` : coordonnées du clic dans le plan, pour « Zoomer ici ».
    function proposer(indices, clientX, clientY, point) {
      if (!indices.length) return;
      bulle.textContent = "";
      var liste = element("ul");
      indices.forEach(function (i) { liste.appendChild(ligne(i)); });
      bulle.appendChild(liste);
      if (point) bulle.appendChild(bouton("action", "Zoomer ici", function () { fermer(); zoomer(point); }));

      // Sous le clic, ou au-dessus faute de place ; toujours dans la fenêtre.
      bulle.hidden = false;
      var z = zone.getBoundingClientRect(), hauteur = bulle.offsetHeight;
      var gauche = Math.min(clientX - z.left + 12, zone.clientWidth - bulle.offsetWidth - 4);
      var haut = clientY - z.top + 12;
      if (clientY + 12 + hauteur > window.innerHeight) haut = clientY - z.top - 12 - hauteur;
      haut = Math.max(4 - z.top, Math.min(haut, window.innerHeight - z.top - hauteur - 4));
      bulle.style.left = Math.max(0, gauche) + "px";
      bulle.style.top = haut + "px";
      liste.querySelector("button").focus({ preventScroll: true });
      survoler(indices[0], "bulle");
    }

    // Fermée dès l'appui ailleurs, pour qu'un clic sur un autre point en ouvre une nouvelle.
    document.addEventListener("pointerdown", function (evenement) {
      if (!bulle.contains(evenement.target)) fermer();
    }, true);
    document.addEventListener("keydown", function (evenement) {
      if (evenement.key === "Escape") fermer();
    });
    document.addEventListener("acp:proposer", function (evenement) {
      var indices = evenement.detail.cles.map(function (cle) { return rang[cle]; })
        .filter(function (i) { return i !== undefined; });
      proposer(indices, evenement.detail.x, evenement.detail.y, null);
    });

    // --- Zoom ---

    var vueEnsemble = bouton("vue-ensemble", "Vue d'ensemble", function () { plan = null; redessiner(); });
    vueEnsemble.hidden = true;
    cadre.appendChild(vueEnsemble);

    function zoomer(point) {
      var xa = div._fullLayout.xaxis, ya = div._fullLayout.yaxis;
      var lx = (xa.range[1] - xa.range[0]) / 10, ly = (ya.range[1] - ya.range[0]) / 10;
      Plotly.relayout(div, { "xaxis.range": [point[0] - lx, point[0] + lx], "yaxis.range": [point[1] - ly, point[1] + ly] });
    }

    function suivreZoom() {
      var ensemble = etendue(axes()[0]), courant = div._fullLayout.xaxis.range;
      vueEnsemble.hidden = courant[1] - courant[0] > 0.95 * (ensemble[1] - ensemble[0]);
    }

    // --- Départ ---

    // ?q=Lau&x=1&y=3 : l'état de la page tient dans son adresse.
    var parametres = new URLSearchParams(location.search);
    if (parametres.get("q")) champ.value = parametres.get("q");
    ["x", "y"].forEach(function (nom) {
      var axe = parseInt(parametres.get(nom), 10);
      if (axe >= 1 && axe <= nuage.axes.length) document.getElementById("axe-" + nom).value = String(axe - 1);
    });

    function indice(point) {
      return [point.pointIndex, nommes[point.pointIndex], marques[point.pointIndex]][point.curveNumber];
    }

    Plotly.newPlot(div, figure.data, figure.layout, config).then(function () {
      changer();
      div.on("plotly_relayout", suivreZoom);
      div.on("plotly_update", suivreZoom);
      div.on("plotly_hover", function (evenement) {
        var i = indice(evenement.points[0]);
        if (i !== undefined) survoler(i, "nuage");
      });
      div.on("plotly_unhover", function () { survoler(null, "nuage"); });

      div.on("plotly_click", function (evenement) {
        var souris = evenement.event, r = div.getBoundingClientRect();
        var xa = div._fullLayout.xaxis, ya = div._fullLayout.yaxis;
        var px = souris.clientX - r.left - xa._offset, py = souris.clientY - r.top - ya._offset;
        var xy = axes(), proches = [];
        for (var i = 0; i < xy[0].length; i++) {
          var d = Math.pow(xa.l2p(xy[0][i]) - px, 2) + Math.pow(ya.l2p(xy[1][i]) - py, 2);
          if (d <= RAYON * RAYON) proches.push([d, i]);
        }
        proches.sort(function (a, b) { return a[0] - b[0]; });
        var indices = proches.slice(0, MAX_PROPOSES).map(function (p) { return p[1]; });
        if (!indices.length && indice(evenement.points[0]) !== undefined) indices = [indice(evenement.points[0])];
        proposer(indices, souris.clientX, souris.clientY, [xa.p2l(px), ya.p2l(py)]);
      });
    });
    choixX.addEventListener("change", redessiner);
    choixY.addEventListener("change", redessiner);
    champ.addEventListener("input", redessiner);
    champ.addEventListener("keydown", function (evenement) {
      if (evenement.key !== "Enter" || !marques.length || marques.length >= nuage.seuil_noms) return;
      evenement.preventDefault();
      marques.forEach(function (i) { if (nommes.indexOf(i) === -1) nommes.push(i); });
      champ.value = "";
      changer();
    });
  };
})();
