"""profiles.json → モデルプロファイルカード（単一の静的 HTML）。順位表・総合点は作らない。

指紋はレーダーではなく「点 + 95% CI の横棒」で描く。全指標を同じ 0–1 軸に並べるので
セル同士を縦に見比べられ、レーダーの面積錯視（軸の並び順で形が変わる）を避けつつ CI も載せられる。
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path

from ..extract.metaphor import category_groups

# (ラベル, profiles の指標キー, 説明)
FINGERPRINT = [
    ("比喩 Top-1 集中度", "metaphor_top1", "最頻の主比喩の比率。高いほど単一アトラクタに吸われている"),
    ("比喩エントロピー（正規化）", "metaphor_entropy", "H / log2(カテゴリ数+1)。低いほど比喩選択が単調"),
    ("構造テンプレ一致率", "structure_template_match_rate", "最頻のセクション系列の比率。定型化の度合い"),
    ("意味的類似度（平均）", "semantic_similarity", "応答どうしの平均 cos 類似度。高いほどモード崩壊"),
    ("最終式 正答率", "rate_formula_correct", "Layer 1 の SymPy 等価判定。説明の良し悪しとは別"),
    ("コードあり", "rate_code_present", "コードブロックを含む応答の比率"),
    ("循環検証の候補", "rate_circular_verification_candidate", "Layer 1 のヒューリスティック。確定は Layer 3"),
    ("専門語が比喩より先", "rate_jargon_before_metaphor", "5歳児制約の代理指標"),
    ("比喩なし", "rate_no_metaphor", "辞書の比喩が 1 つも出ない応答の比率"),
]
DISTRIBUTIONS = [
    ("主比喩の分布", "metaphor_distribution"),
    ("検証スタイル", "verification_type_distribution"),
    ("最終式の判定", "formula_status_distribution"),
]

CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--mark:#2a78d6;--ci:#86b6ef;--warn:#8a5a00;--ring:rgba(11,11,11,.10)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;
--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--mark:#3987e5;
--ci:#1c5cab;--warn:#fab219;--ring:rgba(255,255,255,.10)}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--mark:#3987e5;--ci:#1c5cab;--warn:#fab219;--ring:rgba(255,255,255,.10)}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px}
h1{font-size:20px;margin:0 0 4px}.meta{color:var(--ink2);font-size:12px;margin:0 0 20px}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:12px;padding:16px;margin:0 0 20px}
.card h2{font-size:16px;margin:0}.card .sub{color:var(--ink2);font-size:12px;margin:2px 0 12px}
.warn{color:var(--warn);font-size:12px;margin:0 0 8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(260px,100%),1fr));gap:16px}
.grid>div,.fp{min-width:0}.fp{max-width:560px;margin-bottom:12px}
.meta{overflow-wrap:anywhere}
h3{font-size:13px;margin:8px 0 4px;color:var(--ink2);font-weight:600}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--ink2);font:11px system-ui,-apple-system,"Segoe UI",sans-serif}
svg .val{fill:var(--ink);font-variant-numeric:tabular-nums}
svg .tick{fill:var(--muted)}
.gridline{stroke:var(--grid);stroke-width:1}.base{stroke:var(--axis);stroke-width:1}
.cibar{stroke:var(--ci);stroke-width:6;stroke-linecap:round}
.dot{fill:var(--mark);stroke:var(--surface);stroke-width:2}
.bar{fill:var(--mark)}
.hit{fill:transparent}.hit:hover{fill:var(--grid);fill-opacity:.5}
details{margin-top:8px}summary{cursor:pointer;color:var(--ink2);font-size:12px}
table{border-collapse:collapse;font-size:12px;margin-top:6px;width:100%}
td,th{border-bottom:1px solid var(--grid);padding:3px 6px;text-align:left;font-variant-numeric:tabular-nums}
"""


def _fmt(x) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}"


def _normalized_entropy(est: dict, k: int) -> dict:
    scale = math.log2(k + 1)
    f = lambda v: None if v is None else v / scale
    return {"value": f(est.get("value")), "ci95": [f(c) for c in est.get("ci95", [None, None])], "n": est.get("n")}


def _fingerprint_svg(metrics: dict, k_categories: int) -> tuple[str, list[tuple]]:
    label_w, plot_w, row_h, top = 170, 260, 26, 18
    width = label_w + plot_w + 50
    height = top + row_h * len(FINGERPRINT) + 6
    x = lambda v: label_w + plot_w * max(0.0, min(1.0, v))
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="指紋（0〜1、点は推定値、帯は95%CI）">']
    for t in (0, 0.25, 0.5, 0.75, 1):
        parts.append(f'<line class="gridline" x1="{x(t)}" x2="{x(t)}" y1="{top - 4}" y2="{height - 6}"/>')
        parts.append(f'<text class="tick" x="{x(t)}" y="{top - 8}" text-anchor="middle">{t:g}</text>')
    rows = []
    for i, (label, key, desc) in enumerate(FINGERPRINT):
        est = metrics.get(key) or {}
        if key == "metaphor_entropy" and est:
            est = _normalized_entropy(est, k_categories)
        v, (lo, hi) = est.get("value"), (est.get("ci95") or [None, None])
        cy = top + row_h * i + row_h / 2
        rows.append((label, v, lo, hi, est.get("n")))
        tip = html.escape(f"{label}: {_fmt(v)}（95%CI {_fmt(lo)}–{_fmt(hi)}, n={est.get('n')}）— {desc}")
        parts.append(f'<g><title>{tip}</title><rect class="hit" x="0" y="{cy - row_h / 2}" width="{width}" height="{row_h}"/>')
        parts.append(f'<text x="{label_w - 10}" y="{cy + 4}" text-anchor="end">{html.escape(label)}</text>')
        if v is not None:
            if lo is not None and hi is not None:
                parts.append(f'<line class="cibar" x1="{x(lo)}" x2="{x(hi)}" y1="{cy}" y2="{cy}"/>')
            parts.append(f'<circle class="dot" cx="{x(v)}" cy="{cy}" r="5"/>')
            parts.append(f'<text class="val" x="{label_w + plot_w + 10}" y="{cy + 4}">{_fmt(v)}</text>')
        else:
            parts.append(f'<text class="tick" x="{label_w + 4}" y="{cy + 4}">データなし</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts), rows


def _dist_svg(dist: dict, max_rows: int = 8) -> tuple[str, list[tuple]]:
    items = sorted(((k, v) for k, v in dist.items() if (v.get("value") or 0) > 0), key=lambda kv: -kv[1]["value"])
    if len(items) > max_rows:  # 残りは「その他」にまとめる（系列を増やさない）
        rest = sum(v["value"] for _, v in items[max_rows - 1:])
        items = items[: max_rows - 1] + [("（その他）", {"value": rest, "ci95": [None, None]})]
    label_w, plot_w, row_h = 96, 150, 20
    width, height = label_w + plot_w + 50, row_h * max(len(items), 1) + 4
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img">']
    rows = []
    for i, (k, v) in enumerate(items):
        y = row_h * i + 2
        w = max(plot_w * v["value"], 2)
        lo, hi = (v.get("ci95") or [None, None])
        rows.append((k, v["value"], lo, hi))
        tip = html.escape(f"{k}: {_fmt(v['value'])}（95%CI {_fmt(lo)}–{_fmt(hi)}）")
        parts.append(f'<g><title>{tip}</title><rect class="hit" x="0" y="{y}" width="{width}" height="{row_h}"/>')
        parts.append(f'<text x="{label_w - 8}" y="{y + 13}" text-anchor="end">{html.escape(str(k))}</text>')
        parts.append(f'<rect class="bar" x="{label_w}" y="{y + 4}" width="{w:.1f}" height="{row_h - 8}" rx="3"/>')
        parts.append(f'<text class="val" x="{label_w + w + 6:.1f}" y="{y + 13}">{v["value"]:.0%}</text></g>')
    parts.append(f'<line class="base" x1="{label_w}" x2="{label_w}" y1="0" y2="{height}"/></svg>')
    return "".join(parts), rows


def _table(header: list[str], rows: list[tuple]) -> str:
    th = "".join(f"<th>{h}</th>" for h in header)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(_fmt(c) if not isinstance(c, str) else c)}</td>" for c in r)
                   + "</tr>" for r in rows)
    return f"<details><summary>表で見る</summary><table><tr>{th}</tr>{body}</table></details>"


def render(profiles: dict) -> str:
    k = len(set(category_groups()))
    cards = []
    for c in profiles["cells"]:
        title = " / ".join(f"{v}" for v in c["cell"].values())
        warn = (f'<p class="warn">⚠ n={c["n"]} は推奨 {profiles.get("min_n_recommended", 100)} 未満。'
                "CI が広く、分布の比較には使えない。</p>") if c.get("underpowered") else ""
        fp_svg, fp_rows = _fingerprint_svg(c["metrics"], k)
        dists = []
        for label, key in DISTRIBUTIONS:
            svg, rows = _dist_svg(c["metrics"].get(key, {}))
            dists.append(f"<div><h3>{label}</h3>{svg}{_table(['カテゴリ', '比率', 'CI下限', 'CI上限'], rows)}</div>")
        top_tmpl = c["metrics"].get("structure_template_match_rate", {}).get("label", "")
        cards.append(
            f'<section class="card"><h2>{html.escape(title)}</h2>'
            f'<p class="sub">n={c["n"]} ・ 最頻構造: {html.escape(str(top_tmpl))}</p>{warn}'
            f'<div class="fp"><h3>指紋（点=推定値、帯=95%CI）</h3>{fp_svg}'
            f"{_table(['指標', '値', 'CI下限', 'CI上限', 'n'], fp_rows)}</div>"
            f'<div class="grid">{"".join(dists)}</div></section>'
        )
    meta = (f"feature_version {profiles.get('feature_version')} ・ lexicon {', '.join(profiles.get('lexicon_version') or [])}"
            f" ・ embedder {profiles.get('embedder')} ・ bootstrap B={profiles['bootstrap']['B']}"
            f" seed={profiles['bootstrap']['seed']} ・ 生成 {profiles.get('generated_at')}")
    return (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>bench29 プロファイル</title><style>{CSS}</style></head><body><main>"
        "<h1>bench29 モデルプロファイル</h1>"
        f'<p class="meta">順位ではなく、セルごとの崩れ方・引き寄せられ方の指紋。{html.escape(meta)}</p>'
        + "".join(cards) + "</main></body></html>"
    )


def write_cards(profiles_path: str | Path, out_path: str | Path) -> None:
    profiles = json.loads(Path(profiles_path).read_text(encoding="utf-8"))
    Path(out_path).write_text(render(profiles), encoding="utf-8")
