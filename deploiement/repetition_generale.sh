#!/bin/bash
# Répétition générale : rejouer une soirée entière de dépouillement, sur une
# copie de la base, avant le vrai dimanche.
#
#   DATE_SCRUTIN=20260927 ./deploiement/repetition_generale.sh
#
# Ce que ça met à l'épreuve, et qu'aucun test ne couvre : les deux imports du
# jour J qui s'enchaînent sur le fichier réel du scrutin à venir, avec ses
# objets et ses communes à lui, et la projection qui sort un nombre plausible
# à chaque tour. Les résultats rejoués sont ceux d'anciennes votations, donc
# le %oui final n'a aucun sens politique : ce qui compte est que la suite
# converge sans planter et sans trou.
#
# Compter une dizaine de minutes : chaque commande démarre son conteneur.

set -eu

DATE_SCRUTIN="${DATE_SCRUTIN:?à définir, ex. DATE_SCRUTIN=20260927}"
DOSSIER_DATA="${DOSSIER_DATA:-var/scrutins}"
# Un tour par valeur. Les instantanés sont emboîtés (voir la docstring de
# create_fake_json_input), donc une commune dépouillée le reste.
FRACTIONS="${FRACTIONS:-0.05 0.15 0.25 0.50 0.80 1.00}"

BASE="${BASE:-var/votation.sqlite3}"
COPIE="var/repetition.sqlite3"
# Tout tourne sur la copie : la base réelle n'est jamais ouverte en écriture.
# Comme download_data.sh, par défaut dans le conteneur ; pour tourner sans
# Docker, activer un venv puis MANAGE="python manage.py".
MANAGE="${MANAGE:-docker compose run --rm -e DB_PATH=/app/${COPIE} web python manage.py}"
export DB_PATH="${DB_PATH:-${COPIE}}"

GRAINE="${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json"
DOSSIER_REPET="${DOSSIER_DATA}/repetition"

if [ ! -f "${GRAINE}" ]; then
  echo "instantané de départ absent : ${GRAINE} — amorcer d'abord (§ 7 de DEPLOIEMENT.md)" >&2
  exit 1
fi

# VACUUM INTO et non `cp` : sûr même si un tour du timer écrit au même moment.
echo "== copie de la base vers ${COPIE}"
rm -f "${COPIE}"
python3 - "${BASE}" "${COPIE}" <<'PY'
import sqlite3
import sys

source, copie = sys.argv[1], sys.argv[2]
connexion = sqlite3.connect(source)
connexion.execute("VACUUM INTO ?", (copie,))
connexion.close()
PY

mkdir -p "${DOSSIER_REPET}"
rm -f "${DOSSIER_REPET}"/*.json

echo "== amorçage : lignes vides du scrutin"
${MANAGE} add_initial_scrutin_en_cours "${GRAINE}"

PRECEDENT="${GRAINE}"
for fraction in ${FRACTIONS}; do
  COURANT="${DOSSIER_REPET}/depouille_${fraction}.json"
  echo "== tour à ${fraction} de dépouillement"
  ${MANAGE} create_fake_json_input "${GRAINE}" "${COURANT}" --fraction "${fraction}"
  ${MANAGE} update_scrutin_en_cours "${PRECEDENT}" "${COURANT}"
  ${MANAGE} run_extrapolation
  ${MANAGE} shell -c "
from scrutin.models import Extrapolation, SujetVote
for sujet in SujetVote.objects.filter(date=SujetVote.objects.latest('date').date):
    e = Extrapolation.objects.filter(sujet_vote=sujet).order_by('moment_creation').last()
    if e is None:
        print(f'  {sujet.nom[:45]:45} pas encore de projection')
    else:
        print(f'  {sujet.nom[:45]:45} avance {e.avance:6.1%}  confirmé {e.pourcentage_oui_connu:6.1%}  projeté {e.pourcentage_oui_extrapole:6.1%}')
"
  PRECEDENT="${COURANT}"
done

cat <<MSG

== répétition terminée
La copie ${COPIE} et les instantanés ${DOSSIER_REPET}/ sont conservés pour
inspection. À relire avant de conclure :
  - l'avance monte-t-elle à chaque tour, jusqu'à ~100 % ?
  - la projection reste-t-elle dans [0 %, 100 %] et se rapproche-t-elle du
    confirmé à mesure que l'avance monte ?
  - update_scrutin_en_cours a-t-il signalé des communes introuvables ?
Puis effacer : rm -f ${COPIE} ${DOSSIER_REPET}/*.json
MSG
