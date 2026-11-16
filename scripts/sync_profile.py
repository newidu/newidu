from __future__ import annotations

import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

PROFILE_USER = "newidu"
README = Path(__file__).resolve().parents[1] / "README.md"
START = "<!-- PROJECTS:START -->"
END = "<!-- PROJECTS:END -->"


def github_get(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "newidu-profile-sync",
            **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def all_public_repositories() -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"type": "owner", "sort": "updated", "direction": "desc", "per_page": 100, "page": page})
        batch = github_get(f"https://api.github.com/users/{PROFILE_USER}/repos?{query}")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [repo for repo in repos if not repo.get("private") and repo.get("name") != PROFILE_USER]


def cell(value: object) -> str:
    return html.escape(str(value), quote=False).replace("|", "\\|").replace("\n", " ").strip()


def render(repositories: list[dict]) -> str:
    lines = [
        START,
        "",
        f"_Automatically synced from {len(repositories)} public repositories._",
        "",
        "| Project | Description | Language | Stars | Updated |",
        "| :---: | :---: | :---: | :---: | :---: |",
    ]
    for repo in repositories:
        name = cell(repo.get("name", "project"))
        url = repo.get("html_url", f"https://github.com/{PROFILE_USER}/{name}")
        description = cell(repo.get("description") or "Open-source project by Newidu.")
        language = cell(repo.get("language") or "—")
        stars = int(repo.get("stargazers_count") or 0)
        updated = str(repo.get("updated_at") or "")[:10] or "—"
        lines.append(f"| [{name}]({url}) | {description} | {language} | {stars} | {updated} |")
    if not repositories:
        lines.append(f"| [@{PROFILE_USER}](https://github.com/{PROFILE_USER}) | No public repositories found. | — | 0 | — |")
    lines.extend(["", END])
    return "\n".join(lines)


def main() -> None:
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("README project markers were not found")
    before, remainder = text.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = before + render(all_public_repositories()) + after
    if updated != text:
        README.write_text(updated, encoding="utf-8")
        print("README project index updated")
    else:
        print("README project index already current")


if __name__ == "__main__":
    main()
