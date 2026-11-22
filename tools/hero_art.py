"""Erzeugt die Hero-Grafik (Prognosepfade) als SVG, in der Bildsprache der Piktogramme der Seite.

Bildsprache: kräftige Linien mit runden Enden, Bögen mit waagrechten Ein- und Ausläufen, Knoten als grüne Kreise mit
weißem Rand. Die Vergangenheit ist eine durchgezogene Linie bis zum Jetzt-Punkt, mögliche Zukünfte sind gestrichelt.
An jedem Knoten steht eine Frage (?), am Ende jedes Pfads seine Wahrscheinlichkeit.

Animation (langsam): Die drei Pfade wachsen beim Laden vom Jetzt-Punkt aus, zuerst bis zu den Fragen, dann bis zu den
Wahrscheinlichkeiten. Danach entsteht alle 10 Sekunden an einer Frage eine neue Abzweigung mit einer neuen Frage, und
die Wahrscheinlichkeiten verschieben sich. Bei reduzierter Bewegung steht das fertige Bild still.

Die Striche sind einzelne kurze Pfade, die nacheinander eingeblendet werden. Das wirkt wie eine wachsende gestrichelte
Linie und läuft in allen Browsern (animierte Masken zeichnet Safari nicht zuverlässig neu).

Die Grafik wird von build.py direkt in die Seite eingebettet, damit sie die Schriften der Seite nutzt.

    python tools/hero_art.py   ->  static/img/hero_prognosepfade_v9.svg
"""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "img" / "hero_prognosepfade_v9.svg"

W, H = 1000, 800
WHITE, SAGE, GREEN, GREEN_TEXT = "#ffffff", "#9dc09f", "#135b49", "#0f3d32"
CRIMSON, CRIMSON_LINE = "#bb2649", "#d9607a"  # Linie heller, damit sie auf Dunkelgrün trägt
FONT = "'Roboto Condensed', 'Arial Narrow', Arial, sans-serif"

LW = 9                 # Linienstärke
DASH, GAP = 10, 20     # gestrichelt; die runden Enden verlängern jeden Strich sichtbar um LW
NOW = (270, 400)
QX = 520               # Fragen erster Ebene
SX = 740               # neue Fragen (Abzweigungen)
PILL_X, PILL_W, PILL_H = 838, 140, 64

# Hauptpfade: Farbe der Linie, Füllung und Schrift der Wahrscheinlichkeit, Höhe der Frage, Höhe des Endes
PATHS = [
    (WHITE, WHITE, GREEN, 205, 135),
    (CRIMSON_LINE, CRIMSON, WHITE, 400, 400),
    (SAGE, SAGE, GREEN_TEXT, 595, 665),
]
# Wahrscheinlichkeiten je Durchlauf (weiß, karmesin, salbei)
RUNS = [("52 %", "15 %", "33 %"), ("47 %", "18 %", "35 %"), ("55 %", "14 %", "31 %"), ("61 %", "12 %", "27 %")]
# Neue Abzweigungen je Durchlauf: (Hauptpfad, Höhe der neuen Frage); sie entstehen kurz bevor die Zahlen wechseln
SPROUTS = {1: [(1, 288)], 2: [(0, 302), (2, 498)], 3: [(1, 512)], 0: [(2, 758)]}

GROW = 1.8             # Sekunden, bis ein Abschnitt gezeichnet ist
RUN = 10.0             # Sekunden je Durchlauf
PERIOD = RUN * len(RUNS)
NUM_START = 5.0        # erste Zahlen erscheinen nach dem Aufbau
SPROUT_LEAD = 3.5      # so viele Sekunden vor dem Zahlenwechsel wächst die neue Abzweigung


def g(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def bend(x0, y0, x1, y1, run_in=0, run_out=0):
    """Punkte entlang eines Bogens mit waagrechtem Ein- und Auslauf, wie in den Piktogrammen."""
    a, b = x0 + run_in, x1 - run_out
    k = (b - a) * 0.5
    pts = [(x0, y0)]
    if run_in:
        pts.append((a, y0))
    n = 60
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        px = u**3 * a + 3 * u * u * t * (a + k) + 3 * u * t * t * (b - k) + t**3 * b
        py = u**3 * y0 + 3 * u * u * t * y0 + 3 * u * t * t * y1 + t**3 * y1
        pts.append((px, py))
    if run_out:
        pts.append((x1, y1))
    return pts


def dashes(pts):
    """Zerlegt die Linie in Striche; liefert je Strich (Pfad-d, Anteil der Länge an seiner Mitte)."""
    seg = [math.dist(p, q) for p, q in zip(pts, pts[1:])]
    total = sum(seg)
    cum = [0.0]
    for s in seg:
        cum.append(cum[-1] + s)

    def at(s):
        for i in range(len(seg)):
            if cum[i + 1] >= s:
                f = (s - cum[i]) / seg[i] if seg[i] else 0
                return (pts[i][0] + f * (pts[i + 1][0] - pts[i][0]), pts[i][1] + f * (pts[i + 1][1] - pts[i][1]))
        return pts[-1]

    out = []
    s = GAP / 2
    while s < total:
        e = min(s + DASH, total)
        inner = [pts[i] for i in range(len(pts)) if s < cum[i] < e]
        line = [at(s)] + inner + [at(e)]
        out.append(("M" + " L".join(f"{g(x)},{g(y)}" for x, y in line), (s + e) / 2 / total))
        s += DASH + GAP
    return out


def pct(t):
    return f"{t / PERIOD * 100:.2f}%"


def question(x, y, cls="", delay=None):
    attr = f' class="{cls}"' if cls else ""
    if delay is not None:
        attr += f' style="animation-delay:{delay:.2f}s"'
    return (f'<g{attr}><circle cx="{x}" cy="{y}" r="30" fill="{GREEN}" stroke="{WHITE}" stroke-width="6"/>'
            f'<text x="{x}" y="{y + 13}" font-family="{FONT}" font-size="38" font-weight="700" fill="{WHITE}" '
            f'text-anchor="middle">?</text></g>')


def build():
    lines, nodes, labels, sprouts = [], [], [], []

    def dashed(pts, color, cls, t0):
        parts = [f'<path class="{cls}" style="animation-delay:{t0 + GROW * u:.2f}s" d="{d}"/>' for d, u in dashes(pts)]
        return f'<g stroke="{color}">{"".join(parts)}</g>'

    # Vergangenheit: durchgezogen, links weich eingeblendet
    past = bend(0, 470, NOW[0], NOW[1], run_in=70, run_out=50)
    lines.append(f'<path d="M{" L".join(f"{g(x)},{g(y)}" for x, y in past)}" stroke="url(#hp-past)"/>')

    # Aufbau beim Laden: Jetzt -> Frage, dann Frage -> Wahrscheinlichkeit
    for j, (line, fill, text, qy, ey) in enumerate(PATHS):
        t1 = 0.4 + 0.35 * j
        lines.append(dashed(bend(NOW[0], NOW[1], QX, qy, run_out=30), line, "hp-d", t1))
        nodes.append(question(QX, qy, "hp-pop", t1 + GROW))
        t2 = 2.9 + 0.35 * j
        lines.append(dashed(bend(QX, qy, PILL_X, ey, run_in=40, run_out=90), line, "hp-d", t2))
        labels.append(f'<rect class="hp-pop" style="animation-delay:{t2 + GROW:.2f}s" x="{PILL_X}" y="{ey - PILL_H // 2}" '
                      f'width="{PILL_W}" height="{PILL_H}" rx="{PILL_H // 2}" fill="{fill}"/>')
        for k, run in enumerate(RUNS):
            delay = NUM_START + RUN * k + 0.35 * j
            labels.append(f'<text class="hp-num hp-run{k}" style="animation-delay:{delay:.2f}s" x="{PILL_X + PILL_W / 2:g}" '
                          f'y="{ey + 13}" font-family="{FONT}" font-size="38" font-weight="700" fill="{text}" '
                          f'text-anchor="middle">{run[j]}</text>')

    # Neue Abzweigungen, je Durchlauf eine oder zwei: Striche erscheinen nacheinander, dann die Frage, nach gut 8 s
    # blendet die Gruppe aus
    for k, items in SPROUTS.items():
        start = NUM_START + RUN * k - SPROUT_LEAD
        if start < NUM_START:
            start += PERIOD
        for i, (p, sy) in enumerate(items):
            line, _, _, qy, _ = PATHS[p]
            t = start + 0.4 * i
            sprouts.append(f'<g class="hp-sg" style="animation-delay:{t:.2f}s">'
                           f'{dashed(bend(QX, qy, SX, sy, run_in=30, run_out=20), line, "hp-sd", t)}'
                           f'{question(SX, sy, "hp-sq", t)}</g>')

    # Jetzt-Punkt
    nodes.append(f'<circle cx="{NOW[0]}" cy="{NOW[1]}" r="23" fill="{WHITE}"/>'
                 f'<circle cx="{NOW[0]}" cy="{NOW[1]}" r="10" fill="{GREEN}"/>')

    P = f"{PERIOD:g}s"
    style = (
        "<style>"
        f".hp path{{fill:none;stroke-width:{LW};stroke-linecap:round;stroke-linejoin:round}}"
        # Aufbau beim Laden, einmalig
        ".hp-d{animation:hp-in .3s ease-out both}"
        "@keyframes hp-in{from{opacity:0}}"
        ".hp-pop{transform-box:fill-box;transform-origin:center;animation:hp-pop .6s cubic-bezier(.3,1.4,.5,1) both}"
        "@keyframes hp-pop{from{opacity:0;transform:scale(.4)}}"
        # Wahrscheinlichkeiten wechseln alle 10 s
        f".hp-num{{opacity:0;animation:hp-num {P} linear infinite both}}"
        f"@keyframes hp-num{{0%{{opacity:0}}{pct(0.5)}{{opacity:1}}{pct(RUN - 0.5)}{{opacity:1}}{pct(RUN)}{{opacity:0}}"
        "100%{opacity:0}}"
        # neue Abzweigung
        f".hp-sd{{animation:hp-sd {P} linear infinite both}}"
        f"@keyframes hp-sd{{0%{{opacity:0}}{pct(0.3)}{{opacity:1}}{pct(9.5)}{{opacity:1}}{pct(9.6)}{{opacity:0}}100%{{opacity:0}}}}"
        f".hp-sq{{animation:hp-sq {P} linear infinite both}}"
        f"@keyframes hp-sq{{0%{{opacity:0}}{pct(GROW)}{{opacity:0}}{pct(GROW + 0.5)}{{opacity:1}}{pct(9.5)}{{opacity:1}}"
        f"{pct(9.6)}{{opacity:0}}100%{{opacity:0}}}}"
        f".hp-sg{{animation:hp-sg {P} linear infinite both}}"
        f"@keyframes hp-sg{{0%{{opacity:1}}{pct(7.6)}{{opacity:1}}{pct(8.6)}{{opacity:0}}{pct(12)}{{opacity:0}}"
        f"{pct(12.1)}{{opacity:1}}100%{{opacity:1}}}}"
        "@media (prefers-reduced-motion:reduce){.hp *{animation:none!important}.hp-sg{display:none}.hp-num.hp-run0{opacity:1}}"
        "</style>"
    )
    defs = (
        '<defs><linearGradient id="hp-past" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="220" y2="0">'
        f'<stop offset="0" stop-color="{WHITE}" stop-opacity="0"/><stop offset="1" stop-color="{WHITE}" stop-opacity=".9"/>'
        "</linearGradient></defs>"
    )
    body = "".join(lines + sprouts + nodes + labels)
    return (f'<svg class="hp" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'preserveAspectRatio="xMidYMid meet" focusable="false">{style}{defs}{body}</svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print(OUT, OUT.stat().st_size, "Bytes")
