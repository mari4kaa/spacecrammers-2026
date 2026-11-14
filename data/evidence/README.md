# Fire-safety evidence data

Small datasets behind the dashboard's **Safety evidence** tab, each copied from a published source and checked against it.

**AI use:** these tables were extracted from the sources by Claude (Anthropic) and compared with the source pages by Claude. See [`../../AI_USE.md`](../../AI_USE.md).

| File | What | Source | How it was captured |
|---|---|---|---|
| `bre_iss_tests.csv` | 83 ACME BRE tests on the ISS (25 mm burner, ethylene or ethylene/N2): O2 before/after, pressure, fuel mass flux, heat fluxes, flame size, radiant fraction, end condition | Dehghani & Quintiere (2023), Combustion and Flame, Table A.1 (accepted manuscript, Elsevier user license) | Parsed from the PDF text and every row compared with the rendered page images. Pressure in bar (psi added), mass flux g/m2s, heat flux kW/m2, flame height/radius mm, times s. End condition: SE self-extinguished; FT burned until the fuel was shut off; FTO the same with oscillation. |
| `flex_loi_by_diluent.csv` | FLEX limiting oxygen index at 1 atm for methanol and heptane with N2, CO2 or helium added to air | Dietrich et al. (2014), Microgravity Sci. Technol. 26:65-76 (open access, CC BY 4.0), abstract | Copied from the abstract wording. |
| `same_smoke_particle_sizes.csv` | Smoke particle size moments for four spacecraft materials, fresh and aged, from SAME flight tests | SAME Final Science Report (PSI-102), Table 1, p. 27 | Copied from the report table. |

Notes:
- In `bre_iss_tests.csv`, oxygen and pressure were not varied independently (most 1-bar tests were at 18-25% O2), so the pressure effect cannot be separated cleanly from these rows alone; the paper concludes oxygen fraction dominated over 0.56-1 bar.
- Test 20261G1 shows O2 falling from 0.392 to 0.298 during the test, much more than any other row; kept as published.
- The ISS smoke detector reference lines (0.3 um minimum reported sensitivity; most sensitive above 1 um) come from Urban et al., Particle and Smoke Detection on ISS for Next Generation Smoke Detectors (NASA, 2007, NTRS 20070031686).
