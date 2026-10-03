import json
W="."
d=json.load(open("primary-Q008.json",encoding="utf-8"))
src=open("Q008/source.txt",encoding="utf-8").read()
ref=json.load(open("Q008/reference.json",encoding="utf-8"))
acc={g["ref_id"] for g in ref["groups"] if g["status"]=="accepted"}
files={f:open("Q008/"+f,encoding="utf-8").read() for f in ["O1.md","O1_ledger.md","O2.md"]}
for o in d["inputs"][0]["outputs"]:
    a=o["output_alias"]; bad=[]
    got={c["ref_id"] for c in o["correspondence"]}
    print(a,"refs ok" if got==acc else ("refs mismatch",got^acc), len(o["correspondence"]))
    for c in o["correspondence"]:
        for s in c["evidence_spans"]:
            if s["text"] not in files[s["file"]]: bad.append(("span",c["ref_id"],s["text"]))
    np=0;nd=0
    for p in o["parents"]:
        ft=files[p["file"]]
        if p["text"] not in ft: bad.append(("parent",p["parent_id"]))
        if p["duplicate_of"] is None:
            np+=1
            if any(c["stance"]=="P" for c in p["claims"]): nd+=1
        for c in p["claims"]:
            if c["text"] not in p["text"]: bad.append(("claim",c["claim_id"],c["text"]))
            for q in c["source_quotes"]:
                if q not in src: bad.append(("src",c["claim_id"],q))
    print(a,"parents",len(o["parents"]),"nondup",np,"doubt",nd,"bad",bad)
