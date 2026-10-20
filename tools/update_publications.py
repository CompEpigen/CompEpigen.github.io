"""Refresh the publication lists from PubMed.

Rewrites the HTML between the PUBLICATIONS markers in publications/index.html
and the RECENT-PUBLICATIONS markers in index.html. Standard library only:

    python tools/update_publications.py

Items PubMed doesn't index (e.g. arXiv preprints) go in EXTRA below.
"""
import html
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERY = "Lutsik P[Author]"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# Current and former lab members (PubMed "Surname Initials").
# A paper counts as lab-led when one of them is first or last author.
LAB = {"Lutsik P", "Sarnataro A", "Ratto ML", "Rizdvanetskyi D", "Sacchetti G", "Mongardi C",
       # alumni
       "Roos N", "Tardieu N", "Kubalová K", "Jeong Y", "Kelly K", "Sollier E", "Chen MJ", "Moeed A"}
HIGHLIGHT = "Lutsik P"

# DOI -> software tag shown next to the paper.
SOFTWARE = {
    "10.1186/s13059-017-1182-6": "MeDeCom",
    "10.1038/s41467-025-55920-z": "MethylBERT",
    "10.1038/nmeth.3115": "RnBeads",
    "10.1186/s13059-019-1664-9": "RnBeads",
    "10.1093/nar/gkr312": "BiQ Analyzer HT",
    "10.1093/nar/gku457": "BiQ Analyzer HiMod",
    "10.1093/bioinformatics/btaa1048": "methrix",
    "10.1080/15592294.2020.1834921": "AmpliconDesign",
    "10.1186/s12859-024-05880-w": "scMAUI",
    "10.1186/s13059-024-03446-w": "epiCHAOS",
    "10.1093/bioinformatics/btae354": "figeno",
    "10.1038/s41596-020-0369-6": "DecompPipeline",
    "10.1158/2643-3230.BCD-24-0278": "Pyjacker",
}

EXTRA = [
    {
        "year": "2026",
        "title": "Data-driven soft labeling scales DNA read classification to whole-body cell-type deconvolution.",
        "authors": ["Rizdvanetskyi D", "Roos N", "Lutsik P"],
        "source": "NeurIPS 2026 (main track)",
        "url": "https://arxiv.org/abs/2607.04987",
        "tags": ["Syto"],
        "post": "blog/syto/",
    },
]


def fetch(endpoint, **params):
    url = EUTILS + endpoint + "?" + urllib.parse.urlencode({"db": "pubmed", "retmode": "json", **params})
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def pubmed_records():
    ids = fetch("esearch.fcgi", term=QUERY, retmax=500, sort="pub_date")["esearchresult"]["idlist"]
    res = fetch("esummary.fcgi", id=",".join(ids))["result"]
    out, seen_titles = [], set()
    # Published versions come first (sorted by date), so later preprint duplicates are skipped.
    recs = sorted((res[u] for u in res["uids"]), key=lambda r: "Preprint" in r.get("pubtype", []))
    for r in recs:
        types = r.get("pubtype", [])
        if "Published Erratum" in types:
            continue
        key = re.sub(r"\W+", "", r["title"].lower())
        if key in seen_titles:
            continue
        seen_titles.add(key)
        doi = next((a["value"] for a in r["articleids"] if a["idtype"] == "doi"), "")
        tags = []
        if "Preprint" in types:
            tags.append("Preprint")
        if "Review" in types:
            tags.append("Review")
        if "News" in types or "Comment" in types:
            tags.append("Commentary")
        if doi in SOFTWARE:
            tags.append(SOFTWARE[doi])
        out.append({
            "year": r["pubdate"][:4],
            "sortdate": r.get("sortpubdate", r["pubdate"]),
            "title": html.unescape(r["title"]),
            "authors": [a["name"] for a in r["authors"]],
            "source": r["source"],
            "url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{r['uid']}/",
            "tags": tags,
        })
    return out


def authors_html(authors):
    def fmt(a):
        return f"<b>{html.escape(a)}</b>" if a == HIGHLIGHT else html.escape(a)
    if len(authors) <= 6:
        return ", ".join(fmt(a) for a in authors)
    shown = authors[:3]
    if HIGHLIGHT in authors[3:-1]:
        shown += ["…", HIGHLIGHT]
    shown += ["…", authors[-1]]
    return ", ".join("…" if a == "…" else fmt(a) for a in shown).replace(", …,", " …")


def is_led(p):
    return p["authors"][0] in LAB or p["authors"][-1] in LAB


def item_html(p, indent, prefix=""):
    tags = "".join(
        f'<span class="tag {"tag-outline" if t in ("Preprint", "Review", "Commentary") else "tag-accent"}">{html.escape(t)}</span>'
        for t in p["tags"])
    post = f'<a href="{prefix}{p["post"]}">Blog post</a>' if p.get("post") else ""
    led = " data-led" if is_led(p) else ""
    pad = " " * indent
    return (
        f'{pad}<li class="pub"{led}>\n'
        f'{pad}  <span class="pub-year">{p["year"]}</span>\n'
        f'{pad}  <div>\n'
        f'{pad}    <a class="pub-title" href="{html.escape(p["url"])}">{html.escape(p["title"])}</a>\n'
        f'{pad}    <div class="pub-authors">{authors_html(p["authors"])}</div>\n'
        f'{pad}    <div class="pub-venue"><em>{html.escape(p["source"])}</em>{tags}{post}</div>\n'
        f'{pad}  </div>\n'
        f'{pad}</li>'
    )


def replace_between(path, name, body):
    text = path.read_text(encoding="utf-8")
    pat = re.compile(rf"(<!-- {name}:START -->)(.*?)(\s*<!-- {name}:END -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"markers {name} not found in {path}")
    path.write_text(pat.sub(lambda m: m.group(1) + "\n" + body + m.group(3), text), encoding="utf-8")


def main():
    pubs = pubmed_records()
    for e in EXTRA:
        pubs.append({**e, "sortdate": e["year"] + "/12/31"})
    pubs.sort(key=lambda p: p["sortdate"], reverse=True)

    by_year = defaultdict(list)
    for p in pubs:
        by_year[p["year"]].append(p)
    blocks = []
    for year in sorted(by_year, reverse=True):
        items = "\n".join(item_html(p, 10, "../") for p in by_year[year])
        blocks.append(
            f'      <section class="year-block" aria-label="{year}">\n'
            f'        <h3>{year}</h3>\n'
            f'        <ol class="pubs">\n{items}\n        </ol>\n'
            f'      </section>')
    replace_between(ROOT / "publications" / "index.html", "PUBLICATIONS", "\n".join(blocks))


    recent = [p for p in pubs if is_led(p)][:5]
    items = "\n".join(item_html(p, 8) for p in recent)
    replace_between(ROOT / "index.html", "RECENT-PUBLICATIONS", f'      <ol class="pubs">\n{items}\n      </ol>')
    print(f"{len(pubs)} publications written ({sum(map(is_led, pubs))} lab-led).")


if __name__ == "__main__":
    main()
