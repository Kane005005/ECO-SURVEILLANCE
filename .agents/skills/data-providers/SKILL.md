# Skill: Data Providers

## Objectif
Maintenir l'abstraction des sources de données externes.

## Conventions
- Chaque provider hérite de `data_providers/base.py:DataProvider`.
- Un provider ne fait pas de calcul métier : il retourne des données normalisées.
- Providers optionnels : retourner un état dégradé si la clé/config manque.

## Contraintes
- Respecter les limites des APIs externes.
- Mettre en cache les réponses quand c'est pertinent.
- Ne jamais faire dépendre le cœur d'un provider optionnel comme Earth Engine.

## Pièges à éviter
- Cacher des secrets dans le code provider.
- Dépendre d'un provider optionnel pour une fonctionnalité core.
- Mélanger données simulées et réelles sans flag `is_simulated`.

## Fichiers concernés
- `data_providers/base.py`
- `data_providers/*.py`
- `.env.example`
