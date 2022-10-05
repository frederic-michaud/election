#!/bin/bash

#avant de lancer le scipt, s'assurer d'avoir un fichier de données vides en exécutant
#wget https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-20220925-eidgAbstimmung.json -O data/votation_septembre_2022_0.json;
# AVANT QU'IL N'Y AIT LA MOINDRE DONNEE DISPONIBLE


#lancer django pour pouvoir activer les scripts
source ~/env/django/bin/activate

#lancer la boucle qui va mettre à jour le site, le jour des votations.
i=2
while true;
do
  #récupérer les données des dépouillements partiels (stockage incrémentiel)
((i=i+1));
curl --output ../data/votation_septembre_2022_${i}.json.gz https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-20220925-eidgAbstimmung.json;

gunzip ../data/votation_septembre_2022_${i}.json.gz;

  #mettre les données récupérées ci-dessus dans la base de donnée du site
((j=i-1))
python manage.py runscript update_scrutin_en_cours --script-args ../data/votation_septembre_2022_${i}.json ../data/votation_septembre_2022_${j}.json

#python manage.py runscript update_scrutin_en_cours --script-args ../data/votation_septembre_2022_1.json json_fake.json

echo "--------scrutin en cours mis à jour ---------"

  #fabriquer l'extrapolation sur la base des dépouillements partiels
python manage.py runscript run_extrapolation
echo " ** extrapolation terminée ** "
#sleep 500;

  #copier le site dans le dossier où apache saura le trouver
wget      --recursive      --no-clobber      --page-requisites      --html-extension      --convert-links      --restrict-file-names=windows                    192.168.1.20:8000  -P politiques

echo "!!!! site téléchargé !!!!";

cp -r politiques/192.168.1.20+8000/* /srv/html/
echo "** ** **"

done
