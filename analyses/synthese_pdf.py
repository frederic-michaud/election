"""Note de synthese PDF, assemblee a partir des figures du backtest.

    .venv/bin/python var/synthese_pdf.py var/backtest doc/synthese_backtest.pdf
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mimage  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

SOURCE = Path(sys.argv[1] if len(sys.argv) > 1 else "var/backtest")
SORTIE = Path(sys.argv[2] if len(sys.argv) > 2 else "doc/synthese_backtest.pdf")
FOND, ENCRE, GRIS = "#fcfcfb", "#0b0b0b", "#52514e"
PAGE = [0]


def apercu(figure):
    """Chaque page aussi en PNG : le PDF ne se relit pas a l'oeil ici."""
    PAGE[0] += 1
    figure.savefig(SORTIE.parent / f"apercu_page{PAGE[0]}.png", dpi=110,
                   facecolor=FOND)


def page_texte(pdf, titre, blocs):
    figure = plt.figure(figsize=(8.3, 11.7), facecolor=FOND)
    figure.text(0.08, 0.945, titre, fontsize=17, color=ENCRE, va="top")
    y = 0.885
    for genre, texte in blocs:
        if genre == "h":
            y -= 0.018
            figure.text(0.08, y, texte, fontsize=11.5, color=ENCRE, va="top")
            y -= 0.028
        elif genre == "p":
            figure.text(0.08, y, texte, fontsize=9.3, color=GRIS, va="top",
                        linespacing=1.6)
            y -= 0.0175 * (texte.count("\n") + 1) + 0.016
        elif genre == "mono":
            figure.text(0.08, y, texte, fontsize=8.2, color=ENCRE, va="top",
                        family="monospace", linespacing=1.55)
            y -= 0.0165 * (texte.count("\n") + 1) + 0.014
    apercu(figure)
    pdf.savefig(figure, facecolor=FOND)
    plt.close(figure)


def page_image(pdf, chemin, legende):
    if not chemin.exists():
        print(f"  figure absente, page sautee : {chemin}")
        return
    image = mimage.imread(chemin)
    figure = plt.figure(figsize=(11.7, 8.3), facecolor=FOND)
    axe = figure.add_axes((0.03, 0.10, 0.94, 0.85))
    axe.imshow(image)
    axe.axis("off")
    figure.text(0.03, 0.075, legende, fontsize=8.5, color=GRIS, va="top",
                linespacing=1.6)
    apercu(figure)
    pdf.savefig(figure, facecolor=FOND)
    plt.close(figure)


SORTIE.parent.mkdir(parents=True, exist_ok=True)
with PdfPages(SORTIE) as pdf:
    page_texte(pdf, "Projections de votations — où en est le modèle", [
        ("p", "Politiques.ch — note de synthèse du 17 septembre 2026.\n"
              "Backtest de 30 votations réelles (2016-2026), rejouées commune par\n"
              "commune sous 100 ordres d'arrivée calibrés sur des données cantonales."),
        ("h", "Le modèle marche, et il est sans biais"),
        ("p", "À 25 % de dépouillement, l'erreur médiane est de 0,45 point de %oui,\n"
              "contre 3,2 points pour un affichage sans extrapolation. Le gain vient de\n"
              "la correction d'un biais d'ordre : les petites communes dépouillent en\n"
              "premier, et elles ne votent pas comme les grandes.\n\n"
              "Ce biais est bien un effet d'ordre, pas une propriété du modèle : sous un\n"
              "ordre d'arrivée aléatoire, le dépouillement nu tombe de lui-même à −0,11\n"
              "point de biais et l'extrapolation à +0,02. Il n'y a donc pas de biais\n"
              "ville/campagne résiduel caché dans la méthode."),
        ("h", "Le vrai sujet est la queue, pas la moyenne"),
        ("p", "Quelques votations restent à 2-3 points pendant une bonne partie de la\n"
              "soirée. Elles ne ratent pas pour la même raison :"),
        ("mono", "  vaches à cornes 2018    R² 0,33   le modèle ne comprend pas l'objet\n"
                 "  logements 2020          R² 0,93   résidu aligné sur la taille\n"
                 "  impôt immobilier 2025   σ 5,90    dispersion sans structure"),
        ("h", "Ce qui les améliore"),
        ("mono", "  variante                              6 pires   médiane\n"
                 "  ------------------------------------  -------   -------\n"
                 "  sans extrapolation                      4,153     3,180\n"
                 "  6 axes ACP  (production)                1,385     0,445\n"
                 "  ACP pondérée par la taille              1,203     0,366\n"
                 "  6 axes + log(taille)                    0,784     0,432\n"
                 "  20 axes ACP                             0,749     0,337\n"
                 "  ACP pondérée + 20 axes + log(taille)    0,623     0,346"),
        ("p", "Le nombre de composantes est le levier principal. La troncature à 6 axes,\n"
              "et non la qualité des données, est la limite actuelle du modèle."),
    ])

    page_image(pdf, SOURCE / "oracle_six_pires.png",
               "Les six votations les plus mal projetées, à 25 % de dépouillement. Chaque "
               "barre donne l'écart au résultat final ; l'étiquette, le %oui projeté.\n"
               "La barre hachurée est une borne d'oracle — une ACP qui a vu le résultat du "
               "jour. Elle fait moins bien que plusieurs variantes honnêtes : c'est la "
               "troncature qui limite, pas le corpus.")

    page_image(pdf, SOURCE / "leviers_outliers.png",
               "Le même chiffre sous trois critères. Le classement des leviers change : "
               "l'ACP pondérée est deuxième sur la médiane des 30 objets et quatrième sur "
               "le pire cas.\nLa colonne log(taille) ne se distingue que sur la queue — "
               "c'est là qu'elle sert.")

    page_image(pdf, SOURCE / "distribution_objets.png",
               "Les 30 votations triées par difficulté. La variante riche écrase la queue "
               "de gauche — mais dégrade une dizaine d'objets faciles à droite, "
               "2021-06-13 en tête (0,77 → 1,32).\nUn modèle plus riche aide là où c'est "
               "dur et ajoute du bruit là où c'était déjà simple : c'est l'arbitrage à "
               "assumer.")

    page_texte(pdf, "Les pistes explorées", [
        ("h", "Retenu"),
        ("p", "Garder plus de composantes d'ACP, en nombre croissant avec le dépouillement.\n"
              "Pondérer l'ACP par la taille des communes : gratuit et sans risque.\n"
              "Ajouter log(électeurs) au design — sous réserve de vérifier que le premier\n"
              "affichage se fait bien vers 25 % de dépouillement."),
        ("h", "Écarté, et pourquoi"),
        ("p", "Corriger une commune par ses voisines (krigeage). Prédit très bien le résidu\n"
              "commune par commune (r = 0,42) et ne change rien au total : les résidus\n"
              "ajustés sont de somme pondérée nulle par construction, donc la correction\n"
              "transportée l'est aussi. Utile pour les cartes, pas pour la projection."),
        ("p", "Apprendre les régions par clustering plutôt qu'utiliser les cantons. Une fois\n"
              "le modèle bien spécifié, le canton fait mieux que le clustering appris. Les\n"
              "découpages officiels encodent déjà la structure : les modes de co-variation\n"
              "des résidus ont un R² de 0,73 sur le district, et la corrélation spatiale\n"
              "s'annule au-delà de 40 km."),
        ("p", "Importer les 27 colonnes OFS inutilisées — urbanisation, montagne, type de\n"
              "commune. Moins de 3 % de la variance résiduelle : l'ACP, construite sur cent\n"
              "votations, les a déjà absorbées."),
        ("h", "Un résultat négatif qui compte"),
        ("p", "Aucun indicateur ne dit, en direct, si la soirée en cours se passe mal.\n"
              "Vingt-deux métriques testées — dispersion des résidus, outliers, levier,\n"
              "jackknife par canton, sensibilités — sont toutes à |rho| ≤ 0,12 d'un ordre\n"
              "d'arrivée à l'autre. L'erreur vient de la moyenne des résidus des communes\n"
              "dépouillées, orthogonale par construction à tout ce qu'on observe.\n\n"
              "La fourchette affichée doit donc être calibrée sur l'historique des erreurs\n"
              "et modulée par objet — pas conditionnée à la soirée."),
        ("h", "Pour aller plus loin"),
        ("p", "Le détail complet — protocole, chiffres, impasses — est dans\n"
              "RESULTATS_BACKTEST.md sur la branche moteur/backtest-ordre-depouillement,\n"
              "avec les scripts d'analyse dans analyses/. Les décisions sont reprises dans\n"
              "PLAN_AMELIORATION_MODELE.md."),
    ])
print(f"{SORTIE} — {SORTIE.stat().st_size // 1024} Ko")
