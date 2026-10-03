#!/bin/bash
# Un tour de la boucle du jour de scrutin : télécharger le fichier fédéral,
# mettre à jour la base, recalculer la projection.
#
#   DATE_SCRUTIN=20260927 ./download_data.sh

set -eu

DATE_SCRUTIN="${DATE_SCRUTIN:?à définir, ex. DATE_SCRUTIN=20260927}"
# Sous ./var, donc visible à l'identique dans le conteneur (voir compose.yaml).
DOSSIER_DATA="${DOSSIER_DATA:-var/scrutins}"
# Domaine du site : en fin de tour, on y redemande les pages qui changent, pour
# que nginx les remette en cache tout de suite. Vide : pas de rafraîchissement.
DOMAINE="${DOMAINE:-}"
# Comment exécuter les commandes Django. Par défaut dans le conteneur ; pour
# tourner sans Docker, activer un venv puis MANAGE="python manage.py".
MANAGE="${MANAGE:-docker compose run --rm web python manage.py}"

URL_SCRUTIN="https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-${DATE_SCRUTIN}-eidgAbstimmung.json"

mkdir -p "${DOSSIER_DATA}"

# Chaque tour réimporte toutes les communes dépouillées : le script ne garde
# aucun état entre deux appels, ce qui permet à un timer de l'appeler. Seul
# l'amorçage doit avoir eu lieu.
if [ ! -f "${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json" ]; then
  cat >&2 <<MSG
Aucun instantané de départ dans ${DOSSIER_DATA}. Amorcer d'abord :

  curl -o ${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json "${URL_SCRUTIN}"
  ${MANAGE} add_initial_scrutin_en_cours ${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json
MSG
  exit 1
fi

COURANT="${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_$(date +%H%M%S).json"
# Le fichier peut arriver compressé le jour J : --compressed décode un
# `Content-Encoding: gzip`, gunzip rattrape un gzip servi sans cet en-tête.
curl -fsS --compressed -o "${COURANT}.partiel" "${URL_SCRUTIN}"
if gzip -t "${COURANT}.partiel" 2>/dev/null; then
  gunzip -c "${COURANT}.partiel" > "${COURANT}.json_" && mv "${COURANT}.json_" "${COURANT}.partiel"
fi

mv "${COURANT}.partiel" "${COURANT}"

echo "instantané ${COURANT}"
${MANAGE} update_scrutin_en_cours "${COURANT}"
${MANAGE} run_extrapolation

if [ -n "${DOMAINE}" ]; then
  for page in / /cartes; do
    curl -fsS -o /dev/null --max-time 120 -H "X-Rafraichir: 1" \
      --resolve "${DOMAINE}:443:127.0.0.1" "https://${DOMAINE}${page}" \
      || echo "rafraîchissement de ${page} raté : le cache se renouvellera seul" >&2
  done
fi
