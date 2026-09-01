#!/bin/bash
# Boucle du jour de scrutin : télécharger le JSON fédéral, mettre à jour la
# base, relancer l'extrapolation, puis régénérer le mirroir statique.
#
# Tout ce qui change d'un scrutin à l'autre est en haut, ou surchargeable par
# l'environnement :
#   DATE_SCRUTIN=20260927 ./download_data.sh

set -u

DATE_SCRUTIN="${DATE_SCRUTIN:?à définir, ex. DATE_SCRUTIN=20260927}"
DOSSIER_DATA="${DOSSIER_DATA:-../data}"
HOTE_DJANGO="${HOTE_DJANGO:-192.168.1.20:8000}"
DOSSIER_HTML="${DOSSIER_HTML:-/srv/html/}"
VENV="${VENV:-~/env/django/bin/activate}"
CADENCE="${CADENCE:-0}"

URL_SCRUTIN="https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-${DATE_SCRUTIN}-eidgAbstimmung.json"
PREFIXE="${DOSSIER_DATA}/votation_${DATE_SCRUTIN}"

# Avant de lancer le script, s'assurer d'avoir un instantané initial — celui
# d'avant toute donnée disponible :
#   wget "$URL_SCRUTIN" -O "${PREFIXE}_0.json"
# puis, une fois la base peuplée :
#   python manage.py add_initial_scrutin_en_cours "${PREFIXE}_0.json"

# shellcheck source=/dev/null
source "${VENV}"

i=2
while true;
do
  #récupérer les données des dépouillements partiels (stockage incrémentiel)
((i=i+1));
curl --output "${PREFIXE}_${i}.json.gz" "${URL_SCRUTIN}";

gunzip "${PREFIXE}_${i}.json.gz";

  #mettre les données récupérées ci-dessus dans la base de donnée du site
((j=i-1))
python manage.py update_scrutin_en_cours "${PREFIXE}_${j}.json" "${PREFIXE}_${i}.json"

echo "--------scrutin en cours mis à jour ---------"

  #fabriquer l'extrapolation sur la base des dépouillements partiels
python manage.py run_extrapolation
echo " ** extrapolation terminée ** "

  #copier le site dans le dossier où apache saura le trouver
wget      --recursive      --no-clobber      --page-requisites      --html-extension      --convert-links      --restrict-file-names=windows                    "${HOTE_DJANGO}"  -P politiques

echo "!!!! site téléchargé !!!!";

cp -r "politiques/${HOTE_DJANGO/:/+}"/* "${DOSSIER_HTML}"
echo "** ** **"

sleep "${CADENCE}";
done
