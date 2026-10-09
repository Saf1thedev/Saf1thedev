#!/usr/bin/env python3
"""Generate profile graphs as self-contained SVGs (stdlib only).

Outputs, in graphs/:
  activity-{dark,light}.svg   weekly public contributions, last 12 months
  languages-{dark,light}.svg  language breakdown of public, non-fork repos

Environment:
  GITHUB_TOKEN  token provided by GitHub Actions (read-only use)
  GH_USER       GitHub login (defaults to the repository owner)
  OUT_DIR       output folder (default: graphs)

Flags:
  --placeholder  write neutral "updates daily" images (no data, no network)
  --selftest     render with fake data into /tmp (visual check only)
"""
import datetime as dt
import html
import json
import os
import pathlib
import sys
import urllib.request

USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "Saf1thedev"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = pathlib.Path(os.environ.get("OUT_DIR", "graphs"))

THEMES = {
    "dark": dict(bg="#0D1117", card="#161B22", text="#E6EDF3", muted="#8B949E", accent="#3FB8A0", line="#30363D"),
    "light": dict(bg="#FFFFFF", card="#F6F8FA", text="#1F2328", muted="#59636E", accent="#0F766E", line="#D1D9E0"),
}
FONT = '-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif'


def http(url, data=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-graphs"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_weeks():
    query = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{totalContributions weeks{firstDay contributionDays{contributionCount}}}}}}"""
    res = http("https://api.github.com/graphql", {"query": query, "variables": {"login": USER}})
    if "errors" in res or not res.get("data", {}).get("user"):
        raise RuntimeError(f"GraphQL error: {res.get('errors') or 'user not found'}")
    cal = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [(w["firstDay"], sum(d["contributionCount"] for d in w["contributionDays"])) for w in cal["weeks"]]
    return weeks, cal["totalContributions"]


def fetch_languages():
    totals = {}
    page = 1
    while True:
        repos = http(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo.get("fork") or repo.get("archived") or repo.get("name", "").lower() == USER.lower():
                continue
            for lang, n in http(repo["languages_url"]).items():
                totals[lang] = totals.get(lang, 0) + n
        if len(repos) < 100:
            break
        page += 1
    return totals


def frame(t, w, h, title, subtitle, body, label):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(label)}">
<title>{html.escape(label)}</title>
<rect width="{w}" height="{h}" rx="10" fill="{t['card']}" stroke="{t['line']}"/>
<text x="24" y="38" font-family='{FONT}' font-size="17" font-weight="600" fill="{t['text']}">{html.escape(title)}</text>
<text x="24" y="60" font-family='{FONT}' font-size="13" fill="{t['muted']}">{html.escape(subtitle)}</text>
{body}
</svg>
"""


def activity_svg(t, weeks, total):
    w, h = 900, 260
    left, right, top, bottom = 24, 24, 84, 44
    cw, ch = w - left - right, h - top - bottom
    peak = max([c for _, c in weeks] + [1])
    n = len(weeks)
    step = cw / n
    bw = max(step - 3, 2)
    parts = [f'<line x1="{left}" y1="{top+ch}" x2="{w-right}" y2="{top+ch}" stroke="{t["line"]}"/>']
    last_month = None
    for i, (day, c) in enumerate(weeks):
        x = left + i * step
        bh = 0 if c == 0 else max(3, ch * c / peak)
        if bh:
            parts.append(f'<rect x="{x:.1f}" y="{top+ch-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" fill="{t["accent"]}"><title>{day}: {c}</title></rect>')
        else:
            parts.append(f'<rect x="{x:.1f}" y="{top+ch-2}" width="{bw:.1f}" height="2" rx="1" fill="{t["line"]}"/>')
        month = day[:7]
        if month != last_month and i < n - 2:
            parts.append(f'<text x="{x:.1f}" y="{h-18}" font-family=\'{FONT}\' font-size="11" fill="{t["muted"]}">{dt.date.fromisoformat(day).strftime("%b")}</text>')
            last_month = month
    label = f"Weekly public contributions over the last 12 months: {total} total"
    return frame(t, w, h, "Contribution activity", f"{total} public contributions in the last 12 months (weekly totals)", "\n".join(parts), label)


def languages_svg(t, totals):
    top_langs = sorted(totals.items(), key=lambda kv: -kv[1])[:6]
    whole = sum(totals.values()) or 1
    w = 900
    row = 34
    h = 84 + row * max(len(top_langs), 1) + 20
    parts = []
    bar_x, bar_w = 190, 560
    for i, (lang, n) in enumerate(top_langs):
        y = 90 + i * row
        pct = 100 * n / whole
        parts.append(f'<text x="24" y="{y+13}" font-family=\'{FONT}\' font-size="14" fill="{t["text"]}">{html.escape(lang)}</text>')
        parts.append(f'<rect x="{bar_x}" y="{y}" width="{bar_w}" height="16" rx="8" fill="{t["line"]}"/>')
        parts.append(f'<rect x="{bar_x}" y="{y}" width="{max(bar_w*pct/100, 6):.1f}" height="16" rx="8" fill="{t["accent"]}"/>')
        parts.append(f'<text x="{bar_x+bar_w+16}" y="{y+13}" font-family=\'{FONT}\' font-size="13" fill="{t["muted"]}">{pct:.1f}%</text>')
    summary = ", ".join(f"{l} {100*n/whole:.0f}%" for l, n in top_langs)
    return frame(t, w, h, "Languages", "Public, non-fork repositories (by bytes of code)", "\n".join(parts), f"Language breakdown: {summary}")


def placeholder_svg(t, title, message, label):
    w, h = 900, 150
    body = f'<text x="24" y="104" font-family=\'{FONT}\' font-size="14" fill="{t["muted"]}">{html.escape(message)}</text>'
    return frame(t, w, h, title, "Generated by a GitHub Action, no third-party widgets", body, label)


def write(name, svg):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(svg, encoding="utf-8")
    print("wrote", OUT / name)


def main():
    if "--placeholder" in sys.argv:
        for mode, t in THEMES.items():
            write(f"activity-{mode}.svg", placeholder_svg(t, "Contribution activity", "This chart appears after the first scheduled run.", "Contribution activity placeholder"))
            write(f"languages-{mode}.svg", placeholder_svg(t, "Languages", "This chart appears after the first scheduled run.", "Languages placeholder"))
            write(f"snake-{mode}.svg", placeholder_svg(t, "Contribution snake", "This animation appears after the first scheduled run.", "Contribution snake placeholder"))
        return 0

    if "--selftest" in sys.argv:
        global OUT
        OUT = pathlib.Path("/tmp/selftest")
        base = dt.date(2025, 10, 5)
        weeks = [((base + dt.timedelta(weeks=i)).isoformat(), (i * 7) % 23 if i % 5 else 0) for i in range(53)]
        langs = {"TypeScript": 163000, "PLpgSQL": 32000, "CSS": 9000, "JavaScript": 4000}
        for mode, t in THEMES.items():
            write(f"activity-{mode}.svg", activity_svg(t, weeks, sum(c for _, c in weeks)))
            write(f"languages-{mode}.svg", languages_svg(t, langs))
        return 0

    ok = True
    try:
        weeks, total = fetch_weeks()
        for mode, t in THEMES.items():
            write(f"activity-{mode}.svg", activity_svg(t, weeks, total))
    except Exception as e:  # keep the previous image, but make the run fail visibly
        print("activity failed:", e, file=sys.stderr)
        ok = False
    try:
        langs = fetch_languages()
        if langs:
            for mode, t in THEMES.items():
                write(f"languages-{mode}.svg", languages_svg(t, langs))
        else:
            print("no languages found; keeping previous image")
    except Exception as e:
        print("languages failed:", e, file=sys.stderr)
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
