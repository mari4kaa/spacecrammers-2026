# Flammability boundary data (BASS-II, PSI-25)

Microgravity flammability boundaries used by the dashboard's **Flammability boundary** view. All points come from the BASS-II Summary Report, NASA/TM-20210011385 (2021), file `PSI-25_Reports_BASS-II Summary Report.pdf` in PSI investigation PSI-25 (DOI 10.60555/4qc4-de67). Tests ran on the ISS at about 1 atm in N2-diluted cabin air. NTRS record: https://ntrs.nasa.gov/citations/20210011385.

The 15.4% O2 normal-gravity comparison value is the upward flame-spread limit for PMMA with an extra 4 cm/s forced flow, which the report quotes from Hirsch, D., et al., ASTM STP1454 (2003), pp. 21-26 (its ref. 23, chapter 6). It is not a BASS-II measurement, and the Hirsch paper was not read directly.

**AI use:** the points were digitized with code written with the assistance of Claude (Anthropic), and every candidate marker was checked with Claude's assistance on zoomed crops of the figure (step 3 below); Tables 7.1 and 2.1 were transcribed with Claude's assistance. The fitting script was also written with Claude's assistance. See [`../../AI_USE.md`](../../AI_USE.md).

| File | What it is |
|---|---|
| `bass2_boundary_points.csv` | 74 verified points: material, flow, O2, outcome, source |
| `flammability_boundary.json` | Fitted curves, uncertainty bands, validation numbers, caveats (made by `scripts/flammability_boundary.py`) |

## Sources and how each was captured

| Material | Points | Source in the report | Method |
|---|---|---|---|
| PMMA rods, stagnation (concurrent) flow (Olson) | 8 quench, 14 blowoff, 27 stable flame | Figure 6.10, p. 76 | Digitized (see below) |
| SIBAL cotton-fiberglass fabric, concurrent flow (T'ien) | 23 tests (2.2 and 1.2 cm wide) | Table 7.1, p. 96 | Copied exactly |
| Thin PMMA sheet, opposed flow (Bhattacharjee) | 2 extinction speeds | Table 2.1, p. 28 | Copied exactly |

The report's appendix Table A.5 lists Olson's tests, but its flows are fan dial settings, not cm/s, so the figure is the only source of the boundary in physical units.

### Digitizing Figure 6.10

1. The page was rendered at 400 dpi. Axes were calibrated from the tick marks: `x = 882.5 + 779·log10(a)`, `y = 3223 − 219.45·(O2 − 13)` (pixels); checked on the minor ticks at a = 2 and 200, within 1 px.
2. Markers were found by color (blue diamonds = ISS stable flame, red asterisks = ISS quench, black X = ISS blowoff), with a shape filter to reject pieces of the dashed fit lines drawn in the same colors. Black X markers hidden behind diamonds were found by matching an X-shaped template.
3. Every candidate was checked by eye on zoomed crops. Decisions: two template hits that were diamonds were dropped; one X over a diamond (a ≈ 67 s⁻¹, 16.1%) was added by hand; one detection that was two touching diamonds (a ≈ 2.1 s⁻¹, 15.3% and 15.2%) was split; two diamonds hidden under red asterisks (a ≈ 1.55 s⁻¹, 16.7% and a ≈ 6.4 s⁻¹, 14.6%) were added. Drop-tower points in the same figure were not used.
4. Digitizing error is about ±0.02% O2 and ±2% in a, much smaller than the test-to-test scatter (~0.6% O2).

Stretch rate converts to air speed with the report's definition `a = (3/2)(U/r)(r/r0)^½`, `r0 = 0.318 cm`, so for the base rod `U = a·r0/1.5` (cm/s). The CSV keeps both.

### SIBAL flows

For quench and blowoff tests the final flow is used (the flow at which the flame went out); for spreading flames the lowest flow they survived; for non-ignition the test flow. Reused samples (T23–T29) are excluded, as the report does. Two tests have O2 readings the report flags as possibly inaccurate (footnote b), noted in the CSV.

## Model (PMMA rods)

Same form as the report's Eq. 6.1: `O2 = A·exp(−B·a) + C·a + D`, least-squares fit to the 22 extinction points; 3,000 case-resampling bootstrap fits give the 90% confidence band (where the boundary lies) and, with the residual scatter, the 90% prediction band (where a single test goes out).

Results (2026-11-14): A = 4.91, B = 0.50, C = 0.0161, D = 13.73 (report: 6, 0.5, 0.0167, 13.4); the two curves differ by at most 0.33 points of O2. Residual RMS 0.56; leave-one-out RMSE 0.63. The prediction band holds 95% of extinction points, and all 27 stable flames lie above its lower edge, so that lower edge is a usable "no flame below" line for this data. Minimum of the boundary: 13.9% O2 (90% CI 13.7–14.2) near 2.1 cm/s; conservative minimum 12.9% vs the 15.4% normal-gravity upward-spread limit for PMMA (Hirsch et al., quoted in the report).

## Limits

About 1 atm only; microgravity only; two materials; O2 up to about 21%. See `caveats` in `flammability_boundary.json`.
