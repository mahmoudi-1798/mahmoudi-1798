#!/usr/bin/env python3
"""Draws every image the profile README uses, so nothing depends on a third-party server.

    python3 scripts/render.py            # header + footer only
    GH_TOKEN=xxx python3 scripts/render.py   # + stats, streak, languages (live from the GitHub API)

Output goes to assets/. The GitHub Action in .github/workflows/stats.yml runs this daily.
"""
import base64
import datetime as dt
import json
import math
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
LOGIN = os.environ.get("GH_LOGIN", "mahmoudi-1798")
TOKEN = os.environ.get("GH_TOKEN", "")

# ---- look -----------------------------------------------------------------
WAVE = ("#1a0000", "#5c0a0a", "#8b1a1a")  # front wave: dark -> blood red
WAVE_BACK = ("#a32020", "#6e0f0f", "#3a0606")  # back wave: the same reds, flipped and lighter
CARD_BG, CARD_EDGE = "#110606", "#3d1212"
TITLE, TEXT, MUTED, HOT = "#ff5252", "#ecdcdc", "#9c7474", "#ff6b6b"

NAME = "KOUROSH MAHMOODI"
TAGLINE = "full-stack engineer  //  co-founder @ dokkodo studio  //  C++ survivor"
TYPED = [
    "C++ raised me. Python feeds me.",
    "Segfaults first. Startups later.",
    "Talk is cheap. Show me the commits.",
    "Yes, I build cool shit. On purpose.",
    "rm -rf doubt && make it_work",
]
EXCLUDED_LANGS = {"Jupyter Notebook"}


def font_css() -> str:
    out = []
    for w in (400, 700):
        data = base64.b64encode((ASSETS / "fonts" / f"fira-code-latin-{w}-normal.woff2").read_bytes()).decode()
        out.append(
            f"@font-face{{font-family:'FiraEmbed';font-weight:{w};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
        )
    out.append("text{font-family:'FiraEmbed','Fira Code',ui-monospace,monospace;}")
    return "".join(out)


def svg(w: int, h: int, body: str, extra_css: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f"<style>{font_css()}{extra_css}</style>{body}</svg>\n"
    )


def gradient(gid: str, stops) -> str:
    n = len(stops) - 1
    s = "".join(f'<stop offset="{i / n:.2f}" stop-color="{c}"/>' for i, c in enumerate(stops))
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">{s}</linearGradient>'


# ---- waves ----------------------------------------------------------------
def wave_path(w, h, base, amp, phase, top: bool) -> str:
    """Filled shape with a sine edge. top=True fills from y=0 down to the wave."""
    pts = [(x, base + amp * math.sin(2 * math.pi * x / w * 1.5 + phase)) for x in range(0, w + 1, 10)]
    edge = " ".join(f"L{x},{y:.1f}" for x, y in pts)
    if top:
        return f"M0,0 L{w},0 L{w},{pts[-1][1]:.1f} " + " ".join(
            f"L{x},{y:.1f}" for x, y in reversed(pts)
        ) + " Z"
    return f"M0,{h} L0,{pts[0][1]:.1f} {edge} L{w},{h} Z"


def wave_layer(w, h, base, amp, top, fill, opacity, dur, phase0=0.0, direction=1) -> str:
    frames = [wave_path(w, h, base, amp, phase0 + direction * k * 2 * math.pi / 12, top) for k in range(13)]
    return (
        f'<path d="{frames[0]}" fill="{fill}" opacity="{opacity}">'
        f'<animate attributeName="d" dur="{dur}s" repeatCount="indefinite" values="{";".join(frames)}"/>'
        f"</path>"
    )


# ---- header with typing line ---------------------------------------------
def typing(lines, cx, y, size, color) -> str:
    cw = size * 0.6  # Fira Code advance width is exactly 0.6em
    per_char, hold, erase, gap = 0.06, 1.8, 0.35, 0.3
    slots, t = [], 0.0
    for ln in lines:
        n = len(ln) + 2  # "$ " prompt
        slots.append((t, n))
        t += n * per_char + hold + erase + gap
    total = t
    out = []
    for i, (ln, (start, n)) in enumerate(zip(lines, slots)):
        x0 = cx - n * cw / 2
        end_typing = start + n * per_char
        steps = 6
        # (time, chars shown, cursor visible)
        frames = [(0.0, 0, start == 0)]
        frames += [(start + k * per_char, k, True) for k in range(1, n + 1)]
        frames.append((end_typing + hold, n, True))
        frames += [(end_typing + hold + erase * k / steps, round(n * (1 - k / steps)), k < steps) for k in range(1, steps + 1)]
        dedup = {}
        for tm, c, v in frames:
            dedup[round(tm / total, 5)] = (c, v)
        frames = sorted(dedup.items())
        key_times = ";".join(f"{a:.5f}" for a, _ in frames)
        widths = ";".join(f"{c * cw:.1f}" for _, (c, _) in frames)
        cursor_x = ";".join(f"{x0 + c * cw:.1f}" for _, (c, _) in frames)
        vis = ";".join("1" if v else "0" for _, (_, v) in frames)
        cid = f"clip{i}"
        out.append(
            f'<clipPath id="{cid}"><rect x="{x0:.1f}" y="{y - size}" height="{size * 1.4}" width="0">'
            f'<animate attributeName="width" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{key_times}" values="{widths}"/></rect></clipPath>'
            f'<text x="{x0:.1f}" y="{y}" font-size="{size}" font-weight="700" clip-path="url(#{cid})">'
            f'<tspan fill="#ffffff" opacity="0.55">$ </tspan><tspan fill="{color}">{escape(ln)}</tspan></text>'
            f'<rect y="{y - size * 0.85:.1f}" width="{cw * 0.55:.1f}" height="{size:.0f}" fill="{color}" x="{x0:.1f}" opacity="0">'
            f'<animate attributeName="x" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{key_times}" values="{cursor_x}"/>'
            f'<animate attributeName="opacity" dur="{total:.2f}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{key_times}" values="{vis}"/>'
            f"</rect>"
        )
    return "".join(out)


def header() -> str:
    w, h = 1200, 320
    body = (
        f"<defs>{gradient('g', WAVE)}{gradient('b', WAVE_BACK)}</defs>"
        + wave_layer(w, h, 266, 22, True, "url(#b)", 1, 11, 2.0, -1)
        + wave_layer(w, h, 246, 24, True, "url(#g)", 1, 8)
        + f'<text x="{w / 2}" y="112" font-size="64" font-weight="700" fill="#ffffff" text-anchor="middle" letter-spacing="2">{NAME}</text>'
        + f'<text x="{w / 2}" y="152" font-size="19" fill="#ffd0d0" opacity="0.8" text-anchor="middle">{escape(TAGLINE)}</text>'
        + typing(TYPED, w / 2, 205, 26, "#ffb1b1")
    )
    return svg(w, h, body)


def footer() -> str:
    w, h = 1200, 140
    body = (
        f"<defs>{gradient('g', WAVE[::-1])}{gradient('b', WAVE_BACK[::-1])}</defs>"
        + wave_layer(w, h, 34, 22, False, "url(#b)", 1, 11, 2.0, -1)
        + wave_layer(w, h, 54, 24, False, "url(#g)", 1, 8)
        + f'<text x="{w / 2}" y="112" font-size="18" fill="#ffd0d0" opacity="0.75" text-anchor="middle">/* EOF. go build something. */</text>'
    )
    return svg(w, h, body)


# ---- GitHub data ----------------------------------------------------------
def gql(query: str, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-readme-render"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if data.get("errors"):
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]


def fetch():
    base = gql(
        """query($login:String!){ user(login:$login){
             createdAt
             pullRequests{totalCount} issues{totalCount}
             contributionsCollection{contributionYears} }}""",
        login=LOGIN,
    )["user"]

    repos, cursor = [], None
    while True:
        page = gql(
            """query($login:String!,$after:String){ user(login:$login){
                 repositories(first:100,after:$after,ownerAffiliations:OWNER,isFork:false){
                   pageInfo{hasNextPage endCursor}
                   nodes{ stargazerCount
                     languages(first:20,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}} } } }}""",
            login=LOGIN,
            after=cursor,
        )["user"]["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    days, commits, this_year = {}, 0, 0
    today = dt.datetime.now(dt.timezone.utc).date()
    for year in base["contributionsCollection"]["contributionYears"]:
        c = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
                 contributionsCollection(from:$from,to:$to){
                   totalCommitContributions restrictedContributionsCount
                   contributionCalendar{ weeks{ contributionDays{ date contributionCount } } } } }}""",
            login=LOGIN,
            **{"from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]
        for wk in c["contributionCalendar"]["weeks"]:
            for d in wk["contributionDays"]:
                day = dt.date.fromisoformat(d["date"])
                if day <= today:
                    days[day] = d["contributionCount"]
        if year == today.year:
            this_year = sum(v for k, v in days.items() if k.year == year)

    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            if n in EXCLUDED_LANGS:
                continue
            size, color = langs.get(n, (0, e["node"]["color"]))
            langs[n] = (size + e["size"], color or "#888888")

    return {
        "stars": sum(r["stargazerCount"] for r in repos),
        "repos": len(repos),
        "prs": base["pullRequests"]["totalCount"],
        "issues": base["issues"]["totalCount"],
        "commits": commits,
        "this_year": this_year,
        "days": days,
        "langs": langs,
        "today": today,
    }


def streaks(days: dict, today: dt.date):
    ordered = sorted(days)
    longest, run, run_start, best = 0, 0, None, (None, None)
    for d in ordered:
        if days[d] > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > longest:
                longest, best = run, (run_start, d)
        else:
            run = 0
    # current streak: today with zero contributions doesn't break it yet
    d = today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    cur, cur_end = 0, d
    while days.get(d, 0) > 0:
        cur += 1
        d -= dt.timedelta(days=1)
    cur_range = (d + dt.timedelta(days=1), cur_end) if cur else (None, None)
    return cur, cur_range, longest, best


def fmt_range(r) -> str:
    a, b = r
    if not a:
        return "-"
    f = lambda x: x.strftime("%b %-d, %Y") if x.year != b.year or a == b else x.strftime("%b %-d")
    return f"{f(a)} - {b.strftime('%b %-d, %Y')}" if a != b else b.strftime("%b %-d, %Y")


def card(w, h, title, inner) -> str:
    return svg(
        w,
        h,
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" fill="{CARD_BG}" stroke="{CARD_EDGE}"/>'
        f'<circle cx="22" cy="22" r="5" fill="#ff5f56"/><circle cx="40" cy="22" r="5" fill="#5a1d1d"/><circle cx="58" cy="22" r="5" fill="#5a1d1d"/>'
        f'<text x="78" y="27" font-size="14" font-weight="700" fill="{TITLE}">{escape(title)}</text>'
        f"{inner}",
    )


def stats_card(s) -> str:
    rows = [
        ("commits (incl. private)", s["commits"]),
        (f"contributions in {s['today'].year}", s["this_year"]),
        ("pull requests", s["prs"]),
        ("issues", s["issues"]),
        ("repos owned", s["repos"]),
        ("stars earned", s["stars"]),
    ]
    inner = ""
    for i, (label, val) in enumerate(rows):
        y = 70 + i * 23
        inner += (
            f'<text x="24" y="{y}" font-size="14" fill="{MUTED}">&gt;</text>'
            f'<text x="42" y="{y}" font-size="14" fill="{TEXT}">{escape(label)}</text>'
            f'<text x="470" y="{y}" font-size="15" font-weight="700" fill="{HOT}" text-anchor="end">{val:,}</text>'
        )
    return card(495, 210, "kourosh@github:~$ ./stats", inner)


def streak_card(s) -> str:
    cur, cur_r, longest, long_r = streaks(s["days"], s["today"])
    total = sum(s["days"].values())
    first = min(s["days"]) if s["days"] else s["today"]
    cols = [
        (82, f"{total:,}", "contributions", f"since {first.strftime('%b %Y')}"),
        (247, str(cur), "current streak", fmt_range(cur_r)),
        (412, str(longest), "longest streak", fmt_range(long_r)),
    ]
    inner = f'<line x1="165" y1="60" x2="165" y2="180" stroke="{CARD_EDGE}"/><line x1="330" y1="60" x2="330" y2="180" stroke="{CARD_EDGE}"/>'
    inner += f'<circle cx="247" cy="106" r="36" fill="none" stroke="{HOT}" stroke-width="4" opacity="0.9"/>'
    for x, big, label, sub in cols:
        inner += (
            f'<text x="{x}" y="{117}" font-size="{26 if len(big) < 6 else 22}" font-weight="700" fill="{HOT if x == 247 else TEXT}" text-anchor="middle">{big}</text>'
            f'<text x="{x}" y="166" font-size="13" fill="{TEXT}" text-anchor="middle">{label}</text>'
            f'<text x="{x}" y="186" font-size="11" fill="{MUTED}" text-anchor="middle">{escape(sub)}</text>'
        )
    return card(495, 210, "kourosh@github:~$ ./streak", inner)


def langs_card(s) -> str:
    top = sorted(s["langs"].items(), key=lambda kv: -kv[1][0])[:10]
    total = sum(v[0] for _, v in top) or 1
    w, bar_x, bar_w = 1000, 24, 952
    inner, x = f'<clipPath id="bar"><rect x="{bar_x}" y="50" width="{bar_w}" height="12" rx="6"/></clipPath><g clip-path="url(#bar)">', bar_x
    for name, (size, color) in top:
        seg = bar_w * size / total
        inner += f'<rect x="{x:.2f}" y="50" width="{seg + 0.5:.2f}" height="12" fill="{color}"/>'
        x += seg
    inner += "</g>"
    for i, (name, (size, color)) in enumerate(top):
        cx, cy = 30 + (i % 5) * 192, 94 + (i // 5) * 28
        inner += (
            f'<circle cx="{cx}" cy="{cy - 5}" r="6" fill="{color}"/>'
            f'<text x="{cx + 14}" y="{cy}" font-size="13" fill="{TEXT}">{escape(name)} '
            f'<tspan fill="{MUTED}">{100 * size / total:.1f}%</tspan></text>'
        )
    return card(w, 150, "kourosh@github:~$ ./languages --top 10", inner)


def main():
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "header.svg").write_text(header())
    (ASSETS / "footer.svg").write_text(footer())
    if not TOKEN:
        print("no GH_TOKEN: drew header/footer only")
        return
    s = fetch()
    (ASSETS / "stats.svg").write_text(stats_card(s))
    (ASSETS / "streak.svg").write_text(streak_card(s))
    (ASSETS / "langs.svg").write_text(langs_card(s))
    print(f"drew everything: {s['commits']} commits, {len(s['langs'])} languages")


if __name__ == "__main__":
    main()
