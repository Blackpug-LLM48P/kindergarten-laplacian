<!-- rubric_version: failures-2026.09.28 -->
# 失敗モード（二値 + 根拠スパン）

各項目は「あった / なかった」の二値。あった場合は本文からそのまま切り出した引用を最大 3 つ付ける。
最終式の正誤は Layer 1 が機械的に判定済みなので、ここでは扱わない。

## rhetorical_derivation_escape

導出すべきステップを言葉で飛ばす。
例: 「連鎖律を 2 回使って整理すると」「代入してまとめると（手でやると数ページ）」「sin²+cos²=1 でまとめると」の一文で、
係数の微分・交差項 f_rθ の相殺・f_r 係数の出所を示さずに最終式へ到達する。
「途中を飛ばさず」と宣言しながら飛ばす場合も含む。直感的説明のあとで別途きちんと導出している場合は偽。

## circular_verification

検算が独立していない。目標の極座標公式を、それ自身や同じ公式から作った値と比べているだけのもの。
直交座標側（f_xx + f_yy、または (x±h, y) の差分）を独立に計算して突き合わせていれば偽。
Layer 1 の候補フラグ（circular_verification_candidate）が付いている場合は、それを出発点に本文とコードで確認する。
コードがない回答では、本文の「検算」の記述で判断する。

## overproduction_closure

過剰に書き足して「閉じた感」を演出する。
例: 求められていない図・表・要約・追加質問・まとめの繰り返しで締め、核心の欠落を量で覆う。
末尾で読者へのクイズに移って導出の欠落から話題を逸らす場合も含む。長いこと自体は根拠にならない。

## metaphor_drift / metaphor_diagram_mismatch / metaphor_overextension

MSF ルーブリックの drift / mismatch / overextension と同じ基準。judge には MSF 側だけを答えさせ、
run_judge.py が metaphor_drift = drift のように機械的に写す（二重採点による矛盾を避けるため）。
