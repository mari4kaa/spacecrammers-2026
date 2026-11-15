# Written with AI assistance (Claude, Anthropic) for InfoFlame, NASA Space Apps Challenge 2026, team Spacecrammers. See AI_USE.md.
"""Fit microgravity flammability boundaries from BASS-II (PSI-25) data.

Input : data/boundary/bass2_boundary_points.csv  (verified points, see README in that folder)
Output: data/boundary/flammability_boundary.json (fits, bands, validation, points) used by the dashboard

PMMA rods (Olson): extinction points (quench + blowoff) are fitted with the form the report uses,
    O2(a) = A*exp(-B*a) + C*a + D        a = stretch rate (s^-1) = 1.5*U/r for the 6.35-mm rod
  - 90% confidence band of the boundary: case-resampling bootstrap (3000 resamples)
  - 90% prediction band for a single test: bootstrap curve spread + residual scatter
  - validation: leave-one-out cross-validation, share of stable flames on the flammable side,
    comparison with the report's own equation (A=6, B=0.5, C=0.0167, D=13.4)
SIBAL fabric 2.2 cm (T'ien): quench flow vs O2, linear least squares with t-based 90% bands (n=4).
"""
import csv, json, math, pathlib
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data" / "boundary"
R0 = 0.318                       # cm, Olson's base rod radius
A2U = R0 / 1.5                   # U (cm/s) = a * r0 / 1.5 for the base rod
PSI_PER_ATM = 14.696
rng = np.random.default_rng(20261114)

pts = list(csv.DictReader(open(D / "bass2_boundary_points.csv")))
for p in pts:
    for k in ("flow_cm_s", "a_per_s", "o2_pct"):
        p[k] = float(p[k]) if p[k] not in ("", None) else None

def model(a, A, B, C, Dd):
    return A * np.exp(-B * a) + C * a + Dd

P0 = [6, 0.5, 0.0167, 13.4]
BOUNDS = ([0, 0.01, 0, 10], [60, 5, 0.1, 17])
PUBLISHED = dict(A=6, B=0.5, C=0.0167, D=13.4)

# ---------------------------------------------------------------- PMMA rods
rod = [p for p in pts if p["material"] == "pmma_rod"]
ext = [p for p in rod if p["outcome"] in ("quench", "blowoff")]
stable = [p for p in rod if p["outcome"] == "stable flame"]
a = np.array([p["a_per_s"] for p in ext]); y = np.array([p["o2_pct"] for p in ext])
popt, pcov = curve_fit(model, a, y, p0=P0, bounds=BOUNDS, maxfev=20000)
res = y - model(a, *popt); dof = len(a) - 4
s_res = math.sqrt((res ** 2).sum() / dof)

grid = np.unique(np.round(np.logspace(0, math.log10(160), 140), 4))
boot = []
for _ in range(3000):
    i = rng.integers(0, len(a), len(a))
    if len(set(i)) < 8: continue
    try:
        pb, _ = curve_fit(model, a[i], y[i], p0=popt, bounds=BOUNDS, maxfev=20000)
        boot.append(pb)
    except RuntimeError:
        continue
boot = np.array(boot)
curves = np.array([model(grid, *pb) for pb in boot])
mid = model(grid, *popt)
c_lo, c_hi = np.percentile(curves, 5, axis=0), np.percentile(curves, 95, axis=0)
se_fit = curves.std(axis=0)
tq = stats.t.ppf(0.95, dof)
p_lo, p_hi = mid - tq * np.sqrt(se_fit ** 2 + s_res ** 2), mid + tq * np.sqrt(se_fit ** 2 + s_res ** 2)

# minimum of the boundary (most flammable flow) with bootstrap CI
fine = np.logspace(0, math.log10(160), 2000)
def argmin_curve(pp):
    v = model(fine, *pp); k = int(np.argmin(v)); return fine[k], v[k]
amin, omin = argmin_curve(popt)
mins = np.array([argmin_curve(pb) for pb in boot])
# leave-one-out CV
loo = []
for k in range(len(a)):
    m = np.arange(len(a)) != k
    try:
        pk, _ = curve_fit(model, a[m], y[m], p0=popt, bounds=BOUNDS, maxfev=20000)
        loo.append(y[k] - model(a[k], *pk))
    except RuntimeError:
        pass
loo = np.array(loo)
st_a = np.array([p["a_per_s"] for p in stable]); st_y = np.array([p["o2_pct"] for p in stable])
st_above = float((st_y >= model(st_a, *popt) - 1e-9).mean())
st_above_pub = float((st_y >= model(st_a, *PUBLISHED.values()) - 1e-9).mean())
pub_curve = model(grid, *PUBLISHED.values())
# band checks: interpolate bands at each point's stretch rate
lo_at = lambda aa: np.interp(np.log(aa), np.log(grid), p_lo); hi_at = lambda aa: np.interp(np.log(aa), np.log(grid), p_hi)
pred_coverage = float(((y >= lo_at(a)) & (y <= hi_at(a))).mean())
st_above_lo = float((st_y >= lo_at(st_a)).mean())
param_ci = {n: [float(np.percentile(boot[:, j], 5)), float(np.percentile(boot[:, j], 95))] for j, n in enumerate("ABCD")}

rod_out = {
    "label": "PMMA rods, stagnation flow (Olson, BASS-II)",
    "x_note": "Air speed is the equivalent free-stream speed for a 6.35-mm-diameter rod (a = 1.5·U/r). Other rod sizes scale as in the report.",
    "equation": "O2 = A·exp(−B·a) + C·a + D,  a = 1.5·U / 0.318 cm",
    "params": {n: float(v) for n, v in zip("ABCD", popt)}, "params_ci90": param_ci,
    "published": PUBLISHED,
    "n_extinction": int(len(a)), "n_quench": int(sum(p["outcome"] == "quench" for p in ext)), "n_blowoff": int(sum(p["outcome"] == "blowoff" for p in ext)),
    "n_stable": len(stable), "n_bootstrap": int(len(boot)),
    "rms_residual": float(s_res), "loo_rmse": float(math.sqrt((loo ** 2).mean())), "loo_mae": float(np.abs(loo).mean()),
    "stable_on_flammable_side": st_above, "stable_on_flammable_side_published": st_above_pub,
    "max_diff_vs_published": float(np.abs(mid - pub_curve).max()),
    "pred_band_coverage": pred_coverage, "stable_above_lower_bound": st_above_lo,
    "minimum": {"a": float(amin), "U_cm_s": float(amin * A2U), "o2": float(omin),
                "o2_ci90": [float(np.percentile(mins[:, 1], 5)), float(np.percentile(mins[:, 1], 95))],
                "U_ci90": [float(np.percentile(mins[:, 0], 5) * A2U), float(np.percentile(mins[:, 0], 95) * A2U)]},
    "valid_U": [float(min(p["flow_cm_s"] for p in rod)), float(max(p["flow_cm_s"] for p in rod))],
    "one_g_reference": {"o2": 15.4, "note": "upward-spread limit in normal gravity (with an extra 4 cm/s forced flow), same report"},
    "curve": {"U": [round(float(v * A2U), 4) for v in grid], "mid": [round(float(v), 3) for v in mid],
              "conf_lo": [round(float(v), 3) for v in c_lo], "conf_hi": [round(float(v), 3) for v in c_hi],
              "pred_lo": [round(float(v), 3) for v in p_lo], "pred_hi": [round(float(v), 3) for v in p_hi],
              "published": [round(float(v), 3) for v in pub_curve]},
}

# ---------------------------------------------------------------- SIBAL 2.2 cm quench branch
sib = [p for p in pts if p["material"] == "sibal_22"]
q = [p for p in sib if p["outcome"] == "quench"]
qo = np.array([p["o2_pct"] for p in q]); qu = np.array([p["flow_cm_s"] for p in q])
lr = stats.linregress(qo, qu); n = len(qo); s = math.sqrt(((qu - (lr.intercept + lr.slope * qo)) ** 2).sum() / (n - 2))
og = np.linspace(qo.min(), qo.max(), 30); um = lr.intercept + lr.slope * og
se = s * np.sqrt(1 / n + (og - qo.mean()) ** 2 / ((qo - qo.mean()) ** 2).sum()); t2 = stats.t.ppf(0.95, n - 2)
spread = [p for p in sib if p["outcome"] == "spread"]
sib_out = {
    "label": "SIBAL cotton-fiberglass fabric 2.2 cm, concurrent flow (T'ien, BASS-II)",
    "equation": "quench flow U_q = α + β·O2 (linear, within 16.9–18.7% O2)",
    "params": {"alpha": float(lr.intercept), "beta": float(lr.slope)}, "r2": float(lr.rvalue ** 2), "n_quench": n, "rms_residual": float(s),
    "lowest_spread_o2": float(min(p["o2_pct"] for p in spread)), "no_ignition_o2": sorted({p["o2_pct"] for p in sib if p["outcome"] == "no ignition"}),
    "curve": {"o2": [round(float(v), 3) for v in og], "U_mid": [round(float(v), 3) for v in um],
              "U_lo": [round(float(v), 3) for v in um - t2 * se], "U_hi": [round(float(v), 3) for v in um + t2 * se]},
}

out = {
    "about": "Microgravity flammability boundaries from PSI-25 (BASS-II) at about 1 atm in N2-diluted cabin air. Fitted by InfoFlame; PMMA-rod points digitized from the report's Figure 6.10, SIBAL and thin-PMMA values copied from Tables 7.1 and 2.1.",
    "source_doc": "BASS-II Summary Report, NASA/TM-20210011385 (2021), file PSI-25_Reports_BASS-II Summary Report.pdf in PSI-25",
    "pressure_atm": 1.0,
    "pmma_rod": rod_out, "sibal_22": sib_out,
    "points": [{k: p[k] for k in ("material", "material_label", "configuration", "test_id", "flow_cm_s", "a_per_s", "o2_pct", "outcome", "outcome_detail", "method", "notes")} for p in pts],
    "caveats": [
        "Measured near 1 atm (14.7 psi). Planned lunar habitats run at about 8.2-10.2 psi; these curves do not include pressure effects.",
        "Microgravity only. Partial gravity (Moon, Mars) adds buoyant flow and may be more flammable; no PSI data yet (LUCI, FM2).",
        "Material- and geometry-specific: PMMA rods and one cotton-fiberglass fabric. Other materials need their own tests.",
        "Highest O2 tested here is about 18-21%. Above that the boundary only says the material burns; it cannot predict how fast.",
        "PMMA-rod points are digitized from a figure (about ±0.02% O2 and ±2% flow), smaller than the test-to-test scatter.",
    ],
}
(D / "flammability_boundary.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: rod_out[k] for k in ("params", "params_ci90", "n_extinction", "n_bootstrap", "rms_residual", "loo_rmse", "stable_on_flammable_side",
                                         "stable_on_flammable_side_published", "max_diff_vs_published", "pred_band_coverage", "stable_above_lower_bound", "minimum", "valid_U")}, indent=1))
print(json.dumps({k: sib_out[k] for k in ("params", "r2", "rms_residual", "lowest_spread_o2", "no_ignition_o2")}, indent=1))
