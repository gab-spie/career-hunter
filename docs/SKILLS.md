# Compétences mobilisées

Ce projet couvre une chaîne complète, de la donnée brute à un outil utilisable au quotidien.

## Ingénierie logicielle

- Architecture modulaire : sources, filtres, scoring, stockage, livraison et suivi sont découplés.
- Interface de source extensible (ajout d'une source sans toucher au pipeline).
- Base SQLite avec anti-doublon, file d'attente persistante et migrations douces de schéma.
- Gestion propre des secrets, isolés hors du dépôt.

## Intégration d'API et de données

- Consommation d'une API REST officielle (authentification par jeton, requêtes géolocalisées, pagination).
- Normalisation de données hétérogènes vers un modèle commun.
- Google Sheets API via compte de service (écriture, mise en forme conditionnelle, préservation des saisies manuelles).

## Automatisation et outils

- Bot Telegram interactif (long polling, claviers en ligne, machine à états de triage).
- Planification système avec `launchd` (exécutions récurrentes, service maintenu en vie).
- Notifications déclenchées par l'état des données.

## Logique métier finance

- Modèle de scoring pensé pour un profil finance : M&A, Private Equity, Corporate Finance, banques d'affaires, boutiques, fonds.
- Distinction fine des types de contrat et des campagnes de recrutement.

## Méthode

- Décisions guidées par la donnée réelle (mesure de la couverture d'une source avant de l'intégrer).
- Choix assumés de précision : préférer le silence au bruit.
- Usage d'outils d'IA pour concevoir, itérer et fiabiliser rapidement.
