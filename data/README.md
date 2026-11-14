# FireSight data

Data behind the FireSight dashboard. Machine-readable description: `datapackage.json` (Frictionless Data format).

**AI use:** these files were produced with AI assistance (Claude, Anthropic). Cleaning rules and scripts were written with Claude; the boundary points were digitized and the evidence tables extracted by Claude; the summaries in `curated.json` were written by Claude from the sources named in each finding. Every value keeps its source (PSI file and row, or the report table and page). Full statement: [`../AI_USE.md`](../AI_USE.md).

| File | What it is | How it was made |
|---|---|---|
| `tests.csv` | 1,958 test rows from 19 PSI experiment tables in one schema (`src_file`, `src_row` point back to PSI) | `scripts/normalize.py` (written with Claude) over the PSI tables |
| `quality_log.csv` | 157 data-quality issues and what was done | Same script |
| `curated.json` | Investigation summaries, findings, relevance notes, incidents, spinoffs, references | Written by Claude from the cited sources; checked against them on 2026-11-14 |
| `bundle.json` | Everything merged for the page | `scripts/build_data.py` |
| `boundary/` | Flammability-boundary points and fitted model from BASS-II | See `boundary/README.md` |
| `evidence/` | BRE, FLEX and SAME fire-safety tables | See `evidence/README.md` |

Data: NASA Physical Sciences Informatics, https://psi.nasa.gov (CC0). Cite each investigation by its DOI. Exception: the tables in `evidence/` come from published papers and a PSI report; they are not all CC0, so see `evidence/README.md` for each source, its terms and how to cite it.
