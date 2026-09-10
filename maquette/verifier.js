// Dit à voix haute ce qui manque, plutôt que d'afficher une page vide.
//
// `figures.js` et `plotly.min.js` sont **générés** (donc absents d'un clone
// frais). Sans eux, la page s'arrête à la première ligne de son script et ne
// montre qu'un cadre vide, sans rien expliquer — le symptôme le plus courant
// de cette maquette. Ce fichier le transforme en message lisible.
(function () {
  const MANQUES = [
    [() => typeof window.Plotly !== "undefined", "plotly.min.js", "la bibliothèque de graphes"],
    [() => typeof window.VUE !== "undefined", "figures.js", "les données et les figures"],
  ];

  function banniere(absents) {
    const el = document.createElement("div");
    el.setAttribute("role", "alert");
    el.style.cssText = [
      "position:relative;z-index:9999",
      "margin:16px;padding:18px 20px",
      "border:1px solid #e0b400;border-left:5px solid #e0b400;border-radius:8px",
      "background:#fffbe8;color:#3a3320",
      "font:15px/1.6 system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif",
    ].join(";");
    const liste = absents.map(([f, r]) => `<li><code>maquette/${f}</code> — ${r}</li>`).join("");
    el.innerHTML = `
      <strong style="display:block;margin-bottom:8px;font-size:1.05rem">
        Maquette incomplète : il manque les fichiers générés.</strong>
      <p style="margin:0 0 10px">Cette page est vide parce que ceci n'a pas été trouvé :</p>
      <ul style="margin:0 0 12px;padding-left:22px">${liste}</ul>
      <p style="margin:0 0 8px">Ils ne sont pas versionnés : on les fabrique depuis la base
      fictive, avec le code du site. Depuis la racine du dépôt, sur la branche
      <code>maquette</code> :</p>
      <pre style="margin:0 0 10px;padding:12px 14px;background:#fff;border:1px solid #ece3bd;
        border-radius:6px;overflow-x:auto;font-size:13px">python manage.py migrate
python manage.py peupler_demo
python maquette/construire.py</pre>
      <p style="margin:0;font-size:.9rem;color:#6b6450">Puis recharger cette page.
      Détail dans <code>maquette/README.md</code>.</p>`;
    document.body.insertBefore(el, document.body.firstChild);
  }

  // `true` si la page peut se dessiner. Chaque variante s'arrête sinon.
  window.maquettePrete = function () {
    const absents = MANQUES.filter(([present]) => !present()).map(([, f, r]) => [f, r]);
    if (absents.length) {
      banniere(absents);
      return false;
    }
    return true;
  };
})();
