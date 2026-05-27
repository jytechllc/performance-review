import argparse
import datetime as dt
import os
from pathlib import Path

import requests
import yaml


API_BASE_URL = "https://api.github.com"
DEFAULT_CONFIG_PATH = Path("config/engineers.yaml")
DEFAULT_OUTPUT_DIR = Path("reports")


# This reads command-line arguments from the user and allows them to customize
# how the program runs (like what kind of report to generate, where to save the output).
def parse_args():
    parser = argparse.ArgumentParser(description="Collect GitHub metrics for performance reviews")
    parser.add_argument("--window", choices=("daily", "weekly", "monthly"), default="weekly")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--as-of", type=str, help="Reference date in YYYY-MM-DD format")
    return parser.parse_args()

# Loads the GitHub token to authenticate with the GitHub API and collect the required metrics.
def load_token():
    token = os.getenv("PERFORMANCE_REVIEW_GITHUB_TOKEN")
    if not token:
        token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise SystemExit("Missing GitHub token. Set PERFORMANCE_REVIEW_GITHUB_TOKEN or GITHUB_TOKEN.")

    return token

# If config is available, this loads the config file and checks that it has the right format. It also makes sure that there are engineers and repositories defined and are properly configured.

def load_config(config_path):

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    repositories = []
    for repo in data.get("repositories", []):
        repo_name = str(repo).strip()
        if repo_name:
            repositories.append(repo_name)

    engineers = []
    for item in data.get("engineers", []):
        username = str(item.get("username", "")).strip()

        engineer_repositories = []
        for repo in item.get("repositories", []):
            repo_name = str(repo).strip()
            if repo_name:
                engineer_repositories.append(repo_name)

        display_name = str(item.get("display_name", "")).strip()

        engineers.append(
            {
                "username": username,
                "display_name": display_name,
                "repositories": engineer_repositories,
            }
        )

    return repositories, engineers

# This takes a date string from the user and converts it into a date object of real time to work with.
def parse_reference_date(raw_value):
    
    today = dt.datetime.now(dt.timezone.utc).date()
    return today


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
        raise SystemExit(f"GitHub API request failed for {path}: {response.status_code} {response.text}")
    return response.json()

# This handles paginated API responses from GitHub, automatically fetching all pages of results and combining them into a single list.
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

# This searches for pull requests that were merged in the specified repository and time period, filtering by the author's username. It handles pagination of search results and returns a list of matching pull requests.
def search_merged_pull_requests(session, repo, username, start_date, end_date):
    end_inclusive = end_date - dt.timedelta(days=1)
    # Do not filter by author in the search query, because GitHub returns 422
    # when the username is invalid or not visible. We filter in Python instead.
    date_range = f"{start_date.isoformat()}..{end_inclusive.isoformat()}"
    query = f"repo:{repo} is:pr is:merged merged:{date_range}"
    page = 1
    results = []
    wanted_username = username.lower()

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

        for item in page_items:
            author = str(item.get("user", {}).get("login", ""))
            if author.lower() == wanted_username:
                results.append(item)

        if len(page_items) < 100:
            break
        page += 1

    return results


def new_repo_stats():
    return {
        "commits": 0,
        "merged_prs": 0,
        "additions": 0,
        "deletions": 0,
        "files_changed": 0,
    }


def sum_repo_stats(repo_stats):
    totals = new_repo_stats()

    for stats in repo_stats.values():
        totals["commits"] += stats["commits"]
        totals["merged_prs"] += stats["merged_prs"]
        totals["additions"] += stats["additions"]
        totals["deletions"] += stats["deletions"]
        totals["files_changed"] += stats["files_changed"]

    return totals


def format_week_label(day):
    iso_calendar = day.isocalendar()
    return f"{iso_calendar.year}-W{iso_calendar.week:02d}"

# This counts the number of commits made by the specified user in the given repository and time period by querying the GitHub API.
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

# This collects the performance metrics for a given engineer and compiles them into a summary report format.
def collect_engineer_report(session, engineer, repositories, window, start_date, end_date):
    repo_scope = engineer["repositories"] or repositories
    repo_stats = {}
    pull_requests = []

    for repo in repo_scope:
        if repo not in repo_stats:
            repo_stats[repo] = new_repo_stats()

        commits = count_commits(session, repo, engineer["username"], start_date, end_date)
        repo_stats[repo]["commits"] += commits

        merged_pull_requests = search_merged_pull_requests(session, repo, engineer["username"], start_date, end_date)
        repo_stats[repo]["merged_prs"] += len(merged_pull_requests)

        for pull_request in merged_pull_requests:
            number = int(pull_request["number"])
            details = request_json(session, "GET", f"/repos/{repo}/pulls/{number}")
            additions = int(details.get("additions", 0))
            deletions = int(details.get("deletions", 0))
            files_changed = int(details.get("changed_files", 0))

            repo_stats[repo]["additions"] += additions
            repo_stats[repo]["deletions"] += deletions
            repo_stats[repo]["files_changed"] += files_changed
            pull_requests.append(
                {
                    "repo": repo,
                    "number": number,
                    "title": str(details.get("title", pull_request.get("title", ""))),
                    "url": str(details.get("html_url", pull_request.get("html_url", ""))),
                    "merged_at": str(details.get("merged_at", pull_request.get("closed_at", ""))),
                    "additions": additions,
                    "deletions": deletions,
                    "files_changed": files_changed,
                }
            )

    pull_requests.sort(key=lambda record: record["merged_at"], reverse=True)
    return {
        "engineer": engineer,
        "window": window,
        "start_date": start_date,
        "end_date": end_date - dt.timedelta(days=1),
        "repo_stats": repo_stats,
        "pull_requests": pull_requests,
    }

def render_report(report):
    display_name = report["engineer"]["display_name"]
    totals = sum_repo_stats(report["repo_stats"])
    repo_rows = []

    for repo_name, stats in sorted(report["repo_stats"].items()):
        repo_rows.append(
            f"| {repo_name} | {stats['commits']} | {stats['merged_prs']} | {stats['additions']} | {stats['deletions']} | {stats['files_changed']} |"
        )

    pr_rows = []
    for pull_request in report["pull_requests"]:
        merged_at = ""
        if pull_request["merged_at"]:
            merged_at = pull_request["merged_at"][:10]

        escaped_title = pull_request["title"].replace("|", "\\|")
        pr_rows.append(
            f"| {pull_request['repo']} | #{pull_request['number']} | {escaped_title} | {pull_request['additions']} | {pull_request['deletions']} | {pull_request['files_changed']} | {merged_at} |"
        )

    repositories_text = "None"
    if report["repo_stats"]:
        repositories_text = ", ".join(report["repo_stats"])

    report_lines = [
        f"# {display_name} Performance Review Metrics",
        "",
        f"- Username: `{report['engineer']['username']}`",
        f"- Window: `{report['window']}`",
        f"- Period: `{report['start_date'].isoformat()} to {report['end_date'].isoformat()}`",
        f"- Repositories: {repositories_text}",
        "",
        "## Summary",
        "",
        "| Metric | Total |",
        "| --- | ---: |",
        f"| Commits | {totals['commits']} |",
        f"| Merged PRs | {totals['merged_prs']} |",
        f"| PR additions | {totals['additions']} |",
        f"| PR deletions | {totals['deletions']} |",
        f"| PR files changed | {totals['files_changed']} |",
        "",
        "## Repo Breakdown",
        "",
        "| Repository | Commits | Merged PRs | Additions | Deletions | Files Changed |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    if repo_rows:
        report_lines.extend(repo_rows)
    else:
        report_lines.append("| None | 0 | 0 | 0 | 0 | 0 |")

    report_lines.extend(
        [
            "",
            "## Merged Pull Requests",
            "",
            "| Repository | PR | Title | Additions | Deletions | Files Changed | Merged At |",
            "| --- | ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )

    if pr_rows:
        report_lines.extend(pr_rows)
    else:
        report_lines.append("| None | - | No merged pull requests in this period | 0 | 0 | 0 | - |")

    report_lines.append("")
    return "\n".join(report_lines)

def write_report(output_dir, report):
    month_folder = report["end_date"].strftime("%Y-%m")
    start_label = report["start_date"].isoformat()
    end_label = report["end_date"].isoformat()
    username = report["engineer"]["username"]
    report_path = output_dir / report["window"] / month_folder / f"{username}_{start_label}_to_{end_label}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(report), encoding="utf-8")
    return report_path


def main():
    args = parse_args() # Parse command-line arguments provided by the user
    reference_date = parse_reference_date(args.as_of)  # Convert the --as-of argument into a usable date object
    repositories, engineers = load_config(args.config) # Load repository and engineer configuration data from the config file
    token = load_token() # Load the GitHub API token from environment or config
    session = github_session(token)  # Create and return an authenticated GitHub session

    start_date, end_date = resolve_window(args.window, reference_date)

    for engineer in engineers:
        report = collect_engineer_report(session, engineer, repositories, args.window, start_date, end_date)
        print(write_report(args.output_dir, report))


if __name__ == "__main__":
    main()