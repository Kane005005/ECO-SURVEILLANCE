# Instructions pour OpenCode

## Mission
Développer le MVP d'ECO-SURVEILLANCE MALI en respectant strictement le cahier des charges et le design system.

## Documents de référence obligatoires
- `README.md` — vision, stack, modules
- `docs/cahier-des-charges-v1.0.docx` — spécifications détaillées
- `logo/eco.html` — branding et composants UI

## Règles non négociables
1. Django monolithique + Templates. Pas de React.
2. PostgreSQL + PostGIS obligatoires en modèle.
3. Celery + Redis pour les tâches longues.
4. Toutes les données simulées doivent être marquées `SIMULATION`.
5. L'IA (Groq par défaut) ne calcule pas les scores ; elle interprète seulement.
6. Earth Engine ne doit jamais être une dépendance obligatoire.
7. `.env.example` est la référence des variables d'environnement. Jamais de secret dans le code.
8. Respecter la structure modulaire indiquée dans `README.md`.

## Ordre de développement suggéré
1. `config/` — settings, urls, asgi, wsgi
2. `core/services/` — Risk Engine, IEZ, Anomaly detection
3. `apps/geography/` — modèle géospatial Mali
4. `data_providers/` — FIRMS, NASA POWER, CHIRPS, etc.
5. `apps/sensors/` — stations simulées
6. Modules métiers : fires, vegetation, water, climate, atmosphere
7. `apps/risk/`, `apps/iez/`, `apps/incidents/`, `apps/alerts/`
8. `ai/` — GroqProvider
9. Frontend Templates + Tailwind + carte + charts
10. Tests et démo

## Git
- Petits commits fonctionnels.
- Ne jamais committer `.env` ni secrets.
- Ne pas supprimer de contenu existant sans demande explicite.

## Livraison attendue
- MVP démontrable avec au moins :
  - Dashboard national
  - Carte Mali interactive
  - FIRMS connecté
  - 5 stations simulées
  - 1 scénario IA Groq
  - IEZ calculé sur au moins une zone
