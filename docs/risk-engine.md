# Documentation du Moteur de Risque

## Vue d'ensemble

Le moteur de risque (`core/services/risk.py`) calcule des scores de risque explicables et reproductibles pour chaque zone de surveillance. Il utilise des données réelles provenant de multiples sources (FIRMS, NASA POWER, Sentinel-2, capteurs) pour évaluer différents types de risques environnementaux.

## Types de Risques

Le système évalue 7 types de risques :

| Risque | Description | Facteurs principaux |
|--------|-------------|---------------------|
| **WILDFIRE** | Risque d'incendie de forêt | Détections FIRMS, température, vent, humidité, végétation sèche |
| **DROUGHT** | Risque de sécheresse | Déficit pluviométrique, anomalie température, humidité |
| **VEGETATION_DEGRADATION** | Dégradation de la végétation | Baisse NDVI, changement NBR, impact incendie |
| **WATER_POLLUTION** | Pollution de l'eau | pH, turbidité, oxygène dissous, conductivité |
| **WATER_STRESS** | Stress hydrique | Niveau d'eau, déficit pluviométrique, évaporation |
| **HEAT** | Risque de canicule | Anomalie température, durée, humidité |
| **ATMOSPHERIC_ANOMALY** | Anomalie atmosphérique | Aérosols, SO2, O3, NO2 |

## Formule de Calcul

### Score de risque pondéré

```
risk_score = Σ(factor_score × factor_weight) / Σ(factor_weight)
```

Où :
- `factor_score` : Valeur normalisée 0-100 pour chaque facteur
- `factor_weight` : Poids du facteur (0-1, somme = 1)

### Niveaux de risque

| Score | Niveau | Sévérité | Couleur |
|-------|--------|----------|---------|
| < 25 | GREEN | LOW | Vert |
| 25-49 | YELLOW | MEDIUM | Jaune |
| 50-79 | ORANGE | HIGH | Orange |
| ≥ 80 | RED | CRITICAL | Rouge |

### Calcul de la confiance

```python
confidence = nombre_facteurs_avec_données_réelles / nombre_total_facteurs
```

Les données manquantes utilisent une valeur neutre de 50.0.

## Structure des données

### RiskFactor
```python
@dataclass
class RiskFactor:
    name: str          # Nom du facteur (ex: "fire_detections")
    score: float       # Score 0-100
    weight: float      # Poids 0-1
    value: Any         # Valeur brute
    description: str   # Description lisible
```

### RiskResult
```python
@dataclass
class RiskResult:
    risk_score: float      # Score final 0-100
    confidence: float      # Confiance 0-1
    level: str             # GREEN, YELLOW, ORANGE, RED
    severity: str          # LOW, MEDIUM, HIGH, CRITICAL
    factors: List[RiskFactor]  # Détail des facteurs
    risk_type: str         # Type de risque
    algorithm_version: str # Version de l'algorithme
```

## Exemple d'utilisation

```python
from core.services.risk import RiskEngine

engine = RiskEngine()

# Calcul du risque incendie pour une zone
result = engine.compute_fire_risk(zone)

print(f"Score: {result.risk_score}")
print(f"Niveau: {result.level}")
print(f"Confiance: {result.confidence}")

# Détail des facteurs
for factor in result.factors:
    print(f"  {factor.name}: {factor.score} (poids: {factor.weight})")
```

## Sources de données

| Source | Utilisation |
|--------|-------------|
| **FIRMS** | Détections de feux actifs |
| **NASA POWER** | Température, humidité, précipitations |
| **Sentinel-2** | NDVI, NDMI (stress végétal) |
| **Sentinel-5P** | Aérosols, SO2, O3, NO2 |
| **Capteurs IoT** | Niveau d'eau, qualité eau |

## Personnalisation

### Ajouter un nouveau type de risque

1. Ajouter le profil dans `RISK_PROFILES` :
```python
"NEW_RISK": {
    "factors": {
        "factor1": {"weight": 0.5, "description": "Description"},
        "factor2": {"weight": 0.5, "description": "Description"},
    },
}
```

2. Implémenter la méthode `compute_new_risk(zone)` si nécessaire

### Modifier les poids

Les poids doivent être ajustés selon l'expertise domaine. La somme des poids doit être égale à 1.0.

## Versioning

Chaque résultat inclut `algorithm_version` pour tracer les changements d'algorithme. Incrémenter cette version lors de modifications significatives.
