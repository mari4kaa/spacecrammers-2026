"""Build the single-file dashboard.

Usage: python3 scripts/build_page.py            (reads site.config.json, writes docs/index.html)
Inserts data/bundle.json and the AI proxy URL into web/template.html.
"""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "site.config.json").read_text())
bundle = (ROOT / "data" / "bundle.json").read_text().replace("</", "<\\/")
html = (ROOT / "web" / "template.html").read_text()
html = html.replace("/*__DATA__*/", bundle).replace("/*__AI_PROXY__*/", cfg.get("ai_proxy_url", "").strip())
out = ROOT / "docs" / "index.html"
out.write_text(html)
print(f"wrote {out.relative_to(ROOT)} ({len(html)//1024} KB), AI proxy: {cfg.get('ai_proxy_url') or '(none - own-key mode only)'}")
