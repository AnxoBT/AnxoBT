"""Genera las tarjetas de estadísticas del perfil (SVG) con la API de GitHub.

Sin servicios externos: lo ejecuta un GitHub Action cada día y guarda las imágenes en stats/.
Uso: GH_TOKEN=... python tools/stats.py AnxoBT
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path

API = "https://api.github.com"
OUT = Path(__file__).resolve().parent.parent / "stats"

# Colores habituales de cada lenguaje (los de GitHub); el resto, gris.
LANG_COLORS = {
    "Kotlin": "#A97BFF", "Python": "#3572A5", "Swift": "#F05138", "Java": "#B07219",
    "JavaScript": "#F1E05A", "TypeScript": "#3178C6", "HTML": "#E34C26", "CSS": "#663399",
    "Shell": "#89E051", "Batchfile": "#C1F12E", "PowerShell": "#012456", "C": "#555555",
    "C++": "#F34B7D", "Dart": "#00B4AB", "Go": "#00ADD8", "Rust": "#DEA584", "Ruby": "#701516",
}

TEXT = {
    "en": {
        "stars": "Stars", "commits": "Commits (public)", "prs": "Pull requests", "issues": "Issues",
        "repos": "Public repositories", "langs": "Most used languages",
    },
    "es": {
        "stars": "Estrellas", "commits": "Commits (públicos)", "prs": "Pull requests", "issues": "Incidencias",
        "repos": "Repositorios públicos", "langs": "Lenguajes más usados",
    },
}

THEMES = {
    "light": {"bg": "#FFFFFF", "text": "#1F2328", "muted": "#59636E", "track": "#EFF2F5"},
    "dark": {"bg": "#0D1117", "text": "#E6EDF3", "muted": "#9198A1", "track": "#21262D"},
}


def get(path, **params):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats",
        **({"Authorization": "Bearer " + os.environ["GH_TOKEN"]} if os.environ.get("GH_TOKEN") else {}),
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect(user):
    profile = get(f"/users/{user}")
    repos = [r for r in get(f"/users/{user}/repos", per_page=100, type="owner") if not r["fork"] and not r["private"]]
    languages = {}
    for repo in repos:
        for name, size in get(f"/repos/{user}/{repo['name']}/languages").items():
            languages[name] = languages.get(name, 0) + size
    return {
        "repos": profile["public_repos"],
        "stars": sum(r["stargazers_count"] for r in repos),
        "commits": get("/search/commits", q=f"author:{user}", per_page=1)["total_count"],
        "prs": get("/search/issues", q=f"author:{user} type:pr", per_page=1)["total_count"],
        "issues": get("/search/issues", q=f"author:{user} type:issue", per_page=1)["total_count"],
        "languages": languages,
    }


def font(theme):
    return f"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:{theme}"


def stats_card(data, lang, theme):
    t, c = TEXT[lang], THEMES[theme]
    rows = [("repos", data["repos"]), ("commits", data["commits"]), ("stars", data["stars"]),
            ("prs", data["prs"]), ("issues", data["issues"])]
    lines = "".join(
        f'<text x="24" y="{34 + i * 24}" style="{font(c["muted"])};font-size:14px">{escape(t[key])}</text>'
        f'<text x="316" y="{34 + i * 24}" text-anchor="end" style="{font(c["text"])};font-size:14px;font-weight:600">{value:,}</text>'
        for i, (key, value) in enumerate(rows)
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="340" height="150" viewBox="0 0 340 150">'
            f'<rect width="340" height="150" rx="8" fill="{c["bg"]}"/>{lines}</svg>')


def langs_card(data, lang, theme):
    t, c = TEXT[lang], THEMES[theme]
    total = sum(data["languages"].values()) or 1
    top = sorted(data["languages"].items(), key=lambda item: -item[1])[:6]
    x, bar = 24.0, ""
    for name, size in top:
        width = 292 * size / total
        bar += f'<rect x="{x:.1f}" y="44" width="{width:.1f}" height="8" fill="{LANG_COLORS.get(name, "#8B949E")}"/>'
        x += width
    legend = "".join(
        f'<circle cx="{30 + (i % 2) * 150}" cy="{80 + (i // 2) * 22}" r="5" fill="{LANG_COLORS.get(name, "#8B949E")}"/>'
        f'<text x="{42 + (i % 2) * 150}" y="{85 + (i // 2) * 22}" style="{font(c["text"])};font-size:13px">'
        f'{escape(name)} <tspan style="{font(c["muted"])}">{100 * size / total:.1f}%</tspan></text>'
        for i, (name, size) in enumerate(top)
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="340" height="150" viewBox="0 0 340 150">'
            f'<rect width="340" height="150" rx="8" fill="{c["bg"]}"/>'
            f'<text x="24" y="30" style="{font(c["text"])};font-size:14px;font-weight:600">{escape(t["langs"])}</text>'
            f'<clipPath id="r"><rect x="24" y="44" width="292" height="8" rx="4"/></clipPath>'
            f'<rect x="24" y="44" width="292" height="8" rx="4" fill="{c["track"]}"/><g clip-path="url(#r)">{bar}</g>'
            f'{legend}</svg>')


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "AnxoBT"
    data = collect(user)
    OUT.mkdir(exist_ok=True)
    for lang in TEXT:
        for theme in THEMES:
            (OUT / f"stats-{lang}-{theme}.svg").write_text(stats_card(data, lang, theme), encoding="utf-8")
            (OUT / f"langs-{lang}-{theme}.svg").write_text(langs_card(data, lang, theme), encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k != "languages"}), sorted(data["languages"]))


if __name__ == "__main__":
    main()
