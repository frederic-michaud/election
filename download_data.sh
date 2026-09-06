#!/bin/bash
# Un tour de la boucle du jour de scrutin : télécharger le fichier fédéral,
# mettre à jour la base, recalculer la projection.
#
#   DATE_SCRUTIN=20260927 ./download_data.sh
#
# Le script ne boucle plus et n'aspire plus le site : il fait une passe et rend
# la main. C'est `deploiement/politiques-scrutin.timer` qui le rappelle toutes
# les cinq minutes, et nginx qui encaisse le trafic
# (`deploiement/nginx-politiques.conf`).

set -eu

DATE_SCRUTIN="${DATE_SCRUTIN:?à définir, ex. DATE_SCRUTIN=20260927}"
# Sous ./var, donc visible à l'identique dans le conteneur (voir compose.yaml).
DOSSIER_DATA="${DOSSIER_DATA:-var/scrutins}"
# Comment exécuter les commandes Django. Par défaut dans le conteneur ; pour
# tourner sans Docker, activer un venv puis MANAGE="python manage.py".
MANAGE="${MANAGE:-docker compose run --rm web python manage.py}"

URL_SCRUTIN="https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-${DATE_SCRUTIN}-eidgAbstimmung.json"

mkdir -p "${DOSSIER_DATA}"

# L'instantané le plus récent sert de référence : `update_scrutin_en_cours` ne
# réimporte que les communes dépouillées depuis lui. Le script ne garde donc
# aucun état entre deux appels, ce qui permet à un timer de l'appeler.
PRECEDENT=$(ls -1t "${DOSSIER_DATA}"/votation_"${DATE_SCRUTIN}"_*.json 2>/dev/null | head -1 || true)
if [ -z "${PRECEDENT}" ]; then
  cat >&2 <<MSG
Aucun instantané de départ dans ${DOSSIER_DATA}. Amorcer d'abord :

  curl -o ${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json "${URL_SCRUTIN}"
  ${MANAGE} add_initial_scrutin_en_cours ${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json
MSG
  exit 1
fi

# Téléchargement sous un nom temporaire : un fichier tronqué ou une page
# d'erreur ne doit pas devenir la référence du tour suivant.
COURANT="${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_$(date +%H%M%S).json"
curl -fsS -o "${COURANT}.partiel" "${URL_SCRUTIN}"
mv "${COURANT}.partiel" "${COURANT}"

echo "instantané ${COURANT}, précédent ${PRECEDENT}"
${MANAGE} update_scrutin_en_cours "${PRECEDENT}" "${COURANT}"
${MANAGE} run_extrapolation
