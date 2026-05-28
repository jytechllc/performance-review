# Performance Review Metrics

This repo collects GitHub activity and turns it into simple Markdown reports for performance reviews.

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

Every report is saved under `reports/`.

Engineer report files use this pattern:

`reports/<window>/<YYYY-MM>/<username>_<start>_to_<end>.md`

Example:

`reports/weekly/2026-05/octocat_2026-05-11_to_2026-05-17.md`

What each part means:

- `<window>` is the time range. Use `daily`, `weekly`, or `monthly`.
- `<YYYY-MM>` is the month folder for the report end date.
- `<username>` is the GitHub username made safe for file names.
- `<start>` and `<end>` are the dates covered by the report.

In addition to individual files, the collector also writes one team-level summary README per run:

`reports/summary/<window>/<YYYY-MM>/README_<start>_to_<end>.md`

This gives you one file with everyone's totals and links to each person's report.

## GitHub token

The script needs a GitHub token so it can call the GitHub API.

It checks these environment variables in this order:

1. `PERFORMANCE_REVIEW_GITHUB_TOKEN`
2. `GITHUB_TOKEN`

For GitHub Actions, store the token as a repository secret named `PERFORMANCE_REVIEW_GITHUB_TOKEN`.

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
  - username: hubot
    display_name: Hubot
```

How it works:

- Put the GitHub usernames under `engineers`.
- Use `display_name` if you want a nicer name in the report.
- Add `repositories` under one engineer if you want to track only certain repos for that person.
- If an engineer does not have a repo list, the script uses the top-level `repositories` list.

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

## What the collector measures

The first version collects:

- commit count
- merged pull request count
- additions from merged pull requests
- deletions from merged pull requests
- files changed in merged pull requests

That gives you a simple starting point, and you can add more metrics later if you want.
