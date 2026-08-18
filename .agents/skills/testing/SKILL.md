# Skill: Testing

## Objectif
Tester le MVP sans entrer dans une usine à tests démesurée.

## Conventions
- Tests par module dans `tests/`.
- Couvrir d'abord : Risk Engine, IEZ, providers critiques (FIRMS), sensors.
- Mocks pour les APIs externes.

## Contraintes
- Pas de tests d'intégration système complets au démarrage.
- Vérifier la séparation réel/simulé.
- Vérifier que l'IA n'influence pas les scores déterministes.

## Pièges à éviter
- Tester des providers externes sans mock.
- Croire qu'un test UI vert = produit démontrable.
- Oublier les cas dégradés : Earth Engine absent, GroQ indisponible.

## Fichiers concernés
- `tests/`
- `apps/*/tests.py`
- `core/services/tests/`
