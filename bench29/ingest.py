"""既存データを Layer 0（trials.jsonl）へ取り込む。

対応形式:
  - JSONL / CSV: schema.Trial のフィールド名をそのまま列に持つもの（余分な列は meta へ）
  - records/: このリポジトリの記録フォルダ（answer-original.md、または README.md の「## 回答原文」以降）

records/ の記録はモデル名・バージョンが未確認のものが多い。取り込み時は model_version に
"unverified:<フォルダ名>" を入れ、未確認であることを値そのものに残す。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .schema import Trial, make_trial_id

# records/ フォルダ名 → (model, surface)。確認できた範囲だけを書く。
RECORD_META = {
    "2026-09-05-astra-max": ("gpt-astra-max", "chat"),
    "2026-09-16-fugu": ("fugu", "chat"),
    "2026-09-28-astra-ultra": ("gpt-astra-ultra", "chat"),
}


def from_table(path: str | Path) -> list[Trial]:
    path = Path(path)
    if path.suffix == ".jsonl":
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    elif path.suffix == ".csv":
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            for k in ("params", "code_blocks", "meta"):
                if isinstance(r.get(k), str) and r[k].strip():
                    r[k] = json.loads(r[k])
                elif k in r and not r[k]:
                    r.pop(k)
            if r.get("tokens_out"):
                r["tokens_out"] = int(r["tokens_out"])
            for k in ("exec_log", "timestamp"):
                if k in r and r[k] == "":
                    r[k] = None
    else:
        raise ValueError(f"unsupported file type: {path}")
    trials = []
    for r in rows:
        if not r.get("trial_id"):
            r["trial_id"] = make_trial_id(r["model"], r["model_version"], r["lang"], r["surface"], r["response_text"])
        trials.append(Trial.from_dict(r))
    return trials


def _record_answer(folder: Path) -> str | None:
    ans = folder / "answer-original.md"
    if ans.exists():
        return ans.read_text(encoding="utf-8")
    readme = folder / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        m = re.search(r"^## 回答原文\s*$(.*)", text, re.M | re.S)
        if m:
            body = m.group(1)
            # 見出し直後の注記段落と区切り線を除く
            parts = re.split(r"^---\s*$", body, maxsplit=1, flags=re.M)
            return (parts[1] if len(parts) == 2 else body).strip()
    return None


def from_records(records_dir: str | Path) -> list[Trial]:
    trials = []
    for folder in sorted(Path(records_dir).iterdir()):
        if not folder.is_dir():
            continue
        text = _record_answer(folder)
        if text is None:
            continue
        model, surface = RECORD_META.get(folder.name, (folder.name, "chat"))
        version = f"unverified:{folder.name}"
        trials.append(Trial(
            trial_id=make_trial_id(model, version, "ja", surface, text),
            model=model,
            model_version=version,
            surface=surface,
            lang="ja",
            response_text=text,
            timestamp=folder.name[:10],
            meta={"source": str(folder), "note": "records/ から取り込み。統制試行ではない"},
        ))
    return trials
