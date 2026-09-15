#!/usr/bin/env python3
"""
Build the usdGeospatial slide deck by DERIVING it from README.md.

The README is the single grounding document. It carries invisible HTML-comment
slide markers (which GitHub renders as nothing) that this script parses into
slides, so the deck, the PR body, and the README can never drift -- fix the
story once in the README and the deck regenerates.

Marker vocabulary (one per line, an HTML comment so it's invisible on GitHub):

  <!-- slide:title subtitle="..." -->            cover slide
  <!-- slide:section title="..." subtitle="..." --> full-bleed divider
  <!-- slide:text eyebrow="..." title="..." -->  text slide; body = markdown
      between this marker and the next marker OR next heading (image lines dropped)
  <!-- slide:image src="docs/x.png" eyebrow="..." title="..." caption="..." -->
      image slide; caption falls back to the alt-text of the next image
  <!-- slide:grid eyebrow="..." title="..." srcs="a.png|b.png" labels="1|2" -->

Markers are the ONLY thing that produce slides; prose between markers that no
text-slide claims is ignored. The deck is a curated projection, not a dump.

Render to PDF:
  python3 docs/build_deck.py
  google-chrome --headless=new --disable-gpu --no-sandbox --disable-dev-shm-usage \
    --user-data-dir=$(mktemp -d) --print-to-pdf=docs/usdGeospatial.pdf docs/deck.html
  rm -f core.*
"""
import os, re, html as _html

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)                      # .../usdGeospatial
README = os.path.join(BASE, "README.md")
OUT = os.path.join(HERE, "deck.html")


def datauri(rel):
    """Resolve an image src relative to the example dir (so 'docs/x.png' works)."""
    rel = rel.strip()
    p = rel if os.path.isabs(rel) else os.path.join(BASE, rel)
    return "file://" + p


def parse_attrs(s):
    return dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', s))


def md_inline(t):
    t = _html.escape(t)
    t = t.replace("&amp;nbsp;", "&nbsp;").replace("&amp;amp;", "&amp;")
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'`(.+?)`', r'<span class="mono">\1</span>', t)
    t = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1', t)          # drop link chrome on slides
    t = re.sub(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*', r'<i>\1</i>', t)
    return t


def md_block_to_html(lines):
    out, i, n = [], 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1; continue
        if s.startswith(">"):
            out.append(f'<p class="theme">{md_inline(s.lstrip("> ").strip())}</p>')
            i += 1; continue
        if re.match(r'^\d+\.\s+', s):
            items = []
            while i < n and re.match(r'^\d+\.\s+', lines[i].strip()):
                items.append(md_inline(re.sub(r'^\d+\.\s+', '', lines[i].strip()))); i += 1
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in items) + "</ol>")
            continue
        if s.startswith(("- ", "* ")):
            items = []
            while i < n and lines[i].strip().startswith(("- ", "* ")):
                items.append(md_inline(lines[i].strip()[2:])); i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue
        para = [s]; i += 1
        while i < n and lines[i].strip() and not lines[i].strip().startswith((">", "-", "*")) \
                and not re.match(r'^\d+\.\s', lines[i].strip()):
            para.append(lines[i].strip()); i += 1
        out.append(f"<p>{md_inline(' '.join(para))}</p>")
    return "".join(out)


def first_image_after(lines, start):
    for j in range(start, min(start + 8, len(lines))):
        m = re.search(r'!\[[^\]]*\]\(([^)]+)\)', lines[j])
        if m: return m.group(1)
    return None


def caption_after(lines, start):
    for j in range(start, min(start + 8, len(lines))):
        m = re.search(r'!\[([^\]]*)\]\(([^)]+)\)', lines[j])
        if m: return m.group(1)
    return ""


MARKER = re.compile(r'<!--\s*slide:(\w+)\s*(.*?)-->')


def build_slides():
    lines = open(README, encoding="utf-8").read().splitlines()
    marks = [(i, m.group(1), parse_attrs(m.group(2)))
             for i, ln in enumerate(lines) for m in [MARKER.search(ln)] if m]
    slides = []
    for k, (idx, kind, attrs) in enumerate(marks):
        nxt = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        if kind == "title":
            slides.append(("TITLE", attrs.get("subtitle", "")))
        elif kind == "section":
            slides.append(("SECTION", attrs.get("title", ""), attrs.get("subtitle", "")))
        elif kind == "image":
            src = attrs.get("src") or first_image_after(lines, idx + 1)
            cap = attrs.get("caption") or caption_after(lines, idx + 1)
            slides.append(("IMG", src, attrs.get("eyebrow", ""), attrs.get("title", ""), md_inline(cap)))
        elif kind == "grid":
            srcs = [s for s in attrs.get("srcs", "").split("|") if s]
            labels = [s for s in attrs.get("labels", "").split("|") if s]
            slides.append(("GRID", attrs.get("eyebrow", ""), attrs.get("title", ""), srcs, labels))
        elif kind == "text":
            if attrs.get("body"):
                # deck-authored concise body: '|' separates bullet items;
                # keeps dense long-form README prose out of the presenter slide.
                items = [x.strip() for x in attrs["body"].split("|") if x.strip()]
                if len(items) > 1:
                    body_md = ["- " + x for x in items]
                else:
                    body_md = items
                slides.append(("TEXT", attrs.get("eyebrow", ""), attrs.get("title", ""),
                               md_block_to_html(body_md)))
                continue
            stop = nxt
            for j in range(idx + 1, nxt):
                if re.match(r'^#{1,6}\s', lines[j]):
                    stop = j; break
            txt = [l for l in lines[idx + 1:stop] if not l.strip().startswith("![")]
            slides.append(("TEXT", attrs.get("eyebrow", ""), attrs.get("title", ""),
                           md_block_to_html(txt)))
    return slides


def render(slides):
    out = []
    for s in slides:
        kind = s[0]
        if kind == "TITLE":
            sub = s[1] or "a codeless CRS schema for OpenUSD"
            out.append(f"""
            <section class="slide title">
              <div class="title-wrap">
                <div class="eyebrow">OpenUSD geospatial · co-submission preview</div>
                <h1>usdGeospatial</h1>
                <div class="subtitle">{_html.escape(sub)}</div>
                <div class="footer-note">schema declares · runtime resolves · one real-world coordinate frame</div>
              </div>
            </section>""")
        elif kind == "SECTION":
            _, title, sub = s
            out.append(f"""
            <section class="slide section">
              <div class="section-wrap"><h2>{_html.escape(title)}</h2>
              <div class="section-sub">{_html.escape(sub)}</div></div>
            </section>""")
        elif kind == "TEXT":
            _, eyebrow, title, body = s
            out.append(f"""
            <section class="slide text">
              <div class="eyebrow">{_html.escape(eyebrow)}</div>
              <h2>{_html.escape(title)}</h2>
              <div class="body">{body}</div>
            </section>""")
        elif kind == "IMG":
            _, img, eyebrow, title, caption = s
            out.append(f"""
            <section class="slide img">
              <div class="img-head"><span class="eyebrow">{_html.escape(eyebrow)}</span><h2>{_html.escape(title)}</h2></div>
              <div class="img-frame"><img src="{datauri(img)}"></div>
              <div class="caption">{caption}</div>
            </section>""")
        elif kind == "GRID":
            _, eyebrow, title, imgs, labels = s
            cells = "".join(
                f'<figure><img src="{datauri(im)}"><figcaption>{_html.escape(lb)}</figcaption></figure>'
                for im, lb in zip(imgs, labels))
            out.append(f"""
            <section class="slide grid">
              <div class="eyebrow">{_html.escape(eyebrow)}</div>
              <h2>{_html.escape(title)}</h2>
              <div class="grid-wrap">{cells}</div>
            </section>""")
    return "".join(out)


CSS = """
@page { size: 1280px 720px; margin: 0; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Helvetica Neue','Liberation Sans',Arial,sans-serif; background:#0b0e14; color:#e9edf6; }
.slide { width:1280px; height:720px; position:relative; overflow:hidden; padding:64px 80px;
         display:flex; flex-direction:column; page-break-after:always; background:#0b0e14; }
.eyebrow { text-transform:uppercase; letter-spacing:.22em; font-size:15px; color:#5fb0e6; font-weight:600; }
h1 { font-size:96px; font-weight:800; letter-spacing:-.02em; line-height:1; color:#8fd3ff; }
h2 { font-size:44px; font-weight:750; letter-spacing:-.01em; margin-top:6px; color:#f3f6fc; }
.body { margin-top:26px; font-size:25px; line-height:1.5; color:#cfd6e6; max-width:1040px; }
.body p { margin-bottom:16px; }
.body ul, .body ol { margin:6px 0 6px 30px; } .body li { margin-bottom:12px; }
.theme { margin-top:28px; font-size:26px; color:#8fd3ff; border-left:4px solid #2f9e6f; padding-left:20px; }
.mono { font-family:'SF Mono',Menlo,monospace; background:#161c2b; padding:1px 8px; border-radius:5px; font-size:.84em; color:#9fe0c2; }
/* section divider */
.slide.section { justify-content:center; align-items:center; text-align:center;
                 background:linear-gradient(135deg,#0a1322 0%,#0f2540 55%,#0c2e2a 100%); }
.slide.section h2 { font-size:58px; color:#ffffff; }
.section-sub { margin-top:18px; font-size:24px; color:#a9c7e8; max-width:860px; }
/* image slide */
.slide.img { padding:48px 64px; }
.img-head { display:flex; align-items:baseline; gap:18px; margin-bottom:14px; }
.img-head h2 { font-size:36px; }
.img-frame { flex:1; display:flex; align-items:center; justify-content:center; min-height:0;
             border-radius:14px; overflow:hidden; box-shadow:0 20px 60px rgba(0,0,0,.55); background:#05070d; }
.img-frame img { max-width:100%; max-height:100%; object-fit:contain; }
.caption { margin-top:16px; font-size:20px; line-height:1.4; color:#b6c0d6; max-width:1120px; }
/* title */
.slide.title { justify-content:center; align-items:flex-start;
               background:radial-gradient(ellipse at 70% 30%, #14304f 0%, #0b0e14 60%); }
.title-wrap { max-width:960px; }
.subtitle { font-size:32px; color:#ffffff; margin-top:22px; font-weight:400; }
.footer-note { margin-top:40px; font-size:18px; color:#9fb6d6; letter-spacing:.04em; }
/* grid */
.slide.grid { padding:48px 64px; }
.grid-wrap { margin-top:24px; flex:1; display:grid; grid-template-columns:repeat(3,1fr); grid-template-rows:1fr; gap:18px; min-height:0; }
.grid-wrap figure { display:flex; flex-direction:column; min-height:0; }
.grid-wrap img { width:100%; flex:1; object-fit:contain; border-radius:9px; min-height:0; background:#05070d; box-shadow:0 8px 24px rgba(0,0,0,.5); }
.grid-wrap figcaption { margin-top:8px; font-size:15px; color:#a4b2cc; text-align:center; }
"""


def main():
    slides = build_slides()
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
           f"<body>{render(slides)}</body></html>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT} ({len(slides)} slides, {len(doc)//1024}KB)")
    print("order:", " ".join(s[0].lower() for s in slides))


if __name__ == "__main__":
    main()
