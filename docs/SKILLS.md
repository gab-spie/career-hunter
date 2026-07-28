# Skills involved

This project spans a full chain, from raw data to a tool used day to day.

## Software engineering

- Modular architecture: sources, filters, scoring, storage, delivery and tracking are decoupled.
- Extensible source interface (adding a source without touching the pipeline).
- SQLite database with URL and cross-source deduplication, a persistent queue, and soft schema migrations.
- Clean secret handling, kept out of the repo.

## API and data integration

- Consuming an official REST API (token auth, geolocated queries, pagination).
- Normalizing heterogeneous data into a common model.
- Google Sheets API via a service account (writing, conditional formatting, preserving manual edits).

## Automation and tooling

- Interactive Telegram bot (long polling, inline keyboards, a triage state machine).
- System scheduling with `launchd` (recurring runs, a kept-alive service).
- Notifications driven by the state of the data.

## Finance domain logic

- A scoring model designed for a finance profile: M&A, Private Equity, Corporate Finance, investment banks, boutiques, funds.
- Fine-grained handling of contract types and recruitment campaigns.

## Method

- Decisions driven by real data (measuring a source's coverage before integrating it).
- Deliberate precision trade-offs: prefer silence over noise.
- Using AI tools to design, iterate and harden quickly.
