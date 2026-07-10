#!/usr/bin/env python3
"""Generate Sergio Peterson's theme-aware GitHub profile cards."""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


USERNAME = "SergioPeterson"
BIRTH_DATE = dt.date(2002, 1, 10)
REST_URL = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
MAX_PAGES = 1_000


@dataclass(frozen=True)
class CommitTotals:
    commits: int = 0
    additions: int = 0
    deletions: int = 0


@dataclass(frozen=True)
class ProfileStats:
    owned_repos: int
    contributed_repos: int
    stars: int
    commits: int
    followers: int
    additions: int
    deletions: int

    @property
    def net_lines(self) -> int:
        return self.additions - self.deletions


def _replace_year(value: dt.date, year: int) -> dt.date:
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)


def _add_months(value: dt.date, months: int) -> dt.date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def calculate_age_parts(born: dt.date, today: dt.date) -> tuple[int, int, int]:
    """Return elapsed calendar years, months, and days."""
    if today < born:
        raise ValueError("today must not be before the birth date")

    years = today.year - born.year - (
        (today.month, today.day) < (born.month, born.day)
    )
    year_anchor = _replace_year(born, born.year + years)
    months = (today.year - year_anchor.year) * 12 + today.month - year_anchor.month
    if today.day < year_anchor.day:
        months -= 1
    month_anchor = _add_months(year_anchor, months)
    return years, months, (today - month_anchor).days


def format_age(born: dt.date, today: dt.date) -> str:
    years, months, days = calculate_age_parts(born, today)
    def unit(value: int, name: str) -> str:
        return f"{value} {name}{'' if value == 1 else 's'}"

    return ", ".join(
        (unit(years, "year"), unit(months, "month"), unit(days, "day"))
    )


def format_number(value: int) -> str:
    return f"{value:,}"


def _history_from_response(response: dict[str, Any]) -> dict[str, Any] | None:
    repository = response.get("repository")
    if not repository:
        return None
    branch = repository.get("defaultBranchRef")
    if not branch:
        return None
    target = branch.get("target")
    if not target:
        return None
    return target.get("history")


def aggregate_commit_history(
    fetch_page: Callable[[str | None], dict[str, Any]],
) -> CommitTotals:
    """Aggregate one repository's authored default-branch commit history."""
    cursor: str | None = None
    seen_cursors: set[str] = set()
    commits = additions = deletions = 0

    for _ in range(MAX_PAGES):
        history = _history_from_response(fetch_page(cursor))
        if not history:
            return CommitTotals(commits, additions, deletions)

        nodes = history.get("nodes") or []
        commits += len(nodes)
        additions += sum(int(node.get("additions") or 0) for node in nodes)
        deletions += sum(int(node.get("deletions") or 0) for node in nodes)

        page_info = history.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            return CommitTotals(commits, additions, deletions)

        next_cursor = page_info.get("endCursor")
        if not next_cursor or next_cursor in seen_cursors:
            raise RuntimeError("GitHub returned a repeated or empty history cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise RuntimeError("GitHub history pagination exceeded the safety limit")


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token

    def _request(
        self,
        url: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SergioPeterson-profile-readme",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API request failed ({error.code}): {detail}"
            ) from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"GitHub API request failed: {error.reason}") from error

    def rest(self, path: str, parameters: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(parameters or {})
        url = f"{REST_URL}{path}"
        if query:
            url = f"{url}?{query}"
        return self._request(url)

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError(
                "GITHUB_TOKEN is required for complete public contribution stats"
            )
        result = self._request(
            GRAPHQL_URL,
            payload={"query": query, "variables": variables},
        )
        if result.get("errors"):
            raise RuntimeError(
                f"GitHub GraphQL request failed: {json.dumps(result['errors'])}"
            )
        return result["data"]


def _public_owned_repositories(
    client: GitHubClient,
) -> tuple[list[str], int]:
    repositories: list[str] = []
    stars = 0
    for page in range(1, MAX_PAGES + 1):
        batch = client.rest(
            f"/users/{USERNAME}/repos",
            {"type": "owner", "sort": "full_name", "per_page": 100, "page": page},
        )
        for repository in batch:
            if repository.get("private"):
                continue
            repositories.append(repository["full_name"])
            stars += int(repository.get("stargazers_count") or 0)
        if len(batch) < 100:
            return repositories, stars
    raise RuntimeError("GitHub repository pagination exceeded the safety limit")


CONTRIBUTED_REPOSITORIES_QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    id
    repositoriesContributedTo(
      first: 100
      after: $after
      includeUserRepositories: false
      privacy: PUBLIC
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, PULL_REQUEST_REVIEW, REPOSITORY]
    ) {
      totalCount
      nodes { nameWithOwner }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


def _public_contributed_repositories(
    client: GitHubClient,
) -> tuple[str, list[str], int]:
    cursor: str | None = None
    seen_cursors: set[str] = set()
    repositories: list[str] = []
    total_count = 0
    user_id = ""

    for _ in range(MAX_PAGES):
        data = client.graphql(
            CONTRIBUTED_REPOSITORIES_QUERY,
            {"login": USERNAME, "after": cursor},
        )
        user = data.get("user")
        if not user:
            raise RuntimeError(f"GitHub user {USERNAME!r} was not found")
        user_id = user["id"]
        connection = user["repositoriesContributedTo"]
        total_count = int(connection["totalCount"])
        repositories.extend(node["nameWithOwner"] for node in connection["nodes"])
        page_info = connection["pageInfo"]
        if not page_info["hasNextPage"]:
            return user_id, repositories, total_count
        next_cursor = page_info["endCursor"]
        if not next_cursor or next_cursor in seen_cursors:
            raise RuntimeError(
                "GitHub returned a repeated or empty repository cursor"
            )
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise RuntimeError("GitHub contribution pagination exceeded the safety limit")


COMMIT_HISTORY_QUERY = """
query(
  $owner: String!
  $name: String!
  $authorId: ID!
  $after: String
) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, after: $after, author: {id: $authorId}) {
            nodes { additions deletions }
            pageInfo { hasNextPage endCursor }
          }
        }
      }
    }
  }
}
"""


def _repository_commit_totals(
    client: GitHubClient,
    repository: str,
    author_id: str,
) -> CommitTotals:
    owner, name = repository.split("/", 1)
    return aggregate_commit_history(
        lambda cursor: client.graphql(
            COMMIT_HISTORY_QUERY,
            {
                "owner": owner,
                "name": name,
                "authorId": author_id,
                "after": cursor,
            },
        )
    )


def fetch_public_stats(client: GitHubClient) -> ProfileStats:
    """Collect stats from public repositories and their default branches."""
    user = client.rest(f"/users/{USERNAME}")
    owned, stars = _public_owned_repositories(client)
    author_id, contributed, contributed_count = (
        _public_contributed_repositories(client)
    )

    totals = CommitTotals()
    for repository in sorted(set(owned) | set(contributed)):
        current = _repository_commit_totals(client, repository, author_id)
        totals = CommitTotals(
            commits=totals.commits + current.commits,
            additions=totals.additions + current.additions,
            deletions=totals.deletions + current.deletions,
        )

    return ProfileStats(
        owned_repos=len(owned),
        contributed_repos=contributed_count,
        stars=stars,
        commits=totals.commits,
        followers=int(user["followers"]),
        additions=totals.additions,
        deletions=totals.deletions,
    )


PALETTES = {
    "dark": {
        "background": "#0d1117",
        "panel": "#161b22",
        "border": "#30363d",
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "accent": "#58a6ff",
        "green": "#3fb950",
        "red": "#f85149",
        "portrait": "#7ee787",
    },
    "light": {
        "background": "#ffffff",
        "panel": "#f6f8fa",
        "border": "#d0d7de",
        "text": "#24292f",
        "muted": "#57606a",
        "accent": "#0969da",
        "green": "#1a7f37",
        "red": "#cf222e",
        "portrait": "#116329",
    },
}


def _text(
    x: int,
    y: int,
    value: str,
    color: str,
    *,
    size: int = 14,
    weight: str = "400",
) -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
        f'font-weight="{weight}">{html.escape(value)}</text>'
    )


def render_svg(
    theme: str,
    portrait: list[str],
    stats: ProfileStats,
    *,
    today: dt.date,
) -> str:
    if theme not in PALETTES:
        raise ValueError(f"Unknown theme: {theme}")
    colors = PALETTES[theme]
    age = format_age(BIRTH_DATE, today)

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="985" height="530" '
        'viewBox="0 0 985 530" role="img" '
        'aria-label="Sergio W. Peterson terminal profile">',
        "<style>"
        "text{font-family:'SFMono-Regular',Consolas,'Liberation Mono',monospace;"
        "white-space:pre}"
        "</style>",
        f'<rect width="985" height="530" rx="14" fill="{colors["background"]}"/>',
        f'<rect x="8" y="8" width="969" height="514" rx="10" '
        f'fill="{colors["panel"]}" stroke="{colors["border"]}"/>',
        '<circle cx="30" cy="29" r="6" fill="#ff5f56"/>',
        '<circle cx="50" cy="29" r="6" fill="#ffbd2e"/>',
        '<circle cx="70" cy="29" r="6" fill="#27c93f"/>',
        _text(492, 34, "sergio@github: ~", colors["muted"], size=12),
        f'<line x1="16" y1="48" x2="969" y2="48" stroke="{colors["border"]}"/>',
    ]

    for index, line in enumerate(portrait[:24]):
        parts.append(
            _text(28, 76 + index * 13, line, colors["portrait"], size=11)
        )

    info = [
        ("$ whoami", colors["green"], 16, "600"),
        ("Sergio W. Peterson", colors["text"], 23, "700"),
        (
            "Founding Engineer @ Mars Accounting / Minerva Intelligence",
            colors["text"],
            13,
            "400",
        ),
        ("AI & Robotics Engineer", colors["accent"], 14, "600"),
        (f"Uptime              {age}", colors["text"], 13, "400"),
        (
            "Stack               Python · PyTorch · TypeScript · React",
            colors["text"],
            13,
            "400",
        ),
        ("                    ROS · Docker · AWS", colors["text"], 13, "400"),
        ("Focus               Robot learning · VLM systems", colors["text"], 13, "400"),
        (
            "                    Evaluation infrastructure",
            colors["text"],
            13,
            "400",
        ),
        ("Web                 sergiopeterson.dev", colors["accent"], 13, "400"),
        (
            "LinkedIn            linkedin.com/in/sergio-w-peterson",
            colors["accent"],
            13,
            "400",
        ),
        (
            "Email               sergiopeterson.dev@gmail.com",
            colors["accent"],
            13,
            "400",
        ),
    ]
    y = 80
    for value, color, size, weight in info:
        parts.append(_text(405, y, value, color, size=size, weight=weight))
        y += 25 if size >= 16 else 21

    parts.extend(
        [
            f'<line x1="28" y1="394" x2="957" y2="394" '
            f'stroke="{colors["border"]}"/>',
            _text(
                28,
                420,
                "$ github-stats --scope public-default-branches",
                colors["green"],
                size=14,
                weight="600",
            ),
            _text(
                720,
                420,
                "Public default-branch data",
                colors["muted"],
                size=11,
            ),
        ]
    )

    left_stats = [
        ("Owned Repos", stats.owned_repos),
        ("Contributed Repos", stats.contributed_repos),
        ("Stars", stats.stars),
        ("Followers", stats.followers),
    ]
    right_stats = [
        ("Commits", stats.commits),
        ("Net Lines", stats.net_lines),
        ("Additions (++)", stats.additions),
        ("Deletions (--)", stats.deletions),
    ]
    for index, (label, value) in enumerate(left_stats):
        parts.append(
            _text(
                40,
                447 + index * 19,
                f"{label:<19} {format_number(value):>12}",
                colors["text"],
                size=12,
            )
        )
    for index, (label, value) in enumerate(right_stats):
        value_color = colors["text"]
        if label == "Additions (++)":
            value_color = colors["green"]
        elif label == "Deletions (--)":
            value_color = colors["red"]
        parts.append(
            _text(
                510,
                447 + index * 19,
                f"{label:<16} {format_number(value):>14}",
                value_color,
                size=12,
            )
        )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        type=dt.date.fromisoformat,
        default=dt.date.today(),
        help="render date in YYYY-MM-DD format (defaults to today)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    portrait = (root / "portrait.txt").read_text(encoding="utf-8").splitlines()
    token = os.environ.get("GITHUB_TOKEN")
    stats = fetch_public_stats(GitHubClient(token))
    for theme in PALETTES:
        output = render_svg(theme, portrait, stats, today=args.date)
        (root / f"{theme}_mode.svg").write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
