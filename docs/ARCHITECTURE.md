# Architecture

## Vue d'ensemble

```
Sources ─▶ Normalisation ─▶ Filtres (contrat, rentrée) ─▶ Scoring ─▶ SQLite
                                                                        │
                                       Google Sheet ◀── Bot Telegram ◀──┘
```

## Modules

| Fichier | Rôle |
|---|---|
| `config.yaml` | Tous les critères (mots-clés, employeurs, profils, filtres). Aucune ligne de code à toucher. |
| `src/source_lba.py` | Source : API officielle de l'alternance. Interroge par géolocalisation, normalise les offres. |
| `src/appconfig.py` | Chargement de la config et lecture des secrets. |
| `src/scoring.py` | Note une offre sur 10 : mots-clés forts/moyens, employeurs cibles, diplôme, exclusions simples et dures. |
| `src/contrat.py` | Filtre strict du type de contrat (alternance vs stage). |
| `src/datematch.py` | Filtre de rentrée visée (date de début ou année dans l'intitulé). |
| `src/db.py` | Base SQLite : anti-doublon par URL, file d'attente, états d'une offre, migrations. |
| `scan.py` | Orchestration d'un passage : collecte, filtres, scoring, mise en file. |
| `telegram_bot.py` | Bot de triage : digest, cartes une par une, boutons, statuts. |
| `src/sheet.py` | Google Sheets : onglets, mise en forme conditionnelle, préservation des saisies manuelles. |
| `src/sink.py` | Miroir CSV local des offres retenues. |
| `run_once.py` | Un scan + notification, pour la planification. |
| `notify.py` | Envoi du digest Telegram. |

## États d'une offre

```
pending  ─▶ proposed ─▶ kept ─▶ applied
                     └▶ passed
```

- `pending` : trouvée, pas encore proposée.
- `proposed` : carte envoyée, en attente d'un choix.
- `kept` : retenue (écrite dans le suivi).
- `applied` : candidature marquée (avec date).
- `passed` : écartée, jamais reproposée.

## Extensibilité

Une source est un module exposant `fetch(profil, config) -> list[dict]`, chaque offre au format normalisé (`url`, `entreprise`, `titre`, `lieu`, `contrat`, `date_debut`, ...). On l'active via `sources_extra` dans la config. Le pipeline en aval est identique pour toutes les sources.
