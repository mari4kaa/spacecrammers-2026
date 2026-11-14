"""Merge PSI metadata + curated notes + normalized tests + quality log into one compact JSON bundle.
Usage: python3 build_data.py <raw_meta_dir> <data_dir> <out_json>
"""
import json, csv, sys, re, pathlib, math
META = pathlib.Path(sys.argv[1]); D = pathlib.Path(sys.argv[2]); OUT = pathlib.Path(sys.argv[3])
cur = json.load(open(D / "curated.json"))
tests = list(csv.DictReader(open(D / "tests.csv")))
qlog = list(csv.DictReader(open(D / "quality_log.csv")))


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


SHORT = {"PSI-62": "BASS flame model", "PSI-115": "SAME smoke sim", "PSI-60": "SPICE soot analysis", "PSI-142": "Cool-flame limits", "PSI-117": "Cool-flame CFD"}
inv = []
for pid, c in cur["inv"].items():
    j = json.load(open(META / f"{pid}.json"))
    files = j.get("added") or []
    cats = {}
    for f in files:
        k = f["remote_path"].split("/")[4] if f["remote_path"].count("/") >= 4 else "other"
        cats[k] = cats.get(k, 0) + 1
    pubs = [{"t": clean(p.get("title")), "a": clean(p.get("authors"))[:120], "doi": clean(p.get("doi"))} for p in (j.get("publications") or [])]
    hw = j.get("experimentHardware")
    if isinstance(hw, list): hw = ", ".join(hw)
    rows = [t for t in tests if t["psi_id"] == pid]
    inv.append({
        "id": pid, "acr": j.get("investigationAcronym") or SHORT.get(pid, pid), "title": clean(j.get("title")),
        "type": j.get("projectType"), "platform": j.get("flightProgram") or "", "hw": clean(hw), "sub": j.get("subResearchArea"),
        "start": j.get("investigationStartDate"), "end": j.get("investigationEndDate"), "doi": j.get("doi"),
        "url": f"https://psi.nasa.gov/physci/repo/data/investigations/{pid}",
        "sizeGB": round((j.get("totalFileSize") or 0) / 1e9, 1), "nfiles": len(files), "cats": cats,
        "objective": clean(j.get("objective")), "approach": clean(j.get("approach")), "hypothesis": clean(j.get("hypothesis")),
        "impacts": clean(j.get("researchImpacts")), "pubs": pubs, "ntests": len(rows),
        "related": clean(", ".join(j.get("related_glds") or [])) if isinstance(j.get("related_glds"), list) else clean(j.get("related_glds")),
        **{k: v for k, v in c.items()},
        "quality": cur["inv_quality"].get(pid, []),
    })

# compact tests: keep only fields the page uses
KEEP = ["psi_id", "src_file", "src_row", "granularity", "test_id", "date", "fuel", "fuel_phase", "fuel_class", "sample", "size_mm", "thickness_mm",
        "o2_pct", "o2_pct_max", "o2_source", "p_atm", "p_atm_max", "p_source", "flow_cm_s", "flow_cm_s_max", "flow_source", "flow_dir", "diluent",
        "outcome", "metric_name", "metric_value", "metric_unit", "metric2_name", "metric2_value", "metric2_unit", "flags", "notes"]
NUM = {"src_row", "size_mm", "thickness_mm", "o2_pct", "o2_pct_max", "p_atm", "p_atm_max", "flow_cm_s", "flow_cm_s_max", "metric_value", "metric2_value"}
cols = KEEP
rows = []
for t in tests:
    r = []
    for k in KEEP:
        v = t[k]
        if k in NUM:
            try:
                v = float(v); v = int(v) if v.is_integer() else round(v, 4)
            except ValueError:
                v = None
        r.append(v)
    rows.append(r)

fbp = D / "boundary" / "flammability_boundary.json"
boundary = json.load(open(fbp)) if fbp.exists() else None

bundle = {"built": "2026-11-14", "about": cur["_about"], "sources": cur["sources"], "inv": inv, "cols": cols, "rows": rows,
          "quality": qlog, "incidents": cur["incidents"], "spinoffs": cur["spinoffs"], "gaps_external": cur["gaps_external"], "boundary": boundary,
          "families": cur.get("families", {}), "shared_links": cur.get("shared_links", [])}
s = json.dumps(bundle, separators=(",", ":"), ensure_ascii=False)
OUT.write_text(s)
print("bundle KB", len(s) // 1024, "inv", len(inv), "rows", len(rows), "quality", len(qlog))
