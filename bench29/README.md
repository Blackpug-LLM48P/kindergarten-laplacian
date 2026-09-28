# bench29：29文字ベンチマークの評価パイプライン

「幼稚園児にわかる極座標ラプラシアンの導出。Python使用可。」への回答を、**順位ではなくモデルごとの指紋**として観測する。
正解スコアは出さない。唯一の例外は最終式の数学的正誤で、これは説明の良し悪しとは分けて機械的に判定する。

## 層構成

| 層 | 場所 | judge | 内容 |
|---|---|---|---|
| 0 | `schema.py`, `ingest.py` | 不要 | trial 単位の生データ（JSONL が正本） |
| 1 | `extract/` | 不要 | 構造・最終式の正誤・Python 監査・比喩・5歳児制約の代理指標 |
| 2 | `distrib/` | 不要 | セル単位の分布指標 + ブートストラップ 95% CI（**本体**） |
| 3 | `judge/` | 固定 judge | MSF 4 軸・失敗モード（根拠スパン付き）、アンカーで κ 較正 |
| 出力 | `report/` | – | プロファイルカード（HTML）、バージョン間ドリフト（Markdown） |

Layer 1・2 は judge なしで完結し、モデル世代交代や judge の入れ替えで腐らない背骨になる。

## 使い方

```bash
pip install -r bench29/requirements.txt

python -m bench29 ingest  --records records/ --table my_runs.jsonl -o trials.jsonl
python -m bench29 extract trials.jsonl -o features.parquet
python -m bench29 profile trials.jsonl features.parquet -o profiles.json      # --pool-lang で ja/en を同一セルに
python -m bench29 card    profiles.json -o profiles.html
python -m bench29 drift   profiles.json -o drift.md

# Layer 3（任意・API 課金あり）
python -m bench29 judge     trials.jsonl --judge-model <固定したモデルID> --features features.parquet -o judge.jsonl
python -m bench29 calibrate bench29/judge/anchors --judge-model <同上> -o calibration.json

python -m pytest tests
```

### Layer 0 の 1 行（trials.jsonl）

```json
{"trial_id": "...", "model": "grok", "model_version": "grok-4.2-0915", "surface": "chat", "lang": "ja",
 "params": {"temperature": 1.0}, "timestamp": "2026-09-28T10:00:00+09:00",
 "response_text": "...", "code_blocks": null, "exec_log": null, "tokens_out": 1834}
```

`model_version` は必須（空だとエラー）。`code_blocks` を省くと本文のフェンスから抽出する（```math は除外）。
`records/` からの取り込みはモデル版が未確認なので `model_version = "unverified:<フォルダ名>"` になる。

## Layer 1 の要点

- **formula.py**：数式区間（`$$`, `\[ \]`, `\( \)`, `$ $`, ```math、平文の `∇²f = f_rr + …`）から候補式を拾い、
  自前の再帰下降パーサで SymPy 式にしてから、導関数値と座標に乱数を入れて標準形と数値照合する。
  `\frac{\partial^2 f}{\partial r^2}`、`\partial_r`、`f_{rr}`、`∂²f/∂θ²`、作用素形の `∇² = …`、`(1/r)∂_r(r∂_r f)`、
  `\underbrace`/`\boxed`、関数名 u・Φ、角度 φ などに対応。`f_x = …` のような連鎖律の途中式は候補から外す。
  判定は**最後の候補式**で行い、`formula_any_incorrect` で途中の誤りも残す。位置は初出で head/middle/tail。
  latex2sympy2 を使わないのは、外部パーサの版で結果が変わると Layer 1 の再現性が崩れるため。
- **code_audit.py**：`symbolic_derivation` / `symbolic_check` / `numeric` / `none` と、
  「極座標公式がコードにあるのに直交座標側の独立計算がない」循環検証の**候補**。確定は Layer 3。
- **metaphor.py**：`lexicon/{ja,en}.yaml`。長い語優先で重なりを解消（パンケーキ ≠ ケーキ）、数式・コード内は数えない。
  カテゴリ（pizza, cake…）と粗いグループ（round_food…）の両方を記録する。

## Layer 2 の要点

セル = `model × model_version × lang × surface`。n < 100 のセルは `underpowered: true`。
全指標にパーセンタイル・ブートストラップ 95% CI（B=2000、seed=29 固定）。

| 指標 | profiles.json のキー |
|---|---|
| 比喩エントロピー H（bits） | `metaphor_entropy` / `metaphor_group_entropy` |
| Top-1 集中度 | `metaphor_top1`（`label` 付き） |
| 構造テンプレ一致率 | `structure_template_match_rate` |
| 意味的多様性（平均 cos 類似度） | `semantic_similarity`（`embedder` をファイル先頭に記録） |
| 各分布 | `*_distribution`（カテゴリごとの比率 + CI） |
| JSD（モデル間・バージョン間・言語間・surface 間） | `comparisons[].jsd.*`（`relation` で種別） |

## Layer 3 の要点

- ルーブリック：`judge/rubric_msf.md`, `judge/rubric_failures.md`。`rubric_version` は宣言版 + 内容ハッシュ。
- judge には MSF の drift/mismatch/overextension だけを答えさせ、失敗モードの `metaphor_*` は機械的に写す（二重採点の矛盾防止）。
- 根拠スパンは本文に実在するか照合し、実在しない引用は `evidence_unverified` に分離。真なのに実在根拠がない軸は `*_needs_review`。
- `calibrate.py`：アンカーの人手ラベル（複数ラベラーなら多数決）と judge の Cohen's κ（stretch_level は二次重み付き）。
  全軸が閾値以上で採用、1 軸でも下回れば不採用（終了コード 1）。

## 未決事項（黒パグ判断）と、実装での扱い

| 未決事項 | 現状の実装 |
|---|---|
| 比喩辞書の粒度 | カテゴリとグループを両方記録。どちらを正本にするかは未決 |
| ja / en を同一セルで比較するか | 既定は別セル。`--pool-lang` で統合。`relation: "lang"` の JSD も出す |
| 意味的多様性の埋め込み | 既定は決定論的な文字 3-gram ハッシュ（表層の類似しか測らない）。`Embedder` を差し替え可能 |
| アンカーのラベラー | 単独・複数どちらの形式でも動く。アンカー自体は未作成 |
| Layer 3 rubric の公開範囲 | ルーブリックは独立ファイルなので、公開時に除外しやすい構成 |
| κ の閾値 | 暫定 0.6（`--threshold`） |

## 既知の制約

- 引き継ぎ書にある「既存 n=500+ データ」はこのリポジトリに含まれていない（ルート README の 2026-09-03 観察では、
  この数字自体が存在未確認の言及として記録されている）。取り込み器は JSONL/CSV に対応済みで、データが来れば流せる。
  現時点の実データは `records/` の 3 件のみ。「Grok ピザ 90%」の再現確認は、合成データでの動作確認に留まる。
- 構造タグ・専門語・比喩辞書はヒューリスティック。変えたら `FEATURE_VERSION` / 辞書 `version` を上げ、版をまたいで比較しない。
