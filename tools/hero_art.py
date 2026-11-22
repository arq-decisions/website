"""Erzeugt die Hero-Grafik (Prognosepfade) als SVG für die Startseite und die anderen Hero-Bereiche.

Aufbau von links nach rechts: vergangene Pfade (verästelt, links ausgeblendet), der tatsächlich gegangene Weg
bis zum Jetzt-Punkt, drei mögliche Zukünfte mit Fragezeichen, deren Spuren sich weiter verzweigen, und rechts
die Wahrscheinlichkeiten, die im Takt wechseln. Die Grafik wird von build.py direkt in die Seite eingebettet,
damit sie die Schriften der Seite nutzt (Roboto Condensed für Fragezeichen und Zahlen).

    python tools/hero_art.py   ->  static/img/hero_prognosepfade_v7.svg
"""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "img" / "hero_prognosepfade_v7.svg"

W, H = 1000, 800
WHITE, SAGE, CRIMSON_LIGHT, CRIMSON, GREEN, GREEN_DEEP = "#ffffff", "#9dc09f", "#e05a78", "#bb2649", "#135b49", "#0f3d32"
FONT = "'Roboto Condensed', 'Arial Narrow', Arial, sans-serif"

NOW = (400, 400)
Q1_X, Q2_X, TRAIL_END_X, PILL_X = 530, 680, 790, 902
BRANCHES = [  # y, Linienfarbe, Pille (Füllung, Schrift), Werte im Takt, Startverzögerung obere/untere Spur
    (170, WHITE, (WHITE, GREEN), ("52 %", "47 %", "55 %", "61 %"), (-16.0, -9.0)),
    (400, CRIMSON_LIGHT, (CRIMSON, WHITE), ("15 %", "18 %", "14 %", "12 %"), (-12.0, -5.0)),
    (630, SAGE, (SAGE, GREEN_DEEP), ("33 %", "35 %", "31 %", "27 %"), (-14.0, -7.0)),
]
SPREAD_Q2, SPREAD_END = 65, 88


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def curve(p0, p1, k=0.45):
    """Kubischer S-Bogen von p0 nach p1 (horizontale Tangenten), als Kontrollpunkte."""
    dx = (p1[0] - p0[0]) * k
    return p0, (p0[0] + dx, p0[1]), (p1[0] - dx, p1[1]), p1


def d_of(c):
    a, b, cc, d = c
    return f"M{f(a[0])},{f(a[1])} C{f(b[0])},{f(b[1])} {f(cc[0])},{f(cc[1])} {f(d[0])},{f(d[1])}"


def bez(c, t):
    a, b, cc, d = c
    u = 1 - t
    return (u**3 * a[0] + 3 * u * u * t * b[0] + 3 * u * t * t * cc[0] + t**3 * d[0],
            u**3 * a[1] + 3 * u * u * t * b[1] + 3 * u * t * t * cc[1] + t**3 * d[1])


def sample(curves, step):
    """Punkte in gleichem Bogenabstand entlang mehrerer Kurven."""
    pts = []
    for c in curves:
        pts += [bez(c, i / 400) for i in range(401)]
    out, acc = [pts[0]], 0.0
    for p, q in zip(pts, pts[1:]):
        acc += math.dist(p, q)
        if acc >= step:
            out.append(q)
            acc = 0.0
    return out


def node(x, y, r=7):
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="url(#hp-fade)"/>'


def build():
    s = []
    # ---------------------------------------------------------------- Vergangenheit
    root = (70, 400)
    tree = {  # Knoten -> Kinder
        root: [(180, 220), (180, 395), (180, 590)],
        (180, 220): [(290, 135), (290, 275)],
        (180, 395): [(290, 335), (290, 420)],
        (180, 590): [(290, 545), (290, 680)],
        (290, 135): [(400, 100), (400, 160)],
        (290, 275): [(400, 240), (400, 300)],
        (290, 335): [(400, 345)],
        (290, 420): [NOW, (400, 458)],
        (290, 545): [(400, 520), (400, 572)],
        (290, 680): [(400, 650), (400, 708)],
    }
    taken = [(-20, 408), root, (180, 395), (290, 420), NOW]
    taken_edges = set(zip(taken, taken[1:]))
    for a, kids in tree.items():
        for b in kids:
            if (a, b) not in taken_edges:
                s.append(f'<path d="{d_of(curve(a, b))}" stroke="url(#hp-fade)" stroke-width="3"/>')
    for a, b in zip(taken, taken[1:]):
        s.append(f'<path d="{d_of(curve(a, b))}" stroke="url(#hp-fade-strong)" stroke-width="6.5"/>')
    for a in tree:
        if a[0] < 400:
            s.append(node(*a, r=6))
    for kids in tree.values():
        for b in kids:
            if b[0] == 400 and b != NOW:
                s.append(f'<circle cx="{b[0]}" cy="{b[1]}" r="7" fill="#0b3a2d" stroke="{WHITE}" stroke-opacity=".5" stroke-width="3"/>')

    # ---------------------------------------------------------------- Zukunft
    q_marks, trails, pills = [], [], []
    for y, col, (pill_bg, pill_fg), values, delays in BRANCHES:
        s.append(f'<path class="hp-flow" d="{d_of(curve(NOW, (Q1_X, y)))}" stroke="{col}" stroke-width="6.5"/>')
        q_marks.append(qmark(Q1_X, y, 30))
        for sign, d0 in zip((-1, 1), delays):
            q2 = (Q2_X, y + sign * SPREAD_Q2)
            end = (TRAIL_END_X, y + sign * SPREAD_END)
            pts = sample([curve((Q1_X, y), q2, 0.4), curve(q2, end, 0.4)], 23)
            near = min(range(len(pts)), key=lambda i: math.dist(pts[i], q2))
            for i, p in enumerate(pts[2:], start=2):
                op = 1 if p[0] < TRAIL_END_X - 60 else max(0.25, (TRAIL_END_X - p[0]) / 60)
                trails.append(f'<circle class="hp-lf" style="animation-delay:{d0 + 0.05 * i:.2f}s" cx="{f(p[0])}" '
                              f'cy="{f(p[1])}" r="5" fill="{col}" fill-opacity="{op:.2f}"/>')
            q_marks.append(qmark(*q2, 24, cls="hp-lf", delay=d0 + 0.05 * near))
        pills.append(pill(PILL_X, y, pill_bg, pill_fg, values))
    s += trails
    # Jetzt-Punkt
    s.append(f'<circle class="hp-halo" cx="{NOW[0]}" cy="{NOW[1]}" r="26" fill="none" stroke="{WHITE}" stroke-width="4"/>')
    s.append(f'<circle cx="{NOW[0]}" cy="{NOW[1]}" r="28" fill="{WHITE}"/>')
    s.append(f'<circle cx="{NOW[0]}" cy="{NOW[1]}" r="12" fill="{GREEN}"/>')
    s += q_marks + pills

    style = (
        "<style>"
        ".hp path{fill:none;stroke-linecap:round}"
        ".hp-flow{stroke-dasharray:2 17;animation:hp-flow 14s linear infinite}"
        "@keyframes hp-flow{to{stroke-dashoffset:-380}}"
        ".hp-halo{transform-box:fill-box;transform-origin:center;animation:hp-halo 4s ease-out infinite}"
        "@keyframes hp-halo{0%{transform:scale(1);opacity:.55}100%{transform:scale(2.2);opacity:0}}"
        ".hp-lf{opacity:0;animation:hp-life 16s linear infinite}"
        "@keyframes hp-life{0%{opacity:0}2%{opacity:1}54%{opacity:1}58%{opacity:0}100%{opacity:0}}"
        ".hp-ph{opacity:0;animation:hp-ph 16s linear infinite}"
        "@keyframes hp-ph{0%{opacity:0}3%{opacity:1}22%{opacity:1}25%{opacity:0}100%{opacity:0}}"
        "@media (prefers-reduced-motion:reduce){.hp-flow,.hp-halo{animation:none}.hp-lf{animation:none;opacity:1}"
        ".hp-ph{animation:none}.hp-ph0{opacity:1}}"
        "</style>"
    )
    defs = (
        "<defs>"
        '<linearGradient id="hp-fade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="230" y2="0">'
        f'<stop offset="0" stop-color="{WHITE}" stop-opacity="0"/><stop offset="1" stop-color="{WHITE}" stop-opacity=".36"/></linearGradient>'
        '<linearGradient id="hp-fade-strong" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="200" y2="0">'
        f'<stop offset="0" stop-color="{WHITE}" stop-opacity="0"/><stop offset="1" stop-color="{WHITE}" stop-opacity=".95"/></linearGradient>'
        '<linearGradient id="hp-cone" gradientUnits="userSpaceOnUse" x1="400" y1="0" x2="1000" y2="0">'
        f'<stop offset="0" stop-color="{SAGE}" stop-opacity=".20"/><stop offset="1" stop-color="{SAGE}" stop-opacity="0"/></linearGradient>'
        '<radialGradient id="hp-glow" gradientUnits="userSpaceOnUse" cx="640" cy="400" r="400">'
        f'<stop offset="0" stop-color="{SAGE}" stop-opacity=".16"/><stop offset="1" stop-color="{SAGE}" stop-opacity="0"/></radialGradient>'
        "</defs>"
    )
    bg = (f'<circle cx="640" cy="400" r="400" fill="url(#hp-glow)"/>'
          f'<polygon points="{NOW[0]},{NOW[1]} 1000,40 1000,760" fill="url(#hp-cone)"/>')
    return (f'<svg class="hp" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'preserveAspectRatio="xMidYMid meet" focusable="false">{style}{defs}{bg}{"".join(s)}</svg>\n')


def qmark(x, y, r, cls="", delay=None):
    a = f' class="{cls}"' if cls else ""
    a += f' style="animation-delay:{delay:.2f}s"' if delay is not None else ""
    fs = round(r * 1.25)
    return (f'<g{a}><circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="{GREEN}" stroke="{WHITE}" stroke-width="{4.5 if r > 26 else 4}"/>'
            f'<text x="{f(x)}" y="{f(y + fs * 0.36)}" font-family="{FONT}" font-size="{fs}" font-weight="700" '
            f'fill="{WHITE}" text-anchor="middle">?</text></g>')


def pill(x, y, bg, fg, values):
    w, h = 132, 58
    out = [f'<rect x="{f(x - w / 2)}" y="{f(y - h / 2)}" width="{w}" height="{h}" rx="{h / 2}" fill="{bg}"/>']
    for i, v in enumerate(values):
        out.append(f'<text class="hp-ph hp-ph{i}" style="animation-delay:{-16 + 4 * i:.2f}s" x="{f(x)}" y="{f(y + 11)}" '
                   f'font-family="{FONT}" font-size="32" font-weight="700" fill="{fg}" text-anchor="middle">{v}</text>')
    return "".join(out)


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print(OUT, OUT.stat().st_size, "Bytes")
