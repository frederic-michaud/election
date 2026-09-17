# Checklist d'un dimanche de votation

À dérouler dans l'ordre. `DEPLOIEMENT.md` explique *pourquoi* chaque commande
existe et comment monter la machine ; ce fichier-ci ne dit que *quoi faire*, le
jour venu, sur une machine déjà en service.

Toutes les commandes se lancent depuis le dépôt de production
(`WorkingDirectory` du service systemd).

```bash
DATE=20260927        # la date du scrutin, partout ci-dessous
```

---

## J-7 — répétition générale

- [ ] **Le fichier fédéral du scrutin est publié.** Il apparaît une à deux
      semaines avant, avec ses objets et ses communes, mais tous les résultats
      à `null`.
      ```bash
      curl -fsS -o "var/scrutins/votation_${DATE}_0.json" \
        "https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-${DATE}-eidgAbstimmung.json"
      ```
      Un 403 ou un 404 signifie qu'il n'est pas encore là — réessayer le
      lendemain. Vérifier ensuite le nombre d'objets, qui commande tout le
      reste :
      ```bash
      python3 -c "
      import json; d=json.load(open('var/scrutins/votation_${DATE}_0.json'))
      for o in d['schweiz']['vorlagen']: print(o['vorlagenId'], o['vorlagenTitel'][1]['text'][:70])"
      ```

- [ ] **Rejouer une soirée entière** sur une copie de la base :
      ```bash
      DATE_SCRUTIN=$DATE ./deploiement/repetition_generale.sh
      ```
      Attendu : l'avance monte à chaque tour jusqu'à 100 %, la projection reste
      dans [0 %, 100 %] et rejoint le confirmé au dernier tour. Les résultats
      rejoués viennent d'anciennes votations : le %oui n'a aucun sens
      politique, seule la mécanique est testée.

- [ ] **Les deux pages du menu répondent** (Méthodes, Contact) : le pipeline
      réel ne les crée pas, et un menu vide donne des onglets en 404.

## J-1 — amorçage

- [ ] **Sauvegarder la base**, avant que la soirée la réécrive toutes les cinq
      minutes. L'historique est le bien précieux : il se reconstruit en deux
      minutes, une soirée de dépouillement non.
      ```bash
      tar czf "sauvegarde-$(date +%F).tar.gz" var/
      ```

- [ ] **Semer les lignes vides du scrutin.** Cette commande supprime celles du
      scrutin précédent : la page d'accueil passe au prochain objet, sans
      projection, avec la mention « Projection dès les premiers résultats ».
      ```bash
      docker compose run --rm web python manage.py add_initial_scrutin_en_cours \
        "var/scrutins/votation_${DATE}_0.json"
      ```

- [ ] **La page d'accueil s'affiche** avec les nouveaux objets, sans projection
      et sans trace du scrutin précédent.

- [ ] **La date est à jour aux deux endroits** — c'est le piège de cette
      checklist, les deux fichiers ne la portent pas au même titre :
      `DATE_SCRUTIN=` dans `politiques-scrutin.service` (l'URL téléchargée) et
      `OnCalendar=` dans `politiques-scrutin.timer` (le jour où les tours ont
      lieu). Une seule des deux corrigée, et le timer tourne dans le vide ou ne
      part jamais.

      Les deux ne s'écrivent pas pareil — `20260927` contre `2026-09-27` —
      donc un `sed` sur la date manquerait le timer sans rien signaler. D'où
      deux remplacements ancrés sur le nom du réglage :
      ```bash
      sudo sed -i "s|^Environment=DATE_SCRUTIN=.*|Environment=DATE_SCRUTIN=$DATE|" \
        /etc/systemd/system/politiques-scrutin.service
      sudo sed -i "s|^OnCalendar=.*|OnCalendar=$(date -d "$DATE" +%F) *:0/5|" \
        /etc/systemd/system/politiques-scrutin.timer
      sudo systemctl daemon-reload
      grep -H "DATE_SCRUTIN\|OnCalendar" /etc/systemd/system/politiques-scrutin.*
      ```

- [ ] **Armer le timer, puis lancer un tour à blanc.** L'armement seul ne
      déclenche rien : `OnCalendar` attend le dimanche, et une erreur de
      `User=`, de `WorkingDirectory=` ou de droits Docker resterait invisible
      jusqu'à midi. Un tour lancé à la main éprouve l'unité entière.
      ```bash
      sudo systemctl enable --now politiques-scrutin.timer
      systemctl list-timers politiques-scrutin.timer    # doit annoncer le dimanche
      sudo systemctl start politiques-scrutin.service   # le tour à blanc
      journalctl -u politiques-scrutin.service -n 30 --no-pager
      ```
      Attendu : un instantané téléchargé, zéro nouvelle commune, et
      « pas de projection » — le fichier fédéral est encore vide.

      **Armer après l'amorçage**, jamais avant : sans instantané de départ,
      chaque tour échoue en rappelant les commandes d'amorçage.

- [ ] **Les communes sans profil ACP sont connues et peu nombreuses.** À faire
      ici, une fois les lignes du scrutin semées — au J-7 la requête lit encore
      celles du scrutin précédent et ne verrait pas une commune qui s'est mise
      à publier séparément, le cas même qu'elle surveille. Ces communes ne font
      plus tomber la projection — elles sont projetées avec le profil moyen de
      leur district — mais une envolée du nombre signale un décrochage de
      l'appariement OFS.
      ```bash
      docker compose run --rm web python manage.py shell -c "
      from scrutin.models import ResultatCommunalEnCours
      from pca.models import PCAResult
      sans = ResultatCommunalEnCours.objects.exclude(commune__in=PCAResult.objects.values('commune'))
      print(sorted(set(sans.values_list('commune__nom', flat=True))))"
      ```
      En septembre 2026 : `Jaberg` et `Rüti bei Lyssach`.

- [ ] **Effacer les traces de la répétition**, pour ne pas les confondre avec
      les vrais instantanés du dimanche :
      ```bash
      rm -f var/repetition.sqlite3 var/scrutins/repetition/*.json
      ```
      Ne pas toucher à `votation_${DATE}_0.json` : c'est la référence du
      premier tour.

## Le dimanche

- [ ] **Vers 12 h 10**, après le premier tour du timer, vérifier qu'il a tourné :
      ```bash
      journalctl -u politiques-scrutin.service --since "1 hour ago"
      ```
      Attendu : un instantané téléchargé, un nombre de nouvelles communes, puis
      la projection. Tant qu'il y a moins de sept communes dépouillées,
      `run_extrapolation` note « pas de projection » et n'écrit rien — c'est
      normal en début de soirée.

- [ ] **Contrôle visuel de la page d'accueil** : projection plausible, avance
      cohérente avec l'heure, cartes remplies, pas de trace d'erreur Django.

- [ ] **Une sauvegarde pendant la soirée**, vers le milieu du dépouillement.

- [ ] **Le lundi**, désarmer le timer. `OnCalendar=` porte une date fixe, donc
      il ne repartira pas tout seul — mais laissé armé, il masque le fait que
      la date devra être changée au prochain scrutin :
      ```bash
      sudo systemctl disable --now politiques-scrutin.timer
      ```

## Si ça casse

| symptôme | cause la plus probable |
|---|---|
| le service échoue toutes les cinq minutes | pas d'instantané de départ sous `var/scrutins` — rejouer l'amorçage du J-1 |
| le timer n'annonce aucun prochain tour | `OnCalendar=` est resté sur la date du scrutin précédent — un `sed` sur `20260927` ne l'atteint pas, il l'écrit `2026-09-27` |
| 404 au téléchargement | `DATE_SCRUTIN=` dans le `.service` ne correspond pas au fichier publié |
| la projection ne bouge pas d'un tour à l'autre | aucune commune nouvellement dépouillée **pour tous les objets** : une commune n'est reprise que lorsqu'elle est rentrée partout |
| le site répond mais sans CSS ni logo | `collectstatic` ou whitenoise — reconstruire l'image |
| page lente au premier appel | `--preload` absent de la commande gunicorn |

Un tour à la main, sans attendre le timer :

```bash
DATE_SCRUTIN=$DATE ./download_data.sh
```
