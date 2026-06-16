import argparse
import datetime as dt
import os
from pathlib import Path

import requests
import yaml


API_BASE_URL = "https://api.github.com"
DEFAULT_CONFIG_PATH = Path("config/engineers.yaml")
DEFAULT_OUTPUT_DIR = Path("reports")


class GitHubApiError(RuntimeError):
    pass


# This reads command-line arguments from the user and allows them to customize
# how the program runs (like what kind of report to generate, where to save the output).
def parse_args():
    parser = argparse.ArgumentParser(description="Collect GitHub metrics for performance reviews")
    parser.add_argument("--window", choices=("daily", "weekly", "monthly"), default="weekly")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--as-of", type=str, help="Reference date in YYYY-MM-DD format")
    return parser.parse_args()

# Loads the fallback GitHub token used when no per-engineer token is provided.
def load_fallback_token():
    token = os.getenv("PERFORMANCE_REVIEW_GITHUB_TOKEN")
    if not token:
        token = os.getenv("GITHUB_TOKEN")
    return token


def normalize_repo_name(raw_value):
    if raw_value is None:
        return ""

    repo_name = str(raw_value).strip()
    if not repo_name:
        return ""

    lowered = repo_name.lower()
    if lowered in {"none", "null", "~"}:
        return ""

    # Keep only canonical owner/repo values.
    if "/" not in repo_name:
        return ""

    owner, repo = repo_name.split("/", 1)
    owner = owner.strip()
    repo = repo.strip()
    if not owner or not repo:
        return ""

    return f"{owner}/{repo}"


def normalize_text(raw_value):
    if raw_value is None:
        return ""

    value = str(raw_value).strip()
    if not value:
        return ""

    if value.lower() in {"none", "null", "~"}:
        return ""

    return value

# If config is available, this loads the config file and checks that it has the right format. It also makes sure that there are engineers and repositories defined and are properly configured.

def load_config(config_path):

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    repositories = []
    for repo in data.get("repositories", []):
        repo_name = normalize_repo_name(repo)
        if repo_name:
            repositories.append(repo_name)

    engineers = []
    for item in data.get("engineers", []):
        if not isinstance(item, dict):
            continue

        username = normalize_text(item.get("username", ""))
        if not username:
            continue

        engineer_repositories = []
        for repo in item.get("repositories", []):
            repo_name = normalize_repo_name(repo)
            if repo_name:
                engineer_repositories.append(repo_name)

        display_name = normalize_text(item.get("display_name", ""))

        engineers.append(
            {
                "username": username,
                "display_name": display_name,
                "repositories": engineer_repositories,
                "token_env": normalize_text(item.get("token_env", "")),
            }
        )

    return repositories, engineers

# This takes a date string from the user and converts it into a date object of real time to work with.
def parse_reference_date(raw_value):
    if not raw_value:
        return dt.datetime.now(dt.timezone.utc).date()

    try:
        return dt.date.fromisoformat(raw_value)
    except ValueError as error:
        raise SystemExit("Invalid --as-of value. Use YYYY-MM-DD.") from error


# This calculates the start and end dates for the report based on the specified time window (daily, weekly, monthly) and the reference date.
def resolve_window(window, as_of):
    if window == "daily":
        start = as_of - dt.timedelta(days=1)
        end = as_of
    elif window == "weekly":
        current_week_start = as_of - dt.timedelta(days=as_of.weekday())
        start = current_week_start - dt.timedelta(days=7)
        end = current_week_start
    elif window == "monthly":
        first_of_month = as_of.replace(day=1)
        previous_month_last_day = first_of_month - dt.timedelta(days=1)
        start = previous_month_last_day.replace(day=1)
        end = first_of_month
    else:
        raise ValueError(f"Unsupported window: {window}")

    return start, end

# A GitHub connection for making API requests. It sets the necessary headers for authentication and API versioning.
def github_session(token):
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "performance-review-metrics",
        }
    )
    return session


# This function makes a request to the GitHub API and returns the JSON response.
def request_json(session, method, path, params=None):
    url = f"{API_BASE_URL}{path}"
    response = session.request(method, url, params=params, timeout=30)
    if response.status_code >= 400:
        raise GitHubApiError(f"GitHub API request failed for {path}: {response.status_code} {response.text}")
    return response.json()


def paginate_list(session, path, params=None):
    page = 1
    items = []

    if params:
        base_params = dict(params)
    else:
        base_params = {}

    if "per_page" not in base_params:
        base_params["per_page"] = 100

    per_page = int(base_params["per_page"])

    while True:
        page_params = dict(base_params)
        page_params["page"] = page
        result = request_json(session, "GET", path, page_params)

        items.extend(result)
        if len(result) < per_page:
            break
        page += 1

    return items


def search_items(session, query):
    page = 1
    results = []

    while True:
        payload = request_json(
            session,
            "GET",
            "/search/issues",
            {
                "q": query,
                "page": page,
                "per_page": 100,
            },
        )

        page_items = payload.get("items", [])
        results.extend(page_items)

        if len(page_items) < 100:
            break
        page += 1

    return results

# This searches for pull requests that were merged in the specified repository and time period, filtering by the author's username. It handles pagination of search results and returns a list of matching pull requests.
def search_merged_pull_requests(session, repo, username, start_date, end_date):
    end_inclusive = end_date - dt.timedelta(days=1)
    date_range = f"{start_date.isoformat()}..{end_inclusive.isoformat()}"
    query = f"repo:{repo} is:pr is:merged merged:{date_range}"
    results = []
    wanted_username = username.lower()

    for item in search_items(session, query):
        author = str(item.get("user", {}).get("login", ""))
        if author.lower() == wanted_username:
            results.append(item)

    return results


def count_commits(session, repo, username, start_date, end_date):
    commits = paginate_list(
        session,
        f"/repos/{repo}/commits",
        {
            "author": username,
            "since": f"{start_date.isoformat()}T00:00:00Z",
            "until": f"{end_date.isoformat()}T00:00:00Z",
        },
    )
    return len(commits)


def count_closed_issues(session, repo, username, start_date, end_date):
    closed_issues = paginate_list(
        session,
        f"/repos/{repo}/issues",
        {
            "state": "closed",
            "per_page": 100,
        },
    )

    count = 0
    for item in closed_issues:
        if item.get("pull_request"):
            continue

        author = str(item.get("user", {}).get("login", ""))
        if author.lower() != username.lower():
            continue

        closed_at = item.get("closed_at")
        if not closed_at:
            continue

        closed_date = dt.date.fromisoformat(closed_at[:10])
        if start_date <= closed_date < end_date:
            count += 1

    return count


def new_pr_stats():
    return {
        "commits": 0,
        "merged_prs": 0,
        "closed_issues": 0,
        "additions": 0,
        "deletions": 0,
        "files_changed": 0,
    }


def resolve_engineer_token(engineer, fallback_token):
    token_env_name = engineer.get("token_env", "")
    if token_env_name:
        # Prefer per-engineer token, but gracefully fall back to shared token.
        return os.getenv(token_env_name) or fallback_token
    return fallback_token


def validate_engineer_connection(session, engineer, repositories):
    request_json(session, "GET", "/user")
    for repo in repositories:
        request_json(session, "GET", f"/repos/{repo}")


# This collects automatic activity metrics for a given engineer across the configured repositories.
def collect_engineer_activity_metrics(session, engineer, repositories, start_date, end_date):
    repo_scope = engineer["repositories"] or repositories
    totals = new_pr_stats()

    actual_name = get_github_display_name(session, engineer["username"])

    for repo in repo_scope:
        totals["commits"] += count_commits(
            session, repo, engineer["username"], start_date, end_date
        )

        totals["closed_issues"] += count_closed_issues(
            session, repo, engineer["username"], start_date, end_date
        )

        merged_pull_requests = search_merged_pull_requests(
            session, repo, engineer["username"], start_date, end_date
        )
        totals["merged_prs"] += len(merged_pull_requests)

        for pull_request in merged_pull_requests:
            number = int(pull_request["number"])
            details = request_json(session, "GET", f"/repos/{repo}/pulls/{number}")

            totals["additions"] += int(details.get("additions", 0))
            totals["deletions"] += int(details.get("deletions", 0))
            totals["files_changed"] += int(details.get("changed_files", 0))

    return {
        "username": engineer["username"],
        "display_name": engineer["display_name"] or actual_name,
        "connection": "connected",
        "tracked_repos": len(repo_scope),
        "commits": totals["commits"],
        "merged_prs": totals["merged_prs"],
        "closed_issues": totals["closed_issues"],
        "additions": totals["additions"],
        "deletions": totals["deletions"],
        "files_changed": totals["files_changed"],
    }


def build_disconnected_metrics(engineer, repositories, reason):
    repo_scope = engineer["repositories"] or repositories
    return {
        "username": engineer["username"],
        "display_name": engineer["display_name"] or engineer["username"],
        "connection": reason,
        "tracked_repos": len(repo_scope),
        "commits": 0,
        "merged_prs": 0,
        "closed_issues": 0,
        "additions": 0,
        "deletions": 0,
        "files_changed": 0,
    }


def render_mvp_table(engineer_metrics):
    totals = new_pr_stats()
    rows = []

    for item in sorted(engineer_metrics, key=lambda record: record["username"]):
        totals["commits"] += item["commits"]
        totals["merged_prs"] += item["merged_prs"]
        totals["closed_issues"] += item["closed_issues"]
        totals["additions"] += item["additions"]
        totals["deletions"] += item["deletions"]
        totals["files_changed"] += item["files_changed"]
        rows.append(
            "| "
            f"{item['display_name']} | "
            f"{item['username']} | "
            f"{item['connection']} | "
            f"{item['tracked_repos']} | "
            f"{item['commits']} | "
            f"{item['merged_prs']} | "
            f"{item['closed_issues']} | "
            f"{item['additions']} | "
            f"{item['deletions']} | "
            f"{item['files_changed']} |"
        )

    lines = [
        "| Engineer | Username | Connection | Repos | Commits | Merged PRs | Closed Issues | Additions | Deletions | Files Changed |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    if rows:
        lines.extend(rows)
    else:
        lines.append("| None | - | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 |")

    lines.append(
        "| **Team Total** | - | - | - | "
        f"**{totals['commits']}** | "
        f"**{totals['merged_prs']}** | "
        f"**{totals['closed_issues']}** | "
        f"**{totals['additions']}** | "
        f"**{totals['deletions']}** | "
        f"**{totals['files_changed']}** |"
    )
    return "\n".join(lines)


def render_summary_markdown(window, start_date, end_date_exclusive, engineer_metrics):
    end_date = end_date_exclusive - dt.timedelta(days=1)
    lines = [
        f"# Activity Metrics Summary ({window.title()})",
        "",
        f"- Window: `{window}`",
        f"- Period: `{start_date.isoformat()} to {end_date.isoformat()}`",
        f"- Engineers: `{len(engineer_metrics)}`",
        "- Connection mode: `PAT (env token)`",
        "",
        render_mvp_table(engineer_metrics),
        "",
    ]
    return "\n".join(lines)


def write_summary_readme(output_dir, window, start_date, end_date_exclusive, engineer_metrics):
    end_date = end_date_exclusive - dt.timedelta(days=1)
    month_folder = end_date.strftime("%Y-%m")
    start_label = start_date.isoformat()
    end_label = end_date.isoformat()
    summary_dir = output_dir / "summary" / window / month_folder
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"README_{start_label}_to_{end_label}.md"
    summary_path.write_text(render_summary_markdown(window, start_date, end_date_exclusive, engineer_metrics), encoding="utf-8")
    return summary_path


def write_github_step_summary(markdown):
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return

    summary_path = Path(summary_file)
    summary_path.write_text(markdown, encoding="utf-8")

def get_github_display_name(session, username):
    user = request_json(session, "GET", f"/users/{username}")
    return user.get("name") or username


def main():
    args = parse_args() # Parse command-line arguments provided by the user
    reference_date = parse_reference_date(args.as_of)  # Convert the --as-of argument into a usable date object
    repositories, engineers = load_config(args.config) # Load repository and engineer configuration data from the config file
    fallback_token = load_fallback_token() # Load fallback GitHub token from environment

    start_date, end_date = resolve_window(args.window, reference_date)
    engineer_metrics = []
    session_cache = {}

    for engineer in engineers:
        token = resolve_engineer_token(engineer, fallback_token)
        if not token:
            engineer_metrics.append(build_disconnected_metrics(engineer, repositories, "missing_token"))
            continue

        if token not in session_cache:
            session_cache[token] = github_session(token)

        session = session_cache[token]
        repo_scope = engineer["repositories"] or repositories

        try:
            validate_engineer_connection(session, engineer, repo_scope)
            metrics = collect_engineer_activity_metrics(session, engineer, repositories, start_date, end_date)
            engineer_metrics.append(metrics)
        except GitHubApiError as error:
            print(f"Warning for {engineer['username']}: {error}")
            engineer_metrics.append(build_disconnected_metrics(engineer, repositories, "connection_error"))

    summary_markdown = render_summary_markdown(args.window, start_date, end_date, engineer_metrics)
    summary_path = write_summary_readme(args.output_dir, args.window, start_date, end_date, engineer_metrics)
    write_github_step_summary(summary_markdown)
    print(summary_path)
    


if __name__ == "__main__":
    main()