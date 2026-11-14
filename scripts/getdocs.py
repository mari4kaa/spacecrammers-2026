import json,requests,sys,pathlib
B="https://psi.nasa.gov/geode-py/ws"
want={"PSI-26":["PSI-26_Reports_BASS_FinalReport.pdf","PSI-26_Presentations_BASS_Overview of Recent ISS Results.pdf"],
"PSI-25":["PSI-25_Science Documents_BASS-II_ReadMe.docx","PSI-25_Reports_BASS-II Summary Report.pdf"],
"PSI-98":["PSI-98_Science Documents_SAFFIRE Objectives, Development and Status.pdf","PSI-98_Science Documents_SAFFIRE-I and SAFFIRE-III Readme.docx"],
"PSI-100":["PSI-100_Presentations_SAFFIRE_47th I Con of Env Sys presentation.pdf"],
"PSI-102":["PSI-102_Reports_SAME_Final Science Report.pdf"],
"PSI-101":["PSI-101_Reports_SAME-R_Final Report.pdf"],
"PSI-47":["PSI-47_Reports_DAFT_30Day.PostFlightReport.pdf","PSI-47_Reports_DAFT_FinalReport.doc"],
"PSI-107":["PSI-107_Reports_SPICE_FinalReport.pdf"],
"PSI-10":["PSI-10_Reports_FinalRpt_ACMEFlameDesign.pdf"],
"PSI-159":["PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"],
"PSI-23":["PSI-23_Reports_s_Flame_final_report_20210729.pdf"],
"PSI-39":["PSI-39_Reports_CFI Science Final Report.pdf"],
"PSI-115":["PSI-115_Reports_NNX17AF08A_FinalReport.pdf"]}
s=requests.Session()
for i,files in want.items():
    j=json.load(open(f"raw/meta/{i}.json")); idx={a["file_name"]:a for a in j["added"]}
    for fn in files:
        a=idx[fn]; out=pathlib.Path("raw/docs")/fn
        try:
            u=s.get(f"{B}/studies/{i}/download",params={"file":fn,"version":a.get("version",1),"redirect":"false"},timeout=60).text.strip().strip('"')
            r=s.get(u,timeout=300); out.write_bytes(r.content); print(r.status_code,len(r.content),fn)
        except Exception as e: print("ERR",fn,e)
