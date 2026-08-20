---
name: document-design
description: >
  Use when creating polished, branded project documentation for ECO-SURVEILLANCE MALI or other apps.
  Produces readable deliverables in Markdown, DOCX, PDF, or PPTX from project facts, screenshots, and diagrams.
  Triggers: "documente l'app", "crée un rapport présentable", "génère la doc du projet", "make a nice report".
---

# Document Design — Documents présentables pour projet

## Objectif
Produire des documents de projet **lisibles, structurés et présentables**, pas des notes brutes.
Ce skill ne code pas l’application ; il met en forme sa documentation.

## Formats de sortie
- Markdown → `docs/` pour le repo et la lecture web
- DOCX → `docs/<projet>_Documentation_vX.Y.docx`
- PDF → `docs/<projet>_Documentation_vX.Y.pdf`
- PPTX → optionnel pour soutenance/démo

## Sources de vérité à utiliser
- `README.md`
- `docs/cahier-des-charges-v1.0.docx`
- `logo/eco.html`
- Le code source : `apps/`, `core/`, `data_providers/`, `ai/`
- Les retours utilisateurs / tickets si présents

## Structure recommandée d’un document projet
1. Couverture : nom, version, date, auteur, statut
2. Résumé exécutif : 1 page max
3. Vision & périmètre MVP
4. Architecture technique
5. Modules fonctionnels
6. Sources de données & intégrations
7. IA & moteur de risques
8. Design system & interfaces
9. Tests & déploiement
10. Annexes : schémas, captures, glossaire

## Règles de présentation
- Titres hiérarchisés, table des matières
- Tableaux pour stack, modules, sources
- Listes à puces pour principes et règles
- Badges pour statuts : `MVP`, `En dev`, `Simulé`, `Réel`
- Mise en garde visible pour :
  - données simulées
  - dépendances optionnelles
  - secrets/clés API
- Captures d’écran annotées si possible
- Schémas simples pour flux de données, architecture

## Branding ECO-SURVEILLANCE MALI
- Palette : Territory green + Data blue + Risk colors
- Typo : Space Grotesk / Inter / JetBrains Mono
- Logo référence : `logo/eco.html`
- Ton : institutionnel, transparent, scientifique, sobre

## Outils autorisés
- `docx` skill pour Word
- `pdf` skill pour PDF
- `powerpoint` skill pour soutenance
- `markdown` natif pour documentation technique
- Génération de schémas via mermaid/text-to-diagram si besoin

## Pièges à éviter
- Copier-coller le cahier des charges sans adaptation
- Présenter des données simulées comme réelles
- Faire un document trop long sans synthèse
- Oublier la version et la date
- Mettre des secrets dans les exemples

## Fichiers concernés
- `docs/*.md`
- `docs/*.docx`
- `docs/*.pdf`
- `docs/*.pptx`
- `README.md`
