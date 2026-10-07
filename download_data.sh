#!/bin/bash
# Le jour de scrutin : à chaque nouvelle version du fichier fédéral, mettre à
# jour la base, recalculer la projection et rafraîchir l'accueil.
#
#   DATE_SCRUTIN=20260927 ./download_data.sh            # un tour
#   DATE_SCRUTIN=20260927 ./download_data.sh --suivre   # la boucle du service

set -eu

DATE_SCRUTIN="${DATE_SCRUTIN:?à définir, ex. DATE_SCRUTIN=20260927}"
# Sous ./var, donc visible à l'identique dans le conteneur (voir compose.yaml).
DOSSIER_DATA="${DOSSIER_DATA:-var/scrutins}"
# Domaine du site : en fin de tour, on y redemande l'accueil, pour que nginx
# le remette en cache tout de suite. Vide : pas de rafraîchissement.
DOMAINE="${DOMAINE:-}"
# Comment exécuter les commandes Django. Par défaut dans le conteneur du site,
# déjà lancé : 2 s par commande, contre 12 s pour en démarrer un. Pour tourner
# sans Docker, activer un venv puis MANAGE="python manage.py".
MANAGE="${MANAGE:-docker compose exec -T web python manage.py}"
# Interroger ne coûte qu'une réponse vide (304) tant que le fichier n'a pas
# changé ; importer occupe la machine, d'où le délai minimal entre deux imports.
INTERROGATION="${INTERROGATION:-15}"
PLANCHER="${PLANCHER:-120}"

URL_SCRUTIN="${URL_SCRUTIN:-https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-${DATE_SCRUTIN}-eidgAbstimmung.json}"
# Empreinte (ETag) de la dernière version importée.
ETAG="${DOSSIER_DATA}/etag_${DATE_SCRUTIN}.txt"

mkdir -p "${DOSSIER_DATA}"

# Chaque tour réimporte toutes les communes dépouillées. Seul l'amorçage doit
# avoir eu lieu.
if [ ! -f "${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json" ]; then
  cat >&2 <<MSG
Aucun instantané de départ dans ${DOSSIER_DATA}. Amorcer d'abord :

  curl -o ${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json "${URL_SCRUTIN}"
  ${MANAGE} add_initial_scrutin_en_cours ${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_0.json
MSG
  exit 1
fi

# 0 : nouvelle version importée ; 1 : rien de neuf ; 2 : échec.
tour() {
  local courant code
  courant="${DOSSIER_DATA}/votation_${DATE_SCRUTIN}_$(date +%H%M%S).json"
  # Le fichier n'est envoyé que si son empreinte a changé. L'empreinte n'est
  # retenue qu'une fois l'import réussi : sinon le tour suivant recevrait un
  # 304 et cette version ne serait jamais importée.
  code=$(curl -fsS --compressed -w '%{http_code}' -o "${courant}.partiel" \
           --etag-compare "${ETAG}" --etag-save "${ETAG}.nouveau" "${URL_SCRUTIN}") || return 2
  [ "${code}" = 304 ] && return 1
  # --compressed décode un `Content-Encoding: gzip` ; gunzip rattrape un gzip
  # servi sans cet en-tête.
  if gzip -t "${courant}.partiel" 2>/dev/null; then
    gunzip -c "${courant}.partiel" > "${courant}.json_" && mv "${courant}.json_" "${courant}.partiel"
  fi
  mv "${courant}.partiel" "${courant}"

  echo "instantané ${courant}"
  ${MANAGE} update_scrutin_en_cours "${courant}" || return 2
  ${MANAGE} run_extrapolation || return 2
  # La page des erreurs de saisie ne doit pas bloquer la projection.
  ${MANAGE} detecter_anomalies || echo "détection des anomalies ratée" >&2
  mv "${ETAG}.nouveau" "${ETAG}"

  if [ -n "${DOMAINE}" ]; then
    curl -fsS -o /dev/null --max-time 120 -H "X-Rafraichir: 1" \
      --resolve "${DOMAINE}:443:127.0.0.1" "https://${DOMAINE}/" \
      || echo "rafraîchissement de l'accueil raté : le cache se renouvellera seul" >&2
  fi
}

if [ "${1:-}" != "--suivre" ]; then
  statut=0
  tour || statut=$?
  [ "${statut}" = 1 ] && echo "fichier inchangé depuis le dernier import"
  [ "${statut}" != 2 ]
  exit
fi

while true; do
  statut=0
  tour || statut=$?
  case "${statut}" in
    1) sleep "${INTERROGATION}" ;;
    2) echo "tour raté, nouvel essai dans ${PLANCHER} s" >&2; sleep "${PLANCHER}" ;;
    *) sleep "${PLANCHER}" ;;
  esac
done
