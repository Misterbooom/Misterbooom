"""Update README.md and assets/waka-stats.svg with minimalist dev statistics."""

import base64
from datetime import datetime, timedelta, timezone
import html
import json
import os
import re
import urllib.request

ALL_TIME_URL = "https://wakatime.com/api/v1/users/current/all_time_since_today"
LAST_7_DAYS_URL = "https://wakatime.com/api/v1/users/current/stats/last_7_days"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
WAKA_SECTION_RE = re.compile(
    r"(<!--START_SECTION:waka-->).*?(<!--END_SECTION:waka-->)",
    re.DOTALL,
)

GITHUB_COMMITS_QUERY = """
query($login: String!, $from7: DateTime!, $from1y: DateTime!, $to: DateTime!) {
  user(login: $login) {
    week: contributionsCollection(from: $from7, to: $to) {
      totalCommitContributions
    }
    year: contributionsCollection(from: $from1y, to: $to) {
      totalCommitContributions
    }
  }
}
"""


def build_auth_header(api_key: str) -> str:
    """Build HTTP Basic Auth header value from a WakaTime API key."""
    encoded = base64.b64encode(api_key.encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def fetch_json(url: str, auth_header: str) -> dict:
    """Fetch JSON payload from a WakaTime API endpoint."""
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": auth_header,
            "User-Agent": "waka-readme-python",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_github_commits(username: str, token: str) -> tuple[int, int] | None:
    """Fetch 7-day and 1-year commit counts from GitHub GraphQL API."""
    if not username or not token:
        return None

    now = datetime.now(timezone.utc)
    payload = json.dumps(
        {
            "query": GITHUB_COMMITS_QUERY,
            "variables": {
                "login": username,
                "from7": (now - timedelta(days=7)).isoformat(),
                "from1y": (now - timedelta(days=365)).isoformat(),
                "to": now.isoformat(),
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "waka-readme-python",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        user = (data.get("data") or {}).get("user")
        if not user:
            return None
        week = int(user["week"]["totalCommitContributions"])
        year = int(user["year"]["totalCommitContributions"])
        return week, year
    except Exception:
        return None


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if it exceeds max_len."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _render_rows(
    items: list[dict],
    x_start: int,
    width: int,
    max_name_len: int,
    empty_label: str,
) -> str:
    """Render up to 5 minimalist stat rows with hairline progress bars."""
    if not items:
        return (
            f'  <text x="{x_start}" y="146" class="muted" font-size="13">'
            f"{html.escape(empty_label)}</text>"
        )

    lines = []
    time_x = x_start + width - 54
    pct_x = x_start + width

    for index, item in enumerate(items[:5]):
        y = 140 + index * 26
        name = html.escape(_truncate(str(item.get("name", "Unknown")), max_name_len))
        duration = html.escape(str(item.get("text", "0 mins")))
        percent = max(0.0, min(100.0, float(item.get("percent", 0.0))))
        bar_width = max(2.0, (percent / 100.0) * width) if percent > 0 else 0.0

        lines.append(
            f'  <text x="{x_start}" y="{y}" class="label" font-size="13">{name}</text>'
        )
        lines.append(
            f'  <text x="{time_x}" y="{y}" text-anchor="end" class="mono muted" '
            f'font-size="12">{duration}</text>'
        )
        lines.append(
            f'  <text x="{pct_x}" y="{y}" text-anchor="end" class="mono label" '
            f'font-size="12">{percent:.1f}%</text>'
        )
        lines.append(
            f'  <rect x="{x_start}" y="{y + 6}" width="{width}" height="2" '
            f'rx="1" class="track" />'
        )
        if bar_width > 0:
            lines.append(
                f'  <rect x="{x_start}" y="{y + 6}" width="{bar_width:.1f}" '
                f'height="2" rx="1" class="accent" />'
            )

    return "\n".join(lines)


def render_svg(
    total_text: str,
    projects: list[dict],
    editors: list[dict],
    commits: tuple[int, int] | None,
) -> str:
    """Render a theme-adaptive minimalist SVG card for GitHub README."""
    commits_str = f"{commits[0]:,} / {commits[1]:,}" if commits is not None else "—"
    primary_ide = _truncate(str(editors[0]["name"]), 18) if editors else "—"

    projects_svg = _render_rows(projects, x_start=28, width=364, max_name_len=20, empty_label="No project activity")
    editors_svg = _render_rows(editors, x_start=448, width=324, max_name_len=16, empty_label="No editor activity")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 280" width="800" height="280" role="img" aria-label="Development Stats">
  <style>
    :root {{
      --bg: #0d1117;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --track: #21262d;
      --accent: #58a6ff;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #ffffff;
        --border: #d0d7de;
        --text: #1f2328;
        --muted: #656d76;
        --track: #eaeef2;
        --accent: #0969da;
      }}
    }}
    text {{
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
      font-variant-numeric: tabular-nums;
    }}
    .card {{ fill: var(--bg); stroke: var(--border); }}
    .divider {{ stroke: var(--border); stroke-width: 1; }}
    .label {{ fill: var(--text); }}
    .muted {{ fill: var(--muted); }}
    .track {{ fill: var(--track); }}
    .accent {{ fill: var(--accent); }}
    .kpi-title {{ fill: var(--muted); font-size: 11px; font-weight: 600; letter-spacing: 0.08em; }}
    .kpi-value {{ fill: var(--text); font-size: 20px; font-weight: 600; }}
  </style>

  <rect x="0.5" y="0.5" width="799" height="279" rx="10" class="card" />

  <text x="28" y="38" class="kpi-title">TOTAL CODED</text>
  <text x="28" y="64" class="kpi-value">{html.escape(total_text)}</text>

  <text x="300" y="38" class="kpi-title">COMMITS (7D / 1Y)</text>
  <text x="300" y="64" class="kpi-value mono">{html.escape(commits_str)}</text>

  <text x="560" y="38" class="kpi-title">PRIMARY IDE</text>
  <text x="560" y="64" class="kpi-value">{html.escape(primary_ide)}</text>

  <line x1="28" y1="88" x2="772" y2="88" class="divider" />
  <line x1="420" y1="106" x2="420" y2="254" class="divider" />

  <text x="28" y="114" class="kpi-title">PROJECTS (7D)</text>
{projects_svg}

  <text x="448" y="114" class="kpi-title">EDITORS (7D)</text>
{editors_svg}
</svg>
"""


def write_if_changed(path: str, content: str) -> bool:
    """Write content to path only if it differs from existing content."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            if file.read() == content:
                return False
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return True


def update_readme(readme_path: str, stats_markdown: str) -> bool:
    """Replace the WakaTime section in README.md. Return True if modified."""
    with open(readme_path, "r", encoding="utf-8") as file:
        original = file.read()

    updated, count = WAKA_SECTION_RE.subn(
        lambda m: f"{m.group(1)}\n\n{stats_markdown}\n\n{m.group(2)}",
        original,
        count=1,
    )
    if count == 0:
        raise ValueError(f"WakaTime section markers not found in {readme_path}")

    if updated == original:
        return False

    with open(readme_path, "w", encoding="utf-8") as file:
        file.write(updated)
    return True


def main() -> None:
    api_key = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("WAKATIME_API_KEY environment variable is required")

    auth_header = build_auth_header(api_key)
    all_time_data = fetch_json(ALL_TIME_URL, auth_header)
    last_7_days_data = fetch_json(LAST_7_DAYS_URL, auth_header)

    total_text = all_time_data.get("data", {}).get("text") or "0 secs"
    stats_data = last_7_days_data.get("data", {})
    projects = stats_data.get("projects") or []
    editors = stats_data.get("editors") or []

    github_user = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("GITHUB_ACTOR") or "Misterbooom"
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    commits = fetch_github_commits(github_user, github_token)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    svg_path = os.path.join(repo_root, "assets", "waka-stats.svg")
    readme_path = os.path.join(repo_root, "README.md")

    svg_content = render_svg(total_text, projects, editors, commits)
    write_if_changed(svg_path, svg_content)
    update_readme(readme_path, "![Development Stats](./assets/waka-stats.svg)")


if __name__ == "__main__":
    main()
