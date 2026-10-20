"""Draw the Syto teaser (reads -> deconvolution -> mixture) in the Industry style.

    python tools/make_syto_teaser.py

Writes tools/syto-teaser.html (inline SVG on the site's stylesheet). Screenshot it
at 2x with headless Chrome to produce blog/syto/teaser.png / .webp, e.g.

    chrome --headless=new --hide-scrollbars --force-device-scale-factor=2 \
        --window-size=800,600 --screenshot=teaser.png tools/syto-teaser.html
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H = 800, 600
CELL, GAP = 34, 4
STEP = CELL + GAP

# Reads from the paper's teaser figure. Letters; for each C of a CpG: 'm' methylated, 'u' unmethylated.
READS = [
    (0, "CGTGCGCG", "u...u.u."),
    (0, "CGTACGCGA", "u...u.m.."),
    (2, "ACGCGAC", ".m.m..m"),
    (3, "CGCGCCGCTC", "m.m..m...m"),
    (4, "CGACGCTC", "m..u...m"),
]
MIXTURE = [("40%", "var(--color-accent-800)", "var(--color-bg)"),
           ("20%", "var(--color-accent-500)", "var(--color-bg)"),
           ("40%", "var(--color-accent-300)", "var(--color-accent-900)"),
           ("0%", "transparent", "var(--color-neutral-700)")]


def label(x, y, text, size=17, anchor="start", color="var(--color-neutral-700)", spacing="0.14em"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" style="font-family:var(--font-heading);'
            f'font-size:{size}px;letter-spacing:{spacing};text-transform:uppercase;fill:{color}">{text}</text>')


def corners(x, y, w, h):
    out = []
    for cx, cy in [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]:
        out.append(f'<path d="M{cx-6} {cy}h12M{cx} {cy-6}v12" style="stroke:var(--color-neutral-600);stroke-width:1"/>')
    return "".join(out)


def svg():
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         f'<rect width="{W}" height="{H}" style="fill:var(--color-bg)"/>']

    # reads panel
    px, py, pw, ph = 40, 40, 720, 300
    s.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" style="fill:none;stroke:var(--color-divider)"/>')
    s.append(corners(px, py, pw, ph))
    s.append(label(px + 20, py + 32, "Sequenced DNA fragments (reads)"))
    x0, y0 = px + 20, py + 56
    for r, (off, seq, meth) in enumerate(READS):
        y = y0 + r * (CELL + 14)
        rx = x0 + off * STEP
        s.append(f'<rect x="{rx-4}" y="{y-4}" width="{len(seq)*STEP+4}" height="{CELL+8}" '
                 f'style="fill:var(--color-accent-100);stroke:var(--color-accent-300)"/>')
        for i, (ch, m) in enumerate(zip(seq, meth)):
            cx, cy = rx + i * STEP + CELL / 2, y + CELL / 2
            if m == "m":
                s.append(f'<circle cx="{cx}" cy="{cy}" r="14" style="fill:var(--color-accent-700)"/>')
                fill = "var(--color-bg)"
            elif m == "u":
                s.append(f'<circle cx="{cx}" cy="{cy}" r="13.5" style="fill:var(--color-bg);stroke:var(--color-accent-700);stroke-width:1.5"/>')
                fill = "var(--color-accent-800)"
            else:
                fill = "var(--color-neutral-700)"
            s.append(f'<text x="{cx}" y="{cy+6}" text-anchor="middle" style="font-family:var(--font-heading);'
                     f'font-weight:600;font-size:18px;fill:{fill}">{ch}</text>')
    # legend
    ly = py + 26
    lx = px + pw - 320
    s.append(f'<circle cx="{lx}" cy="{ly}" r="8" style="fill:var(--color-accent-700)"/>')
    s.append(label(lx + 16, ly + 5, "Methylated", 15, color="var(--color-neutral-800)", spacing="0.1em"))
    s.append(f'<circle cx="{lx+150}" cy="{ly}" r="7.5" style="fill:var(--color-bg);stroke:var(--color-accent-700);stroke-width:1.5"/>')
    s.append(label(lx + 166, ly + 5, "Unmethylated", 15, color="var(--color-neutral-800)", spacing="0.1em"))

    # deconvolution step (solid accent: the one filled object, like the primary button)
    bx, by, bw, bh = 40, 410, 260, 110
    ax = bx + bw / 2
    s.append(f'<path d="M{ax} {py+ph}V{by-10}" style="stroke:var(--color-text);stroke-width:1.5"/>')
    s.append(f'<path d="M{ax-7} {by-17}l7 9 7-9" style="fill:none;stroke:var(--color-text);stroke-width:1.5"/>')
    s.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" style="fill:var(--color-accent)"/>')
    s.append(corners(bx, by, bw, bh))
    s.append(f'<text x="{ax}" y="{by+50}" text-anchor="middle" style="font-family:var(--font-heading);font-weight:600;'
             f'font-size:26px;letter-spacing:0.04em;text-transform:uppercase;fill:var(--color-bg)">Cell-type</text>')
    s.append(f'<text x="{ax}" y="{by+80}" text-anchor="middle" style="font-family:var(--font-heading);font-weight:600;'
             f'font-size:26px;letter-spacing:0.04em;text-transform:uppercase;fill:var(--color-bg)">deconvolution</text>')

    # mixture panel
    mx, my, mw, mh = 380, 380, 380, 180
    s.append(f'<path d="M{bx+bw} {by+bh/2}H{mx-10}" style="stroke:var(--color-text);stroke-width:1.5"/>')
    s.append(f'<path d="M{mx-17} {by+bh/2-7}l9 7-9 7" style="fill:none;stroke:var(--color-text);stroke-width:1.5"/>')
    s.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" style="fill:none;stroke:var(--color-divider)"/>')
    s.append(corners(mx, my, mw, mh))
    s.append(label(mx + 20, my + 30, "Predicted cell-type mixture"))
    for i, (pct, fill, txt) in enumerate(MIXTURE):
        cx = mx + 60 + (i % 2) * 170
        cy = my + 80 + (i // 2) * 62
        stroke = "var(--color-neutral-500)" if fill == "transparent" else fill
        dash = ";stroke-dasharray:3 3" if fill == "transparent" else ""
        s.append(f'<circle cx="{cx}" cy="{cy}" r="22" style="fill:{fill};stroke:{stroke};stroke-width:1.5{dash}"/>')
        s.append(f'<text x="{cx+36}" y="{cy+9}" style="font-family:var(--font-heading);font-weight:600;'
                 f'font-size:26px;fill:var(--color-text)">{pct}</text>')
    s.append("</svg>")
    return "".join(s)


def main():
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<link rel="stylesheet" href="../assets/css/industry.css">
<style>html,body{{margin:0;background:var(--color-bg)}} svg{{display:block}}</style>
</head><body>{svg()}</body></html>
"""
    out = ROOT / "tools" / "syto-teaser.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
