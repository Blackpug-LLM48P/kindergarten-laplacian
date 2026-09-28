"""bench29 CLI。

  python -m bench29 ingest   --records records/ [--table data.jsonl|.csv] -o trials.jsonl
  python -m bench29 extract  trials.jsonl -o features.parquet
  python -m bench29 profile  trials.jsonl features.parquet -o profiles.json [--pool-lang] [--no-diversity]
  python -m bench29 card     profiles.json -o profiles.html
  python -m bench29 drift    profiles.json -o drift.md [--model NAME]
  python -m bench29 judge    trials.jsonl --judge-model MODEL_ID -o judge.jsonl [--features features.parquet]
  python -m bench29 calibrate bench29/judge/anchors --judge-model MODEL_ID -o calibration.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _write_table(rows: list[dict], path: str) -> None:
    import pandas as pd

    df = pd.DataFrame(rows)
    if path.endswith(".parquet"):
        df.to_parquet(path, index=False)
    elif path.endswith(".csv"):
        df.to_csv(path, index=False)
    else:
        df.to_json(path, orient="records", lines=True, force_ascii=False)


def _read_table(path: str) -> list[dict]:
    import pandas as pd

    if path.endswith(".parquet"):
        df = pd.read_parquet(path)
    elif path.endswith(".csv"):
        df = pd.read_csv(path)
    else:
        df = pd.read_json(path, lines=True)
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


def cmd_ingest(a) -> None:
    from .ingest import from_records, from_table
    from .schema import _check_unique, write_jsonl

    trials = []
    if a.records:
        trials += from_records(a.records)
    for t in a.table or []:
        trials += from_table(t)
    _check_unique(trials)
    write_jsonl(trials, a.output)
    print(f"{len(trials)} trials -> {a.output}")


def cmd_extract(a) -> None:
    from .extract.features import extract_all
    from .schema import read_jsonl

    rows = extract_all(read_jsonl(a.trials))
    _write_table(rows, a.output)
    print(f"{len(rows)} rows -> {a.output}")


def cmd_profile(a) -> None:
    from .distrib.profiles import DEFAULT_CELL_KEYS, build_profiles, dump_profiles
    from .schema import read_jsonl

    rows = _read_table(a.features)
    texts = None if a.no_diversity else {t.trial_id: t.response_text for t in read_jsonl(a.trials)}
    keys = tuple(k for k in DEFAULT_CELL_KEYS if not (a.pool_lang and k == "lang"))
    prof = build_profiles(rows, texts, cell_keys=keys, b=a.bootstrap)
    dump_profiles(prof, a.output)
    print(f"{len(prof['cells'])} cells, {len(prof['comparisons'])} comparisons -> {a.output}")


def cmd_card(a) -> None:
    from .report.profile_card import write_cards

    write_cards(a.profiles, a.output)
    print(f"-> {a.output}")


def cmd_drift(a) -> None:
    from .report.drift_report import write_report

    write_report(a.profiles, a.output, a.model)
    print(f"-> {a.output}")


def cmd_judge(a) -> None:
    from .judge.run_judge import AnthropicJudge, run
    from .schema import read_jsonl

    l1 = {r["trial_id"]: r for r in _read_table(a.features)} if a.features else None
    rows = run(read_jsonl(a.trials), AnthropicJudge(a.judge_model), l1, a.output)
    print(f"{len(rows)} newly judged -> {a.output}")


def cmd_calibrate(a) -> None:
    from .judge.calibrate import calibrate, load_anchors
    from .judge.run_judge import AnthropicJudge

    res = calibrate(load_anchors(a.anchors), AnthropicJudge(a.judge_model), a.threshold)
    Path(a.output).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"accepted={res['accepted']} -> {a.output}")
    if not res["accepted"]:
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="bench29")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ingest")
    s.add_argument("--records")
    s.add_argument("--table", action="append")
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("extract")
    s.add_argument("trials")
    s.add_argument("-o", "--output", default="features.parquet")
    s.set_defaults(func=cmd_extract)

    s = sub.add_parser("profile")
    s.add_argument("trials")
    s.add_argument("features")
    s.add_argument("-o", "--output", default="profiles.json")
    s.add_argument("--pool-lang", action="store_true", help="ja/en を同一セルにまとめる")
    s.add_argument("--no-diversity", action="store_true")
    s.add_argument("--bootstrap", type=int, default=2000)
    s.set_defaults(func=cmd_profile)

    s = sub.add_parser("card")
    s.add_argument("profiles")
    s.add_argument("-o", "--output", default="profiles.html")
    s.set_defaults(func=cmd_card)

    s = sub.add_parser("drift")
    s.add_argument("profiles")
    s.add_argument("-o", "--output", default="drift.md")
    s.add_argument("--model")
    s.set_defaults(func=cmd_drift)

    s = sub.add_parser("judge")
    s.add_argument("trials")
    s.add_argument("--judge-model", required=True, help="バージョンまで固定した judge モデル ID")
    s.add_argument("--features")
    s.add_argument("-o", "--output", default="judge.jsonl")
    s.set_defaults(func=cmd_judge)

    s = sub.add_parser("calibrate")
    s.add_argument("anchors")
    s.add_argument("--judge-model", required=True)
    s.add_argument("--threshold", type=float, default=0.6)
    s.add_argument("-o", "--output", default="calibration.json")
    s.set_defaults(func=cmd_calibrate)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
