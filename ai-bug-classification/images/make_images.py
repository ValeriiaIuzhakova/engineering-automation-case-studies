"""Generate the case-study images (SVG, light + dark via prefers-color-scheme).

Usage: python3 make_images.py .   (run from this folder)
Data for the chart is the synthetic sample in examples/calibration.py.
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

STYLE = f"""
<style>
  svg {{ font-family: {FONT}; }}
  .surface {{ fill: #fcfcfb; stroke: rgba(11,11,11,0.10); }}
  .ink {{ fill: #0b0b0b; }}
  .ink2 {{ fill: #52514e; }}
  .muted {{ fill: #898781; }}
  .grid {{ stroke: #e1e0d9; stroke-width: 1; }}
  .axis {{ stroke: #c3c2b7; stroke-width: 1; }}
  .bar {{ fill: #2a78d6; }}
  .empty {{ fill: none; stroke: #c3c2b7; stroke-width: 1.5; stroke-dasharray: 4 4; }}
  .box {{ fill: #ffffff; stroke: #c3c2b7; stroke-width: 1.25; }}
  .box-accent {{ fill: #eef4fc; stroke: #2a78d6; stroke-width: 1.25; }}
  .lane {{ fill: #f3f2ee; }}
  .arrow {{ stroke: #898781; stroke-width: 1.5; fill: none; }}
  .arrowhead {{ fill: #898781; }}
  .good {{ fill: #0ca30c; }}
  .warn {{ fill: #fab219; }}
  .crit {{ fill: #d03b3b; }}
  .good-s {{ stroke: #0ca30c; }}
  .warn-s {{ stroke: #fab219; }}
  .crit-s {{ stroke: #d03b3b; }}
  .on-status {{ fill: #ffffff; }}
  .on-warn {{ fill: #0b0b0b; }}
  svg {{ --ring: #fcfcfb; }}
  @media (prefers-color-scheme: dark) {{
    .surface {{ fill: #1a1a19; stroke: rgba(255,255,255,0.10); }}
    .ink {{ fill: #f0efec; }}
    .ink2 {{ fill: #c3c2b7; }}
    .grid {{ stroke: #2c2c2a; }}
    .axis {{ stroke: #383835; }}
    .bar {{ fill: #3987e5; }}
    .empty {{ stroke: #52514e; }}
    .box {{ fill: #242423; stroke: #52514e; }}
    .box-accent {{ fill: #1c2a3b; stroke: #3987e5; }}
    .lane {{ fill: #212120; }}
    svg {{ --ring: #1a1a19; }}
  }}
</style>
<defs>
  <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path class="arrowhead" d="M0,0 L10,5 L0,10 z"/>
  </marker>
</defs>
"""


def svg(w, h, title, desc, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n'
            f'<desc id="d">{escape(desc)}</desc>\n{STYLE}\n'
            f'<rect class="surface" x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="12"/>\n{body}\n</svg>\n')


def text(x, y, s, cls="ink", size=14, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(s)}</text>')


def lines(x, y, rows, cls="ink", size=14, weight=400, anchor="start", lh=None):
    lh = lh or round(size * 1.35)
    return "\n".join(text(x, y + i * lh, r, cls, size, weight, anchor) for i, r in enumerate(rows))


def arrow(x1, y1, x2, y2):
    return f'<path class="arrow" d="M{x1},{y1} L{x2},{y2}" marker-end="url(#ah)"/>'


def path_arrow(d):
    return f'<path class="arrow" d="{d}" marker-end="url(#ah)"/>'


# ---------------------------------------------------------------- calibration chart
def calibration():
    # Same synthetic samples as examples/calibration.py; threshold = APPLY_AT in examples/pipeline.py
    A = [(0.65, False), (0.68, False), (0.66, True), (0.75, True), (0.78, False), (0.72, True),
         (0.85, True), (0.88, True), (0.83, False), (0.93, True), (0.95, True), (0.97, True), (0.91, True)]
    B = [(0.86, True), (0.88, False), (0.90, True), (0.91, True), (0.92, False), (0.93, True),
         (0.94, True), (0.95, False), (0.96, True), (0.89, True), (0.87, True), (0.97, False)]
    T = 0.90
    W, H = 900, 500
    x0, x1, lo, hi = 150, 690, 0.60, 1.00
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    body = [
        text(32, 44, "A high confidence score did not mean a right answer", size=20, weight=650),
        text(32, 70, "Each mark is one AI answer, placed by the confidence the model reported. "
             "Synthetic illustration.", "ink2", 14),
    ]
    top, bottom = 132, 400
    tx = X(T)
    # "written automatically" zone
    body.append(f'<rect class="lane" x="{tx}" y="{top-20}" width="{x1+14-tx}" height="{bottom-top+20}" rx="6"/>')
    body.append(f'<line class="axis" x1="{tx}" y1="{top-20}" x2="{tx}" y2="{bottom}" stroke-dasharray="5 4"/>')
    body.append(text(tx + 10, top - 2, "Written automatically", "ink", 13, 650))
    body.append(text(tx - 10, top - 2, "Sent to a person / failed", "muted", 13, 400, "end"))
    rows = [("Trustworthy", "confidence", A, 200), ("What the audit", "found", B, 330)]
    for title1, title2, data, cy in rows:
        body.append(f'<line class="grid" x1="{x0}" y1="{cy}" x2="{x1+14}" y2="{cy}"/>')
        body.append(text(32, cy - 4, title1, "ink", 14, 650))
        body.append(text(32, cy + 14, title2, "ink", 14, 650))
        placed = []
        for v, ok in sorted(data):
            x = X(v)
            # beeswarm: move a mark up or down until it no longer overlaps a placed one
            for dy in (0, -17, 17, -34, 34):
                if all((x - px) ** 2 + (dy - py) ** 2 >= 17 ** 2 for px, py in placed):
                    break
            placed.append((x, dy))
            y = cy + dy
            if ok:
                body.append(f'<circle class="bar" cx="{x}" cy="{y}" r="7" stroke="var(--ring, #fcfcfb)" stroke-width="2"/>')
            else:
                body.append(f'<g class="crit-s" stroke-width="3" stroke-linecap="round">'
                            f'<line x1="{x-6}" y1="{y-6}" x2="{x+6}" y2="{y+6}"/>'
                            f'<line x1="{x-6}" y1="{y+6}" x2="{x+6}" y2="{y-6}"/></g>')
        written = [ok for v, ok in data if v >= T]
        wrong = written.count(False)
        body.append(text(x1 + 28, cy - 4, f"{len(written)} written", "ink", 14, 650))
        body.append(text(x1 + 28, cy + 14, f"{wrong} of them wrong" if wrong else "none of them wrong",
                         "ink", 14, 400))
        if wrong:
            body.append(text(x1 + 28, cy + 32, "with no comment", "ink2", 13))
    # axis
    body.append(f'<line class="axis" x1="{x0}" y1="{bottom}" x2="{x1+14}" y2="{bottom}"/>')
    for v in (0.6, 0.7, 0.8, 0.9, 1.0):
        body.append(text(X(v), bottom + 20, f"{v:.1f}", "muted", 12, anchor="middle"))
    body.append(text((x0 + x1) / 2, bottom + 40, "Confidence reported by the model", "muted", 12, anchor="middle"))
    # legend
    ly = 96
    body.append(f'<circle class="bar" cx="{x1 - 150}" cy="{ly-4}" r="6"/>')
    body.append(text(x1 - 138, ly, "right answer", "ink2", 13))
    lx = x1 - 40
    body.append(f'<g class="crit-s" stroke-width="3" stroke-linecap="round"><line x1="{lx-5}" y1="{ly-9}" x2="{lx+5}" y2="{ly+1}"/>'
                f'<line x1="{lx-5}" y1="{ly+1}" x2="{lx+5}" y2="{ly-9}"/></g>')
    body.append(text(lx + 12, ly, "wrong answer", "ink2", 13))
    body.append(text(32, H - 18, "Synthetic data (examples/calibration.py, illustrative threshold 0.90). "
                     "It shows the pattern the audit found; the real numbers are internal.", "muted", 12))
    return svg(W, H, "A high confidence score did not mean a right answer",
               "Dot plot of AI answers by reported confidence, with a threshold at 0.90 above which answers are "
               "written automatically. Trustworthy confidence: wrong answers sit below the threshold; 4 answers "
               "are written and none are wrong. What the audit found: all answers are bunched between 0.86 and "
               "0.97; 8 are written automatically and 3 of them are wrong, with no comment. Synthetic data.",
               "\n".join(body))


# ---------------------------------------------------------------- overview diagram
def overview():
    W, H = 900, 440
    body = [
        text(32, 44, "How a new bug gets classified", size=20, weight=650),
        text(32, 70, "One run per bug. Every run ends with a comment on the bug and a row in the audit log.",
             "ink2", 14),
    ]
    cols = [
        ("1  Trigger", [["New bug", "is filed"], ["Automation rule", "adds a trigger label"],
                        ["Workflow starts", "(skips bugs already done)"]]),
        ("2  Classify", [["Read the taxonomy", "(versioned wiki page)"], ["AI step 1:", "product area"],
                         ["AI step 2:", "failure type"]]),
        ("3  Check", [["Validate strictly", "(no near-misses)"], ["Compare confidence", "with thresholds"],
                      ["Pick one outcome", "(see next diagram)"]]),
        ("4  Record & use", [["Comment on the bug", "explaining why"], ["Audit log row", "(inputs + version)"],
                             ["Weekly review", "of bug clusters"]]),
    ]
    cw, gap, x0, y0 = 196, 20, 32, 96
    bh, bgap = 64, 18
    for ci, (head, boxes) in enumerate(cols):
        x = x0 + ci * (cw + gap)
        body.append(f'<rect class="lane" x="{x}" y="{y0}" width="{cw}" height="{H-y0-56}" rx="10"/>')
        body.append(text(x + 14, y0 + 26, head, "ink", 14, 650))
        for bi, rows in enumerate(boxes):
            by = y0 + 44 + bi * (bh + bgap)
            cls = "box-accent" if ci == 1 and bi > 0 else "box"
            body.append(f'<rect class="{cls}" x="{x+12}" y="{by}" width="{cw-24}" height="{bh}" rx="8"/>')
            body.append(text(x + cw / 2, by + 27, rows[0], "ink", 14, 600, "middle"))
            body.append(text(x + cw / 2, by + 46, rows[1], "ink2", 12.5, 400, "middle"))
            if bi < len(boxes) - 1:
                body.append(arrow(x + cw / 2, by + bh + 2, x + cw / 2, by + bh + bgap - 2))
        if ci < len(cols) - 1:
            yb = y0 + 44 + 2 * (bh + bgap) + bh / 2
            ya = y0 + 44 + bh / 2
            xr = x + cw - 12
            nx = x + cw + gap + 12
            # from bottom box of this column up to the top box of the next one
            body.append(path_arrow(f"M{xr+2},{yb} H{x+cw+gap/2} V{ya} H{nx-2}"))
    body.append(text(32, H - 20, "Simplified, conceptual view. Generic component names; not the production configuration.",
                     "muted", 12))
    return svg(W, H, "How a new bug gets classified",
               "Four stages left to right. Trigger: a new bug is filed, an automation rule adds a trigger label, "
               "the workflow starts and skips bugs already done. Classify: read the versioned taxonomy, AI step 1 "
               "picks the product area, AI step 2 picks the failure type. Check: validate strictly, compare "
               "confidence with thresholds, pick one outcome. Record and use: comment on the bug explaining why, "
               "write an audit log row, and the team reviews bug clusters weekly.", "\n".join(body))


# ---------------------------------------------------------------- outcomes diagram
def outcomes():
    W, H = 900, 500
    body = [
        text(32, 44, "Three outcomes, and only one of them writes data", size=20, weight=650),
        text(32, 70, "Each AI answer goes through the same checks. Area and type are checked separately.",
             "ink2", 14),
    ]
    # decision ladder (left) with outcome chips right next to each exit
    qx, qw, qh = 32, 280, 58
    qs = [("Valid JSON, and the value", "exists in the taxonomy?"),
          ("Is the answer the fallback", "value \u201cOther\u201d?"),
          ("Confidence at or above", "the apply threshold?"),
          ("Confidence at or above", "the review threshold?")]
    ys = [104, 196, 288, 380]
    for (a, b), y in zip(qs, ys):
        body.append(f'<rect class="box" x="{qx}" y="{y}" width="{qw}" height="{qh}" rx="8"/>')
        body.append(text(qx + qw / 2, y + 24, a, "ink", 14, 600, "middle"))
        body.append(text(qx + qw / 2, y + 43, b, "ink", 14, 600, "middle"))
    for y1, y2, lab in [(ys[0], ys[1], "yes"), (ys[1], ys[2], "no"), (ys[2], ys[3], "no")]:
        body.append(arrow(qx + qw / 2, y1 + qh + 2, qx + qw / 2, y2 - 2))
        body.append(text(qx + qw / 2 + 10, y1 + qh + 22, lab, "muted", 12))
    meta = {"Classified": ("good", "on-status", "\u2713"), "Needs review": ("warn", "on-warn", "!"),
            "Failed": ("crit", "on-status", "\u00d7")}

    def chip(x, y, name):
        st, oncls, icon = meta[name]
        w = 150
        out = [f'<rect class="box" x="{x}" y="{y-15}" width="{w}" height="30" rx="15"/>',
               f'<circle class="{st}" cx="{x+15}" cy="{y}" r="10"/>',
               text(x + 15, y + 4.5, icon, oncls, 12, 700, "middle"),
               text(x + 32, y + 5, name, "ink", 13, 600)]
        return "\n".join(out)

    ex = qx + qw
    chipx = ex + 62
    exits = [(ys[0] + qh / 2, "no", "Failed"), (ys[1] + qh / 2, "yes", "Needs review"),
             (ys[2] + qh / 2, "yes", "Classified"), (ys[3] + 8, "yes", "Needs review"),
             (ys[3] + qh - 4, "no", "Failed")]
    for y, lab, name in exits:
        body.append(arrow(ex + 2, y, chipx - 4, y))
        body.append(text(ex + 10, y - 5, lab, "muted", 12))
        body.append(chip(chipx, y, name))
    # explanation cards (right)
    cx, cw2, ch = 540, 328, 104
    cards = [
        ("Classified", ["The fields are written, and a", "comment explains the choice."], 112),
        ("Needs review", ["Nothing is written. A suggestion", "is posted for a person to confirm."], 232),
        ("Failed", ["Nothing is written. A comment says:", "add detail and retry, or tag by hand."], 352),
    ]
    for name, rows, y in cards:
        st, oncls, icon = meta[name]
        body.append(f'<rect class="box" x="{cx}" y="{y}" width="{cw2}" height="{ch}" rx="10"/>')
        body.append(f'<rect class="{st}" x="{cx}" y="{y}" width="8" height="{ch}" rx="4"/>')
        body.append(f'<circle class="{st}" cx="{cx+36}" cy="{y+30}" r="13"/>')
        body.append(text(cx + 36, y + 35, icon, oncls, 15, 700, "middle"))
        body.append(text(cx + 60, y + 36, name, "ink", 16, 650))
        body.append(lines(cx + 24, y + 66, rows, "ink2", 13))
    body.append(text(32, H - 18, "The backfill only sends bugs that have no classification yet. "
                     "Thresholds are illustrative, set from a calibration check.", "muted", 12))
    return svg(W, H, "Three outcomes, and only one of them writes data",
               "Decision ladder. If the answer is not valid JSON or not in the taxonomy: Failed. If it is the "
               "fallback value Other: Needs review. If confidence is at or above the apply threshold: Classified, "
               "fields are written with an explanatory comment. Else if at or above the review threshold: Needs "
               "review, nothing is written, a suggestion is posted and the bug joins the review queue. Otherwise: "
               "Failed, nothing is written and a comment explains the next step.", "\n".join(body))


(OUT / "calibration-chart.svg").write_text(calibration())
(OUT / "pipeline-overview.svg").write_text(overview())
(OUT / "decision-outcomes.svg").write_text(outcomes())
print("wrote", *sorted(p.name for p in OUT.glob("*.svg")))
