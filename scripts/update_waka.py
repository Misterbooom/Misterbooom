"""Update README.md with minimalist WakaTime coding statistics."""

import base64
import json
import os
import re
import urllib.request

ALL_TIME_URL = "https://wakatime.com/api/v1/users/current/all_time_since_today"
LAST_7_DAYS_URL = "https://wakatime.com/api/v1/users/current/stats/last_7_days"
WAKA_SECTION_RE = re.compile(
    r"(<!--START_SECTION:waka-->).*?(<!--END_SECTION:waka-->)",
    re.DOTALL,
)


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


def format_stats(total_text: str, projects: list[dict]) -> str:
    """Format total coding time and top 5 projects into a minimalist code block."""
    lines = [f"Total: {total_text}"]
    top_projects = projects[:5]

    if top_projects:
        name_width = max(len(project["name"]) for project in top_projects)
        time_width = max(len(project["text"]) for project in top_projects)
        pct_strs = [f"{float(project['percent']):.1f}%" for project in top_projects]
        pct_width = max(len(pct) for pct in pct_strs)

        lines.append("")
        for project, pct_str in zip(top_projects, pct_strs):
            lines.append(
                f"{project['name']:<{name_width}}   "
                f"{project['text']:>{time_width}}   "
                f"{pct_str:>{pct_width}}"
            )

    body = "\n".join(lines)
    return f"```text\n{body}\n```"


def update_readme(readme_path: str, stats_block: str) -> bool:
    """Replace the WakaTime section in README.md. Return True if modified."""
    with open(readme_path, "r", encoding="utf-8") as file:
        original = file.read()

    updated, count = WAKA_SECTION_RE.subn(
        lambda m: f"{m.group(1)}\n\n{stats_block}\n\n{m.group(2)}",
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
    projects = last_7_days_data.get("data", {}).get("projects") or []

    stats_block = format_stats(total_text, projects)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_path = os.path.join(repo_root, "README.md")
    update_readme(readme_path, stats_block)


if __name__ == "__main__":
    main()
