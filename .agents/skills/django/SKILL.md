# Skill: Django Core

## Objectif
Coder le cœur Django du projet ECO-SURVEILLANCE MALI.

## Conventions
- Modules apps dans `/apps/`, pas dans `core`.
- Configuration dans `config/`.
- Services partagés dans `core/services/`.
- Pas d'app React. Django Templates uniquement.
- Transparence obligatoire : toute donnée simulée doit être marquée `SIMULATION`.

## Contraintes
- Django 4.2+.
- Base : PostgreSQL avec PostGIS.
- Tâches asynchrones : Celery + Redis.
- Logs : structured logging recommandé.
- Secrets : jamais dans le code, uniquement `.env`.

## Pièges à éviter
- Mettre de la logique métier dans les views : utiliser des services.
- Oublier la séparation réel/simulé pour les stations.
- Créer des dépendances obligatoires vers Earth Engine.
- Dépasser le scope MVP : microservices, Kubernetes, mobile.

## Fichiers concernés
- `config/settings/`
- `core/services/`
- `apps/*/models.py`
- `apps/*/views.py`
- `apps/*/services.py`
