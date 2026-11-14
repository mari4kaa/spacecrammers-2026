# FireSight: fire-safety insights from NASA's microgravity combustion data

NASA Space Apps Challenge 2026 submission by team Spacecrammers.

FireSight ranks and explains the combustion investigations in NASA's Physical Sciences Informatics (PSI) repository against the fire-safety needs of a crewed habitat you describe: a lunar base at 30% O₂ / 10.2 psi, a Mars habitat, the ISS, a spacesuit, or your own settings.

- **Live site:** https://mari4kaa.github.io/spacecrammers-2026/
- **Data:** 24 PSI investigations, 1,958 cleaned test rows from 19 PSI experiment tables, 157 logged data-quality issues
- **AI:** summaries written in advance from 13 PSI reports, plus a live assistant ("Ask the data") that answers with lookups into the dataset

## What's in the repo

| Path | What it is |
|---|---|
| `docs/index.html` | The whole dashboard in one file (served by GitHub Pages) |
| `web/template.html` | Page source; data is inserted at build time |
| `data/` | Cleaned dataset (`tests.csv`), data-quality log, AI-written cards (`curated.json`), bundle used by the page |
| `scripts/` | Data pipeline: PSI snapshot → cleaning → bundle → page |
| `worker/` | Tiny Cloudflare Worker that lets the public site use Claude without exposing the API key |
| `site.config.json` | The AI proxy address the page should use |

## Run it on your computer

You need Python 3 (already on macOS). From the repo folder:

```bash
python3 -m http.server 8000 --directory docs
```

Open http://localhost:8000. Stop it with Ctrl+C.

Double-clicking `docs/index.html` also works, but the live assistant only works through the local server (the AI proxy accepts `http://localhost:8000`, not files). The page loads Plotly and fonts from the internet, so stay online.

## Make the live assistant work for everyone

GitHub Pages only serves static files, and an API key put in a static page is public. So the page talks to a small proxy that keeps the key secret.

How the page picks its AI connection:
1. Opened inside claude.ai → uses Claude through claude.ai.
2. A visitor pasted their own Anthropic API key (under "Use my own Anthropic API key") → calls Anthropic directly from their browser.
3. Otherwise → the proxy in `site.config.json`.

### One-time setup (about 15 minutes)

1. **Get an API key.** At https://console.anthropic.com create an API key and, under billing, set a monthly spending limit. This is your real cost guard.
2. **Deploy the proxy** (needs Node.js; free Cloudflare account):
   ```bash
   cd worker
   npm install
   npx wrangler login                       # opens the browser to sign in to Cloudflare
   npx wrangler secret put ANTHROPIC_API_KEY  # paste the key when asked
   npx wrangler deploy
   ```
   Wrangler prints the address, like `https://firesight-ai.<your-subdomain>.workers.dev`. Check it with `<address>/health`.
3. **Point the site at it.** Put that address in `site.config.json`:
   ```json
   { "ai_proxy_url": "https://firesight-ai.<your-subdomain>.workers.dev" }
   ```
   then rebuild the page and push:
   ```bash
   python3 scripts/build_page.py
   git add -A && git commit -m "Connect live assistant" && git push
   ```

### Limits built into the proxy (`worker/wrangler.toml`)

- `ALLOWED_ORIGINS`: only your GitHub Pages site and `http://localhost:8000` can call it.
- `MODEL`: `claude-haiku-5-5` (fast and cheap); change to another Claude model if you want.
- `MAX_TOKENS`: caps each answer.
- `RATE_PER_MINUTE`: per-visitor request cap.
- A fixed system instruction keeps the assistant on the FireSight topic.

Test the proxy locally: put `ANTHROPIC_API_KEY=...` in `worker/.dev.vars` (git-ignored), run `npm run dev`, set `site.config.json` to `http://localhost:8787`, rebuild, and open http://localhost:8000.

## Publish with GitHub Pages

Repo **Settings → Pages → Build and deployment**: Source *Deploy from a branch*, Branch `main`, folder `/docs`. The site appears at https://mari4kaa.github.io/spacecrammers-2026/ a minute after each push.

## Rebuild the data from PSI

```bash
pip install requests python-docx
python3 scripts/snapshot.py raw                 # PSI metadata + experiment tables (into raw/, git-ignored)
python3 scripts/getdocs.py                       # selected PSI reports (optional, for reading)
python3 scripts/normalize.py raw/tables data     # -> data/tests.csv, data/quality_log.csv
python3 scripts/build_data.py raw/meta data data/bundle.json
python3 scripts/build_page.py                    # -> docs/index.html
```

## Data and credits

Data: NASA Physical Sciences Informatics, https://psi.nasa.gov (CC0). Cite each investigation by its DOI, shown on every card. Investigation summaries and findings were written by Claude from the PSI files named on each card; check them against the source before citing.
