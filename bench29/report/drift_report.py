"""バージョン間ドリフトレポート（Markdown）。

profiles.json の comparisons（relation=version）から、同一モデルの新旧比較を出す。
JSD の 95% CI と、主要な率の差を並べる。有意性の判定は CI を見て人が行う（自動で合否を出さない）。
"""

from __future__ import annotations

import json
from pathlib import Path

JSD_ROWS = [("主比喩", "metaphor"), ("比喩グループ", "metaphor_group"), ("構造系列", "structure"),
            ("検証スタイル", "verification_type"), ("最終式判定", "formula_status"), ("最終式の位置", "formula_position")]
RATE_ROWS = [("最終式 正答率", "rate_formula_correct"), ("比喩 Top-1", "metaphor_top1"),
             ("構造テンプレ一致率", "structure_template_match_rate"), ("コードあり", "rate_code_present"),
             ("循環検証の候補", "rate_circular_verification_candidate"), ("意味的類似度", "semantic_similarity")]


def _ci(est: dict) -> str:
    v, (lo, hi) = est.get("value"), est.get("ci95") or [None, None]
    if v is None:
        return "–"
    return f"{v:.3f} [{lo:.3f}, {hi:.3f}]" if lo is not None else f"{v:.3f}"


def _cell_name(c: dict) -> str:
    return " / ".join(str(v) for v in c.values())


def render(profiles: dict, model: str | None = None) -> str:
    cells = {json.dumps(c["cell"], sort_keys=True): c for c in profiles["cells"]}
    out = ["# bench29 バージョン間ドリフト", "",
           f"feature_version `{profiles.get('feature_version')}` ・ lexicon `{', '.join(profiles.get('lexicon_version') or [])}`"
           f" ・ embedder `{profiles.get('embedder')}` ・ bootstrap B={profiles['bootstrap']['B']}", "",
           "JSD は 0（同一分布）〜1（完全に分離）。括弧内は 95% ブートストラップ CI。", ""]
    comps = [c for c in profiles["comparisons"] if c["relation"] == "version"
             and (model is None or c["a"].get("model") == model)]
    if not comps:
        out.append("比較できるバージョンの組がない（同一モデル・同一 lang・同一 surface で複数バージョンが必要）。")
        return "\n".join(out) + "\n"
    for comp in comps:
        a = cells[json.dumps(comp["a"], sort_keys=True)]
        b = cells[json.dumps(comp["b"], sort_keys=True)]
        out += [f"## {comp['a'].get('model')}: `{comp['a'].get('model_version')}` → `{comp['b'].get('model_version')}`",
                f"（{comp['a'].get('lang')} / {comp['a'].get('surface')}、n = {a['n']} → {b['n']}）", ""]
        if a.get("underpowered") or b.get("underpowered"):
            out += ["> ⚠ どちらかのセルが推奨 n 未満。CI の幅に注意。", ""]
        out += ["| 分布 | JSD [95% CI] |", "|---|---|"]
        out += [f"| {label} | {_ci(comp['jsd'][key])} |" for label, key in JSD_ROWS]
        out += ["", "| 指標 | 旧 | 新 |", "|---|---|---|"]
        out += [f"| {label} | {_ci(a['metrics'].get(key, {}))} | {_ci(b['metrics'].get(key, {}))} |"
                for label, key in RATE_ROWS]
        ta = a["metrics"].get("metaphor_top1", {}).get("label")
        tb = b["metrics"].get("metaphor_top1", {}).get("label")
        out += ["", f"最頻の主比喩: `{ta}` → `{tb}`", ""]
    return "\n".join(out) + "\n"


def write_report(profiles_path: str | Path, out_path: str | Path, model: str | None = None) -> None:
    profiles = json.loads(Path(profiles_path).read_text(encoding="utf-8"))
    Path(out_path).write_text(render(profiles, model), encoding="utf-8")
