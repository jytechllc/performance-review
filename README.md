# Engineering Metrics POC

## Overview

This project is a POC for automated engineering performance metrics collection using the GitHub API.

The system runs through scheduled GitHub Actions workflows and generates simple engineering activity reports for configured engineers.

---

## Goals

The purpose of this project is to:

- Collect GitHub engineering activity metrics
- Aggregate metrics across multiple time windows
- Generate automated reports
- Run entirely through GitHub Actions + Python

---

## Metrics

The MVP currently focuses on collecting:

- Commits
- Pull Requests
- Files Changed
- Lines Added
- Lines Deleted
- Repository Contribution Activity

Metrics can be aggregated by:

- Daily
- Weekly
- Monthly
- Quarterly

---

## Tech Stack

- Python
- GitHub API
- GitHub Actions
- Markdown/CSV reporting

---

## Folder Structure

```text
performance-review/
│
├── .github/
│   └── workflows/
│       └── collect_metrics.yml
│
├── config/
│   └── engineers.yaml
│
├── reports/
│
├── scripts/
│   ├── fetch_metrics.py
│   ├── aggregate_metrics.py
│   └── generate_report.py
│
├── requirements.txt
├── README.md
└── .env.example
```

---

## Setup

### 1. Clone Repository

```bash
git clone <repo-url>
cd performance-review
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## GitHub Token Configuration

Create a GitHub Personal Access Token with repository read permissions.

Store the token

---

## Engineer Configuration

Engineers are configured in:

```text
config/engineers.yaml
```

Example:

```yaml
engineers:
  - username: 

  - username: 
```

---

## Reports

Generated reports are stored in:

```text
reports/YYYY-MM/
```

Example:

```text
reports/2026-05/octocat.md
```

---

## Example Report Output

```markdown
# Weekly Engineering Metrics

## octocat

- Commits: 28
- Pull Requests: 5
- Files Changed: 364
- Lines Added: 33262
- Lines Deleted: 354
```

---
