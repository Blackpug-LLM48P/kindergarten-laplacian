# 2026-10-27 GPT-6.1 Terra「最大」：回文と極座標ラプラシアン

## 結果

500文字回文は、回答中の文字列を再検査したところ、ひらがな500文字で反転しても一致した。短い回文をつないだ250文字とその逆順で構成されており、統一された物語としての自然さは別問題である。

極座標ラプラシアンは、最終式を示し、小さな扇形の面積と外側・内側の辺の差を使って導出した。対象モデルは回答前に４関数×３地点の数値検算を実施し、後続の自己評価では角度方向の熱量の表記、有限差分の近似、原点の滑らかさの条件を修正事項として挙げた。

対象読者についての「園児向けとしては未達」はモデル自身の自己評価であり、園児を対象とする理解度試験や独立した人的評価は行っていない。総合点、順位、モデル間の性能差は未確定。

## 観測条件

| 項目 | 記録 |
|---|---|
| 日付 | 2026-10-27、日本時間 |
| 使用面 | ChatGPT Work。ユーザー添付画面に「6.1 Terra 最大」と表示 |
| 内部API設定 | モデルID、reasoning effortのAPI値、サービス階層などは未取得。画面表示から補完しない |
| 会話の状態 | 新しい会話でテスト開始。回文テスト後、同じ会話でラプラシアンを実施。テストの存在をモデルに伝えている |
| 回文の計測 | 07:43:06〜07:44:15、69秒。開始から作成・検算終了まで |
| ラプラシアンの計測 | 08:40:08〜08:41:06、58秒。開始から導出・検算終了まで |
| 時間の範囲 | いずれも回答全文の画面表示完了までを計っていない。純推論時間・サーバー処理時間と同一視しない |
| トークン数・消費率 | 未取得 |
| Python | 対象モデルが標準ライブラリによる数値検算を実行。sympy は環境内で利用できなかった |

同じ日に別途保存された [Terra medium](../2026-10-27-terra-medium/README.md) とは実行面、会話文脈および計測方法が異なるため、表示時間を直接比較して性能差とはしない。

## 収録内容

| ファイル | 内容 |
|---|---|
| [prompt.txt](prompt.txt) | この会話での試験開始、２問、自己感想の依頼 |
| [palindrome-answer-original.txt](palindrome-answer-original.txt) | 回文試験への最初の回答 |
| [laplacian-answer-original.txt](laplacian-answer-original.txt) | ラプラシアン試験への最初の回答 |
| [self-review-original.txt](self-review-original.txt) | ユーザーの追加指示を受けた後の答え合わせと自己感想 |
| [execution-record.md](execution-record.md) | 時間、設定、ツール使用と転記の根拠 |
| [review.md](review.md) | 回答中・自己評価・記録時再検証の区別と観察 |
| [verification/check_math_original.py](verification/check_math_original.py) | 初回回答前に実行した４関数×３地点の数値検算コード |
| [verification/math-output-original.txt](verification/math-output-original.txt) | 保存した初回検算コードの再実行出力 |
| [verification/check_math_followup.py](verification/check_math_followup.py) | 自己評価時の追加６関数の数値確認コード |
| [verification/math-output-followup.txt](verification/math-output-followup.txt) | 追加確認コードの再実行出力 |
| [verification/check_palindrome.py](verification/check_palindrome.py) | 保存した実回答から回文を抽出し、文字数・一致・ハッシュを照合 |
| [verification/palindrome-output.txt](verification/palindrome-output.txt) | 上記検査の実行出力 |
| [verification/check_geometry.py](verification/check_geometry.py) | 記録作成時に追加した有限セルの式の有理数検算 |
| [verification/geometry-output.txt](verification/geometry-output.txt) | 上記検査の実行出力 |
| [manifest-sha256.txt](manifest-sha256.txt) | 本ディレクトリの保存ファイルのSHA-256。manifest自身は対象外 |

各回答は会話表示からの転記。回答全体の独立した原本ファイルはなく、全文のバイト単位照合は未実施。回文部分のみ、会話中に取得したSHA-256と保存後の抽出文字列を照合した。

## 再実行

リポジトリのルートから実行する。Python標準ライブラリのみ使用。assert を有効にするため python -O は使わない。

~~~bash
python3 records/2026-10-27-terra-max/verification/check_palindrome.py
python3 records/2026-10-27-terra-max/verification/check_math_original.py
python3 records/2026-10-27-terra-max/verification/check_math_followup.py
python3 records/2026-10-27-terra-max/verification/check_geometry.py
~~~

check_math_followup.py は各値を表示する観測用コードで、閾値による合否判定を行わない。check_geometry.py は追加した有限セルの差分式を３つの有理数例で確かめるもので、一般の場合の証明ではない。
