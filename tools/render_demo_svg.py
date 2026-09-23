#!/usr/bin/env python3
"""Render the live `corral demo` output to a terminal-card SVG for the README, in pure Python."""
import html, io, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from corral.demo import main as demo_main
BG, FG, DIM, GREEN, YELLOW = "#0d1117", "#c9d1d9", "#8b949e", "#3fb950", "#d29922"
def render():
    buf = io.StringIO(); o = sys.stdout; sys.stdout = buf
    try: demo_main([])
    finally: sys.stdout = o
    lines = buf.getvalue().rstrip("\n").splitlines()
    W = int(44 + max((len(l) for l in lines), default=64) * 8.0); H = int(52 + len(lines) * 19 + 22)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="SFMono-Regular,Consolas,Menlo,monospace" font-size="13">' % (W, H, W, H),
           '<rect width="%d" height="%d" rx="8" fill="%s"/>' % (W, H, BG),
           '<rect width="%d" height="34" rx="8" fill="#161b22"/><rect y="26" width="%d" height="8" fill="#161b22"/>' % (W, W)]
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        out.append('<circle cx="%d" cy="17" r="6" fill="%s"/>' % (20 + i * 20, c))
    out.append('<text x="%d" y="21" fill="%s" font-size="12">python3 -m corral demo</text>' % (W // 2 - 80, DIM))
    for i, ln in enumerate(lines):
        col = GREEN if ln.strip().startswith("corral demo") or "agents:" in ln else (YELLOW if set(ln.strip()) == {"="} else FG)
        out.append('<text x="22" y="%d" fill="%s" xml:space="preserve">%s</text>' % (52 + i * 19, col, html.escape(ln)))
    out.append('</svg>')
    open(os.path.join(ROOT, "assets", "demo.svg"), "w").write("\n".join(out) + "\n")
    print("wrote assets/demo.svg (%dx%d)" % (W, H))
if __name__ == "__main__": render()
