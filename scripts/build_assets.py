"""Build every README panel as a SoftUI-styled SVG, in light and dark variants.

GitHub strips CSS from READMEs, so each section is HTML inside an SVG
<foreignObject>, styled with SoftUI's own tokens: colours, radii and the
dual-shadow formula (github.com/siddharth-bhansali/softui/blob/main/dist/tokens.json).
Links can't live inside images on GitHub, so buttons are separate SVGs that
the README wraps in <a> tags.

Usage: python scripts/build_assets.py   (needs network once, to fetch brand icons)
"""
import base64
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"
W = 940

THEMES = {
    "light": dict(bg="#E4E9F0", hi="#FFFFFF", lo="#B8C0CC",
                  text="#2D3748", muted="#5A6A7E", primary="#5B54E0", wire="#A9B1C2"),
    "dark": dict(bg="#2A2D35", hi="#33363F", lo="#1E2027",
                 text="#E2E8F0", muted="#9BA5B8", primary="#8B85FF", wire="#4A4E5A"),
}

FONT = "'Plus Jakarta Sans', -apple-system, 'Segoe UI', Roboto, sans-serif"
MONO = "'JetBrains Mono', 'Fira Code', Consolas, Menlo, monospace"


def base_css(t):
    return f"""
    .root {{ box-sizing: border-box; width: {W}px; background: {t["bg"]}; border-radius: 24px;
            font-family: {FONT}; color: {t["text"]}; padding: 30px; }}
    .raised {{ background: {t["bg"]}; box-shadow: 6px 6px 14px {t["lo"]}, -6px -6px 14px {t["hi"]}; }}
    .raised-sm {{ background: {t["bg"]}; box-shadow: 3px 3px 8px {t["lo"]}, -3px -3px 8px {t["hi"]}; }}
    .inset {{ background: {t["bg"]}; box-shadow: inset 3px 3px 8px {t["lo"]}, inset -3px -3px 8px {t["hi"]}; }}
    .title {{ display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700;
             margin: 0 0 22px 4px; }}
    .title::before {{ content: ''; width: 6px; height: 20px; border-radius: 9999px; background: {t["primary"]}; }}
    .fade {{ animation: rise .6s ease-out both; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
    """


def svg(t, height, css, body, width=W):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <foreignObject x="0" y="0" width="{width}" height="{height}">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <style>{base_css(t)}{css} .root {{ height: {height}px; box-sizing: border-box; }}</style>
      {body}
    </div>
  </foreignObject>
</svg>
'''


# ---------------------------------------------------------------- icons

def fetch_icon(slug):
    req = urllib.request.Request(f"https://cdn.simpleicons.org/{slug}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        return r.read().decode()


def luminance(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def icon_uri(raw, colour):
    recoloured = re.sub(r'fill="#[0-9A-Fa-f]{6}"', f'fill="{colour}"', raw)
    if 'fill="' not in recoloured:
        recoloured = recoloured.replace("<svg ", f'<svg fill="{colour}" ', 1)
    return "data:image/svg+xml;base64," + base64.b64encode(recoloured.encode()).decode()


def raw_uri(raw):
    return "data:image/svg+xml;base64," + base64.b64encode(raw.encode()).decode()


def brand_colour(raw):
    m = re.search(r'fill="(#[0-9A-Fa-f]{6})"', raw)
    return m.group(1) if m else "#000000"


def themed_colour(raw, t, name):
    c = brand_colour(raw)
    lum = luminance(c)
    if name == "dark" and lum < 0.25:
        return t["text"]
    if name == "light" and lum > 0.85:
        return t["text"]
    return c


LINKEDIN = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#0A66C2" d="M20.45 20.45h-3.56v-5.57'
            'c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 '
            '3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9'
            'h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73'
            'C24 .77 23.2 0 22.22 0z"/></svg>')

# ---------------------------------------------------------------- panels

def header(t, name):
    css = f"""
    .root {{ display: flex; align-items: center; gap: 28px; padding: 34px 36px; }}
    .avatar {{ width: 96px; height: 96px; border-radius: 50%; display: flex; align-items: center;
              justify-content: center; font-size: 34px; font-weight: 800; color: {t["primary"]}; flex: none; }}
    .avatar span {{ width: 76px; height: 76px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
    .main {{ flex: 1; }}
    h1 {{ margin: 0; font-size: 40px; font-weight: 800; letter-spacing: -0.8px; }}
    .role {{ margin: 6px 0 16px; font-size: 16px; color: {t["muted"]}; font-weight: 500; }}
    .term {{ display: inline-flex; align-items: center; gap: 10px; padding: 11px 18px; border-radius: 9999px;
            font-family: {MONO}; font-size: 15px; color: {t["primary"]}; }}
    .term b {{ color: {t["muted"]}; font-weight: 500; }}
    .cursor {{ width: 9px; height: 17px; background: {t["primary"]}; border-radius: 2px; animation: blink 1s steps(1) infinite; }}
    .chips {{ display: flex; flex-direction: column; gap: 12px; flex: none; }}
    .chip {{ padding: 8px 16px; border-radius: 9999px; font-size: 13px; font-weight: 600; text-align: center; }}
    .chip i {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #1FA96E;
              margin-right: 8px; animation: pulse 2s ease-in-out infinite; }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
    @keyframes pulse {{ 50% {{ opacity: .35; }} }}
    """
    body = f'''<div class="root">
        <div class="avatar raised"><span class="inset">SB</span></div>
        <div class="main">
          <h1>Siddharth Bhansali</h1>
          <div class="role">Technical Lead Manager @ Ajackus · India</div>
          <div class="term inset"><b>~ $</b> connecting AI agents to 900+ APIs <span class="cursor"></span></div>
        </div>
        <div class="chips">
          <div class="chip raised-sm"><i></i>Leading a team at One</div>
          <div class="chip raised-sm">TypeScript · Rust</div>
          <div class="chip raised-sm">AI agents · MCP</div>
        </div>
      </div>'''
    return svg(t, 200, css, body)


ABOUT = [
    "Leading a <b>4-engineer integration team</b> at One, the platform that gives AI agents access to 900+ APIs",
    "Built the <b>AI pipeline</b> that turns API docs into agent-ready integrations",
    "Building a multi-tenant <b>GRC platform</b> for a Big Four firm with Next.js, Django &amp; Azure Kubernetes",
    "Working across One's <b>Rust core</b>: OAuth, credential checks, composed actions",
    "Driving <b>AI-assisted development</b> with Claude Code across the team",
    "Side quest: <b>SoftUI</b>, the neumorphic CSS library this README is styled with (3,900+ downloads)",
]

PLATFORMS = ["Gmail", "Stripe", "Slack", "Jira", "Notion", "HubSpot", "GitHub"]


def about(t, name):
    css = f"""
    .wrap {{ display: flex; gap: 30px; align-items: center; }}
    ul {{ list-style: none; margin: 0; padding: 0; flex: 1; display: flex; flex-direction: column; gap: 12px; }}
    li {{ display: flex; align-items: center; gap: 14px; padding: 11px 16px; border-radius: 14px;
         font-size: 14px; line-height: 1.4; }}
    li b {{ color: {t["primary"]}; font-weight: 700; }}
    .dot {{ flex: none; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
    .dot::after {{ content: ''; width: 8px; height: 8px; border-radius: 50%; background: {t["primary"]}; }}
    .flow {{ position: relative; width: 340px; height: 300px; flex: none; }}
    .flow svg.wires {{ position: absolute; inset: 0; }}
    .wire {{ fill: none; stroke: {t["wire"]}; stroke-width: 1.6; stroke-dasharray: 3 6; animation: flow 1.4s linear infinite; }}
    .node {{ position: absolute; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; }}
    .agent {{ left: 0; top: 124px; width: 82px; height: 52px; border-radius: 14px; flex-direction: column; gap: 2px; }}
    .agent small {{ font-size: 9.5px; color: {t["muted"]}; font-weight: 500; }}
    .hub {{ left: 112px; top: 120px; width: 60px; height: 60px; border-radius: 50%; color: {t["primary"]};
           font-size: 15px; font-weight: 800; }}
    .pill {{ left: 226px; width: 112px; height: 26px; border-radius: 9999px; animation: glow 4s ease-in-out infinite; }}
    .more {{ color: {t["muted"]}; font-weight: 500; }}
    @keyframes flow {{ to {{ stroke-dashoffset: -18; }} }}
    @keyframes glow {{ 0%, 70%, 100% {{ color: {t["text"]}; }} 80% {{ color: {t["primary"]}; }} }}
    """
    items = "".join(
        f'<li class="raised-sm fade" style="animation-delay:{i * .08:.2f}s"><span class="dot inset"></span><span>{txt}</span></li>'
        for i, txt in enumerate(ABOUT))
    tops = [6 + i * 36 for i in range(8)]
    wires = '<path class="wire" d="M82 150 L112 150"/>' + "".join(
        f'<path class="wire" d="M172 150 C200 150 200 {y + 13} 226 {y + 13}"/>' for y in tops)
    pills = "".join(
        f'<div class="node pill raised-sm" style="top:{y}px;animation-delay:{i * .5}s">{p}</div>'
        for i, (y, p) in enumerate(zip(tops, PLATFORMS)))
    pills += f'<div class="node pill inset more" style="top:{tops[7]}px">+930 more</div>'
    body = f'''<div class="root">
        <div class="title">About me</div>
        <div class="wrap">
          <ul>{items}</ul>
          <div class="flow">
            <svg class="wires" width="340" height="300" xmlns="http://www.w3.org/2000/svg">{wires}</svg>
            <div class="node agent raised">AI agent<small>"send invoice"</small></div>
            <div class="node hub raised">One</div>
            {pills}
          </div>
        </div>
      </div>'''
    return svg(t, 500, css, body)


CARDS = [
    ("420+", "API integrations built or rebuilt", 45, "45% of One's 937"),
    ("20,000+", "developers building on One", None, None),
    ("~100K", "API calls a day through the catalogue", None, None),
    ("30+", "OAuth connectors shipped", None, None),
    ("70%", "smaller AI-agent knowledge payloads", None, None),
    ("1,000+", "pull requests across 30+ repos", None, None),
]


def highlights(t, name):
    css = f"""
    .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px 20px; }}
    .card {{ border-radius: 16px; padding: 20px 22px; display: flex; flex-direction: column; gap: 6px; height: 132px; box-sizing: border-box; }}
    .value {{ font-size: 32px; font-weight: 800; color: {t["primary"]}; letter-spacing: -0.5px; }}
    .label {{ font-size: 13px; line-height: 1.4; font-weight: 500; }}
    .track {{ margin-top: auto; height: 10px; border-radius: 9999px; overflow: hidden; }}
    .fill {{ height: 100%; border-radius: 9999px; background: {t["primary"]}; transform-origin: left;
            animation: grow 1.4s .6s ease-out both; }}
    .meta {{ font-size: 11px; color: {t["muted"]}; }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
    """
    cards = ""
    for i, (v, label, pct, meta) in enumerate(CARDS):
        meter = (f'<div class="track inset"><div class="fill" style="width:{pct}%"></div></div>'
                 f'<div class="meta">{meta}</div>') if pct else ""
        cards += (f'<div class="card raised fade" style="animation-delay:{i * .1:.1f}s">'
                  f'<div class="value">{v}</div><div class="label">{label}</div>{meter}</div>')
    body = f'<div class="root"><div class="title">Highlights at One</div><div class="cards">{cards}</div></div>'
    return svg(t, 392, css, body)


STACK = [
    ("typescript", "TypeScript"), ("rust", "Rust"), ("python", "Python"), ("php", "PHP"),
    ("nodedotjs", "Node.js"), ("nextdotjs", "Next.js"), ("react", "React"), ("nestjs", "NestJS"),
    ("django", "Django"), ("laravel", "Laravel"), ("postgresql", "Postgres"), ("redis", "Redis"),
    ("docker", "Docker"), ("kubernetes", "Kubernetes"), ("terraform", "Terraform"), ("googlecloud", "GCP"),
    ("githubactions", "Actions"), ("claude", "Claude Code"), ("modelcontextprotocol", "MCP"), ("pnpm", "pnpm"),
]


def stack(t, name, icons):
    css = f"""
    .grid {{ display: grid; grid-template-columns: repeat(10, 1fr); gap: 18px 14px; }}
    .tile {{ display: flex; flex-direction: column; align-items: center; gap: 8px; }}
    .box {{ width: 54px; height: 54px; border-radius: 14px; display: flex; align-items: center; justify-content: center; }}
    .box img {{ width: 26px; height: 26px; }}
    .tile span {{ font-size: 11px; color: {t["muted"]}; font-weight: 600; white-space: nowrap; }}
    """
    tiles = "".join(
        f'<div class="tile fade" style="animation-delay:{i * .02:.2f}s"><div class="box raised-sm">'
        f'<img src="{icon_uri(icons[slug], themed_colour(icons[slug], t, name))}"/></div><span>{label}</span></div>'
        for i, (slug, label) in enumerate(STACK))
    body = f'<div class="root"><div class="title">Tech stack</div><div class="grid">{tiles}</div></div>'
    return svg(t, 290, css, body)


BUTTONS = [("linkedin", "LinkedIn", None), ("x", "@DeathStalkerSid", "x"), ("softui", "SoftUI docs", None)]


def button(t, name, label, icon_uri_):
    css = """
    .btn { margin: 10px; height: 44px; border-radius: 9999px; display: flex; align-items: center; justify-content: center;
           gap: 10px; font-size: 14px; font-weight: 700; }
    .btn img { width: 18px; height: 18px; }
    """
    css += f".wrapb {{ background: transparent; font-family: {FONT}; color: {t['text']}; }}"
    if name == "dark":
        # Buttons sit on GitHub's own page background, not a SoftUI panel, so the
        # light half of the dual shadow reads as a halo on near-black. Use a drop
        # shadow plus a faint top edge instead.
        css += f""".btn {{ background: {t['bg']}; box-shadow: 0 6px 18px rgba(0,0,0,.35), 0 1px 3px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.05); }}"""
        cls = "btn"
    else:
        cls = "btn raised-sm"
    body = f'<div class="wrapb"><div class="{cls}"><img src="{icon_uri_}"/>{label}</div></div>'
    w = 64 + len(label) * 8 + 28
    return svg(t, 64, css, body, width=w)


SOFTUI_MARK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#5B54E0"/>'
               '<circle cx="12" cy="12" r="5" fill="#ffffff" opacity=".85"/></svg>')


def strip_button(t, name, label, icon_uri_, seg):
    radius = {"left": "24px 0 0 24px", "mid": "0", "right": "0 24px 24px 0"}[seg]
    pad = {"left": "18px 10px 18px 26px", "mid": "18px 10px", "right": "18px 26px 18px 10px"}[seg]
    css = f"""
    .plate {{ box-sizing: border-box; height: 84px; background: {t['bg']}; border-radius: {radius}; padding: {pad};
             font-family: {FONT}; color: {t['text']}; }}
    .btn {{ height: 48px; border-radius: 9999px; display: flex; align-items: center; justify-content: center;
           gap: 10px; font-size: 14px; font-weight: 700; }}
    .btn img {{ width: 18px; height: 18px; }}
    """
    w = 40 + len(label) * 8 + 28 + (16 if seg != "mid" else 0)
    body = f'<div class="plate"><div class="btn raised-sm"><img src="{icon_uri_}"/>{label}</div></div>'
    return svg(t, 84, css, body, width=w)


def main():
    icons = {slug: fetch_icon(slug) for slug, _ in STACK}
    icons["x"] = fetch_icon("x")
    for name, t in THEMES.items():
        files = {
            "header": header(t, name),
            "about": about(t, name),
            "highlights": highlights(t, name),
            "stack": stack(t, name, icons),
        }
        files["strip-linkedin"] = strip_button(t, name, "LinkedIn", raw_uri(LINKEDIN), "left")
        files["strip-x"] = strip_button(t, name, "@DeathStalkerSid", icon_uri(icons["x"], t["text"]), "mid")
        files["strip-softui"] = strip_button(t, name, "SoftUI docs", raw_uri(SOFTUI_MARK), "right")
        for stem, content in files.items():
            (OUT / f"{stem}-{name}.svg").write_text(content, encoding="utf-8")
            print(f"wrote assets/{stem}-{name}.svg")


if __name__ == "__main__":
    main()
