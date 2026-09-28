"""bench29: 29文字ベンチマーク（幼稚園児にわかる極座標ラプラシアン）の評価パイプライン。

正解スコアは出さない。モデルがどう崩れ、どこに引き寄せられるかの分布を観測する。
唯一の例外は最終式の数学的正誤（Layer 1 の formula_status）。

層構成:
  Layer 0  schema.py      生データ（Trial）
  Layer 1  extract/       決定論的特徴量（judge 不要）
  Layer 2  distrib/       セル単位の分布メトリクス（judge 不要）
  Layer 3  judge/         LLM judge 軸（固定 judge + アンカー較正）
  出力     report/        プロファイルカード・バージョン間ドリフト
"""

__version__ = "0.1.0"

# 特徴量の定義が変わったら上げる。features / profiles に必ず記録する。
FEATURE_VERSION = "l1-2026.09.28"
