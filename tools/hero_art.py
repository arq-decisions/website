"""Erzeugt die Hero-Grafik (Prognosepfade) als SVG, im Stil des Fächerdiagramms auf nikwall.de.

Eine einzige Bildsprache: durchgezogene, leicht gezackte Verlaufslinien. Links die Vergangenheit als kräftige Linie
bis zum Jetzt-Punkt, rechts ein Fächer feiner möglicher Zukünfte, drei davon hervorgehoben, am Ende jeweils die
Wahrscheinlichkeit in der Farbe des Pfads. Animation: Die Zukunftslinien zeichnen sich nacheinander vom Jetzt-Punkt
aus; alle 8 Sekunden folgt eine neue Prognose (4 Durchläufe, dann von vorn). Bei reduzierter Bewegung steht der
erste Durchlauf still.

Die Grafik wird von build.py direkt in die Seite eingebettet, damit sie die Schriften der Seite nutzt.

    python tools/hero_art.py   ->  static/img/hero_prognosepfade_v8.svg
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "img" / "hero_prognosepfade_v8.svg"

W, H = 1000, 800
WHITE, SAGE, CRIMSON_LIGHT = "#ffffff", "#9dc09f", "#e05a78"
FONT = "'Roboto Condensed', 'Arial Narrow', Arial, sans-serif"

NOW = (360, 400)
X_END, STEP = 860, 25
TOP, BOTTOM = 40, 760
SET_SECONDS, SETS = 8, 4
PERIOD = SET_SECONDS * SETS
# Je Durchlauf: Endpunkte der drei hervorgehobenen Pfade (weiß, karmesin, salbei) und ihre Wahrscheinlichkeiten
RUNS = [
    ((200, 420, 615), ("52 %", "15 %", "33 %")),
    ((218, 400, 600), ("47 %", "18 %", "35 %")),
    ((190, 432, 630), ("55 %", "14 %", "31 %")),
    ((178, 414, 640), ("61 %", "12 %", "27 %")),
]
HIGHLIGHT = ((WHITE, 3.2), (CRIMSON_LIGHT, 3.2), (SAGE, 3.2))
FAN = 16


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def walk(rng, y0, y1, n, sigma, curve=0.9):
    """Gezackter Pfad von y0 nach y1 in n Schritten: Trend plus Brownsche Brücke, innerhalb der Grenzen."""
    w = [0.0]
    for _ in range(n):
        w.append(w[-1] + rng.gauss(0, 1))
    ys = []
    for i in range(n + 1):
        t = i / n
        bridge = w[i] - t * w[-1]
        y = y0 + (y1 - y0) * t**curve + sigma * bridge
        ys.append(min(BOTTOM, max(TOP, y)))
    return ys


def d_of(xs, ys):
    return "M" + " L".join(f"{f(x)},{f(y)}" for x, y in zip(xs, ys))


def build():
    rng = random.Random(459)
    n = (X_END - NOW[0]) // STEP
    xs = [NOW[0] + i * STEP for i in range(n + 1)]
    out = []

    # Vergangenheit: eine kräftige Linie, links weich eingeblendet
    hn = NOW[0] // 24
    hx = [NOW[0] - (hn - i) * 24 for i in range(hn + 1)]
    hy = walk(rng, 485, NOW[1], hn, 8, curve=1)
    hy[-1] = NOW[1]
    out.append(f'<path d="{d_of(hx, hy)}" stroke="url(#hp-past)" stroke-width="4"/>')
    # Jetzt-Linie
    out.append(f'<line x1="{NOW[0]}" x2="{NOW[0]}" y1="{TOP - 10}" y2="{BOTTOM + 10}" stroke="{WHITE}" stroke-opacity=".16" stroke-width="1.5"/>')

    for k, (ends, labels) in enumerate(RUNS):
        t0 = k * SET_SECONDS
        g = [f'<g class="hp-set hp-set{k}">']
        # Fächer: feine Linien, Endpunkte gleichmäßig verteilt
        for i in range(FAN):
            y1 = TOP + 20 + (BOTTOM - TOP - 40) * i / (FAN - 1) + rng.uniform(-14, 14)
            ys = walk(rng, NOW[1], y1, n, 9)
            delay = t0 + 0.08 * ((i * 5) % FAN)
            g.append(f'<path class="hp-d" style="animation-delay:{delay:.2f}s" pathLength="1" d="{d_of(xs, ys)}" '
                     f'stroke="{WHITE}" stroke-opacity=".2" stroke-width="2"/>')
        # Hervorgehobene Pfade, Endpunkt und Wahrscheinlichkeit
        for j, ((col, sw), y1, label) in enumerate(zip(HIGHLIGHT, ends, labels)):
            ys = walk(rng, NOW[1], y1, n, 8)
            delay = t0 + 1.3 + 0.18 * j
            g.append(f'<path class="hp-d" style="animation-delay:{delay:.2f}s" pathLength="1" d="{d_of(xs, ys)}" '
                     f'stroke="{col}" stroke-width="{sw}"/>')
            ld = t0 + 2.6 + 0.12 * j
            g.append(f'<g class="hp-l" style="animation-delay:{ld:.2f}s"><circle cx="{xs[-1]}" cy="{f(ys[-1])}" r="5.5" fill="{col}"/>'
                     f'<text x="{xs[-1] + 18}" y="{f(ys[-1] + 11.5)}" font-family="{FONT}" font-size="34" font-weight="700" '
                     f'fill="{col}">{label}</text></g>')
        g.append("</g>")
        out += g

    # Jetzt-Punkt zuletzt, damit er über den Linien liegt
    out.append(f'<circle cx="{NOW[0]}" cy="{NOW[1]}" r="9" fill="#135b49" stroke="{WHITE}" stroke-width="3.5"/>')

    p = PERIOD
    draw_end = 1.3 / p * 100          # Linie gezeichnet
    hold_end = 6.7 / p * 100          # danach ausblenden
    gone = 7.8 / p * 100
    l_in, l_hold, l_out = 0.6 / p * 100, 5.0 / p * 100, 6.0 / p * 100
    style = (
        "<style>"
        ".hp path{fill:none;stroke-linecap:round;stroke-linejoin:round}"
        f".hp-d{{stroke-dasharray:1;stroke-dashoffset:1;animation:hp-draw {p}s linear infinite}}"
        f"@keyframes hp-draw{{0%{{stroke-dashoffset:1;opacity:1;animation-timing-function:cubic-bezier(.3,.6,.4,1)}}"
        f"{draw_end:.2f}%{{stroke-dashoffset:0;opacity:1}}{hold_end:.2f}%{{stroke-dashoffset:0;opacity:1}}"
        f"{gone:.2f}%{{stroke-dashoffset:0;opacity:0}}{gone + 0.1:.2f}%{{stroke-dashoffset:1;opacity:0}}"
        "100%{stroke-dashoffset:1;opacity:0}}"
        f".hp-l{{opacity:0;animation:hp-label {p}s linear infinite}}"
        f"@keyframes hp-label{{0%{{opacity:0}}{l_in:.2f}%{{opacity:1}}{l_hold:.2f}%{{opacity:1}}{l_out:.2f}%{{opacity:0}}100%{{opacity:0}}}}"
        "@media (prefers-reduced-motion:reduce){.hp-d,.hp-l{animation:none}.hp-d{stroke-dashoffset:0}.hp-l{opacity:1}"
        ".hp-set:not(.hp-set0){display:none}}"
        "</style>"
    )
    defs = (
        '<defs><linearGradient id="hp-past" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="180" y2="0">'
        f'<stop offset="0" stop-color="{WHITE}" stop-opacity="0"/><stop offset="1" stop-color="{WHITE}" stop-opacity=".95"/>'
        "</linearGradient></defs>"
    )
    return (f'<svg class="hp" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'preserveAspectRatio="xMidYMid meet" focusable="false">{style}{defs}{"".join(out)}</svg>\n')


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print(OUT, OUT.stat().st_size, "Bytes")
