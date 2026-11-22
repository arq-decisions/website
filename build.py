"""Baut www.arqdecisions.com als statische Seiten.

Quelle: content/entries.json und content/assets.json (Export aus Contentful vom 21.11.2026,
nur veröffentlichte Einträge, die von einer Seite, dem Menü oder dem Fuß aus erreichbar sind)
und content/site.json (Seitentitel, Beschreibungen, Weiterleitungen alter Adressen).

Aufruf:  python build.py            -> schreibt docs/
         python build.py --serve    -> baut und startet eine Vorschau auf http://localhost:8000
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
E = json.loads((ROOT / "content/entries.json").read_text(encoding="utf-8"))
A = json.loads((ROOT / "content/assets.json").read_text(encoding="utf-8"))
SITE = json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
# Hero-Grafik, erzeugt mit tools/hero_art.py; eingebettet, damit sie die Schriften der Seite nutzt
HERO_ART = (ROOT / "static/img/hero_prognosepfade_v8.svg").read_text(encoding="utf-8").strip()
DOMAIN = SITE["domain"]

esc = lambda s: html.escape(s or "", quote=True)


def F(eid):
    return E[eid]["fields"]


def T(eid):
    return E[eid]["type"]


def lid(v):
    return v["id"] if isinstance(v, dict) and "id" in v else None


# ---------------------------------------------------------------- Seiten und Adressen
PAGES = {i: e for i, e in E.items() if e["type"] == "landingPage"}
SLUG = {i: e["fields"]["slug"] for i, e in PAGES.items()}


def page_href(pid):
    s = SLUG.get(pid)
    if s is None:
        return "./"
    return "./" if s == "home" else s


def slugify(s):
    s = (s or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:48]


# Abschnitt -> Seite und Anker
SECTION_PAGE, SECTION_ANCHOR = {}, {}
for pid, p in PAGES.items():
    used = set()
    for s in p["fields"].get("pageContent") or []:
        sid = s["id"]
        f = F(sid)
        a = f.get("anchor") or slugify(f.get("headline")) or sid
        while a in used:
            a += "-2"
        used.add(a)
        SECTION_PAGE[sid] = pid
        SECTION_ANCHOR[sid] = a


def section_href(sid, current_pid):
    pid = SECTION_PAGE.get(sid)
    a = SECTION_ANCHOR.get(sid, sid)
    if pid is None or pid == current_pid:
        return "#" + a
    return page_href(pid) + "#" + a


INTERNAL = re.compile(r"^https?://(www\.)?arqdecisions\.com(/[^#?]*)?([#?].*)?$")


def link_attrs(uri):
    m = INTERNAL.match(uri)
    if m:
        path = (m.group(2) or "/").strip("/")
        rest = m.group(3) or ""
        return f'href="{esc((path or "./") + rest)}"'
    if uri.startswith(("mailto:", "tel:", "#")):
        return f'href="{esc(uri)}"'
    return f'href="{esc(uri)}" target="_blank" rel="noopener"'


# ---------------------------------------------------------------- Bilder
VIDEO_STEMS = {p.stem for p in (ROOT / "static/img").glob("*.mp4")}


def asset(aid):
    return A.get(aid)


def img_tag(aid, cls="", max_h=None, alt=None, lazy=True):
    a = asset(aid)
    if not a:
        return ""
    src = "static/img/" + a["file"]
    stem = Path(a["file"]).stem
    alt = alt if alt is not None else (a.get("description") or a.get("title") or "")
    if alt in ("Untitled",):
        alt = ""
    style = f' style="max-height:{int(max_h)}px"' if max_h else ""
    if stem in VIDEO_STEMS:
        return (f'<video class="{cls}" src="static/img/{stem}.mp4" autoplay muted loop playsinline '
                f'preload="metadata" aria-label="{esc(alt)}"{style}></video>')
    w, h = a.get("width"), a.get("height")
    dims = f' width="{w}" height="{h}"' if w and h else ""
    loading = ' loading="lazy" decoding="async"' if lazy else ""
    return f'<img class="{cls}" src="{esc(src)}" alt="{esc(alt)}"{dims}{loading}{style}>'


# ---------------------------------------------------------------- Rich Text
def is_empty_para(n):
    if n.get("nodeType") != "paragraph":
        return False
    for c in n.get("content") or []:
        if c.get("nodeType") != "text" or (c.get("value") or "").strip():
            return False
    return True


def rt(node, ctx=None):
    if not node:
        return ""
    t = node.get("nodeType")
    kids = lambda: "".join(rt(c, ctx) for c in node.get("content") or [])
    if t == "document":
        return kids()
    if t == "text":
        s = esc(node.get("value", "")).replace("\n", "<br>")
        for m in node.get("marks") or []:
            tag = {"bold": "strong", "italic": "em", "underline": "u", "code": "code"}.get(m.get("type"))
            if tag:
                s = f"<{tag}>{s}</{tag}>"
        return s
    if t == "paragraph":
        return "" if is_empty_para(node) else f"<p>{kids()}</p>"
    m = re.match(r"heading-(\d)", t or "")
    if m:
        lvl = max(2, int(m.group(1)))
        return f"<h{lvl}>{kids()}</h{lvl}>"
    if t == "hyperlink":
        return f'<a {link_attrs(node["data"].get("uri", "#"))}>{kids()}</a>'
    if t == "entry-hyperlink":
        tid = node["data"]["target"]["sys"]["id"]
        href = page_href(tid) if tid in PAGES else (section_href(tid, ctx) if tid in SECTION_PAGE else "#")
        return f'<a href="{esc(href)}">{kids()}</a>'
    if t == "embedded-asset-block":
        return f'<figure class="rt-img">{img_tag(node["data"]["target"]["sys"]["id"])}</figure>'
    if t == "unordered-list":
        return f"<ul>{kids()}</ul>"
    if t == "ordered-list":
        return f"<ol>{kids()}</ol>"
    if t == "list-item":
        inner = kids()
        inner = re.sub(r"^<p>(.*)</p>$", r"\1", inner, flags=re.S) if inner.count("<p>") == 1 else inner
        return f"<li>{inner}</li>"
    if t == "hr":
        return "<hr>"
    if t == "blockquote":
        return f"<blockquote>{kids()}</blockquote>"
    return kids()


def rt_plain(node):
    out = []

    def w(n):
        if isinstance(n, dict):
            if n.get("nodeType") == "text":
                out.append(n.get("value", ""))
            for c in n.get("content") or []:
                w(c)
            if n.get("nodeType") in ("paragraph", "heading-2", "heading-3", "heading-4", "list-item"):
                out.append(" ")
    w(node)
    return re.sub(r"\s+", " ", "".join(out)).strip()


# ---------------------------------------------------------------- Bausteine
MODALS_USED = set()


def cta(eid, pid, extra=""):
    f = F(eid)
    variant = f.get("variant") or "contained"
    pal = f.get("colorPalette") or "secondary"
    cls = f"btn btn--{variant} btn--{pal} {extra}".strip()
    text = esc(f.get("ctaText"))
    if f.get("modal"):
        mid = lid(f["modal"])
        MODALS_USED.add(mid)
        return f'<button type="button" class="{cls}" data-modal="m-{mid}">{text}</button>'
    if f.get("targetSection"):
        return f'<a class="{cls}" href="{esc(section_href(lid(f["targetSection"]), pid))}">{text}</a>'
    if f.get("targetPage"):
        return f'<a class="{cls}" href="{esc(page_href(lid(f["targetPage"])))}">{text}</a>'
    return ""


def card(eid, pid):
    f = F(eid)
    t = T(eid)
    body = rt(f.get("body"), pid)
    img = lid(f.get("topImage"))
    if t == "testimonialCard":
        a = asset(img) or {}
        photo = {"1IA6hjHX4YAlXCPx4CYAKL": "niklas_wallmeier.jpg", "3IJYoevNy6e0fi5ejBd4sa": "timo_wienefoet.jpg"}.get(img)
        pic = (f'<img class="person-photo" src="static/img/{photo}" alt="{esc(a.get("title"))}" loading="lazy">'
               if photo else img_tag(img, "person-photo"))
        return f'<article class="card card--person">{pic}<div class="card-body">{body}</div></article>'
    pal = f.get("colorPalette") or "light-200"
    max_h = f.get("topImageMaxHeight")
    if img and not rt_plain(f.get("body")):
        return f'<figure class="card card--media">{img_tag(img, "card-media", max_h)}</figure>'
    media = ""
    if img:
        a = asset(img) or {}
        kind = "quote" if a.get("file", "").startswith("zitat_") else ""
        media = f'<div class="card-img {kind}">{img_tag(img, "", max_h)}</div>'
    idx = '<span class="card-index"></span>' if f.get("withIndex") else ""
    quote = " card--quote" if img and (asset(img) or {}).get("file", "").startswith("zitat_") else ""
    return f'<article class="card card--{pal}{quote}">{media}{idx}<div class="card-body">{body}</div></article>'


def link_card(eid, pid):
    f = F(eid)
    href = page_href(lid(f.get("targetPage"))) if f.get("targetPage") else (f.get("externalUrl") or "#")
    ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
    return (f'<a class="linkcard" href="{esc(href)}"{ext}><div class="card-body">{rt(f.get("body"), pid)}</div>'
            f'<span class="linkcard-arrow" aria-hidden="true">→</span></a>')


def block(eid, pid):
    t = T(eid)
    f = F(eid)
    if t == "cardLayout":
        cards = f.get("cards") or []
        n = max(1, min(4, int(f.get("maxPerRow") or 3)))
        inner = "".join(card(c["id"], pid) for c in cards if c["id"] in E)
        return f'<div class="grid grid--{n}" data-count="{len(cards)}">{inner}</div>'
    if t == "linkList":
        return '<div class="linklist">' + "".join(link_card(c["id"], pid) for c in f.get("cards") or []) + "</div>"
    if t == "ctaComponent":
        return f'<div class="cta-row">{cta(eid, pid)}</div>'
    if t == "textBlockComponent":
        return f'<div class="textblock textblock--{f.get("variant") or "normal"} rt">{rt(f.get("body"), pid)}</div>'
    if t in ("simpleCard", "testimonialCard"):
        return f'<div class="grid grid--1">{card(eid, pid)}</div>'
    if t == "linkCard":
        return f'<div class="linklist">{link_card(eid, pid)}</div>'
    return f"<!-- {t} {eid} nicht dargestellt -->"


def section(eid, pid, n):
    f = F(eid)
    variant = f.get("variant") or "transparent"
    align = f.get("paragraphTextAlign") or "left"
    anchor = SECTION_ANCHOR.get(eid, eid)
    head = f'<h2 class="sec-title">{esc(f.get("headline"))}</h2>' if f.get("headline") else ""
    top = "".join(block(b["id"], pid) for b in f.get("topContent") or [] if b["id"] in E)
    body = rt(f.get("contentBody"), pid)
    body = f'<div class="sec-body rt align-{align}">{body}</div>' if body else ""
    bottom = "".join(block(b["id"], pid) for b in f.get("bottomContent") or [] if b["id"] in E)
    return (f'<section class="sec sec--{variant}" id="{esc(anchor)}"><div class="wrap">'
            f"{head}{top}{body}{bottom}</div></section>")


def hero(eid, pid, slug):
    f = F(eid)
    img = lid(f.get("image"))
    a = asset(img) if img else None
    kicker = ""
    if slug in SITE.get("case_slugs", []):
        kicker = '<p class="hero-kicker">Fallbeispiel</p>'
    body = rt(f.get("bodyText"), pid)
    btn = cta(lid(f["cta"]), pid, "btn--hero") if f.get("cta") else ""
    size = " hero--tall" if int(f.get("vhHeight") or 60) >= 66 else ""
    copy = (f'{kicker}<h1>{esc(f.get("headline"))}</h1><div class="hero-text rt">{body}</div>'
            f'{f"<div class=hero-cta>{btn}</div>" if btn else ""}')
    if a and not a["file"].endswith(".svg"):  # Foto als Hintergrund
        return (f'<section class="hero{size}"><img class="hero-bg hero-bg--photo" src="static/img/{a["file"]}" alt="" '
                f'aria-hidden="true"><div class="hero-shade"></div><div class="wrap hero-inner">{copy}</div></section>')
    # Prognosepfade als eigene Spalte neben dem Text; ohne Bild in Contentful gedämpft
    soft = "" if a else " hero--soft"
    return (f'<section class="hero hero--art{soft}{size}"><div class="wrap hero-inner"><div class="hero-copy">{copy}</div>'
            f'<div class="hero-art" aria-hidden="true">{HERO_ART}</div></div></section>')


# ---------------------------------------------------------------- Navigation und Fuß
NAV = next(e for e in E.values() if e["type"] == "navigationMenu")["fields"]
FOOT = next(e for e in E.values() if e["type"] == "footer")["fields"]
NAV_CTA = SITE["nav_cta"]


def nav(pid):
    items = []
    for mi in NAV["menuItems"]:
        f = F(mi["id"])
        name = esc(f.get("groupName"))
        feats = f.get("featuredPages") or []
        if feats:
            sub = "".join(
                f'<li><a href="{esc(page_href(p["id"]))}"{" aria-current=page" if p["id"] == pid else ""}>'
                f'{esc(PAGES[p["id"]]["fields"].get("pageName"))}</a></li>' for p in feats if p["id"] in PAGES)
            active = " is-active" if pid in [p["id"] for p in feats] else ""
            items.append(f'<li class="has-sub{active}"><button type="button" class="nav-link" aria-expanded="false">'
                         f'{name}<span class="caret" aria-hidden="true"></span></button><ul class="sub">{sub}</ul></li>')
        else:
            tp, ts = lid(f.get("targetPage")), lid(f.get("targetSection"))
            href = section_href(ts, pid) if ts else page_href(tp)
            if ts and SECTION_PAGE.get(ts) == pid:
                href = "#" + SECTION_ANCHOR[ts]
            cur = " aria-current=page" if (tp == pid and not ts) else ""
            items.append(f'<li><a class="nav-link" href="{esc(href)}"{cur}>{name}</a></li>')
    MODALS_USED.add(NAV_CTA["modal"])
    return f"""<header class="site-header" id="top">
  <div class="wrap header-inner">
    <a class="brand" href="./" aria-label="arq decisions – Startseite">
      <img class="logo logo--white" src="static/img/logo_arq_weiss.png" alt="arq decisions" width="160" height="80">
      <img class="logo logo--color" src="static/img/logo_arq.png" alt="" width="160" height="80" aria-hidden="true">
    </a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav"><span></span><span></span><span></span><span class="sr">Menü</span></button>
    <nav id="nav" class="nav" aria-label="Hauptmenü">
      <ul class="nav-list">{"".join(items)}</ul>
      <button type="button" class="btn btn--contained btn--nav" data-modal="m-{NAV_CTA['modal']}">{esc(NAV_CTA['text'])}</button>
    </nav>
  </div>
</header>"""


def footer(pid):
    left = []
    contacts = ""
    for x in FOOT["leftSideContent"]:
        if T(x["id"]) == "textBlockComponent":
            left.append(f'<div class="rt">{rt(F(x["id"]).get("body"), pid)}</div>')
        elif T(x["id"]) == "contactLinksGroup":
            rows = []
            for c in F(x["id"]).get("contactLinks") or []:
                cf = F(c["id"])
                if cf.get("type") == "location":
                    rows.append(f'<li class="ico ico--pin"><a href="{esc(cf["value"])}" target="_blank" rel="noopener">'
                                f'{esc(cf.get("placeholder") or cf["value"])}</a></li>')
                elif cf.get("type") == "email":
                    rows.append(f'<li class="ico ico--mail">{esc((cf.get("value") or "").strip())}</li>')
            contacts = f'<ul class="contacts">{"".join(rows)}</ul>'
    imprint, contact_line = (left + ["", ""])[:2]
    # rechte Seite: Text mit Logos und Datenschutz-Link
    right_body = None
    social = ""
    for x in FOOT["rightSideContent"]:
        if T(x["id"]) == "textBlockComponent":
            right_body = F(x["id"]).get("body")
        elif T(x["id"]) == "socialMediaLinksGroup":
            sl = F(x["id"]).get("socialMediaLinks")
            sl = sl if isinstance(sl, list) else [sl]
            for s in sl:
                sf = F(s["id"])
                social += (f'<a class="social" href="{esc(sf["link"])}" target="_blank" rel="noopener" '
                           f'aria-label="arq decisions auf LinkedIn">{SVG_LINKEDIN}</a>')
    right = ""
    if right_body:
        nodes = right_body.get("content") or []
        imgs = [n for n in nodes if n.get("nodeType") == "embedded-asset-block"]
        rest = {"nodeType": "document", "content": [n for n in nodes if n.get("nodeType") != "embedded-asset-block"]}
        badges = ""
        for n in imgs:
            aid = n["data"]["target"]["sys"]["id"]
            if aid == "54sTaBBt6D14P5o3jjjNMk":  # Logo (salbei) -> weiße Fassung laut Markenhandbuch
                badges += '<img class="foot-logo" src="static/img/logo_arq_weiss.svg" alt="arq decisions" width="90" height="46">'
            else:
                badges += img_tag(aid, "foot-badge")
        right = f'<div class="foot-badges">{badges}</div><div class="rt">{rt(rest, pid)}</div>'
    year = date.today().year
    return f"""<footer class="site-footer">
  <div class="wrap foot-grid">
    <div class="foot-imprint">{imprint}</div>
    <div class="foot-contact">{contact_line}{contacts}</div>
    <div class="foot-right">{right}<div class="foot-social">{social}</div></div>
  </div>
  <div class="wrap foot-bottom"><span>© {year} arq decisions GmbH</span><a href="#top">Nach oben ↑</a></div>
</footer>"""


SVG_LINKEDIN = ('<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M20.45 20.45h-3.56v-5.57'
                'c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 '
                '4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 '
                '0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg>')


def modals(pid):
    out = []
    for mid in sorted(MODALS_USED):
        if mid not in E:
            continue
        f = F(mid)
        frame = ""
        if f.get("iFrame"):
            ff = F(lid(f["iFrame"]))
            src = ff.get("src", "")
            frame = (f'<div class="modal-frame"><iframe data-src="{esc(src)}" title="Termin buchen" loading="lazy"></iframe></div>'
                     f'<p class="modal-alt"><a href="{esc(src)}" target="_blank" rel="noopener">Terminbuchung in neuem Fenster öffnen ↗</a></p>')
        out.append(f"""<dialog class="modal{' modal--wide' if frame else ''}" id="m-{mid}" aria-labelledby="m-{mid}-t">
  <button type="button" class="modal-close" data-close aria-label="Schließen">×</button>
  <h2 id="m-{mid}-t">{esc(f.get("title"))}</h2>
  <div class="rt">{rt(f.get("bodyText"), pid)}</div>{frame}
</dialog>""")
    return "\n".join(out)


# ---------------------------------------------------------------- Seite
def head(title, desc, canonical, noindex=False, extra=""):
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
{robots}
<meta property="og:type" content="website">
<meta property="og:site_name" content="arq decisions">
<meta property="og:locale" content="de_DE">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{DOMAIN}/static/img/og_arq.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#135b49">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" href="favicon.png" type="image/png">
<link rel="apple-touch-icon" href="static/img/apple-touch-icon.png">
<link rel="preload" href="static/fonts/roboto-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="static/fonts/roboto-condensed-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="static/css/site.css?v={VERSION}">
{extra}
</head>"""


def build_page(pid):
    global MODALS_USED
    MODALS_USED = set()
    p = PAGES[pid]["fields"]
    slug = p["slug"]
    meta = SITE["pages"].get(slug, {})
    hero_id = lid(p.get("hero"))
    hf = F(hero_id) if hero_id else {}
    title = meta.get("title") or f'{p.get("pageName")} | arq decisions'
    desc = meta.get("description") or (rt_plain(hf.get("bodyText")) or hf.get("headline") or "")[:158]
    canonical = DOMAIN + ("/" if slug == "home" else "/" + slug)
    nav_html = nav(pid)
    hero_html = hero(hero_id, pid, slug) if hero_id else ""
    sections = "".join(section(s["id"], pid, i) for i, s in enumerate(p.get("pageContent") or []) if s["id"] in E)
    foot = footer(pid)
    ld = ""
    if slug == "home":
        ld = '<script type="application/ld+json">' + json.dumps(SITE["jsonld"], ensure_ascii=False) + "</script>"
    body_cls = "page-" + slug
    return (head(title, desc, canonical, noindex=meta.get("noindex", False), extra=ld)
            + f'\n<body class="{body_cls}">\n<a class="skip" href="#main">Zum Inhalt</a>\n{nav_html}\n<main id="main">\n'
            + hero_html + sections + f"\n</main>\n{foot}\n{modals(pid)}\n"
            + f'<script src="static/js/site.js?v={VERSION}" defer></script>\n</body>\n</html>\n')


def redirect_page(target, base="./"):
    url = DOMAIN + "/" + target.lstrip("./")
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Weiterleitung</title>
<meta name="robots" content="noindex"><link rel="canonical" href="{esc(url)}">
<meta http-equiv="refresh" content="0; url={esc(base + target)}"></head>
<body><p>Diese Seite ist umgezogen: <a href="{esc(base + target)}">weiter</a>.</p></body></html>"""


def build_404():
    global MODALS_USED
    MODALS_USED = set()
    home = next(i for i, s in SLUG.items() if s == "home")
    nav_html = nav(None)
    foot = footer(None)
    base = SITE.get("base", "/")
    body = f"""<section class="hero"><img class="hero-bg hero-bg--soft" src="static/img/hero_prognosepfade_v6.svg" alt="" aria-hidden="true"><div class="hero-shade"></div>
<div class="wrap hero-inner"><p class="hero-kicker">Fehler 404</p><h1>Diese Seite gibt es nicht.</h1>
<div class="hero-text rt"><p>Vielleicht hilft einer dieser Wege weiter.</p></div>
<div class="hero-cta"><a class="btn btn--contained btn--secondary btn--hero" href="./">Zur Startseite</a></div></div></section>
<section class="sec sec--transparent"><div class="wrap"><div class="linklist">""" + "".join(
        f'<a class="linkcard" href="{esc(page_href(i))}"><div class="card-body"><h4>{esc(PAGES[i]["fields"]["pageName"])}</h4></div>'
        f'<span class="linkcard-arrow" aria-hidden="true">→</span></a>'
        for i in [k for k, s in SLUG.items() if s in ("perspektiv", "radar", "fallbeispiele", "forschung")]) + "</div></div></section>"
    return (head("Seite nicht gefunden | arq decisions", "Diese Seite gibt es nicht.", DOMAIN + "/404", noindex=True,
                 extra=f'<base href="{esc(base)}">')
            + f'\n<body class="page-404">\n{nav_html}\n<main id="main">{body}</main>\n{foot}\n{modals(home)}\n'
            + f'<script src="static/js/site.js?v={VERSION}" defer></script>\n</body>\n</html>\n')


VERSION = date.today().strftime("%Y%m%d")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")
    for f in ("favicon.ico", "favicon.png"):
        shutil.copy(ROOT / "static" / f, OUT / f)
    urls = []
    for pid, p in PAGES.items():
        slug = p["fields"]["slug"]
        name = "index.html" if slug == "home" else f"{slug}.html"
        (OUT / name).write_text(build_page(pid), encoding="utf-8", newline="\n")
        if not SITE["pages"].get(slug, {}).get("noindex"):
            urls.append(DOMAIN + ("/" if slug == "home" else "/" + slug))
    (OUT / "404.html").write_text(build_404(), encoding="utf-8", newline="\n")
    for old, new in SITE["redirects"].items():
        (OUT / f"{old}.html").write_text(redirect_page(new), encoding="utf-8", newline="\n")
    today = date.today().isoformat()
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in sorted(urls))
        + "</urlset>\n", encoding="utf-8", newline="\n")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8", newline="\n")
    if SITE.get("cname"):
        (OUT / "CNAME").write_text(SITE["cname"] + "\n", encoding="utf-8", newline="\n")
    (OUT / ".nojekyll").write_text("", encoding="utf-8", newline="\n")
    print(f"{len(PAGES)} Seiten, {len(SITE['redirects'])} Weiterleitungen -> {OUT}")


def serve(port=8000):
    import http.server
    import functools

    class H(http.server.SimpleHTTPRequestHandler):
        def send_head(self):
            path = self.translate_path(self.path)
            p = Path(path)
            if not p.exists() and Path(path + ".html").exists():
                self.path = self.path.split("?")[0] + ".html"
            elif not p.exists():
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                body = (OUT / "404.html").read_bytes()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return None
            return super().send_head()

        def log_message(self, *a):
            pass

    http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=str(OUT))).serve_forever()


if __name__ == "__main__":
    main()
    if "--serve" in sys.argv:
        print("Vorschau: http://localhost:8000")
        serve()
