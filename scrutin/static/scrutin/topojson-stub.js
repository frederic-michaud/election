// Le fond de carte mondial, en trompe-l'œil.
//
// Les cartes en projection SVG (`px.choropleth`) réclament à plotly.js un
// fichier topojson, qu'il va chercher sur cdn.plot.ly. La requête échoue en
// `file://` — d'où des cartes vides — et casserait de toute façon le miroir
// statique hors-ligne. Or nos cartes n'en affichent rien : `geo.visible` est
// à `false`, seuls les contours communaux sont dessinés, et ceux-là voyagent
// avec la figure.
//
// plotly.js consulte son cache `window.PlotlyGeoAssets.topojson` avant de
// télécharger : on y dépose une topologie vide, et il ne sort pas sur le
// réseau. À reprendre côté site si la carte SVG est retenue (Partie 7.2).
window.PlotlyGeoAssets = window.PlotlyGeoAssets || {};
window.PlotlyGeoAssets.topojson = window.PlotlyGeoAssets.topojson || {};

const COUCHES = ["coastlines", "land", "ocean", "lakes", "rivers", "countries", "subunits"];

for (const nom of ["world_110m", "world_50m"]) {
  const objets = {};
  for (const couche of COUCHES) objets[couche] = { type: "GeometryCollection", geometries: [] };
  window.PlotlyGeoAssets.topojson[nom] = {
    type: "Topology",
    transform: { scale: [1, 1], translate: [0, 0] },
    objects: objets,
    arcs: [],
    bbox: [-180, -90, 180, 90],
  };
}
