"""Build docs/passages.json: searchable text passages from the report files the cards were written from.
The live assistant's search_reports tool loads this file on demand and quotes passages with page numbers.
Usage: python3 scripts/build_passages.py <text_dir> docs/passages.json
<text_dir> holds plain-text extractions (pdftotext, pages separated by form feeds) named as in MANIFEST.
Only public-use documents are included (PSI files, NASA publications, NTRS records marked public use permitted).
"""
import json, re, sys, pathlib
T = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
P = "https://psi.nasa.gov/physci/repo/data/investigations/"
N = "https://ntrs.nasa.gov/citations/"
MANIFEST = [
 # file, psi ids, title, url
 ("PSI-25_Reports_BASS-II Summary Report.txt", ["PSI-25"], "BASS-II Summary Report, NASA/TM-20210011385 (2021)", N + "20210011385"),
 ("PSI-25_Science Documents_BASS-II_ReadMe.txt", ["PSI-25"], "BASS-II ReadMe (PSI-25)", P + "PSI-25"),
 ("PSI-26_Presentations_BASS_Overview of Recent ISS Results.txt", ["PSI-26"], "BASS: Overview of Recent ISS Results (2013)", P + "PSI-26"),
 ("PSI-98_Science Documents_SAFFIRE-I and SAFFIRE-III Readme.txt", ["PSI-98", "PSI-100"], "SAFFIRE-I and SAFFIRE-III Readme", P + "PSI-98"),
 ("PSI-101_Reports_SAME-R_Final Report.txt", ["PSI-101"], "SAME-R Final Report", P + "PSI-101"),
 ("PSI-102_Reports_SAME_Final Science Report.txt", ["PSI-102"], "SAME Final Science Report", P + "PSI-102"),
 ("PSI-47_Reports_DAFT_30Day.PostFlightReport.txt", ["PSI-47"], "DAFT 30-Day Post-Flight Report", P + "PSI-47"),
 ("PSI-107_Reports_SPICE_FinalReport.txt", ["PSI-107", "PSI-60"], "SPICE Final Report", P + "PSI-107"),
 ("PSI-10_Reports_FinalRpt_ACMEFlameDesign.txt", ["PSI-10"], "ACME Flame Design Final Report", P + "PSI-10"),
 ("PSI-159_Reports_FinalRpt_ACME.CFI-G.txt", ["PSI-159"], "ACME CFI-G Final Report (2022)", P + "PSI-159"),
 ("PSI-23_Reports_s_Flame_final_report_20210729.txt", ["PSI-23"], "ACME s-Flame Final Report (2021)", P + "PSI-23"),
 ("PSI-39_Reports_CFI Science Final Report.txt", ["PSI-39"], "CFI Science Final Report", P + "PSI-39"),
 ("PSI-115_Reports_NNX17AF08A_FinalReport.txt", ["PSI-115"], "Smoke simulation Final Report NNX17AF08A", P + "PSI-115"),
 ("GUIDE.txt", [], "NASA, A Researcher's Guide to ISS Combustion Science (2015)", "https://www.nasa.gov/wp-content/uploads/2016/05/np-2015-10-034-jsc_combustion_in_reduced_gravity-iss-mini-book-011116-508.pdf"),
 ("ntrs-20150023456.txt", ["PSI-69"], "Dietrich et al., Detailed Results from FLEX, March 2009 to December 2011, NASA/TP-2015-216046", N + "20150023456"),
 ("ntrs-20120016855.txt", ["PSI-69"], "Nayagam et al., Methanol Droplet Extinction in O2/CO2/N2 Mixtures in Microgravity (2011)", N + "20120016855"),
 ("ntrs-20140006750.txt", ["PSI-69", "PSI-39"], "Nayagam et al., Cool-flame Extinction During N-Alkane Droplet Combustion in Microgravity (2014)", N + "20140006750"),
 ("ntrs-20170009141.txt", ["PSI-20"], "Markan et al., Emulation of Condensed Fuel Flames Using a Burning Rate Emulator (BRE) in Microgravity (2017)", N + "20170009141"),
 ("ntrs-20220005205.txt", ["PSI-20", "PSI-21", "PSI-22", "PSI-10", "PSI-23", "PSI-159"], "Stocker, Laminar Non-Premixed Flames of Gaseous Fuel Aboard the ISS (2022)", N + "20220005205"),
 ("PSI-26_fabric_paper_2013.txt", ["PSI-26"], "Ferkul et al., Flammability Aspects of Fabric in Opposed and Concurrent Air Flow in Microgravity (2013)", P + "PSI-26"),
 ("PSI-26_fabric_ASGSR2012.txt", ["PSI-26"], "BASS: Flammability Aspects of Cotton-Fiberglass Fabric (ASGSR 2012 presentation)", P + "PSI-26"),
 ("ntrs-20070031686.txt", ["PSI-102", "PSI-101", "PSI-47"], "Urban et al., Particle and Smoke Detection on ISS for Next Generation Smoke Detectors (2007)", N + "20070031686"),
 ("ntrs-20140017780.txt", ["PSI-106"], "Ma et al., Soot Formation in a Coflow Jet Flame Under Microgravity and Normal Gravity (2014)", N + "20140017780"),
 ("ntrs-20150002322.txt", ["PSI-106"], "Cao et al., Coflow Laminar Methane/Air Diffusion Flames: Effects of Fuel Dilution, Inlet Velocity, and Gravity (2014)", N + "20150002322"),
]
VOCAB = set()
for _fn, *_rest in MANIFEST:
    if (T / _fn).exists(): VOCAB.update(w.lower() for w in re.findall(r"[A-Za-z]+", (T / _fn).read_text(errors="ignore")))
def _join(m):
    a, b = m.group(1), m.group(2)
    return a + b if (a + b).lower() in VOCAB else a + "-" + b
def clean(s):
    s = s.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff")
    s = re.sub(r"([A-Za-z]+)-[ \t]*\n\s*([a-z]+)", _join, s)   # line-end hyphen: join only if the joined word exists elsewhere
    return re.sub(r"[ \t]+", " ", s)
REF = re.compile(r"et al\.|\bpp\.|\bvol\.|\(\d{4}\)|\b(19|20)\d{2}[,.;]|doi|Proc\.|Combust\.|J\. ")
def good(p):
    if len(REF.findall(p)) >= 5: return False          # reference lists
    letters = sum(c.isalpha() for c in p); digits = sum(c.isdigit() for c in p)
    return len(p) >= 160 and letters > 0.6 * len(p.replace(" ", "")) and digits < 0.12 * len(p)
SHORT = {'PSI-25_Reports_BASS-II Summary Report.txt': 'BASS-II Summary Report', 'PSI-25_Science Documents_BASS-II_ReadMe.txt': 'BASS-II ReadMe', 'PSI-26_Presentations_BASS_Overview of Recent ISS Results.txt': 'BASS overview 2013', 'PSI-98_Science Documents_SAFFIRE-I and SAFFIRE-III Readme.txt': 'Saffire Readme', 'PSI-101_Reports_SAME-R_Final Report.txt': 'SAME-R Final Report', 'PSI-102_Reports_SAME_Final Science Report.txt': 'SAME Final Report', 'PSI-47_Reports_DAFT_30Day.PostFlightReport.txt': 'DAFT 30-day report', 'PSI-107_Reports_SPICE_FinalReport.txt': 'SPICE Final Report', 'PSI-10_Reports_FinalRpt_ACMEFlameDesign.txt': 'Flame Design Final Report', 'PSI-159_Reports_FinalRpt_ACME.CFI-G.txt': 'CFI-G Final Report', 'PSI-23_Reports_s_Flame_final_report_20210729.txt': 's-Flame Final Report', 'PSI-39_Reports_CFI Science Final Report.txt': 'CFI Final Report', 'PSI-115_Reports_NNX17AF08A_FinalReport.txt': 'Smoke simulation report', 'GUIDE.txt': "NASA Researcher's Guide 2015", 'ntrs-20150023456.txt': 'Dietrich et al. 2015 (FLEX data report)', 'ntrs-20120016855.txt': 'Nayagam et al. 2011', 'ntrs-20140006750.txt': 'Nayagam et al. 2014', 'ntrs-20170009141.txt': 'Markan et al. 2017', 'ntrs-20220005205.txt': 'Stocker 2022', 'ntrs-20140017780.txt': 'Ma et al. 2014', 'ntrs-20150002322.txt': 'Cao et al. 2014', 'PSI-26_fabric_paper_2013.txt': 'Ferkul et al. 2013', 'PSI-26_fabric_ASGSR2012.txt': 'BASS fabric ASGSR 2012', 'ntrs-20070031686.txt': 'Urban et al. 2007'}
KEY_ON = re.compile(r"^(\d+(\.\d+)*\.?\s*)?(abstract|summary|conclusions?|concluding remarks|results( and discussion)?|key findings)\b", re.I)
KEY_OFF = re.compile(r"^(\d+(\.\d+)*\.?\s*)?(introduction|background|references|acknowledg\w*|nomenclature|appendix)\b", re.I)
docs, passages = [], []
for fn, ids, title, url in MANIFEST:
    f = T / fn
    if not f.exists(): print("missing", fn); continue
    k = len(docs)
    raw = f.read_text(errors="ignore")
    pages = raw.split("\f") if "\f" in raw else [raw]
    key = 0
    for pno, page in enumerate(pages, 1):
        paras = [re.sub(r"\s*\n\s*", " ", x).strip() for x in re.split(r"\n\s*\n", clean(page))]
        buf = ""
        for para in paras:
            if KEY_ON.match(para): key = 1
            elif KEY_OFF.match(para): key = 0
            buf = (buf + " " + para).strip()
            if len(buf) >= 500:
                for i in range(0, len(buf), 900):
                    chunk = buf[i:i + 900]
                    if good(chunk): passages.append([k, pno, chunk, 1 if (key or (pno == 1 and fn.startswith("ntrs-")) or re.search(r"\babstract\b|\bconclu|\bin summary\b", chunk[:120], re.I)) else 0])
                buf = ""
        if buf and good(buf): passages.append([k, pno, buf[:900], 1 if (key or (pno == 1 and fn.startswith("ntrs-"))) else 0])
    docs.append({"title": title, "short": SHORT.get(fn, title), "psi": ids, "url": url, "paged": "\f" in raw})
# re-index docs to the ones kept
OUT.write_text(json.dumps({"about": "Text passages from public-use report files behind the FireSight cards, for the assistant's search_reports tool. [doc index, page, text, 1 if in an abstract/results/conclusions section].", "docs": docs, "passages": passages}, separators=(",", ":"), ensure_ascii=False))
print(len(docs), "docs,", len(passages), "passages,", round(OUT.stat().st_size / 1e6, 2), "MB")
