import json, sys, urllib.parse, requests, pathlib
B="https://psi.nasa.gov/geode-py/ws"
IDS=["PSI-26","PSI-25","PSI-98","PSI-99","PSI-100","PSI-102","PSI-101","PSI-47","PSI-69","PSI-20",
     "PSI-68","PSI-39","PSI-159","PSI-10","PSI-107","PSI-23","PSI-21","PSI-106","PSI-22",
     "PSI-62","PSI-115","PSI-60","PSI-142","PSI-117"]
root=pathlib.Path(sys.argv[1]); s=requests.Session()
for i in IDS:
    j=s.get(f"{B}/repo/investigations/{i}",timeout=60).json()
    (root/"meta"/f"{i}.json").write_text(json.dumps(j))
    for et in j.get("experimentalTable") or []:
        u=s.get(f"{B}/studies/{i}/download",params={"file":et["file_name"],"version":et["version"],"redirect":"false"},timeout=60).text.strip().strip('"')
        r=s.get(u,timeout=120); 
        (root/"tables"/f"{i}.csv").write_bytes(r.content); print(i,"table",r.status_code,len(r.content))
    print(i,"meta ok", j.get("investigationAcronym"), len(j.get("added") or []))
