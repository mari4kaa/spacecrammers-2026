"""Normalize PSI combustion Experimental Tables into one test matrix.

Usage: python3 normalize.py <raw_tables_dir> <out_dir>
Writes tests.csv, tests.json and quality_log.csv.
Every output row keeps psi_id + src_file + src_row so it can be traced back to the PSI CSV.
"""
import csv, json, re, sys, datetime, pathlib, io

RAW = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
ROWS, LOG = [], []
ACR = {"PSI-26": "BASS", "PSI-25": "BASS-II", "PSI-98": "SAFFIRE-I", "PSI-99": "SAFFIRE-II", "PSI-100": "SAFFIRE-III",
       "PSI-102": "SAME", "PSI-101": "SAME-R", "PSI-47": "DAFT", "PSI-69": "FLEX", "PSI-68": "FLEX-2", "PSI-39": "CFI",
       "PSI-159": "ACME CFI-G", "PSI-10": "ACME Flame Design", "PSI-107": "SPICE", "PSI-23": "ACME s-Flame",
       "PSI-21": "ACME CLD Flame", "PSI-106": "SLICE", "PSI-22": "ACME E-FIELD", "PSI-20": "ACME BRE"}

FIELDS = ["uid", "psi_id", "acronym", "src_file", "src_row", "granularity", "test_id", "date", "fuel", "fuel_phase", "fuel_class",
          "sample", "size_mm", "thickness_mm", "o2_pct", "o2_pct_max", "o2_source", "p_atm", "p_atm_max", "p_source",
          "flow_cm_s", "flow_cm_s_max", "flow_source", "flow_dir", "diluent", "outcome", "metric_name", "metric_value",
          "metric_unit", "metric2_name", "metric2_value", "metric2_unit", "flags", "notes"]


def read(name):
    b = (RAW / name).read_bytes()
    try:
        t = b.decode("utf-8-sig")
    except UnicodeDecodeError:
        t = b.decode("latin-1")
    rows = list(csv.reader(io.StringIO(t)))
    hdr = [h.strip() for h in rows[0]]
    return hdr, rows[1:]


def num(s):
    if s is None: return None
    m = re.search(r"-?\d*\.?\d+", str(s).replace(",", ""))
    return float(m.group()) if m else None


def nums(s):
    return [float(x) for x in re.findall(r"-?\d*\.?\d+", str(s or ""))]


def log(pid, src_row, field, raw, action, code):
    LOG.append({"psi_id": pid, "acronym": ACR.get(pid, pid), "src_row": src_row, "field": field, "raw_value": str(raw)[:160],
                "action": action, "code": code})


def add(pid, src, srow, **k):
    r = {f: "" for f in FIELDS}
    r.update(psi_id=pid, acronym=ACR[pid], src_file=src, src_row=srow, uid=f"{pid}:{src.split('.')[0][-2:] if '_' in src else ''}{srow}")
    r.update({kk: ("" if v is None else v) for kk, v in k.items()})
    r["uid"] = f"{pid}:{src}:{srow}"
    ROWS.append(r)
    return r


def flagjoin(*f):
    return ";".join(x for x in f if x)


def solid_class(m):
    m = m.lower()
    if "sibal" in m or "cotton" in m: return "fabric (cotton-fiberglass)"
    if "nomex" in m: return "fabric (Nomex aramid)"
    if "ultem" in m: return "plastic (Ultem PEI)"
    if "kapton" in m: return "plastic (Kapton polyimide)"
    if "teflon" in m: return "plastic (Teflon PTFE)"
    if "silicone" in m: return "elastomer (silicone)"
    if "wax" in m or "candle" in m: return "wax"
    if "lampwick" in m: return "fabric (lampwick cotton)"
    if "pmma" in m or "sphere" in m or "rod" in m or "slab" in m: return "plastic (PMMA acrylic)"
    return "other solid"


# ---------------------------------------------------------------- BASS (PSI-26)
def bass():
    pid, f = "PSI-26", "PSI-26.csv"; h, rows = read(f)
    seen = {}
    for i, r in enumerate(rows, start=2):
        date, gmt, asrun, test, sample, mat = (r + [""] * 6)[:6]
        if not test.strip():
            log(pid, i, "Fuel Sample Material", mat, "row dropped (not a burn)", "NON_TEST_ROW"); continue
        fl = []
        d = date.strip()
        if "`" in d:
            log(pid, i, "Date", d, "read as 2012", "DATE_TYPO"); d = d.replace("`12", "2012"); fl.append("DATE_TYPO")
        if d.endswith("2103"):
            log(pid, i, "Date", d, "read as 2013", "DATE_TYPO"); d = d[:-4] + "2013"; fl.append("DATE_TYPO")
        try:
            dt = datetime.datetime.strptime(d, "%m/%d/%Y")
            if gmt.strip() and int(gmt) != dt.timetuple().tm_yday:
                log(pid, i, "GMT", f"{date} vs GMT {gmt}", f"day-of-year should be {dt.timetuple().tm_yday}; kept date", "DATE_GMT_MISMATCH"); fl.append("DATE_GMT_MISMATCH")
            d = dt.date().isoformat()
        except ValueError:
            pass
        if asrun in seen:
            log(pid, i, "As Run Test #", asrun, f"also used on row {seen[asrun]}; kept both", "DUPLICATE_ID"); fl.append("DUPLICATE_ID")
        seen.setdefault(asrun, i)
        m = re.sub(r"\s+", " ", mat).strip()
        geom = "sphere" if "sphere" in m.lower() else "slab" if "slab" in m.lower() else "candle" if "candle" in m.lower() else "sheet" if "sheet" in m.lower() else "flat sample"
        sz = num(re.search(r"(\d+)\s*cm", m).group(1)) * 10 if re.search(r"(\d+)\s*cm", m) else None
        direction = "opposed" if "oppos" in m.lower() or "oppsed" in m.lower() else ""
        if "oppsed" in m.lower(): log(pid, i, "Fuel Sample Material", m, "read as 'opposed'", "TYPO")
        add(pid, f, i, granularity="test", test_id=test.strip(), date=d, fuel=m, fuel_phase="solid", fuel_class=solid_class(m),
            sample=geom + (" (wake ignition)" if "wake" in m.lower() else ""), size_mm=sz,
            o2_pct=21, o2_source="assumed: ISS cabin air (BASS also ran some N2-diluted tests; O2 not tabulated per test)",
            p_atm=1.0, p_source="assumed: ISS cabin", flow_source="not tabulated (MSG duct fan, 0-40 cm/s)", flow_dir=direction,
            flags=flagjoin(*fl))


# ---------------------------------------------------------------- BASS-II (PSI-25)
def bass2():
    pid, f = "PSI-25", "PSI-25.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        r = (r + [""] * 17)[:17]
        pi, test, date, gmt, sample, mat, restr, fan, air, rad, frames, o2i, o2f, co2i, co2f, coi, cof = r
        if not test.strip(): continue
        fl = []
        m = re.sub(r"\s+", " ", mat).strip().replace('""', '"')
        thick = None
        mm = re.search(r"(\d+)\s*micron", m)
        if mm: thick = float(mm.group(1)) / 1000
        mm2 = re.search(r"(\d+(?:\.\d+)?)\s*mm", m)
        if mm2 and not thick: thick = float(mm2.group(1))
        size = None
        frac = re.search(r'(\d)/(\d)"', m)
        if frac: size = round(int(frac.group(1)) / int(frac.group(2)) * 25.4, 1)
        mw = re.search(r"(\d+(?:\.\d+)?)\s*cm\s*wide", m) or re.search(r"^(\d+)\s*cm", m)
        if mw and not size: size = float(mw.group(1)) * 10
        geom = "rod" if "rod" in m.lower() else "film" if ("film" in m.lower() or "micron" in m.lower()) else "slab" if "slab" in m.lower() else "sphere" if "sphere" in m.lower() else "fabric" if "sibal" in m.lower() else "sample"
        if "nomex" in m.lower(): geom = "fabric"
        if "candle" in m.lower(): geom = "candle"
        fv = [x for x in nums(air) if 0 <= x <= 100]
        if len(fv) > 1: fl.append("FLOW_STEPPED")
        o2a, o2b = num(o2i), num(o2f)
        if o2a is not None and o2b is not None and (o2b > o2a + 1 or o2b < 5):
            log(pid, i, "Calibrated final O2", f"initial {o2i} -> final {o2f}", "kept; check BASS-II Summary Report before use", "NEEDS_VERIFICATION"); fl.append("NEEDS_VERIFICATION")
        co = cof.strip()
        cov = num(co) if co and co not in ("OR",) else None
        if co == "OR": fl.append("CO_OVER_RANGE")
        dirn = "opposed" if pi.strip() == "Fernandez-Pello" else "concurrent (stagnation)" if pi.strip() == "Olson" else ""
        add(pid, f, i, granularity="test", test_id=test.strip(), date=date.strip(), fuel=m, fuel_phase="solid", fuel_class=solid_class(m),
            sample=geom, size_mm=size, thickness_mm=thick, o2_pct=o2a,
            o2_source="measured (calibrated initial; final in notes)", p_atm=1.0, p_source="assumed: ISS cabin",
            flow_cm_s=min(fv) if fv else None, flow_cm_s_max=max(fv) if len(fv) > 1 else None,
            flow_source="duct air display (cm/s, slow response)" if fv else "not recorded", flow_dir=dirn,
            metric_name="final CO", metric_value=cov, metric_unit="ppm" + (" (>1000, over range)" if co == "OR" else ""),
            metric2_name="final CO2", metric2_value=num(co2f), metric2_unit="% vol",
            flags=flagjoin(*fl), notes=f"PI {pi.strip()}; O2 initial {o2i} / final {o2f}; air display '{air.strip()}'")


# ---------------------------------------------------------------- SAFFIRE I/II/III
def saffire():
    for pid, f in (("PSI-98", "PSI-98.csv"), ("PSI-99", "PSI-99.csv"), ("PSI-100", "PSI-100.csv")):
        h, rows = read(f)
        if pid == "PSI-99":
            log(pid, 1, "header", "Samle Thickness ", "read as Sample Thickness", "TYPO")
            log(pid, 1, "header", "?-g Burn Length / ?-g Spread Length", "'?' is a lost 'µ' (micro-g)", "ENCODING_LOSS")
        lastmat = ""
        for i, r in enumerate(rows, start=2):
            r = r + [""] * 20
            sid = r[0].strip()
            if not re.match(r"^(S\d|2-\d)", sid):
                if sid: log(pid, i, "Sample Number", sid[:60], "row dropped (flow-visualization set or note)", "NON_TEST_ROW")
                continue
            fl = []
            mat = r[1].strip()
            if not mat:
                mat = lastmat; log(pid, i, "Material", "(blank)", f"filled down as '{mat}'", "MISSING_FILLED"); fl.append("MISSING_FILLED")
            lastmat = mat
            if pid == "PSI-99":
                th_raw = r[2]
                if re.match(r"^0\d\d\s*mm", th_raw.strip()):
                    log(pid, i, "Sample Thickness", th_raw, "read as 0.37 mm (missing decimal point)", "TYPO"); th = float("0." + th_raw.strip()[1:3]); fl.append("TYPO")
                elif "cm" in th_raw:
                    th = num(th_raw) * 10
                else:
                    th = num(th_raw) if "See" not in th_raw else None
                    if "and" in th_raw: th = None
                length, width = num(r[3]), num(r[4])
                flow, o2txt, ign_w, ign_t, burn, dirn = num(r[5]), r[6], num(r[7]), num(r[8]), r[9], r[10]
                ug_spread, g1_spread = r[12], r[14]
                o2v = nums(o2txt)
                add(pid, f, i, granularity="test", test_id=sid, fuel=mat, fuel_phase="solid", fuel_class=solid_class(mat),
                    sample=f"{length:g} x {width:g} cm sheet" if length and width else "sheet", size_mm=(width or 0) * 10 or None, thickness_mm=th,
                    o2_pct=min(o2v) if o2v else None, o2_pct_max=max(o2v) if len(o2v) > 1 else None, o2_source="derived from CO2 production (Note 1)",
                    p_atm=1.0, p_source="assumed: Cygnus cabin", flow_cm_s=flow, flow_source="nominal", flow_dir=dirn.strip().lower(),
                    outcome=f"burn {burn.strip()}; µg burn length {r[11].strip()}",
                    metric_name="µg spread rate", metric_value=num(ug_spread) if "mm/s" in ug_spread else None, metric_unit="mm/s",
                    metric2_name="1g spread rate (ground ref.)", metric2_value=num(g1_spread) if "mm/s" in g1_spread else None, metric2_unit="mm/s" if "mm/s" in g1_spread else g1_spread.strip(),
                    flags=flagjoin(*fl), notes=f"ignition {ign_w:g} W for {ign_t:g} s" if ign_w and ign_t else "")
            else:
                th_raw = r[2]
                th = num(th_raw)
                if th and th > 0.2:  # SIBAL listed as cm: 0.37 cm / .33 cm
                    log(pid, i, "Sample Thickness", th_raw, "SIBAL fabric is ~0.3-0.4 mm (SAFFIRE-II lists 0.37 mm); value kept as mm", "UNIT_SUSPECT"); fl.append("UNIT_SUSPECT")
                length, width = num(r[3]), num(r[4])
                if pid == "PSI-98":
                    log(pid, i, "Sample Length/Width", f"{r[3]} / {r[4]}", "SAFFIRE-III lists the same sample as 94 cm long x 40.6 cm wide; swapped", "VALUES_SWAPPED"); length, width = width, length; fl.append("VALUES_SWAPPED")
                    flow, o2txt, burn, dirn = num(r[5]), r[6], r[9], r[10]
                    o2v = nums(o2txt)
                    o2a, o2b, src = (min(o2v), max(o2v) if len(o2v) > 1 else None, "nominal (from table)")
                    notes = f"burn time {burn} s; ignition {r[7]} W for {r[8]} s"
                else:
                    flow, dirn = num(r[5]), r[6]
                    o2a, o2b, src = 21, None, "assumed: Cygnus cabin air (not tabulated)"
                    notes = ""
                add(pid, f, i, granularity="test", test_id=sid, fuel=mat, fuel_phase="solid", fuel_class=solid_class(mat),
                    sample=f"{length:g} x {width:g} cm sheet", size_mm=width * 10, thickness_mm=th,
                    o2_pct=o2a, o2_pct_max=o2b, o2_source=src, p_atm=1.0, p_source="assumed: Cygnus cabin",
                    flow_cm_s=flow, flow_source="nominal", flow_dir=dirn.strip().lower(), flags=flagjoin(*fl), notes=notes)


# ---------------------------------------------------------------- SAME / SAME-R / DAFT
def same():
    pid, f = "PSI-102", "PSI-102.csv"; h, rows = read(f)
    base = []
    for i, r in enumerate(rows, start=2):
        mat = r[1].strip()
        if "same conditions as 1-4" in mat:
            m = mat.split(":")[0].strip()
            log(pid, i, "Sample Material", mat, "expanded into the 4 conditions of samples 1-4", "EXPANDED_FROM_NOTE")
            for (_, fr, wl, ag) in base:
                add(pid, f, i, granularity="test condition", test_id=f"{r[0]}", fuel=m, fuel_phase="liquid" if "phthalate" in m.lower() else "solid",
                    fuel_class=solid_class(m) if "phthalate" not in m.lower() else "liquid (dibutyl phthalate)", sample="heated wire/sample (pyrolysis smoke)",
                    o2_pct=21, o2_source="assumed: ISS cabin air", p_atm=1.0, p_source="assumed: ISS cabin", flow_cm_s=fr, flow_source="nominal",
                    metric_name="weight-loss rate", metric_value=wl, metric_unit="mg/min", metric2_name="aging duration", metric2_value=ag, metric2_unit="min",
                    flags="EXPANDED_FROM_NOTE", outcome="smoke particulate collected")
            continue
        fr, wl, ag = num(r[2]), num(r[3]), num(r[4])
        base.append((i, fr, wl, ag))
        add(pid, f, i, granularity="test condition", test_id=r[0], fuel=mat, fuel_phase="solid", fuel_class=solid_class(mat),
            sample="heated wire/sample (pyrolysis smoke)", o2_pct=21, o2_source="assumed: ISS cabin air", p_atm=1.0, p_source="assumed: ISS cabin",
            flow_cm_s=fr, flow_source="nominal", metric_name="weight-loss rate", metric_value=wl, metric_unit="mg/min",
            metric2_name="aging duration", metric2_value=ag, metric2_unit="min", outcome="smoke particulate collected")

    pid, f = "PSI-101", "PSI-101.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        r = (r + [""] * 10)[:10]
        st, tn, desc, date, vel, rr, dur, pa, pm, na = r
        if not st.strip() and not tn.strip(): continue
        m = st.strip()
        add(pid, f, i, granularity="measurement", test_id=tn.strip(), date=date.strip() + " (2010)", fuel=m,
            fuel_phase="liquid" if "dbp" in m.lower() or "phthalate" in m.lower() else "solid",
            fuel_class=solid_class(m) if not ("dbp" in m.lower() or "phthalate" in m.lower()) else "liquid (dibutyl phthalate)",
            sample=desc.strip(), o2_pct=21, o2_source="assumed: ISS cabin air", p_atm=1.0, p_source="assumed: ISS cabin",
            flow_cm_s=num(vel), flow_source="inlet velocity", metric_name="heater Rt/R0 (temperature proxy)", metric_value=num(rr), metric_unit="-",
            metric2_name="net aging time", metric2_value=num(na), metric2_unit="s", outcome="smoke aerosol measured",
            notes=f"duration {dur} s; primary aging {pa} s; mixing {pm} s")

    pid, f = "PSI-47", "PSI-47.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        add(pid, f, i, granularity="session", test_id=r[0], date=r[1], fuel="Arizona Road Dust (test dust, not a fuel)", fuel_phase="dust",
            fuel_class="dust (detection baseline)", sample=r[2][:80], o2_pct=21, o2_source="assumed: ISS cabin air", p_atm=1.0,
            p_source="assumed: ISS cabin", outcome=r[4][:120], notes="Checks smoke instrument response to non-fire aerosol (nuisance-alarm baseline)")


# ---------------------------------------------------------------- FLEX family
def flex():
    pid, f = "PSI-69", "PSI-69.csv"; h, rows = read(f)
    log(pid, 1, "header", "Burning rate; mm", "values 0.3-0.8 match a droplet burning-rate constant in mm²/s; unit relabeled", "UNIT_SUSPECT")
    for i, r in enumerate(rows, start=2):
        r = (r + [""] * 15)[:15]
        tn, ident, date, gmt, fuel, p, xo2, xn2, xco2, xhe, d0, dext, k, bt, end = r
        if not tn.strip(): continue
        fl = []
        pv = num(p)
        if pv is not None and pv <= 0:
            log(pid, i, "Ambient pressure; mmHg", p, "treated as missing", "IMPOSSIBLE_VALUE"); pv = None; fl.append("IMPOSSIBLE_VALUE")
        dil = [n for n, v in (("N2", xn2), ("CO2", xco2), ("He", xhe)) if (num(v) or 0) > 0.005]
        dv = num(dext)
        if dv == 0: dv = None
        add(pid, f, i, granularity="test", test_id=ident.strip(), date=date.strip(), fuel=fuel.strip(), fuel_phase="liquid",
            fuel_class="liquid (alcohol)" if "meth" in fuel.lower() else "liquid (hydrocarbon)", sample="free droplet", size_mm=num(d0),
            o2_pct=round(num(xo2) * 100, 2) if num(xo2) is not None else None, o2_source="measured (initial mole fraction)",
            p_atm=round(pv / 760, 3) if pv else None, p_source="measured" if pv else "missing",
            flow_cm_s=0, flow_source="quiescent chamber", diluent="+".join(dil),
            outcome=end.strip(), metric_name="extinction diameter", metric_value=dv, metric_unit="mm",
            metric2_name="burning-rate constant", metric2_value=num(k), metric2_unit="mm²/s (header says mm)",
            flags=flagjoin(*fl), notes=f"burn time {bt} s; CO2 {xco2}, He {xhe}")

    pid, f = "PSI-68", "PSI-68.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        fuel, d, gas, o2, p, t, v = (r + [""] * 7)[:7]
        o2v, pv, dv, vv = nums(o2), nums(p), nums(d), nums(v)
        add(pid, f, i, granularity="matrix (planned range)", fuel=fuel.strip(), fuel_phase="liquid",
            fuel_class="liquid (alcohol mix)" if "anol" in fuel.lower() else "liquid (hydrocarbon)", sample="droplet (free or fiber)",
            size_mm=min(dv), o2_pct=min(o2v) * 100, o2_pct_max=max(o2v) * 100, o2_source="test-matrix range",
            p_atm=min(pv), p_atm_max=max(pv), p_source="test-matrix range", flow_cm_s=min(vv), flow_cm_s_max=max(vv), flow_source="test-matrix range",
            diluent=gas.strip().replace("O2/", "").replace(" or ", "/"), notes=f"droplet {d.strip()} mm; ambient {t.strip()} °C")

    pid, f = "PSI-39", "PSI-39.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        r = (r + [""] * 10)[:10]
        fn, date, tm, cir, p, o2, n2, he, fiber, fuel = r
        if not fn.strip(): continue
        add(pid, f, i, granularity="test", test_id=fn.strip(), date=date.strip(), fuel=fuel.strip(), fuel_phase="liquid",
            fuel_class="liquid (hydrocarbon)", sample="droplet on fiber" if fiber.strip().lower() == "yes" else "free droplet",
            o2_pct=round(num(o2) * 100, 2) if num(o2) is not None else None, o2_source="nominal", p_atm=num(p), p_source="nominal",
            flow_cm_s=0, flow_source="quiescent chamber", diluent="He" if (num(he) or 0) > 0 else "N2", notes=f"CIR id {cir.strip()}")


# ---------------------------------------------------------------- ACME + CFI-G
def autofix(pid, i, field, s, pat, good):
    if re.search(pat, s) and not re.search(good, s):
        new = re.sub(pat, good.replace("\\", ""), s)
        log(pid, i, field, s, f"read as '{new}' (spreadsheet auto-fill)", "AUTOFILL_FIXED")
        return new, "AUTOFILL_FIXED"
    return s, ""


def acme():
    pid, f = "PSI-20", "PSI-20.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        y, mo, d, burner, fuel, o2, nfl, note = (r + [""] * 8)[:8]
        fl = []
        o2s = o2.strip()
        if re.fullmatch(r"\d+00%", o2s):
            fixed = int(o2s[:-1]) / 100
            log(pid, i, "Oxygen Conc (percent)", o2s, f"read as {fixed:g}% (percent format applied twice)", "PERCENT_FORMAT_FIXED"); o2v = [fixed]; fl.append("PERCENT_FORMAT_FIXED")
        else:
            o2v = nums(o2s)
        add(pid, f, i, granularity="test day", date=f"{y} {mo} {d}", fuel=fuel.strip().replace("%C", "% C"), fuel_phase="gas (solid emulator)",
            fuel_class="gas burner emulating a burning solid", sample=f"porous flat burner {burner} mm", size_mm=num(burner),
            o2_pct=min(o2v), o2_pct_max=max(o2v) if len(o2v) > 1 else None, o2_source="nominal (tests that ignited)",
            p_source="varied, not tabulated", flow_cm_s=0, flow_source="quiescent chamber", diluent="N2",
            metric_name="flames ignited", metric_value=num(nfl), metric_unit="count", flags=flagjoin(*fl), notes=note.strip()[:200])

    pid, f = "PSI-21", "PSI-21.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        tt, day, fmfc, nmfc, bottle, conc, nfl, note = (r + [""] * 8)[:8]
        b, a1 = autofix(pid, i, "Fuel Bottle", bottle.strip(), r"CH(?:[5-9]|1\d)\b", "CH4")
        b, a2 = autofix(pid, i, "Fuel Bottle", b, r"C2H(?:[5-9]|1\d)\b", "C2H4")
        cv = nums(conc)
        add(pid, f, i, granularity="test day", test_id=day, date=f"20{day[:2]} day {int(day[2:])}" if len(day) == 5 else day, fuel=b,
            fuel_phase="gas", fuel_class="gas (hydrocarbon)", sample="coflow burner", o2_pct=21, o2_source="assumed: air coflow",
            p_atm=1.0, p_source="assumed", flow_source="coflow, not tabulated", diluent="N2 (fuel side)",
            metric_name="flames ignited", metric_value=num(nfl), metric_unit="count", flags=flagjoin(a1, a2),
            notes=f"{tt.strip()}; fuel conc. {conc.strip()}")

    pid, f = "PSI-22", "PSI-22.csv"; h, rows = read(f)
    last, seen = None, set()
    for i, r in enumerate(rows, start=2):
        r = (r + [""] * 10)[:10]
        if not r[1].strip():
            if last is not None and r[7].strip():
                last["notes"] += f", {r[7].strip()}"
                log(pid, i, "Fuel Conc", r[7], "continuation row merged into previous test day", "CONTINUATION_MERGED")
            continue
        key = tuple(r[:9])
        if key in seen:
            log(pid, i, "(whole row)", r[1], "exact repeat of an earlier block; dropped", "DUPLICATE_ROW"); last = None; continue
        seen.add(key)
        last = add(pid, f, i, granularity="test day", test_id=r[1], date=f"{r[2]}-{int(r[3]):02d}-{int(r[4]):02d}", fuel=r[6].strip(),
                   fuel_phase="gas", fuel_class="gas (hydrocarbon)", sample=("coflow burner" if "coflow" in r[0] else "gas-jet burner") + " + HV mesh",
                   o2_pct=21, o2_source="assumed: air", p_atm=1.0, p_source="assumed", flow_source="not tabulated", diluent="N2 (fuel side)",
                   outcome=f"mesh polarity {r[5].strip()}", metric_name="flames ignited", metric_value=num(r[8]), metric_unit="count",
                   notes=f"{r[0].strip()}; fuel conc. {r[7].strip()}")

    pid, f = "PSI-23", "PSI-23.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        tt, day, y, mo, d, atm, bottle, nfl, note = (r + [""] * 9)[:9]
        if not day.strip(): continue
        a, x1 = autofix(pid, i, "Atmosphere", atm.strip(), r"\bN[3-9]\b", "N2")
        b, x2 = autofix(pid, i, "Fuel Bottle", bottle.strip(), r"\bN[3-9]\b", "N2")
        o2v = nums(re.sub(r"N\d|O2", "", a))
        add(pid, f, i, granularity="test day", test_id=day, date=f"{y} {mo} {d}", fuel=b, fuel_phase="gas", fuel_class="gas (H2/hydrocarbon)",
            sample="porous spherical burner", o2_pct=min(o2v) if o2v else None, o2_pct_max=max(o2v) if len(o2v) > 1 else None,
            o2_source="nominal (~)", p_atm=1.0, p_source="nominal ~1 atm (rises with vitiation)", flow_cm_s=0, flow_source="quiescent chamber",
            diluent="He" if "He" in a else "N2", metric_name="flames ignited", metric_value=num(nfl), metric_unit="count",
            flags=flagjoin(x1, x2), notes=tt.strip())

    pid, f = "PSI-106", "PSI-106.csv"; h, rows = read(f)
    for i, r in enumerate(rows, start=2):
        d, fuel = (r + ["", ""])[:2]
        add(pid, f, i, granularity="test day", date=d.strip()[:11], fuel=re.sub(r"\s+", " ", fuel).strip(), fuel_phase="gas", fuel_class="gas (hydrocarbon)",
            sample="coflow jet burner (MSG/SPICE duct)", o2_pct=21, o2_source="assumed: ISS cabin air coflow", p_atm=1.0, p_source="assumed: ISS cabin",
            flow_source="coflow, not tabulated", notes=d.strip()[11:].strip())

    # CFI-G and Flame Design, normal + inverse files
    for pid, base in (("PSI-159", "PSI-159"), ("PSI-10", "PSI-10")):
        for k in (0, 1):
            f = f"{base}_{k}.csv"; h, rows = read(f)
            H = {x.strip().lower(): j for j, x in enumerate(h)}
            PH = {"RAMP", "RAMPED", "LOW O2"}
            g = lambda r, *names: next(("" if r[H[n]].strip().upper() in PH else r[H[n]] for n in names if n in H and H[n] < len(r)), "")
            for i, r in enumerate(rows, start=2):
                if not any(c.strip() for c in r): continue
                ftype = g(r, "flame type").strip()
                test = g(r, "test").strip()
                if not test: continue
                fl = []
                ph = sorted({c.strip().upper() for c in r if c.strip().upper() in PH})
                if ph:
                    fl.append("PLACEHOLDER_TEXT")
                inverse = ftype.lower().startswith("inv")
                fuel = g(r, "fuel").strip() or ("C2H4" if pid == "PSI-10" else "")
                if pid == "PSI-159":
                    p = num(g(r, "approx p (bar)"))
                    p_atm = round(p * 0.98692, 3) if p else None
                    if not inverse:
                        o2 = num(g(r, "xo2 before test")); o2b = num(g(r, "xo2  after test"))
                    else:
                        o2 = num(g(r, "xo2")); o2b = None
                    out = "; ".join(x for x in [
                        "cool flame" if g(r, "cool flame?").strip().lower().startswith("y") else "",
                        "hot ignition" if g(r, "hot ignition").strip().lower().startswith("y") else "",
                        {"SE": "self-extinguished", "FT": "flow terminated"}.get(g(r, "self-ext or flow term", "self -ext or flow term").strip(), "")] if x)
                    comm = g(r, "comments").strip()
                    if "fail" in comm.lower(): out = "failed to ignite"
                    add(pid, f, i, granularity="test", test_id=test, date=f"day {g(r, 'day')}", fuel=fuel, fuel_phase="gas", fuel_class="gas (alkane)",
                        sample=("inverse " if inverse else "normal ") + "spherical porous burner",
                        o2_pct=round(o2 * 100, 2) if o2 is not None else None, o2_pct_max=round(o2b * 100, 2) if o2b and o2b > o2 else None,
                        o2_source="burner oxidizer stream (inverse flame; ambient holds the fuel)" if inverse else "measured ambient",
                        p_atm=p_atm, p_source="approx." if p_atm else "missing", flow_cm_s=0, flow_source="quiescent chamber", diluent="N2",
                        outcome=out, metric_name="adiabatic flame temp.", metric_value=num(g(r, "tad (k)")), metric_unit="K",
                        metric2_name="burn time", metric2_value=num(g(r, "burn time (sec)")), metric2_unit="s",
                        flags=flagjoin(*fl), notes=comm[:160])
                else:
                    if not inverse:
                        o2 = num(g(r, "xo2 (init)")); o2b = None
                    else:
                        o2 = num(g(r, "xo2")); o2b = None
                    p_atm = num(g(r, "pmean (atm)"))
                    tad = g(r, "tad (k)")
                    add(pid, f, i, granularity="test", test_id=test, date=f"day {g(r, 'day')}", fuel=fuel, fuel_phase="gas", fuel_class="gas (hydrocarbon)",
                        sample=("inverse " if inverse else "normal ") + "spherical porous burner",
                        o2_pct=round(o2 * 100, 2) if o2 is not None else None,
                        o2_source="burner oxidizer stream (inverse flame)" if inverse else "measured ambient (initial)",
                        p_atm=p_atm, p_source="measured mean", flow_cm_s=0, flow_source="quiescent chamber", diluent="N2",
                        metric_name="stoichiometric mixture fraction Zst", metric_value=num(g(r, "mean zst")), metric_unit="-",
                        metric2_name="adiabatic flame temp.", metric2_value=num(tad), metric2_unit="K",
                        flags=flagjoin(*fl))
                if ph:
                    log(pid, i, "numeric columns", "/".join(ph), "text placeholder in numeric column; set to empty", "PLACEHOLDER_TEXT")


# ---------------------------------------------------------------- SPICE
def spice():
    pid, f = "PSI-107", "PSI-107.csv"; h, rows = read(f)
    seen = {}
    for i, r in enumerate(rows, start=2):
        r = (r + [""] * 9)[:9]
        if not r[3].strip(): continue
        key = tuple(x.strip() for x in r)
        if key in seen:
            log(pid, i, "(whole row)", f"{r[1]} {r[3]} {r[5]}", f"exact duplicate of row {seen[key]}; dropped", "DUPLICATE_ROW"); continue
        seen[key] = i
        fl = []
        fuel = re.sub(r"(\d+)\s+%", r"\1%", r[3].strip())
        if fuel != r[3].strip():
            log(pid, i, "Fuel", r[3], f"normalized to '{fuel}'", "LABEL_VARIANT"); fl.append("LABEL_VARIANT")
        air = num(r[8])
        if air is not None and air < 0:
            log(pid, i, "Air Rate (cm/s)", r[8], "negative reading (sensor offset at ~zero coflow); kept, treat as ≈0", "NEGATIVE_VALUE"); fl.append("NEGATIVE_VALUE")
        elif air is not None and (air < 5.4 or air > 65):
            log(pid, i, "Air Rate (cm/s)", r[8], "outside the 5.4-65 cm/s range stated in the investigation description", "OUT_OF_STATED_RANGE"); fl.append("OUT_OF_STATED_RANGE")
        if not r[2].strip():
            fl.append("MISSING_VALUE")
        fr = num(r[6])
        if fr == 0:
            log(pid, i, "Fuel Rate", r[5], "zero fuel flow", "IMPOSSIBLE_VALUE"); fl.append("IMPOSSIBLE_VALUE")
        add(pid, f, i, granularity="flame condition", test_id=f"GMT{r[0].strip()} {r[1].strip()}", date=f"day {r[0].strip()} (year not given)", fuel=fuel,
            fuel_phase="gas", fuel_class="gas (hydrocarbon)", sample=f"round nozzle {num(r[4]):.2f} mm", size_mm=num(r[4]),
            o2_pct=21, o2_source="assumed: ISS cabin air coflow", p_atm=1.0, p_source="assumed: ISS cabin",
            flow_cm_s=air, flow_source="coflow air velocity", flow_dir="coflow",
            metric_name="fuel mass flow", metric_value=fr, metric_unit="mg/s", flags=flagjoin(*fl),
            notes="" if r[2].strip() else "flame-off time missing")
    # count missing flame-off once
    miss = sum(1 for x in ROWS if x["psi_id"] == pid and "MISSING_VALUE" in x["flags"])
    if miss: log(pid, "", "GMT Flame Off", f"{miss} rows blank", "kept", "MISSING_VALUE")


for fn in (bass, bass2, saffire, same, flex, acme, spice):
    fn()

with open(OUT / "tests.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader(); w.writerows(ROWS)
# group repetitive row-level issues: one log line per (investigation, code, field, raw value)
from collections import OrderedDict
G = OrderedDict()
for l in LOG:
    k = (l["psi_id"], l["code"], l["field"], l["raw_value"] if l["code"] in ("LABEL_VARIANT", "PLACEHOLDER_TEXT", "AUTOFILL_FIXED") else l["src_row"])
    if k in G: G[k]["rows"].append(str(l["src_row"]))
    else: G[k] = dict(l, rows=[str(l["src_row"])])
LOG = [dict({kk: v for kk, v in g.items() if kk not in ("rows", "src_row")}, src_rows=",".join(g["rows"]), count=len(g["rows"])) for g in G.values()]
with open(OUT / "quality_log.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(LOG[0].keys())); w.writeheader(); w.writerows(LOG)
json.dump(ROWS, open(OUT / "tests.json", "w"))
from collections import Counter
print("rows", len(ROWS), Counter(r["acronym"] for r in ROWS))
print("issues", len(LOG), Counter(l["code"] for l in LOG))
