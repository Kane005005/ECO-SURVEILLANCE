# Skill: Sensors

## Objectif
Implémenter les stations environnementales simulées du MVP.

## Conventions
- Même interface que de futurs capteurs physiques.
- Flag explicite `SOURCE=SIMULATION` sur chaque mesure.
- Scénarios configurables.

## Scénarios simulés
- NORMAL
- WATER_POLLUTION
- DROUGHT
- HEAT
- ATMOSPHERIC_ANOMALY
- SENSOR_OFFLINE

## Contraintes
- Les valeurs simulées ne doivent jamais être présentées comme réelles.
- L'architecture doit permettre de remplacer le simulateur par un adaptateur IoT sans refonte.

## Pièges à éviter
- Oublier le marquage SIMULATION dans l'UI.
- Coupler le modèle Station à un provider spécifique.
- Mélanger logique de simulation et logique métier.

## Fichiers concernés
- `apps/sensors/`
- `apps/sensors/models.py`
- `apps/sensors/services.py`
