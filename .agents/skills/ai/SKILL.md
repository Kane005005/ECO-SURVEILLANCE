# Skill: AI / IA

## Objectif
Implémenter la couche IA strictement interprétative.

## Conventions
- IA = `AIProvider` + implémentations (`ai/groq.py`, etc.).
- Entrée IA = signaux normalisés + anomalies + scores, jamais données brutes.
- Sortie IA = texte explicatif, résumé, recommandations.

## Contraintes
- L'IA ne calcule pas NDVI, anomalies, IEZ ou risques.
- Une indisponibilité IA ne doit pas casser le MVP.
- Cache des réponses IA.

## Pièges à éviter
- Utiliser l'IA pour prendre une décision de risque.
- Envoyer des données brutes trop volumineuses aux providers IA.
- Rendre un provider IA obligatoire.

## Fichiers concernés
- `ai/base.py`
- `ai/groq.py`
- `core/services/risk.py`
- `.env.example`
