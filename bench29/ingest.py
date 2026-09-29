"""既存データを Layer 0（trials.jsonl）へ取り込む。

対応形式:
  - JSONL / CSV: schema.Trial のフィールド名をそのまま列に持つもの（余分な列は meta へ）
  - records/: このリポジトリの記録フォルダ（answer-original.md、または README.md の「## 回答原文」以降）

records/ の記録はモデル名・バージョンを独立に確認できていない。画面表示は "ui:<表示>"、ユーザー申告は
"user:<申告>"、手がかりがなければ "unverified:<フォルダ名>" を model_version に入れ、出どころを version_source に残す。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .schema import Trial, make_trial_id

# records/ フォルダ名 → (model, model_version, version_source)。確認できた範囲だけを書く。
# チャット画面ではバージョン文字列を取れないため、画面表示やユーザー申告をそのまま入れ、出どころを version_source に残す。
RECORD_META = {
    "2026-09-05-astra-max": ("gpt-astra-max", "user:アストラ・最大", "user_report"),
    "2026-09-16-fugu": ("fugu", None, "unknown"),
    "2026-09-28-astra-ultra": ("gpt-astra-ultra", "user:アストラウルトラ", "user_report"),
    "2026-09-29-sol-ultra": ("chatgpt-6.1-sol", "ui:6.1 Sol ウルトラ", "ui_label"),
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
        model, version, source = RECORD_META.get(folder.name, (folder.name, None, "unknown"))
        version = version or f"unverified:{folder.name}"
        surface = "chat"
        trials.append(Trial(
            trial_id=make_trial_id(model, version, "ja", surface, text),
            model=model,
            model_version=version,
            surface=surface,
            lang="ja",
            response_text=text,
            timestamp=folder.name[:10],
            version_source=source,
            meta={"source": str(folder), "note": "records/ から取り込み。統制試行ではない"},
        ))
    return trials
