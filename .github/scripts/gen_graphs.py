#!/usr/bin/env python3
"""
Generate profile graphs using stdlib only.
Outputs:
  - graphs/activity-light.svg, graphs/activity-dark.svg
  - graphs/languages-light.svg, graphs/languages-dark.svg
Only commits when content changes.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
import math

GRAPH_DIR = "graphs"
os.makedirs(GRAPH_DIR, exist_ok=True)

# Palette
ACCENT_DARK = "#cc997f"
ACCENT_LIGHT = "#cd622b"
BG_DARK = "#120f11"
BG_DARK_ALT = "#202226"
BG_LIGHT = "#fdfdfd"
TEXT_DARK = "#fdfdfd"
TEXT_LIGHT = "#120f11"
MUTED_DARK = "#a0a0a0"
MUTED_LIGHT = "#4e4f48"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "morocco-kit-graphs",
}
if "GITHUB_TOKEN" in os.environ:
    HEADERS["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"


def gh_get(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def write_if_changed(path: str, content: str) -> bool:
    if os.path.exists(path):
        with open(path, "r") as f:
            if f.read() == content:
                return False
    with open(path, "w") as f:
        f.write(content)
    return True


# ---------- Contribution Activity (12 months) ----------
def fetch_contributions() -> list[int]:
    repos = gh_get("https://api.github.com/users/Saf1thedev/repos?per_page=100&type=public")
    monthly = [0] * 12
    now = datetime.utcnow()
    for repo in repos:
        if repo.get("fork"):
            continue
        pushed = repo.get("pushed_at")
        if not pushed:
            continue
        try:
            dt = datetime.strptime(pushed, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
        months_ago = (now.year - dt.year) * 12 + (now.month - dt.month)
        if 0 <= months_ago < 12:
            monthly[11 - months_ago] += 1
    return monthly


def render_activity_svg(monthly: list[int], dark: bool) -> str:
    accent = ACCENT_DARK if dark else ACCENT_LIGHT
    bg = BG_DARK if dark else BG_LIGHT
    text = TEXT_DARK if dark else TEXT_LIGHT
    muted = MUTED_DARK if dark else MUTED_LIGHT

    max_val = max(monthly) if max(monthly) > 0 else 1
    bar_w = 38
    gap = 8
    start_x = 60
    bottom_y = 320
    top_y = 60
    height = bottom_y - top_y

    bars = []
    labels = []
    for i, val in enumerate(monthly):
        x = start_x + i * (bar_w + gap)
        bar_h = int((val / max_val) * height)
        y = bottom_y - bar_h
        bars.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" fill="{accent}" rx="3"/>')
        month_dt = datetime.utcnow().replace(day=1) - timedelta(days=30 * (11 - i))
        label = month_dt.strftime("%b")
        labels.append(f'<text x="{x + bar_w/2}" y="{bottom_y + 20}" text-anchor="middle" font-size="11" fill="{muted}" font-family="system-ui">{label}</text>')

    bar_svg = "\n    ".join(bars)
    label_svg = "\n    ".join(labels)

    return f'''<svg width="600" height="400" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="12-month contribution activity">
  <rect width="600" height="400" fill="{bg}"/>
  <text x="300" y="35" text-anchor="middle" font-size="18" font-weight="600" fill="{text}" font-family="system-ui">Contribution Activity (12 months)</text>
  <g transform="translate(0,0)">
    {bar_svg}
    {label_svg}
  </g>
  <text x="300" y="385" text-anchor="middle" font-size="11" fill="{muted}" font-family="system-ui">Generated daily via GitHub Actions · No third-party widgets</text>
</svg>'''