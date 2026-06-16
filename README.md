# Performance Review Metrics

This repo collects GitHub activity metrics and turns them into a simple Markdown table for performance reviews.

You can run it on your computer, or you can let GitHub Actions run it on a schedule.

## What is in this repo

- `scripts/collect_metrics.py` is the main Python script.
- `config/engineers.yaml` is where you list the engineers and repos to track.
- `reports/` is where finished reports are saved.
- `.github/workflows/collect_metrics.yml` is the GitHub Actions workflow.
- `requirements.txt` lists the Python packages.

## Folder structure

Here is the simple layout:

- `.github/workflows/` holds the scheduled GitHub Actions job.
- `config/` holds the engineer list and repo list.
- `reports/` holds the output files.
- `scripts/` holds the Python code.
- `README.md` explains how to use the repo.
- `requirements.txt` lists the packages you need.

## Report name and location

The collector writes one team-level summary README per run:

`reports/summary/<window>/<YYYY-MM>/README_<start>_to_<end>.md`

This gives you one file with a single table of PR metrics for all configured engineers.

When running in GitHub Actions, the same table is also shown in the workflow run summary (Actions UI).

## GitHub token and engineer connection

The script supports PAT-based connection in two ways:

- Per-engineer token via `token_env` in `config/engineers.yaml`
- Fallback token via environment variable

Fallback environment variables are checked in this order:

1. `PERFORMANCE_REVIEW_GITHUB_TOKEN`
2. `GITHUB_TOKEN`

For GitHub Actions, you can store one shared token as repository secret `PERFORMANCE_REVIEW_GITHUB_TOKEN`.

If you want per-engineer connection, add separate secrets and map each engineer to a secret name using `token_env`.

For local use, set the same environment variable in your shell.

Do not put a real token into the repo.

## How to add engineers

Add engineers in `config/engineers.yaml`.

Example:

```yaml
repositories:
  - octo-org/platform
  - octo-org/api

engineers:
  - username: octocat
    display_name: Octo Cat
    token_env: OCTOCAT_GITHUB_TOKEN
  - username: hubot
    display_name: Hubot
```

How it works:

- Put the GitHub usernames under `engineers`.
- Use `display_name` if you want a nicer name in the report.
- Use `token_env` to map one engineer to one PAT secret/environment variable.
- Add `repositories` under one engineer if you want to track only certain repos for that person.
- If an engineer does not have a repo list, the script uses the top-level `repositories` list.
- If an engineer does not have `token_env`, the script uses the fallback token.

## How to run it locally

Install the packages:

```bash
pip install -r requirements.txt
```

Run the collector:

```bash
python scripts/collect_metrics.py --window weekly
```

Useful options:

- `--window daily|weekly|monthly`
- `--config config/engineers.yaml`
- `--output-dir reports`
- `--as-of YYYY-MM-DD` to use a specific date

Examples for each summary cadence:

```bash
python scripts/collect_metrics.py --window daily
python scripts/collect_metrics.py --window weekly
python scripts/collect_metrics.py --window monthly
```

## GitHub Actions

The workflow in `.github/workflows/collect_metrics.yml` can run by hand or on a schedule.

When it runs, it:

- checks out the repo
- installs the Python packages
- runs the collector script
- writes new or updated report files back into the repo

## What the collector measures (MVP)

The MVP automatically tracks:

- commit count
- merged pull request count
- closed issue count
- additions from merged pull requests
- deletions from merged pull requests
- files changed in merged pull requests

Output format is intentionally simple: one Markdown table grouped by engineer, including connection status and a team-total row.
