# Image unique : elle sert le site *et* exécute les commandes du pipeline.
# Deux images auraient partagé 99 % de leur contenu, la pile scientifique.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Les dépendances d'abord : cette couche est réutilisée tant que les
# requirements ne bougent pas, et scipy/scikit-learn sont longs à installer.
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/calcul.txt

COPY . .

# DEBUG=1 seulement le temps de la commande : sans lui, settings.py exige un
# SECRET_KEY, qui n'a rien à faire dans une image.
RUN DEBUG=1 python manage.py collectstatic --noinput

EXPOSE 8000
# --timeout : la page d'accueil calcule trois cartes choroplèthes sur 2 100
# communes. Mesuré à 22 s au premier rendu, 3 s ensuite ; les 30 s par défaut
# de gunicorn tuaient le worker avant qu'il ait fini.
# --workers : le VPS a un cœur, et chaque worker charge numpy, scipy et plotly.
# --preload : importer Django et plotly coûte 11 s, payés une fois dans le
# maître avant le fork au lieu d'une fois par worker.
CMD ["gunicorn", "election.wsgi", "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--timeout", "120", "--preload"]
