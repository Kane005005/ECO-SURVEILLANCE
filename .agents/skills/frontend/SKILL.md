# Skill: Frontend

## Objectif
Implémenter le frontend dans le respect du design system de référence.

## Conventions
- Django Templates + Tailwind CSS.
- `logo/eco.html` est la référence visuelle.
- Cartographie : Leaflet ou MapLibre.
- Graphiques : Chart.js si nécessaire.
- Pas de React.

## Contraintes
- Performance tableau de bord < 3s.
- Transparency des sources affichée systématiquement.
- Indicateurs simulés marqués clairement.

## Pièges à éviter
- Réinventer le design system.
- Charger toutes les données côté view sans cache.
- Oublier l'accessibilité des alertes et badges.

## Fichiers concernés
- `templates/`
- `static/css/`
- `static/js/`
- `logo/eco.html`
