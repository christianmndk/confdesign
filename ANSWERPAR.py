#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, sys
from pathlib import Path
from bs4 import BeautifulSoup, Tag

Q_RE = re.compile(r"^\s*\d+\.\s")  # "24. ..." etc.

def load(path: Path) -> BeautifulSoup:
    html = path.read_text(encoding="utf-8", errors="ignore")
    return BeautifulSoup(html, "lxml")  # lxml er mere tolerant

def tag_starts_question(tag: Tag) -> bool:
    # accepter ALLE tags med tekst, ikke kun <p>/<strong>
    txt = tag.get_text(" ", strip=True) if isinstance(tag, Tag) else ""
    return bool(txt) and bool(Q_RE.match(txt))

def collect_blocks(root: Tag):
    # gå gennem ALLE elementer i dokumentrækkefølge
    flat = [t for t in root.descendants if isinstance(t, Tag)]
    # filtrér til “blokstartere”
    starters = [t for t in flat if tag_starts_question(t)]

    blocks = []
    for idx, start in enumerate(starters):
        # block = start .. før næste starter i DOM-orden
        block = [start]
        # lav en mængde af alle efterfølgende elementer for grænse
        stop = starters[idx+1] if idx+1 < len(starters) else None
        # gå frem ad i dokument-orden fra start.next_elements
        for el in start.next_elements:
            if not isinstance(el, Tag):
                continue
            if el is stop:
                break
            block.append(el)
        blocks.append(block)
    return blocks

def find_tables(parts):
    for p in parts:
        for tbl in p.find_all("table"):
            yield tbl

def find_red_answer(parts):
    # fang også rgb() og uppercase og <font color=...>
    COLOR_PAT = re.compile(r"color\s*:\s*(#?ff0000|red|rgb\s*\(\s*255\s*,\s*0\s*,\s*0\s*\))", re.I)
    for p in parts:
        for sp in p.find_all(True):  # alle tags
            style = (sp.get("style") or "")
            color_attr = (sp.get("color") or "")
            if COLOR_PAT.search(style) or re.fullmatch(r"(#?ff0000|red)", color_attr, re.I):
                txt = sp.get_text(" ", strip=True)
                if txt:
                    return txt
    return None

def build_out(blocks):
    out = BeautifulSoup(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>condensed</title>"
        "<style>ul{margin:1em 0;padding-left:1.2em;border:1px solid #ccc;border-radius:8px}"
        "ul>*{margin:.4em 0}li{margin-left:1.2em}"
        "table{border-collapse:collapse;margin:.6em 0}"
        "table,th,td{border:1px solid #aaa;padding:.35em}</style>"
        "</head><body></body></html>", "lxml"
    )
    body = out.body
    for block in blocks:
        ul = out.new_tag("ul")

        # behold hele spørgsmålsteksten (første tag) som HTML
        ul.append(BeautifulSoup(str(block[0]), "lxml"))

        # behold tabeller
        for tbl in find_tables(block[1:]):
            ul.append(BeautifulSoup(str(tbl), "lxml"))

        # kun det røde svar
        ans = find_red_answer(block[1:])
        li = out.new_tag("li")
        if ans:
            strong = out.new_tag("strong")
            span = out.new_tag("span", style="color:#ff0000;")
            span.string = ans
            strong.append(span)
            li.append(strong)
        else:
            # prøv at få nr. ud, ellers “ukendt”
            qtext = block[0].get_text(" ", strip=True)
            qnum = qtext.split(".")[0] if Q_RE.match(qtext) else "ukendt"
            em = out.new_tag("em")
            em.string = f"Kunne ikke finde rødt svar for spørgsmål {qnum}. (Manuel gennemgang)"
            li.append(em)
        ul.append(li)

        body.append(ul)
    return out

def main():
    if len(sys.argv) < 3:
        print("Usage: python condense_ccna_html_v2.py <input.html> <output.html>")
        sys.exit(1)

    inp = Path(sys.argv[1]); outp = Path(sys.argv[2])
    soup = load(inp)
    root = soup.body or soup
    blocks = collect_blocks(root)
    # DEBUG-linje: vis hvor mange
    print(f"Questions found: {len(blocks)}")
    out_soup = build_out(blocks)
    outp.write_text(str(out_soup), encoding="utf-8")
    print(f"Wrote: {outp}")

if __name__ == "__main__":
    main()
