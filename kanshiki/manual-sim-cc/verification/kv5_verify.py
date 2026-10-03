#!/usr/bin/env python3
"""AI鑑識官v5 予備試験：モデル出力の機械検証。

  run    出力1件を検証する
  batch  manifest/runs.csv の全実行を検証し、audit/ にレポートを書く
  diff   2つの出力（初回と訂正後など）の29項目台帳を比べる

検証すること（判断の正しさではなく、機械的に確かめられることだけ）：
  1. 引用：フェンス内の引用ブロックが、入力本文・補助資料と完全一致するか
  2. 台帳：29IDが一度ずつ、規定の7区分のいずれかで記録されているか
  3. 集計：四面のP/K/U/Xが台帳と一致し、K+U+Xが各面の定数になるか
  4. 数値：スコア・評価済み率・欠測幅が、台帳から再計算した値（小数第1位）と一致するか
  5. 形式：JSONコードブロックがないか

判定できなかったものは「判定不能」として残し、合格にしない。
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kv5common import (  # noqa: E402
    ALL_IDS, CAT_K, CAT_U, CAT_X, CATEGORIES, FACE_TOTAL, FACES, TOOL_VERSION,
    read_csv, read_text, repo_root, round1, sha256_file, split_list, write_json,
)

ID_RE = r"(S10|S0[1-9]|C0[1-6]|R0[1-6]|E0[1-7])"
CAT_RE = "(" + "|".join(sorted(CATEGORIES, key=len, reverse=True)) + ")"
# 台帳の行：表（| または ｜）、箇条書き、または行頭のID。IDの後に項目名があってもよい。
LEDGER_ROW = re.compile(
    r"^\s*(?:[|｜]\s*|[-*・]\s*)?\**" + ID_RE + r"\**(?![0-9])[^|｜:：\n]{0,40}?[|｜:：]\s*\**" + CAT_RE + r"\**(?=\s*(?:[|｜]|$))"
)
FACE_ROW = re.compile(
    r"^\s*[|｜]?\s*\**([SCRE])\**\s*[^|｜\d\n]{0,10}[|｜]\s*(\d+)\s*[/／]\s*(\d+)\s*[/／]\s*(\d+)\s*[/／]\s*(\d+)(?=\s*(?:[|｜]|$))"
)
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*([^\s`]*)?.*$")
SCORE_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*/\s*100(?![0-9])")
RATE_RE = re.compile(r"評価済み率[^\d\n]{0,20}?(\d{1,3}(?:\.\d+)?)\s*[%％]")
WIDTH_RE = re.compile(
    r"欠測幅[^\d\n]{0,30}?(\d{1,3}(?:\.\d+)?)\s*[%％]?\s*[〜~～\-–—]\s*(\d{1,3}(?:\.\d+)?)\s*[%％]?"
)
BLOCK_GAP = 4  # 台帳の行がこれより多く途切れたら別の表とみなす


# ---------------------------------------------------------------- 抽出

def extract_fences(md: str) -> list[dict]:
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        fence, info = m.group(1), (m.group(2) or "").lower()
        close = re.compile(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$")
        j = i + 1
        while j < len(lines) and not close.match(lines[j]):
            j += 1
        indent=len(lines[i])-len(lines[i].lstrip(" "))
        content_lines=[ln[min(indent,len(ln)-len(ln.lstrip(" "))):] for ln in lines[i+1:j]]
        out.append({
            "line": i + 1,
            "info": info,
            "content": "\n".join(content_lines),
            "closed": j < len(lines),
        })
        i = j + 1
    return out


def strip_fences(md: str) -> str:
    """フェンス内（引用＝原文）を台帳・集計の解析対象から外す。"""
    lines, out, i = md.split("\n"), [], 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            # Four-space/tab code is also opaque to all structural parsers.
            out.append("" if lines[i].startswith(("    ", "\t")) else lines[i])
            i += 1
            continue
        fence = m.group(1)
        close = re.compile(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$")
        out.append("")
        j = i + 1
        while j < len(lines) and not close.match(lines[j]):
            out.append("")
            j += 1
        out.append("")
        i = j + 1
    text="\n".join(out)
    # Literal HTML code containers are opaque; their sample ledgers are data.
    return re.sub(r"<(pre|code|script|style|textarea|xmp)\b[^>]*>.*?(?:</\1\s*>|$)",lambda m:"\n"*m.group(0).count("\n"),text,flags=re.I|re.S)


def extract_ledgers(md_nofence: str) -> list[dict]:
    """台帳らしい行の塊を取り出す。"""
    blocks, cur, last = [], None, -100
    for n, line in enumerate(md_nofence.split("\n"), start=1):
        m = LEDGER_ROW.match(line)
        if line.startswith(("    ","\t")):continue
        if not m:
            continue
        if cur is None or n - last > BLOCK_GAP:
            cur = {"start_line": n, "rows": []}
            blocks.append(cur)
        cur["rows"].append({"line": n, "id": m.group(1), "cat": m.group(2), "payload": line[m.end():].strip(" |｜")})
        last = n
    for b in blocks:
        ids = [r["id"] for r in b["rows"]]
        c = Counter(ids)
        b["ids"] = sorted(set(ids), key=ALL_IDS.index)
        b["duplicates"] = sorted([i for i, k in c.items() if k > 1], key=ALL_IDS.index)
        b["missing"] = [i for i in ALL_IDS if i not in c]
        b["complete"] = not b["missing"] and not b["duplicates"]
        b["map"] = {r["id"]: r["cat"] for r in b["rows"]}
    return blocks


def extract_face_tables(md_nofence: str) -> list[dict]:
    groups, cur, last = [], None, -100
    for n, line in enumerate(md_nofence.split("\n"), start=1):
        m = FACE_ROW.match(line)
        if not m:
            continue
        face = m.group(1)
        if cur is None or n - last > BLOCK_GAP or face in cur["faces"]:
            cur = {"start_line": n, "faces": {}}
            groups.append(cur)
        cur["faces"][face] = tuple(int(m.group(k)) for k in range(2, 6))
        cur["end_line"] = n
        last = n
    return groups


def find_score_section(md_nofence: str) -> str:
    lines = md_nofence.split("\n")
    for i, ln in enumerate(lines):
        if "文章疑義スコア" in ln:
            return "\n".join(lines[i : i + 20])
    return ""


# ---------------------------------------------------------------- 計算

def tally(cat_map: dict[str, str]) -> dict:
    faces = {}
    for f, ids in FACES.items():
        cats = [cat_map.get(i) for i in ids]
        faces[f] = {
            "P": sum(c == "疑義" for c in cats),
            "K": sum(c in CAT_K for c in cats),
            "U": sum(c in CAT_U for c in cats),
            "X": sum(c in CAT_X for c in cats),
        }
    tot = {k: sum(faces[f][k] for f in faces) for k in "PKUX"}
    applicable = 29 - tot["X"]
    expected = {"faces": faces, "total": tot}
    expected["score"] = None if tot["K"] == 0 else str(round1(tot["P"], tot["K"]))
    expected["score_fraction"] = f"{tot['P']}/{tot['K']}"
    expected["rate"] = None if applicable == 0 else str(round1(tot["K"], applicable))
    if applicable > 0 and tot["U"] > 0:
        expected["width"] = [str(round1(tot["P"], applicable)), str(round1(tot["P"] + tot["U"], applicable))]
    else:
        expected["width"] = None
    expected["state"] = "算出不可" if tot["K"] == 0 else "数値"
    return expected


def one_decimal(s: str) -> bool:
    return re.fullmatch(r"\d{1,3}\.\d", s) is not None


# ---------------------------------------------------------------- 検証

def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s.replace("\r\n", "\n"))
    return "\n".join(ln.rstrip() for ln in s.split("\n")).strip("\n")


def verify_output(output_path: Path, sources: list[Path], ledger_index=None, score_index=None, tally_index=None) -> dict:
    md = read_text(output_path).replace("\r\n", "\n")
    src_texts = {str(p): read_text(p) for p in sources}
    rep: dict = {
        "tool": "kv5-verify-0.3.2",
        "output": str(output_path),
        "output_sha256": sha256_file(output_path),
        "sources": {k: sha256_file(k) for k in src_texts},
        "checks": {},
    }
    checks = rep["checks"]

    # 5. 形式
    fences = extract_fences(md)
    json_blocks = [f["line"] for f in fences if f["info"] == "json"]
    checks["format"] = {
        "status": "fail" if json_blocks else "pass",
        "json_block_lines": json_blocks,
        "unclosed_fence_lines": [f["line"] for f in fences if not f["closed"]],
    }
    if checks["format"]["unclosed_fence_lines"]:
        checks["format"]["status"] = "fail"

    # 1. 引用
    quote_results = []
    for f in fences:
        if f["info"] == "json":
            continue
        content = f["content"]
        if not content.strip():
            quote_results.append({"line": f["line"], "result": "empty"})
            continue
        exact = [k for k, t in src_texts.items() if content in t]
        if exact:
            res = "exact"
        elif any(norm(content) in norm(t) for t in src_texts.values()):
            res = "normalized_only"  # 改行コード・行末空白・Unicode正規化の差だけ
        else:
            res = "no_match"
        quote_results.append({
            "line": f["line"], "info": f["info"], "result": res,
            "matched_sources": exact, "head": content[:40],
        })
    n_q = sum(1 for q in quote_results if q["result"] != "empty")
    n_exact = sum(1 for q in quote_results if q["result"] == "exact")
    checks["quotes"] = {
        "status": "na" if n_q == 0 else ("pass" if n_exact == n_q else "fail"),
        "blocks": n_q,
        "exact": n_exact,
        "normalized_only": sum(1 for q in quote_results if q["result"] == "normalized_only"),
        "no_match": sum(1 for q in quote_results if q["result"] == "no_match"),
        "exact_rate": None if n_q == 0 else round(n_exact / n_q, 4),
        "details": quote_results,
        "note": "フェンス外の「」引用は検証していない。no_match には引用でないフェンスが含まれうるので、headで確認すること。",
    }

    nofence = strip_fences(md)

    # 2. 台帳
    blocks = extract_ledgers(nofence)
    complete = [b for b in blocks if b["complete"]]
    from kv5_output_guard import row_candidates,select_ledger,score_sections,numbers
    candidates=row_candidates(nofence,LEDGER_ROW)
    ledger,status,selection_reason=select_ledger(blocks,candidates,ledger_index)
    checks["ledger"] = {
        "status": status,
        "blocks_found": len(blocks),
        "complete_blocks": [b["start_line"] for b in complete],
        "complete_blocks_agree": None if not complete else all(b["map"] == complete[0]["map"] for b in complete),
        "partial_blocks": [
            {"start_line": b["start_line"], "n_ids": len(b["ids"]), "missing": b["missing"], "duplicates": b["duplicates"]}
            for b in blocks if not b["complete"]
        ],
        "categories": ledger["map"] if ledger else None,
        "note": "複数の完全台帳は明示選択が必要。意味と履歴の役割は人間監査。",
        "selected_complete_index": ledger_index if ledger_index is not None else 1 if ledger else None,
        "selection_reason": selection_reason,
        "invalid_rows": [c for c in candidates if not c["valid"]],
    }

    if not ledger:
        checks["tally"] = {"status": "unverifiable", "reason": "29ID台帳を特定できない"}
        checks["numbers"] = {"status": "unverifiable", "reason": "29ID台帳を特定できない"}
        rep["overall"] = summarize(checks)
        return rep

    exp = tally(ledger["map"])
    rep["recomputed"] = exp
    if n_q == 0 and any(c in {"疑義", "機能"} for c in ledger["map"].values()):
        checks["quotes"]["status"] = "unverifiable"
        checks["quotes"]["reason"] = "疑義・機能があるが検証できる引用フェンスがない。引用監査は未完了"

    # 3. 集計
    groups = extract_face_tables(nofence)
    group_results = []
    for g in groups:
        diffs = {}
        for f in "SCRE":
            if f not in g["faces"]:
                diffs[f] = "missing"
                continue
            p, k, u, x = g["faces"][f]
            e = exp["faces"][f]
            row = {}
            if (p, k, u, x) != (e["P"], e["K"], e["U"], e["X"]):
                row["shown"] = [p, k, u, x]
                row["ledger"] = [e["P"], e["K"], e["U"], e["X"]]
            if k + u + x != FACE_TOTAL[f]:
                row["sum_error"] = f"K+U+X={k + u + x}≠{FACE_TOTAL[f]}"
            if p > k:
                row["p_gt_k"] = True
            if row:
                diffs[f] = row
        group_results.append({"start_line": g["start_line"], "diffs": diffs})
    if tally_index is not None:
        if isinstance(tally_index,int) and not isinstance(tally_index,bool) and 1<=tally_index<=len(group_results):
            active=group_results[tally_index-1];t_status="fail" if active["diffs"] else "pass"
        else:t_status="unverifiable"
    elif not groups:
        t_status = "unverifiable"
    elif not group_results[0]["diffs"]:
        t_status = "pass" if all(not g["diffs"] for g in group_results) else "warn"
    else:
        t_status = "fail"
    from kv5_output_guard import invalid_face_rows
    invalid_faces=invalid_face_rows(nofence,FACE_ROW)
    if invalid_faces:t_status="fail"
    checks["tally"] = {
        "status": t_status,
        "selected_table_index": tally_index if tally_index is not None else 1 if groups else None,
        "invalid_rows": invalid_faces,
        "tables": group_results,
        "note": "最初の四面表を現在値とみなす。2つ目以降（初回値など）の不一致はwarn。",
    }

    # 4. 数値：符号・余分な桁・正確な分数・複数表示を別々に検査。
    sections=score_sections(nofence)
    if score_index is not None:
        selected=sections[score_index-1] if isinstance(score_index,int) and not isinstance(score_index,bool) and 1<=score_index<=len(sections) else ''
        num=numbers(exp,selected)
        if not selected:num.update(status='unverifiable',reason='スコア欄番号が範囲外')
    elif len(sections)>1:
        num=dict(status='unverifiable',reason='スコア欄が複数ある。現在値の欄を番号で指定する必要がある')
    else:num=numbers(exp,sections[0] if sections else '')
    num['selected_score_index']=score_index if score_index is not None else 1 if sections else None
    checks['numbers']=num
    rep['overall']=summarize(checks)
    return rep


def summarize(checks: dict) -> str:
    sts = [c.get("status") for c in checks.values()]
    if "fail" in sts:
        return "fail"
    if "unverifiable" in sts:
        return "unverifiable"
    if "warn" in sts:
        return "warn"
    return "pass"


def print_summary(rep: dict) -> None:
    c = rep["checks"]
    print(f"[{rep['overall'].upper()}] {rep['output']}")
    q = c.get("quotes", {})
    print(f"  引用   {q.get('status')}: {q.get('exact')}/{q.get('blocks')} 完全一致"
          f"（正規化のみ一致 {q.get('normalized_only')}、不一致 {q.get('no_match')}）")
    lg = c.get("ledger", {})
    print(f"  台帳   {lg.get('status')}: 完全な台帳 {len(lg.get('complete_blocks') or [])}件、部分的な塊 {len(lg.get('partial_blocks') or [])}件")
    print(f"  集計   {c.get('tally', {}).get('status')}")
    nm = c.get("numbers", {})
    print(f"  数値   {nm.get('status')}: " + ("; ".join(nm.get("problems", [])) or nm.get("reason", "一致")))
    print(f"  形式   {c.get('format', {}).get('status')}")
    if "recomputed" in rep:
        t = rep["recomputed"]["total"]
        e = rep["recomputed"]
        w = f"、欠測幅 {e['width'][0]}〜{e['width'][1]}" if e["width"] else ""
        print(f"  再計算 P={t['P']} K={t['K']} U={t['U']} X={t['X']}  スコア {e['score']}（{e['score_fraction']}）"
              f"、評価済み率 {e['rate']}{w}")


# ---------------------------------------------------------------- コマンド

def run_source_files(root: Path, run: dict, inp: dict, runs: list[dict]) -> list[Path]:
    """Only the input and materials actually supplied by this conversation turn.

    Continued turns inherit previous turns' materials; initial turns never
    consume the input-level list of planned future supplements.
    """
    from kv5_lock import parse_ts
    index = {r['run_id']: r for r in runs}
    seen, materials = set(), {}
    current = run
    while True:
        rid = current.get('run_id')
        if rid in seen:
            raise ValueError('会話の参照が循環している')
        seen.add(rid)
        if current.get('input_id') != inp.get('input_id'):
            raise ValueError('継続会話の入力IDが一致しない')
        if parse_ts(current.get('started_at')) is None:
            raise ValueError('実行日時が欠落・不正（タイムゾーン必須）')
        if current.get('input_sha256') != inp.get('prep_sha256'):
            raise ValueError('実行時の入力ハッシュがない、または一致しない')
        paths = split_list(current.get('supplement_paths'))
        hashes = split_list(current.get('supplement_sha256s'))
        if len(paths) != len(hashes) or len(paths) != len(set(paths)):
            raise ValueError('実行別の提示資料・ハッシュの対応が不正')
        for rel, digest in [(inp['prep_path'], current['input_sha256']), *zip(paths, hashes)]:
            p = (root / rel).resolve()
            if not p.is_relative_to(root.resolve()) or not p.is_file() or sha256_file(p) != digest:
                raise ValueError(f'実行時資料の内容を確認できない: {rel}')
            if rel in materials and materials[rel] != digest:
                raise ValueError('会話内で資料を上書きした。別パスで版を保存してください')
            materials[rel] = digest
        conv = current.get('conversation', '')
        if conv == 'new':
            break
        if not conv.startswith('continued:') or conv[10:] not in index:
            raise ValueError('継続元の実行を特定できない')
        parent = index[conv[10:]]
        a, b = parse_ts(parent.get('started_at')), parse_ts(current.get('started_at'))
        if a is None or b is None or a >= b:
            raise ValueError('継続元と現在の実行日時が不正')
        current = parent
    return [root / rel for rel in materials]

def cmd_run(args) -> int:
    rep = verify_output(Path(args.output), [Path(s) for s in args.source], args.ledger, args.score, args.tally)
    if args.json_out:
        write_json(args.json_out, rep)
    print_summary(rep)
    return 0 if rep["overall"] == "pass" else 1


def cmd_batch(args) -> int:
    from kv5_audit_guard import strict_csv,checked_file,ID
    root=repo_root();summary=[]
    try:
        input_rows=strict_csv(root/'manifest/inputs.csv',('input_id','prep_path','prep_sha256'))
        runs=strict_csv(root/'manifest/runs.csv',('run_id','input_id','arm','status','conversation','started_at','input_sha256','output_path','output_sha256'))
        if len({i['input_id'] for i in input_rows})!=len(input_rows):raise ValueError('duplicate input ID')
        inputs={i['input_id']:i for i in input_rows}
    except (OSError,ValueError,UnicodeError,csv.Error) as e:
        summary=[dict(run_id=None,overall='error',reason=str(e))];write_json(root/'audit/verify-summary.json',summary);return 1
    counts=Counter(r['run_id'] for r in runs)
    for r in runs:
        rid=r['run_id']
        if not ID.fullmatch(rid) or counts[rid]!=1:
            summary.append(dict(run_id=rid,overall='error',reason='unsafe/blank/duplicate run ID'));continue
        if r['arm'] not in {'A0','B1'}:
            summary.append(dict(run_id=rid,overall='error',reason='unknown comparison arm'));continue
        if r['status'] not in {'ok','error','timeout','connection_error'}:
            summary.append(dict(run_id=rid,overall='error',reason='unknown run status'));continue
        if r['status']!='ok':
            if r['output_path'] or r['output_sha256']:summary.append(dict(run_id=rid,overall='error',reason='non-ok attempt has recorded output'))
            else:summary.append(dict(run_id=rid,overall='skipped',reason='no acquired output: '+r['status']))
            continue
        inp=inputs.get(r['input_id'])
        if not inp:summary.append(dict(run_id=rid,overall='error',reason='input ID missing'));continue
        try:
            sources=run_source_files(root,r,inp,runs);output=checked_file(root,r['output_path'],r['output_sha256'])
            if not read_text(output).strip():raise ValueError('empty acquired output')
            if r['arm']=='B1':
                summary.append(dict(run_id=rid,overall='not_applicable',scope='A0_structure_only',output_sha256=sha256_file(output),reason='B1 has no 29-row/score requirement. Human relation and P-inventory audit remains required.'));continue
            li=int(r['output_ledger_index']) if r.get('output_ledger_index') else None;si=int(r['output_score_index']) if r.get('output_score_index') else None
            ti=int(r['output_tally_index']) if r.get('output_tally_index') else None
            rep=verify_output(output,sources,li,si,ti);write_json(root/'audit'/f'verify-{rid}.json',rep)
            q=rep['checks']['quotes'];summary.append(dict(run_id=rid,overall=rep['overall'],quotes=f"{q['exact']}/{q['blocks']}",ledger=rep['checks']['ledger']['status'],tally=rep['checks']['tally']['status'],numbers=rep['checks']['numbers']['status']))
            print_summary(rep)
        except (OSError,ValueError,UnicodeError,csv.Error) as e:summary.append(dict(run_id=rid,overall='unverifiable',reason=str(e)))
    write_json(root/'audit/verify-summary.json',summary)
    write_json(root/'audit/verify-batch-state.json',dict(status='not_run' if not runs else 'structural_diagnostic_only',recorded_runs=len(runs),A0=sum(r['arm']=='A0' for r in runs),B1=sum(r['arm']=='B1' for r in runs),note='Byte/structure diagnostics do not certify pre-run human annotation or model performance. B1 is excluded from A0 requirements.'))
    print(f"\n{len(summary)}件 → audit/verify-summary.json")
    return int(any(r['overall'] not in {'pass','skipped','not_applicable'} for r in summary))


def compare_outputs(before,after,before_ledger=None,after_ledger=None):
    from kv5_output_guard import row_candidates,select_ledger
    paths=[Path(before),Path(after)];selected=[];scopes=[];errors=[]
    for label,path,index in zip(('before','after'),paths,(before_ledger,after_ledger)):
        text=strip_fences(read_text(path).replace('\r\n','\n'));blocks=extract_ledgers(text)
        ledger,status,reason=select_ledger(blocks,row_candidates(text,LEDGER_ROW),index)
        if status!='pass':errors.append(label+': '+reason)
        selected.append(ledger);scopes.append(index if index is not None else 1 if ledger else None)
    out=dict(before=str(before),after=str(after),before_sha256=sha256_file(paths[0]),after_sha256=sha256_file(paths[1]),document_changed=sha256_file(paths[0])!=sha256_file(paths[1]),selected_ledger_indices=scopes,errors=errors,status='unverifiable' if errors else 'structurally_compared',note='Row payload differences include formatting. Semantic grounds and findings outside the ledger require human history audit.')
    if errors:return out
    la,lb=selected
    out['changed']=[dict(id=i,before=la['map'][i],after=lb['map'][i]) for i in ALL_IDS if la['map'][i]!=lb['map'][i]]
    ra={r['id']:r['payload'] for r in la['rows']};rb={r['id']:r['payload'] for r in lb['rows']}
    out['row_changes']=[dict(id=i,before=ra[i],after=rb[i]) for i in ALL_IDS if ra[i]!=rb[i]]
    out['tally_before']=tally(la['map'])['total'];out['tally_after']=tally(lb['map'])['total']
    out['no_ledger_change_but_document_changed']=out['document_changed'] and not out['changed'] and not out['row_changes']
    return out


def cmd_diff(args) -> int:
    out=compare_outputs(args.before,args.after,args.before_ledger,args.after_ledger)
    if args.json_out:write_json(args.json_out,out)
    if out['errors']:
        for error in out['errors']:print(error)
        return 2
    print(f"区分が変わった項目: {len(out['changed'])}件、根拠等の行が変わった項目: {len(out['row_changes'])}件")
    for c in out['changed']:print(f"  {c['id']}: {c['before']} → {c['after']}")
    if out['no_ledger_change_but_document_changed']:print('台帳以外の文書内容が異なる。所見本文・引用・履歴の人間確認が必要。')
    print('（行変更には表記差も含む。所見本文の意味・根拠と変更理由は第三者が確認する）')
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="出力1件を検証")
    r.add_argument("output")
    r.add_argument("--source", action="append", required=True, help="入力本文・補助資料（複数可）")
    r.add_argument("--json-out")
    r.add_argument("--ledger",type=int,help="完全台帳の番号（1から）。複数版がある場合の明示選択")
    r.add_argument("--score",type=int,help="スコア欄の番号（1から）。複数版がある場合の明示選択")
    r.add_argument("--tally",type=int,help="四面表の番号（1から）。複数版がある場合の明示選択")
    r.set_defaults(func=cmd_run)
    b = sub.add_parser("batch", help="runs.csv の全実行を検証")
    b.set_defaults(func=cmd_batch)
    d = sub.add_parser("diff", help="2つの出力の台帳を比べる")
    d.add_argument("before")
    d.add_argument("after")
    d.add_argument("--json-out")
    d.add_argument("--before-ledger",type=int,help="変更前の完全台帳番号（1から）")
    d.add_argument("--after-ledger",type=int,help="変更後の完全台帳番号（1から）")
    d.set_defaults(func=cmd_diff)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
