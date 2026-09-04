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
CMD ["gunicorn", "election.wsgi", "--bind", "0.0.0.0:8000", "--workers", "3"]
