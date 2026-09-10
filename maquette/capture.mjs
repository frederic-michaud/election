// Capture d'écran d'une variante, pour en discuter par message (le PNG n'est
// jamais le support de travail : la page l'est).
//
//     node maquette/capture.mjs maquette/accueil.html accueil.png [largeur]
//
// Demande Playwright (npm i -g playwright, ou npx). Les cartes Mapbox ont
// besoin de WebGL et de vrai temps : on attend quelques secondes après le
// chargement, et on lance Chromium avec un rendu logiciel si besoin.
import { chromium } from "playwright";
import { resolve } from "node:path";

const [, , page_html = "maquette/accueil.html", sortie = "accueil.png", largeur = "1200"] = process.argv;
const navigateur = await chromium.launch({
  executablePath: process.env.CHROME || undefined,
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await navigateur.newPage({ viewport: { width: Number(largeur), height: 1200 } });
page.on("pageerror", (e) => console.error("Erreur JS :", String(e).slice(0, 200)));
await page.goto("file://" + resolve(page_html), { waitUntil: "load" });
await page.waitForTimeout(8000);
await page.screenshot({ path: sortie, fullPage: true });
await navigateur.close();
console.log(sortie);
