"""Unpack a single-file (bundled) blog post export into a normal page of this site.

    python tools/unpack_post.py "../syto-blog-post-source/Syto Blog Post.html" blog/syto \
        --title "Classifying a tissue sample one DNA fragment at a time" \
        --description "Assigning a DNA fragment to its most likely cell of origin gets harder ..." \
        --image https://compepigen.github.io/blog/syto/teaser.png

The export is a loader page that rebuilds the post in the browser from a
JSON-encoded HTML template plus base64 assets. This script does that work once,
ahead of time: it writes the template out as <out_dir>/index.html (readable,
editable HTML) and every asset as a real file under <out_dir>/assets/, then adds
the site header, page title and link-preview metadata.

The post's runtime looks up React and its data files through window.__resources;
the script defines that map with the local file paths, so nothing is fetched
from a CDN. Serve the result over http(s) (GitHub Pages, or
`python -m http.server`); opening index.html from disk will not load the data.
"""
import argparse
import base64
import gzip
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = {"application/json": "json", "application/javascript": "js", "text/javascript": "js",
       "font/woff2": "woff2", "text/css": "css", "image/png": "png", "image/svg+xml": "svg"}
FOLDER = {"json": "data", "js": "js", "woff2": "fonts", "css": "css", "png": "img", "svg": "img"}


def header_html(prefix):
    return f"""<header class="site-header site-header--post">
  <div class="wrap">
    <nav class="nav" aria-label="Main">
      <a class="brand" href="{prefix}">
        <img src="{prefix}img/ccbe_mark.png" alt="">
        <span><span class="brand-name">CCBE Lab</span><span class="brand-sub">Computational Cancer Biology &amp; Epigenomics</span></span>
      </a>
      <div class="site-nav">
        <a href="{prefix}">Home</a>
        <a href="{prefix}publications/">Publications</a>
        <a href="{prefix}team/">Team</a>
        <a href="{prefix}blog/" aria-current="page">Blog</a>
      </div>
    </nav>
  </div>
</header>
"""


def head_html(prefix, title, description, image=None):
    t, d = html.escape(title), html.escape(description)
    og_image = f'<meta property="og:image" content="{html.escape(image)}">\n' if image else ""
    return (f'<title>{t} · CCBE Lab</title>\n'
            f'<meta name="description" content="{d}">\n'
            f'<meta property="og:title" content="{t}">\n'
            f'<meta property="og:description" content="{d}">\n'
            f'<meta property="og:type" content="article">\n' + og_image +
            f'<link rel="icon" href="{prefix}img/ccbe_mark.png">\n'
            f'<link rel="stylesheet" href="{prefix}assets/css/header.css">\n')


def insert_once(text, anchor, addition):
    if text.count(anchor) != 1:
        raise SystemExit(f"expected exactly one {anchor!r}, found {text.count(anchor)}")
    i = text.index(anchor) + len(anchor)
    return text[:i] + addition + text[i:]


def bundle_parts(page):
    def block(kind):
        m = re.search(rf'<script type="__bundler/{kind}">(.*?)</script>', page, re.S)
        return json.loads(m.group(1)) if m else None
    manifest, template = block("manifest"), block("template")
    if manifest is None or template is None:
        raise SystemExit("no bundler manifest/template found; is this a bundled export?")
    if block("page_order"):
        raise SystemExit("this export embeds nested pages (iframes); not supported by this script")
    return manifest, template, block("ext_resources") or []


def kebab(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def asset_names(manifest, template, ext_resources):
    """A readable file name for each asset uuid."""
    names = {}
    for e in ext_resources:  # e.g. {"id": "regionData"} or {"id": "https://unpkg.com/.../react.production.min.js"}
        rid = e["id"]
        if e["uuid"] in manifest:
            ext = EXT.get(manifest[e["uuid"]]["mime"], "bin")
            base = rid.rstrip("/").rsplit("/", 1)[-1] if "://" in rid else f"{kebab(rid)}.{ext}"
            names[e["uuid"]] = base
    # fonts: name from the @font-face rule that references them
    for subset, family, weight, uuid in re.findall(
            r"/\* ([\w-]+) \*/\s*@font-face\s*\{[^}]*?font-family:\s*'([^']+)';[^}]*?font-weight:\s*(\d+);"
            r"[^}]*?url\(\"([0-9a-f-]{36})\"\)", template):
        names[uuid] = f"{family.lower().replace(' ', '-')}-{weight}-{subset}.woff2"
    for uuid, entry in manifest.items():
        if uuid not in names:
            ext = EXT.get(entry["mime"], "bin")
            names[uuid] = f"{ext}-{uuid[:8]}.{ext}"
    return names


def decode(entry):
    data = base64.b64decode(entry["data"])
    return gzip.decompress(data) if entry.get("compressed") else data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("out_dir")
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", required=True)
    ap.add_argument("--image", help="absolute URL of the link-preview image")
    a = ap.parse_args()

    out_dir = (ROOT / a.out_dir).resolve()
    prefix = "../" * len(out_dir.relative_to(ROOT).parts)
    manifest, template, ext_resources = bundle_parts(Path(a.bundle).read_text(encoding="utf-8"))
    names = asset_names(manifest, template, ext_resources)

    assets = out_dir / "assets"
    if assets.exists():
        shutil.rmtree(assets)
    paths = {}
    for uuid, entry in manifest.items():
        name = names[uuid]
        if name.endswith(".js") and b"dc-runtime" in decode(entry):
            name = "dc-runtime.js"
        elif name.endswith(".js") and b"@ds-bundle" in decode(entry):
            name = "design-system.js"
        rel = f"assets/{FOLDER.get(name.rsplit('.', 1)[-1], 'misc')}/{name}"
        (out_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (out_dir / rel).write_bytes(decode(entry))
        paths[uuid] = rel

    # What the loader does in the browser, done once here.
    for uuid, rel in paths.items():
        template = template.replace(uuid, rel)
    template = re.sub(r'\s+integrity="[^"]*"', "", template, flags=re.I)
    template = re.sub(r'\s+crossorigin="[^"]*"', "", template, flags=re.I)
    resources = {e["id"]: paths[e["uuid"]] for e in ext_resources if e["uuid"] in paths}
    resource_script = ("\n<script>window.__resources = "
                       + json.dumps(resources, indent=1).replace("</", "<\\/") + ";</script>")
    head_open = re.search(r"<head[^>]*>", template, re.I)
    template = template[:head_open.end()] + resource_script + template[head_open.end():]

    # Site integration.
    if "site-header--post" in template:
        raise SystemExit("header already present; run this on the original export")
    template = insert_once(template, '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
                           head_html(prefix, a.title, a.description, a.image))
    template = insert_once(template, "<body>\n", header_html(prefix))
    template = template.replace("<html>", '<html lang="en">', 1)

    (out_dir / "index.html").write_text(template, encoding="utf-8")
    print(f"wrote {out_dir / 'index.html'} and {len(paths)} assets under {assets}")


if __name__ == "__main__":
    main()
