# Architecture

## Overview

```
Sources ─▶ Normalization ─▶ Filters (contract, intake) ─▶ Scoring ─▶ SQLite
                                                                        │
                                        Google Sheet ◀── Telegram bot ◀─┘
```

## Modules

| File | Role |
|---|---|
| `config.yaml` | All criteria (keywords, employers, profiles, filters). No code to touch. |
| `src/source_lba.py` | Source: the official work-study API. Queries by geolocation, normalizes offers. |
| `src/appconfig.py` | Loads the config and reads secrets. |
| `src/scoring.py` | Scores an offer out of 10: strong/medium keywords, target employers, degree, soft and hard exclusions. |
| `src/contrat.py` | Strict contract-type filter (work-study vs internship). |
| `src/datematch.py` | Target-intake filter (start date or year in the title). |
| `src/db.py` | SQLite: URL and cross-source dedup, queue, offer states, migrations, WAL. |
| `scan.py` | Orchestrates one pass: collection, filters, scoring, queueing. |
| `telegram_bot.py` | Triage bot: digest, one-by-one cards, buttons, statuses. |
| `src/sheet.py` | Google Sheets: tabs, conditional formatting, preserves manual edits. |
| `src/sink.py` | Local CSV mirror of kept offers. |
| `run_once.py` + `notify.py` | One scan + digest, for scheduling. |
| launchd plists | macOS scheduling (bot 24/7 + scan several times a day). |

## Offer states

```
pending  ─▶ proposed ─▶ kept ─▶ applied
                     └▶ passed
```

- `pending`: found, not yet proposed.
- `proposed`: card sent, awaiting a decision.
- `kept`: retained (written to the tracker).
- `applied`: application marked (with a date).
- `passed`: dropped, never proposed again.

## Extensibility

A source is a module exposing `fetch(profile, config) -> list[dict]`, each offer in the normalized format (`url`, `company`, `title`, `location`, `contract`, `start_date`, ...). It is enabled via `sources_extra` in the config. The downstream pipeline is identical for every source.
