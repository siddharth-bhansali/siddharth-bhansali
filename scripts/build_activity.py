"""Render the "Activity" panel as SoftUI-styled SVGs, from GitHub's GraphQL API.

Top: all-time contributions, the last 12 months, code reviews in the last 12 months.
Bottom: contributions per month (columns) and the work mix (100% stacked bar).

Calendar numbers (totals, monthly bars) include private work as anonymous counts, so any
token can read them - the workflow uses its built-in GITHUB_TOKEN. The per-type breakdown of
private client work can't be read from the cloud (client orgs block personal tokens), so the
review count and work mix come from scripts/activity_breakdown.json.
If the API fails, the existing images are left untouched.

Usage: STATS_TOKEN=... python scripts/build_activity.py   (locally: STATS_TOKEN=$(gh auth token))
"""
import json
import os
import sys
import urllib.request
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone

from build_assets import OUT, THEMES, svg

BREAKDOWN = __import__("pathlib").Path(__file__).with_name("activity_breakdown.json")

USER = "siddharth-bhansali"
API = "https://api.github.com/graphql"

# Work-mix palette, validated with the dataviz checker (lightness band, CVD separation,
# normal-vision floor) in both themes, in the adjacent order commits · reviews · PRs.
# Reviews wear SoftUI's indigo as the hero. Segments also carry text labels.
MIX = {
    "light": {"commits": "#1baf7a", "reviews": "#5B54E0", "prs": "#eb6834"},
    "dark": {"commits": "#22a877", "reviews": "#7A73F0", "prs": "#e0703f"},
}
MIX_NAMES = {"commits": "Commits", "reviews": "Code reviews", "prs": "Pull requests"}


def gql(token, query, variables=None):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch(token):
    now = datetime.now(timezone.utc)
    user = gql(token, "query($u:String!){user(login:$u){createdAt}}", {"u": USER})["user"]
    first_year = int(user["createdAt"][:4])

    # All-time: the API caps each contributionsCollection at one year, so sum calendar years.
    q_year = """query($u:String!,$from:DateTime!,$to:DateTime!){user(login:$u){
      contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions}}}}"""
    all_time = 0
    for year in range(first_year, now.year + 1):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = min(datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1), now)
        cc = gql(token, q_year, {"u": USER, "from": start.isoformat(), "to": end.isoformat()})
        all_time += cc["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    # Last 12 months (the API's default window): totals and the daily calendar.
    cc = gql(token, """query($u:String!){user(login:$u){contributionsCollection{
      contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}""",
             {"u": USER})["user"]["contributionsCollection"]
    breakdown = json.loads(BREAKDOWN.read_text(encoding="utf-8"))
    months = OrderedDict()
    for week in cc["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            months[day["date"][:7]] = months.get(day["date"][:7], 0) + day["contributionCount"]

    return {
        "first_year": first_year,
        "all_time": all_time,
        "last_year": cc["contributionCalendar"]["totalContributions"],
        "reviews": breakdown["reviews"],
        "monthly": list(months.items())[-12:],  # last 12 calendar months, the current one partial
        "mix": breakdown["mix"],
    }


def stat_cards(d):
    cards = [
        (f"{d['all_time']:,}", "contributions on GitHub", f"since {d['first_year']}"),
        (f"{d['last_year']:,}", "contributions this past year", "last 12 months"),
        (f"{d['reviews']:,}", "code reviews", "last 12 months"),
    ]
    return '<div class="cards">' + "".join(
        f'<div class="card raised fade" style="animation-delay:{i * .1:.1f}s">'
        f'<div class="value">{v}</div><div class="label">{label}</div>'
        f'<div class="foot inset">{foot}</div></div>'
        for i, (v, label, foot) in enumerate(cards)) + '</div>'


def monthly_bars(t, monthly, height=120):
    """Columns: <=24px thick, 4px rounded data-end, square at baseline, one hue.
    The panel is a static image (no hover), so every month is labelled: muted, with the
    peak and the current (partial) month emphasised."""
    peak = max(v for _, v in monthly)
    peak_i = max(range(len(monthly)), key=lambda i: monthly[i][1])
    last = len(monthly) - 1
    cols = ""
    for i, (ym, v) in enumerate(monthly):
        h = max(2, round(v / peak * height))
        strong = " strong" if i in (peak_i, last) else ""
        star = "*" if i == last else ""
        cur = " cur" if i == last else ""
        month = date.fromisoformat(ym + "-01").strftime("%b")
        cols += (f'<div class="col"><div class="val{strong}">{v:,}{star}</div>'
                 f'<div class="track inset"><div class="bar{cur}" style="height:{h}px;'
                 f'animation-delay:{.3 + i * .05:.2f}s"></div></div><div class="mon">{month}</div></div>')
    current = date.fromisoformat(monthly[last][0] + "-01").strftime("%B")
    css = f"""
    .chart {{ display: flex; align-items: flex-end; gap: 8px; height: {height + 44}px; }}
    .col {{ flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; position: relative; }}
    .track {{ width: 22px; height: {height}px; border-radius: 8px; display: flex; align-items: flex-end; overflow: hidden; }}
    .bar {{ width: 100%; background: {t["primary"]}; border-radius: 4px 4px 0 0; opacity: .55;
           transform-origin: bottom; animation: up .9s ease-out both; }}
    .bar.cur {{ opacity: 1; }}
    .mon {{ font-size: 10px; font-weight: 600; color: {t["muted"]}; }}
    .val {{ position: absolute; top: -18px; font-size: 10px; font-weight: 600; white-space: nowrap; color: {t["muted"]}; }}
    .val.strong {{ font-size: 11px; font-weight: 800; color: {t["text"]}; }}
    .note {{ font-size: 10px; color: {t["muted"]}; margin-top: 8px; }}
    @keyframes up {{ from {{ transform: scaleY(0); }} to {{ transform: scaleY(1); }} }}
    """
    return css, f'<div class="chart">{cols}</div><div class="note">* {current} so far</div>'


def work_mix(t, name, mix):
    """100% stacked bar with 2px surface gaps, plus a legend with direct values
    (identity never relies on colour alone)."""
    total = sum(mix.values())
    pal = MIX[name]
    segs = "".join(f'<div class="seg" style="flex:{v};background:{pal[k]}"></div>' for k, v in mix.items())
    items = "".join(
        f'<div class="item"><i style="background:{pal[k]}"></i><b>{round(v / total * 100)}%</b>'
        f'<span>{MIX_NAMES[k]} · {v:,}</span></div>' for k, v in mix.items())
    css = f"""
    .mix {{ display: flex; gap: 2px; height: 22px; border-radius: 9999px; overflow: hidden; padding: 4px; }}
    .seg {{ height: 100%; transform-origin: left; animation: grow 1s .4s ease-out both; }}
    .seg:first-child {{ border-radius: 9999px 0 0 9999px; }}
    .seg:last-child {{ border-radius: 0 9999px 9999px 0; }}
    .legend {{ display: flex; flex-direction: column; gap: 10px; margin-top: 16px; font-size: 12px; }}
    .item {{ display: flex; align-items: center; gap: 8px; }}
    .item i {{ width: 10px; height: 10px; border-radius: 3px; flex: none; }}
    .item b {{ font-size: 14px; font-weight: 800; }}
    .item span {{ color: {t["muted"]}; font-weight: 500; }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
    """
    return css, f'<div class="mix inset">{segs}</div><div class="legend">{items}</div>'


def activity(t, name, d):
    base = f"""
    .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
    .card {{ border-radius: 16px; padding: 20px 18px 18px; display: flex; flex-direction: column; gap: 6px;
            height: 150px; box-sizing: border-box; }}
    .value {{ font-size: 32px; font-weight: 800; color: {t["primary"]}; letter-spacing: -0.5px; }}
    .label {{ font-size: 13px; font-weight: 500; }}
    .foot {{ flex: none; margin-top: auto; height: 26px; border-radius: 9999px; display: flex; align-items: center;
            padding: 0 12px; font-size: 11px; font-weight: 600; color: {t["muted"]}; }}
    .charts {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-top: 22px; }}
    .panel {{ border-radius: 16px; padding: 20px 22px; box-sizing: border-box; }}
    .ptitle {{ font-size: 13px; font-weight: 700; margin-bottom: 14px; }}
    """
    bars_css, bars = monthly_bars(t, d["monthly"])
    mix_css, mix = work_mix(t, name, d["mix"])
    body = (f'<div class="root"><div class="title">Activity</div>{stat_cards(d)}<div class="charts">'
            f'<div class="panel raised fade" style="animation-delay:.3s"><div class="ptitle">Contributions per month</div>{bars}</div>'
            f'<div class="panel raised fade" style="animation-delay:.4s"><div class="ptitle">Work mix</div>{mix}</div>'
            f'</div></div>')
    return svg(t, 532, base + bars_css + mix_css, body)


def main():
    token = os.environ.get("STATS_TOKEN")
    if not token:
        print("STATS_TOKEN not set, skipping")
        return 0
    try:
        data = fetch(token)
    except Exception as e:  # keep yesterday's images rather than failing the workflow
        print(f"GitHub API unavailable, skipping: {e}")
        return 0
    print({k: v for k, v in data.items() if k != "monthly"})
    for name, t in THEMES.items():
        (OUT / f"activity-{name}.svg").write_text(activity(t, name, data), encoding="utf-8")
        print(f"wrote assets/activity-{name}.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
