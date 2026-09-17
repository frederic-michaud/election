"""RESULTATS_BACKTEST.md -> une page HTML lisible sur grand ecran, figures incluses.

Convertisseur minimal : le rapport n'utilise que titres, paragraphes, listes,
tableaux GFM, gras, code et blocs. Pas de dependance.
"""
import html
import re
import sys
from pathlib import Path

CSS = """
:root { color-scheme: light dark; }
body { margin: 0 auto; max-width: 62rem; padding: 2.5rem 1.5rem 6rem;
       font: 16.5px/1.65 -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
       color: #1a1a1a; background: #fdfdfc; }
h1 { font-size: 2.1rem; line-height: 1.2; margin: 0 0 .2em; }
h2 { font-size: 1.45rem; margin: 2.6em 0 .6em; padding-top: .5em;
     border-top: 1px solid #e3e1dc; }
h3 { font-size: 1.12rem; margin: 2em 0 .5em; color: #333; }
p, li { max-width: 46rem; }
code { background: #f0efec; padding: .12em .35em; border-radius: 3px;
       font-size: .88em; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
pre { background: #f5f4f1; border: 1px solid #e3e1dc; border-radius: 6px;
      padding: .9rem 1.1rem; overflow-x: auto; }
pre code { background: none; padding: 0; font-size: .85em; }
table { border-collapse: collapse; margin: 1.3em 0; font-size: .92em; }
th, td { border-bottom: 1px solid #e3e1dc; padding: .4em .85em; text-align: right; }
th:first-child, td:first-child { text-align: left; }
thead th { border-bottom: 2px solid #c9c6bf; font-weight: 600; white-space: nowrap; }
tbody tr:hover { background: #f6f5f2; }
hr { border: none; border-top: 1px solid #e3e1dc; margin: 2.5em 0; }
figure { margin: 2em 0; }
figure img { width: 100%; border: 1px solid #e3e1dc; border-radius: 6px; background: #fff; }
figcaption { font-size: .86rem; color: #5a574f; margin-top: .5em; }
.galerie { display: grid; grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr));
           gap: 1.5rem; margin-top: 1.5rem; }
.galerie figure { margin: 0; }
.galerie figcaption { font-size: .8rem; }
a { color: #1f5fa8; }
.chapeau { color: #5a574f; font-size: .95rem; margin-bottom: 2.5rem; }
@media (prefers-color-scheme: dark) {
  body { color: #e6e4df; background: #17171a; }
  h3 { color: #cfccc5; }
  code, pre { background: #232327; } pre { border-color: #34343a; }
  th, td { border-color: #34343a; } thead th { border-color: #4a4a52; }
  tbody tr:hover { background: #1e1e22; }
  hr, figure img { border-color: #34343a; }
  figcaption, .chapeau { color: #a5a29b; }
  a { color: #77aaee; }
}
"""


def enligne(texte):
    texte = html.escape(texte)
    texte = re.sub(r"`([^`]+)`", r"<code>\1</code>", texte)
    texte = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", texte)
    texte = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<em>\1</em>", texte)
    texte = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', texte)
    return texte.replace("\\|", "|")


def convertir(markdown):
    sortie, lignes, i = [], markdown.split("\n"), 0
    while i < len(lignes):
        ligne = lignes[i]
        if ligne.startswith("```"):
            bloc = []
            i += 1
            while i < len(lignes) and not lignes[i].startswith("```"):
                bloc.append(html.escape(lignes[i]))
                i += 1
            sortie.append("<pre><code>" + "\n".join(bloc) + "</code></pre>")
        elif ligne.startswith("|"):
            table = []
            while i < len(lignes) and lignes[i].startswith("|"):
                table.append(lignes[i])
                i += 1
            i -= 1
            # Un \| dans une cellule (|erreur|) ne doit pas couper la colonne.
            cellules = [[c.strip().replace("\x00", "\\|")
                         for c in r.strip("|").replace("\\|", "\x00").split("|")]
                        for r in table]
            corps = [r for r in cellules[1:] if not set("".join(r)) <= set("-: ")]
            sortie.append("<table><thead><tr>"
                          + "".join(f"<th>{enligne(c)}</th>" for c in cellules[0])
                          + "</tr></thead><tbody>"
                          + "".join("<tr>" + "".join(f"<td>{enligne(c)}</td>" for c in r)
                                    + "</tr>" for r in corps)
                          + "</tbody></table>")
        elif re.match(r"^\s*(\d+\.|[-*])\s", ligne):
            items, balise = [], "ol" if re.match(r"^\s*\d+\.", ligne) else "ul"
            while i < len(lignes) and re.match(r"^\s*(\d+\.|[-*])\s", lignes[i]):
                item = [re.sub(r"^\s*(\d+\.|[-*])\s+", "", lignes[i])]
                i += 1
                while i < len(lignes) and lignes[i].startswith("  ") and lignes[i].strip():
                    item.append(lignes[i].strip())
                    i += 1
                items.append(" ".join(item))
            i -= 1
            sortie.append(f"<{balise}>"
                          + "".join(f"<li>{enligne(x)}</li>" for x in items)
                          + f"</{balise}>")
        elif ligne.startswith("#"):
            niveau = len(ligne) - len(ligne.lstrip("#"))
            sortie.append(f"<h{niveau}>{enligne(ligne.lstrip('# '))}</h{niveau}>")
        elif ligne.strip() == "---":
            sortie.append("<hr>")
        elif ligne.strip():
            para = []
            while i < len(lignes) and lignes[i].strip() and not re.match(
                    r"^(#|\||```|\s*(\d+\.|[-*])\s|---\s*$)", lignes[i]):
                para.append(lignes[i].strip())
                i += 1
            i -= 1
            sortie.append("<p>" + enligne(" ".join(para)) + "</p>")
        i += 1
    return "\n".join(sortie)


def galerie(figures):
    if not figures:
        return ""
    blocs = "".join(
        f'<figure><a href="{png.replace(".png", ".pdf")}">'
        f'<img src="{png}" alt="{html.escape(titre)}" loading="lazy"></a>'
        f'<figcaption>{html.escape(titre)} — <a href="{png.replace(".png", ".pdf")}">PDF</a>'
        f'</figcaption></figure>' for png, titre in figures)
    return f'<div class="galerie">{blocs}</div>'


def main():
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    corps = convertir(source.read_text())

    grandes = [("biais_agrege.png", "Biais signé agrégé sur les 30 objets, run multi-scénarios"),
               ("mecanisme.png", "Le mécanisme : trancher sur le %oui ou sur le profil"),
               ("variance_acp.png", "Éboulis de la variance expliquée par l'ACP")]
    figures = "".join(
        f'<figure><a href="{png.replace(".png", ".pdf")}">'
        f'<img src="{png}" alt="{html.escape(t)}" loading="lazy"></a>'
        f'<figcaption>{html.escape(t)} — <a href="{png.replace(".png", ".pdf")}">PDF</a>'
        f'</figcaption></figure>'
        for png, t in grandes if (destination.parent / png).exists())

    runs = [("realiste_r",
             "Ordre réaliste, les 30 objets",
             "Panneau haut : %oui projeté (trait) et dépouillement nu (tirets), bande = "
             "95 % des 100 tirages. Panneau bas : r de Pearson entre %oui prédit et réel "
             "— plein sur les communes dépouillées, pointillé sur les restantes."),
            ("aleatoire",
             "Ordre aléatoire (témoin), les 30 objets",
             "Permutation uniforme des communes : aucune structure ville/campagne. "
             "%oui projeté (trait) et dépouillement nu (tirets), bandes = 95 % des "
             "100 tirages.")]
    sections = []
    for dossier, titre, chapeau in runs:
        chemin = destination.parent / dossier
        noms = sorted(p.name for p in chemin.glob("objet_*.png")) if chemin.exists() else []
        if not noms:
            continue
        recap = f"{dossier}/recapitulatif.png"
        grand = (f'<figure><a href="{recap.replace(".png", ".pdf")}">'
                 f'<img src="{recap}" alt="récapitulatif" loading="lazy"></a>'
                 f'<figcaption>Récapitulatif — {html.escape(titre.lower())} — '
                 f'<a href="{recap.replace(".png", ".pdf")}">PDF</a></figcaption></figure>'
                 if (destination.parent / recap).exists() else "")
        sections.append(
            f"<h3>{html.escape(titre)}</h3>"
            f'<p class="chapeau">{chapeau} Cliquer une figure pour le PDF vectoriel.</p>'
            + grand
            + galerie([(f"{dossier}/{n}",
                        n.replace("objet_", "objet ").replace(".png", ""))
                       for n in noms]))
    par_objet = "\n".join(sections)

    destination.write_text(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Backtest de l'extrapolation — Politiques.ch</title>
<style>{CSS}</style></head><body>
{corps}
<h2>Figures</h2>
{figures}
{par_objet}
</body></html>""")
    print(f"{destination} — {len(sections)} galerie(s)")


main()
