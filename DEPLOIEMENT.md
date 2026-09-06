# Déployer le site sur une machine neuve

Pas à pas, depuis un serveur où **seul Ubuntu Server est installé**. Chaque
commande a été exécutée telle quelle ; les durées indiquées viennent d'une
machine à un cœur et 2 Go de mémoire.

Compter **une quinzaine de minutes**, dont dix d'attente.

---

## 1. Ce qu'il faut avant de commencer

- Une machine sous Ubuntu Server, avec un compte disposant de `sudo`.
- Un accès réseau sortant : le serveur télécharge l'historique des votations
  chez l'Office fédéral de la statistique.
- Pour un site public : un nom de domaine pointant sur l'adresse IP de la
  machine. Pour un simple essai, ce n'est pas nécessaire.

## 2. Installer Docker

**Attention au nom du paquet.** `apt install docker` installe `wmdocker`, une
applet de barre système qui n'a rien à voir. Le bon paquet est `docker.io`.

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
```

Se donner le droit d'utiliser Docker sans `sudo`, puis **ouvrir une nouvelle
session** pour que l'appartenance au groupe prenne effet :

```bash
sudo usermod -aG docker "$USER"
newgrp docker          # ou se déconnecter et se reconnecter
docker run --rm hello-world
```

La dernière commande doit afficher un message de bienvenue. Si elle répond
« permission denied », la nouvelle session n'a pas été ouverte.

## 3. Récupérer le code

```bash
git clone https://github.com/frederic-michaud/election.git
cd election
```

Toutes les commandes qui suivent se lancent **depuis ce dossier** : c'est là que
Docker trouve `compose.yaml`.

## 4. Écrire la configuration

Le fichier `.env` n'est pas versionné, il faut le créer. Trois valeurs suffisent.

```bash
cat > .env <<EOF
DEBUG=0
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
ALLOWED_HOSTS=localhost,127.0.0.1,politiques.ch
EOF
```

Remplacer `politiques.ch` par votre nom de domaine. Django **refuse** toute
requête dont l'en-tête `Host` n'est pas dans cette liste : un oubli ici se
traduit par une erreur 400 au premier essai depuis un navigateur.

## 5. Construire l'image et démarrer

```bash
docker compose up -d --build
```

Cinq minutes la première fois, le temps d'installer scipy et scikit-learn.
Les fois suivantes, quelques secondes.

Vérifier que le conteneur tourne :

```bash
docker compose ps
curl -I http://127.0.0.1:8000/
```

Le port n'est publié que sur `127.0.0.1` : le site n'est pas encore visible de
l'extérieur, c'est voulu. Si le port 8000 est déjà pris sur la machine, ajouter
`PORT_WEB=8001` dans `.env` et relancer `docker compose up -d`.

## 6. Remplir la base

La base est un simple fichier SQLite, dans `./var`. **Partir d'une base vide** :
une base créée avant septembre 2026 n'a pas le bon schéma et les imports
échoueront.

### Pour vérifier que tout marche : la base de démonstration

```bash
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py peupler_demo
curl -s http://127.0.0.1:8000/ | grep -o "<title>.*</title>"
```

Une base fictive à l'échelle réelle, en quelques secondes, sans réseau. Si le
titre s'affiche, l'installation est bonne.

### Pour de vrai : les données officielles

Six commandes, **dans cet ordre**, chacune dépendant de la précédente.

```bash
docker compose run --rm web python manage.py migrate                    #  7 s
docker compose run --rm web python manage.py populate_commune           #  1 min
docker compose run --rm web python manage.py import_metadata_commune    # 30 s
docker compose run --rm web python manage.py importer_historique        #  2 min
docker compose run --rm web python manage.py set_nb_voix_commune        #  7 s
docker compose run --rm web python manage.py populate_pca               #  1 min 20
```

Ce que fait chacune : les deux premières créent les 26 cantons, 144 districts et
2 110 communes depuis le répertoire officiel, avec leur langue et leur degré
d'urbanisation. La troisième télécharge une centaine de votations passées.
La quatrième note le nombre d'électeurs de chaque commune. La dernière calcule
le profil de vote de chaque commune, qui sert à extrapoler le jour J.

Quelques avertissements sur des communes bernoises sans dépouillement propre
sont normaux : elles votent à l'urne d'une commune voisine.

## 7. Préparer un scrutin

Le fichier de résultats du dimanche est publié par la Confédération à une
adresse qui contient la date. Il doit être téléchargé **sous `./var`**, seul
dossier que le conteneur voit.

```bash
mkdir -p var/scrutins
DATE=20260927
curl -o "var/scrutins/votation_${DATE}_0.json" \
  "https://app-prod-static-voteinfo.s3.eu-central-1.amazonaws.com/v1/ogd/sd-t-17-02-${DATE}-eidgAbstimmung.json"

docker compose run --rm web python manage.py add_initial_scrutin_en_cours \
  "var/scrutins/votation_${DATE}_0.json"
```

Cette dernière commande crée une ligne vide par commune et par objet. Le
gabarit n'est publié que quelques jours avant le scrutin ; avant cela, la
commande n'a rien à lire.

**Contrôle à faire ici**, pas le dimanche soir : vérifier qu'aucune commune du
fichier n'est dépourvue de profil, sans quoi l'extrapolation s'arrête.

```bash
docker compose run --rm web python manage.py shell -c "
from scrutin.models import Commune, ResultatCommunalEnCours
from pca.models import PCAResult
sans = ResultatCommunalEnCours.objects.exclude(commune__in=PCAResult.objects.values('commune'))
print('communes sans profil :', sans.count(), sorted(set(sans.values_list('commune__nom', flat=True))))"
```

La réponse attendue est `0`.

## 7 bis. Les pages du menu

`peupler_demo` sème les pages « Méthodes » et « Contact ». **Le pipeline réel ne
les crée pas** : sur une base montée depuis les données officielles, le menu est
vide et les deux adresses répondent 404. Les créer une fois, avec leur vrai
contenu :

```bash
docker compose run --rm web python manage.py shell -c "
from page_statique.models import PageStatique
PageStatique.objects.get_or_create(url='methode', defaults={
    'titre': 'Méthodes', 'ordre': 1, 'contenu': '<p>À rédiger.</p>'})
PageStatique.objects.get_or_create(url='contact', defaults={
    'titre': 'Contact', 'ordre': 2, 'contenu': '<p>À rédiger.</p>'})"
```

Le contenu est du HTML, modifiable ensuite sans toucher au code : ajouter une
page en base ajoute un onglet au menu.

## 8. Ouvrir le site au public

Le conteneur n'écoute qu'en local. C'est nginx, sur la machine hôte, qui reçoit
le trafic public — et surtout qui **répond depuis son cache**.

```bash
sudo apt install -y nginx
# nginx crée le dernier niveau du dossier de cache, pas ceux d'avant.
sudo mkdir -p /var/cache/nginx
sudo cp deploiement/nginx-politiques.conf /etc/nginx/sites-available/politiques
sudo sed -i "s/politiques\.ch/$VOTRE_DOMAINE/" /etc/nginx/sites-available/politiques
sudo ln -sf /etc/nginx/sites-available/politiques /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Ce que fait ce cache, et pourquoi il compte : une page reste valable 30 s, mais
**aucun visiteur n'attend jamais ce délai**. Passé les 30 s, nginx sert quand
même la version périmée, instantanément, et va chercher la suivante en
arrière-plan. Un seul visiteur à la fois atteint Django. Si Django redémarre ou
tombe, la dernière version connue continue d'être servie.

Puis le certificat HTTPS, gratuit et renouvelé tout seul :

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d politiques.ch
```

Et le pare-feu :

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 9. Le dimanche de scrutin

Un timer systemd rappelle le script toutes les cinq minutes : il télécharge le
nouveau fichier, met à jour la base et recalcule la projection.

```bash
sudo cp deploiement/politiques-scrutin.service deploiement/politiques-scrutin.timer \
        /etc/systemd/system/
sudo sed -i "s/20260927/$DATE/" /etc/systemd/system/politiques-scrutin.service
sudo systemctl daemon-reload
sudo systemctl enable --now politiques-scrutin.timer
```

Adapter aussi `User` et `WorkingDirectory` dans le fichier `.service` si le
dépôt n'est pas dans `/home/ubuntu/election`.

Surveiller la soirée :

```bash
systemctl list-timers politiques-scrutin.timer     # le prochain tour
journalctl -u politiques-scrutin.service -f        # ce qu'il fait
```

Chaque instantané téléchargé est conservé sous `var/scrutins`, ce qui garde la
trace de la soirée et permet de tout rejouer. La mise à jour ne réimporte que
les communes dépouillées depuis l'instantané précédent.

Pour lancer un tour à la main, sans attendre le timer :

```bash
DATE_SCRUTIN=20260927 ./download_data.sh
```

## 10. Sauvegarder

Tout l'état tient dans un dossier. La base est le bien précieux : reconstruire
l'historique prend deux minutes, mais une soirée de dépouillement ne se rejoue
pas.

```bash
tar czf "sauvegarde-$(date +%F).tar.gz" var/
```

À faire avant le scrutin, et une fois pendant la soirée.

## 11. Redémarrage et pannes courantes

Le conteneur redémarre tout seul avec la machine : `restart: unless-stopped`
dans `compose.yaml`, et Docker démarre au boot.

| Symptôme | Cause | Quoi faire |
|---|---|---|
| `docker: command not found` après installation | `wmdocker` installé à la place | `sudo apt install docker.io` |
| `permission denied` sur le socket Docker | session ouverte avant `usermod` | se reconnecter |
| Erreur 400 dans le navigateur | domaine absent de `ALLOWED_HOSTS` | corriger `.env`, `docker compose up -d` |
| Page sans mise en forme | image construite sans `collectstatic` | reconstruire avec `--build` |
| `address already in use` | port 8000 pris | `PORT_WEB=8001` dans `.env` |
| `no such column` à l'import | base créée avant septembre 2026 | repartir d'une base vide |
| 403 pendant `importer_historique` | trop d'objets par requête | garder `--lot 10`, le défaut |

Voir les journaux : `docker compose logs -f`.
