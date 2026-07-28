# About

Career Hunter automates a finance work-study or internship search, from collecting offers to tracking applications.

## The pipeline, in one sentence

It collects offers from several sources, normalizes them into a common format, drops those that do not match the right contract or the right intake, scores the rest out of 10 against a personal profile, queues the best ones, proposes them one at a time on Telegram, and keeps a Google Sheet up to date in real time.

## The filters

1. **Contract type (strict).** The work-study feed keeps only work-study or apprenticeship offers. The internship feed keeps only internships. A "graduate" or permanent role is dropped from the work-study feed.
2. **Target intake.** Only a specific campaign is kept (for example September 2027), from the start date when it is known, or the year read in the title otherwise.
3. **Relevance score.** Each offer gets a score out of 10: role keywords, target employers, degree level, soft and hard exclusions.

Only offers that pass all three filters and clear a score threshold are proposed. Everything else stays silent, by design: zero noise.

## Secrets

No credential is versioned. The project expects a local `secrets/` folder containing, depending on the enabled sources and outputs:

```
secrets/
  lba_token.txt                  # official API token
  telegram_alternance_token.txt  # Telegram bot token
  telegram_chat_id.txt           # chat id
  google_service_account.json    # Google Sheets service account
```

This folder is excluded from the repo by `.gitignore`.

## Additional sources

The project exposes a simple source interface: a Python module providing a `fetch(profile, config)` function that returns a list of normalized offers. A source is enabled by adding it to `extra_sources` in the config. The rest of the pipeline (filters, scoring, delivery, tracking) does not change.
