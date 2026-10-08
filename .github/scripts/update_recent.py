"""Refresh Recent projects section in README.md. Stdlib only."""
import json
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) \
    if "__file__" in globals() else os.getcwd()
# When run from repo root as python .github/scripts/update_recent.py, cwd is repo root.
README = os.path.join(os.getcwd(), "README.md")

REPO = os.environ.get("GITHUB_REPOSITORY", "")
OWNER = REPO.split("/")[0] if "/" in REPO else "Saf1thedev"

START = "<!-- RECENT:START -->"
END = "<!-- RECENT:END -->"

def fetch_repos(owner):
    url = f"https://api.github.com/users/{owner}/repos?sort=pushed&per_page=6&type=public"
    req = urllib.request.Request(url, headers={"User-Agent": "profile-update", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"fetch failed: {e}")
        return []

def main():
    repos = fetch_repos(OWNER)
    if not repos:
        print("no repos fetched, keeping README unchanged")
        return
    lines = []
    for repo in repos[:5]:
        name = repo.get("name", "")
        if name.lower() == OWNER.lower():
            continue  # skip profile repo itself
        desc = (repo.get("description") or "").strip().split("\n")[0][:100]
        lang = repo.get("language") or ""
        url = repo.get("html_url", "")
        suffix = f" — {desc}" if desc else (f" — {lang}" if lang else "")
        lines.append(f"- [{name}]({url}){suffix}")
    if not lines:
        lines = ["- No public projects yet."]
    block = START + "\n" + "\n".join(lines) + "\n" + END
    with open(README, encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if START not in content or END not in content:
        print("markers not found")
        return
    new_content = pattern.sub(block, content, count=1)
    if new_content != content:
        with open(README, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
        print("README updated")
    else:
        print("no changes")

if __name__ == "__main__":
    main()
