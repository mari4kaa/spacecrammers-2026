# FireSight: fire-safety insights from NASA's microgravity combustion data

NASA Space Apps Challenge 2026 submission by team Spacecrammers.

FireSight ranks and explains the combustion investigations in NASA's Physical Sciences Informatics (PSI) repository against the fire-safety needs of a crewed habitat you describe: a lunar base at 30% O₂ / 10.2 psi, a Mars habitat, the ISS, a spacesuit, or your own settings.

- **Live site:** https://mari4kaa.github.io/spacecrammers-2026/
- **Data:** 24 PSI investigations, 1,958 cleaned test rows from 19 PSI experiment tables, 157 logged data-quality issues
- **AI:** built with AI assistance. The code, data-cleaning rules, digitized boundary points, evidence tables and investigation summaries were produced with Claude (Anthropic); the live assistant ("Ask the data") uses Google Gemini and answers only with lookups into the dataset. Full disclosure: [AI_USE.md](AI_USE.md).

## What's in the repo

| Path | What it is |
|---|---|
| `docs/index.html` | The whole dashboard in one file (served by GitHub Pages) |
| `web/template.html` | Page source; data is inserted at build time |
| `data/` | Cleaned dataset (`tests.csv`), data-quality log, AI-written cards (`curated.json`), bundle used by the page; described in `data/README.md` and `data/datapackage.json` |
| `data/evidence/` | Fire-safety evidence tables (BRE, FLEX, SAME) used by the Safety evidence tab (see its README) |
| `AI_USE.md` | How AI was used (Space Apps disclosure) |
| `scripts/` | Data pipeline: PSI snapshot → cleaning → bundle → page; `flammability_boundary.py` fits the boundary model |
| `data/boundary/` | Flammability-boundary points from the BASS-II report, fitted curves, and how they were captured (see its README) |
| `worker/` | Tiny Cloudflare Worker that lets the public site use Gemini without exposing the API key |
| `site.config.json` | The AI proxy address the page should use |

## Run it on your computer

You need Python 3 (already on macOS). From the repo folder:

```bash
python3 -m http.server 8000 --directory docs
```

Open http://localhost:8000. Stop it with Ctrl+C.

Double-clicking `docs/index.html` also works, but the live assistant only works through the local server (the AI proxy accepts `http://localhost:8000`, not files). The page loads Plotly and fonts from the internet, so stay online.

## Make the live assistant work for everyone (Gemini)

GitHub Pages only serves static files, and an API key put in a static page is public. So the page talks to a small proxy that keeps the key secret. The assistant uses Google's Gemini API.

How the page connects:
- On GitHub Pages (and on `http://localhost:8000`) → the proxy set in `site.config.json`, which calls Gemini with the key it keeps secret. Visitors never need a key.
- Inside claude.ai (the artifact copy of the dashboard) → Claude through claude.ai.

### One-time setup (about 15 minutes)

1. **Get a Gemini API key.** Sign in to https://aistudio.google.com with a personal Google account (not a work account), open **API keys**, click **Create API key**, and copy it. Leave billing off to stay on the free tier: nothing can be charged, and when the free daily quota runs out, visitors see "free daily quota is used up" until it resets. Note: on the free tier Google may use prompts to improve its products, so don't type anything private into the assistant.
2. **Deploy the proxy** (needs Node.js; free Cloudflare account):
   ```bash
   cd worker
   npm install
   npx wrangler login                     # opens the browser to sign in to Cloudflare
   cp .env.example .env                     # then open worker/.env and paste your key after GEMINI_API_KEY=
   npm run set-key                          # uploads the key from .env to Cloudflare as an encrypted secret
   npx wrangler deploy
   ```
   Wrangler prints the address, like `https://firesight-ai.<your-subdomain>.workers.dev`. Open `<address>/health`; it should show `"keySet":true`.
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
- `MODEL` / `FALLBACK_MODEL`: `gemini-3.5-flash-lite`, falling back to `gemini-3.1-flash-lite` when the first one's free quota is used up (each has its own free quota, roughly doubling the daily capacity). If you enable billing you can switch to a stronger model such as `gemini-3.8-flash`; then set a budget alert in Google Cloud Billing.
- `MAX_OUTPUT_TOKENS`: caps each answer.
- `RATE_PER_MINUTE`: per-visitor request cap.
- A fixed system instruction keeps the assistant on the FireSight topic.

Where the key lives: only in `worker/.env` on your computer (git-ignored, never pushed) and, encrypted, in Cloudflare's secret store. Never put it in `site.config.json`, `docs/` or any page file: everything in `docs/` is public.

Test the proxy locally: with the key in `worker/.env`, run `npm run dev` (wrangler reads `.env` automatically), set `site.config.json` to `http://localhost:8787`, rebuild, and open http://localhost:8000.

## Flammability boundary (predictive model)

The **Flammability boundary** tab shows the lowest oxygen level at which a material keeps burning in microgravity, as a function of air speed, from the BASS-II experiments (PSI-25).

- **PMMA rods:** 49 points digitized from the report's Figure 6.10 and checked marker by marker. Refitted with the report's equation form, with 90% confidence and prediction bands from 3,000 bootstrap resamples. The fit matches the report's own equation within 0.33 points of O₂.
- **Cotton-fiberglass fabric (SIBAL)** and **thin PMMA:** exact values from report Tables 7.1 and 2.1.
- **Scenario verdict:** for the scenario's air speed and O₂, the page says whether a PMMA flame would keep burning, using the lower edge of the prediction band as the conservative limit.
- **Main result:** the conservative microgravity limit is about 12.9% O₂ near 2 cm/s, against 15.4% in normal gravity. Earth screening tests overstate the safety margin.
- **Limits:** about 1 atm, microgravity only, two materials. Details are in `data/boundary/README.md`.

Re-run the fit after changing the points:
```bash
pip install numpy scipy
python3 scripts/flammability_boundary.py
python3 scripts/build_data.py raw/meta data data/bundle.json   # needs the PSI snapshot in raw/
python3 scripts/build_page.py
```

## Safety evidence tab

Three charts built from measured flight data in the papers (files in `data/evidence/`, sources in its README):
- **Prevention:** 83 ACME BRE ISS tests (Dehghani & Quintiere 2023, Table A.1): oxygen versus fuel flow or pressure, kept burning versus self-extinguished, with the tests near your scenario counted.
- **Suppression:** FLEX limiting oxygen for methanol and heptane with nitrogen, CO2 or helium (Dietrich et al. 2014).
- **Detection:** SAME smoke particle sizes for four materials, fresh and aged, against the ISS smoke detector's limits (SAME Final Science Report; Urban et al. 2007).

At the top of the tab, **Design takeaways for your scenario** turns this evidence into 7 points for fire-safety equipment and controls: material screening, ventilation, small fires in still air, smoke detectors, invisible cool flames, inert-gas suppression, and what no PSI test covers yet. Each card is recomputed by fixed rules from the data when the scenario changes, shows the conditions that were actually tested, and names its source; the three most important ones also appear on the Explore tab. The rules and wording were written with AI assistance (see `AI_USE.md`); no AI model runs in them. They are design inputs from small-scale tests, not a safety certification.

The assistant reads the same data through its `safety_evidence` tool. Design takeaways are available to it through `design_takeaways`. The Data tab also has a **Search the reports** box over `docs/passages.json`.

## Report search for the assistant

The live assistant can search the text of the reports and papers behind the investigation cards (`search_reports` tool). The passages live in `docs/passages.json` (about 1.9 MB, 24 documents, 2,636 passages with page numbers) and are loaded only when the assistant first searches. Every card's findings and data-quality notes are searchable too.

Rebuild it with `python3 scripts/build_passages.py <text_dir> docs/passages.json`, where `<text_dir>` holds `pdftotext` extractions of the files listed in the script's `MANIFEST` (the PDFs themselves are not in the repo). Only public-use documents are included: PSI files, NASA publications, and NTRS records marked "public use permitted". All of them are listed in `SOURCES.md`.

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

Data: NASA Physical Sciences Informatics, https://psi.nasa.gov (CC0).

Flammability boundary sources:
- Olson, S.L., et al.: Burning and Suppression of Solids-II (BASS-II) Summary Report, NASA/TM-20210011385, 2021 (https://ntrs.nasa.gov/citations/20210011385; copy in PSI-25, DOI 10.60555/4qc4-de67). Figure 6.10, Eq. 6.1, Tables 2.1 and 7.1.
- Hirsch, D., et al.: ASTM STP1454, 2003, pp. 21-26. Only the 15.4% O2 normal-gravity upward-spread limit for PMMA, as quoted in the BASS-II report (not read directly).

The full source list, with what each source was used for, is on the dashboard's Method tab. Cite each investigation by its DOI, shown on every card. Investigation summaries and findings were written by Claude (AI) from the files named on each card and fact-checked against those files on 2026-11-14 (each finding traced to a source passage or computed from the PSI table); habitat-relevance notes are interpretation. Check the source before citing.
