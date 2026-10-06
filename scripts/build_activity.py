"""Render the "Activity" panel as SoftUI-styled SVGs, from GitHub's GraphQL API.

Top: all-time contributions, the last 12 months, share of days with a contribution.
Bottom: contributions per month and the weekly rhythm (contributions by weekday).

Everything comes from the contribution calendar, which includes private work as anonymous
counts, so the workflow's built-in GITHUB_TOKEN is enough and it all updates daily.
If the API fails, the existing images are left untouched.

Usage: STATS_TOKEN=... python scripts/build_activity.py   (locally: STATS_TOKEN=$(gh auth token))
"""
import json
import os
import sys
import urllib.request
from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta, timezone

from build_assets import OUT, THEMES, svg

USER = "siddharth-bhansali"
API = "https://api.github.com/graphql"

# Two accents: indigo (SoftUI primary) for contribution counts, orange for days/rhythm.
# Pair validated with the dataviz checker (lightness band, CVD separation, normal-vision
# floor) in both themes. Colour goes on marks/fills/markers only; orange is below 3:1
# against the surface, so every value is also printed in text ink.
ACCENTS = {
    "light": {"all_time": "#5B54E0", "volume": "#5B54E0", "days": "#eb6834"},
    "dark": {"all_time": "#7A73F0", "volume": "#7A73F0", "days": "#e0703f"},
}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_PLURAL = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"]


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

    # Last 12 months (the API's default window): total and the daily calendar.
    cal = gql(token, """query($u:String!){user(login:$u){contributionsCollection{
      contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}""",
              {"u": USER})["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    months = OrderedDict()
    by_weekday = Counter()
    for d in days:
        months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["contributionCount"]
        by_weekday[d["weekday"]] += d["contributionCount"]  # GitHub: 0 = Sunday

    return {
        "first_year": first_year,
        "all_time": all_time,
        "last_year": cal["totalContributions"],
        "active": sum(1 for d in days if d["contributionCount"] > 0),
        "days": len(days),
        "monthly": list(months.items())[-12:],  # last 12 calendar months, the current one partial
        "weekly": [by_weekday[i] for i in (1, 2, 3, 4, 5, 6, 0)],  # Mon..Sun
    }


def stat_cards(d, accent):
    pct = round(d["active"] / d["days"] * 100)
    cards = [
        (f"{d['all_time']:,}", "contributions on GitHub", accent["all_time"],
         f'<div class="foot inset">since {d["first_year"]}</div>'),
        (f"{d['last_year']:,}", "contributions this past year", accent["volume"],
         '<div class="foot inset">last 12 months</div>'),
        (f"{pct}%", "of days with a contribution", accent["days"],
         f'<div class="foot inset"><div class="fill" style="width:{pct}%;background:{accent["days"]}"></div>'
         f'<span>{d["active"]} of {d["days"]} days</span></div>'),
    ]
    return '<div class="cards">' + "".join(
        f'<div class="card raised fade" style="animation-delay:{i * .1:.1f}s">'
        f'<div class="value">{v}</div><div class="label"><i style="background:{c}"></i>{label}</div>{foot}</div>'
        for i, (v, label, c, foot) in enumerate(cards)) + '</div>'


def columns(t, values, labels, colour, emphasise, height=120, star=None):
    """Columns: <=24px thick, 4px rounded data-end, square at baseline, one hue per chart.
    Static image (no hover), so every column is labelled: muted, emphasised ones in bold."""
    peak = max(values) or 1
    cols = ""
    for i, (v, label) in enumerate(zip(values, labels)):
        strong = i in emphasise
        mark = "*" if i == star else ""
        cols += (f'<div class="col"><div class="val{" strong" if strong else ""}">{v:,}{mark}</div>'
                 f'<div class="track inset"><div class="bar" style="height:{max(2, round(v / peak * height))}px;'
                 f'background:{colour};opacity:{1 if strong else .6};animation-delay:{.3 + i * .05:.2f}s"></div></div>'
                 f'<div class="mon">{label}</div></div>')
    return f'<div class="chart">{cols}</div>'


def activity(t, name, d):
    accent = ACCENTS[name]
    css = f"""
    .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
    .card {{ border-radius: 16px; padding: 20px 18px 18px; display: flex; flex-direction: column; gap: 6px;
            height: 150px; box-sizing: border-box; }}
    .value {{ font-size: 32px; font-weight: 800; color: {t["text"]}; letter-spacing: -0.5px; }}
    .label {{ font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 8px; }}
    .label i {{ width: 10px; height: 10px; border-radius: 3px; flex: none; }}
    .foot {{ flex: none; margin-top: auto; height: 26px; border-radius: 9999px; display: flex; align-items: center;
            padding: 0 12px; font-size: 11px; font-weight: 600; color: {t["muted"]}; position: relative; overflow: hidden; }}
    .foot .fill {{ position: absolute; inset: 0 auto 0 0; border-radius: 9999px; opacity: .28;
                  transform-origin: left; animation: grow 1.2s .5s ease-out both; }}
    .foot span {{ position: relative; }}
    .charts {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-top: 22px; }}
    .panel {{ border-radius: 16px; padding: 20px 22px; box-sizing: border-box; }}
    .ptitle {{ font-size: 13px; font-weight: 700; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }}
    .ptitle i {{ width: 10px; height: 10px; border-radius: 3px; flex: none; }}
    .chart {{ display: flex; align-items: flex-end; gap: 8px; height: 164px; }}
    .col {{ flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; position: relative; }}
    .track {{ width: 22px; height: 120px; border-radius: 8px; display: flex; align-items: flex-end; overflow: hidden; }}
    .bar {{ width: 100%; border-radius: 4px 4px 0 0; transform-origin: bottom; animation: up .9s ease-out both; }}
    .mon {{ font-size: 10px; font-weight: 600; color: {t["muted"]}; }}
    .val {{ position: absolute; top: -18px; font-size: 10px; font-weight: 600; white-space: nowrap; color: {t["muted"]}; }}
    .val.strong {{ font-size: 11px; font-weight: 800; color: {t["text"]}; }}
    .note {{ font-size: 10px; color: {t["muted"]}; margin-top: 8px; }}
    @keyframes up {{ from {{ transform: scaleY(0); }} to {{ transform: scaleY(1); }} }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
    """
    # Monthly: peak + current (partial) month emphasised.
    m_vals = [v for _, v in d["monthly"]]
    m_labels = [date.fromisoformat(ym + "-01").strftime("%b") for ym, _ in d["monthly"]]
    last = len(m_vals) - 1
    monthly = columns(t, m_vals, m_labels, accent["volume"], {m_vals.index(max(m_vals)), last}, star=last)
    current = date.fromisoformat(d["monthly"][last][0] + "-01").strftime("%B")

    # Weekly rhythm: busiest weekday emphasised.
    w_vals = d["weekly"]
    busiest = w_vals.index(max(w_vals))
    weekly = columns(t, w_vals, WEEKDAYS, accent["days"], {busiest})
    rhythm = f"Busiest on {WEEKDAYS_PLURAL[busiest]}"
    if (w_vals[5] + w_vals[6]) / max(1, sum(w_vals)) < .15:
        rhythm += " · weekends mostly off"

    body = (f'<div class="root"><div class="title">Activity</div>{stat_cards(d, accent)}<div class="charts">'
            f'<div class="panel raised fade" style="animation-delay:.3s">'
            f'<div class="ptitle"><i style="background:{accent["volume"]}"></i>Contributions per month</div>'
            f'{monthly}<div class="note">* {current} so far</div></div>'
            f'<div class="panel raised fade" style="animation-delay:.4s">'
            f'<div class="ptitle"><i style="background:{accent["days"]}"></i>Weekly rhythm</div>'
            f'{weekly}<div class="note">{rhythm}</div></div>'
            f'</div></div>')
    return svg(t, 532, css, body)


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
