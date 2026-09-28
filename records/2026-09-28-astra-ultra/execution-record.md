# 操作・検証記録

2026-09-28の可視会話とツール結果から、今回の回答に関係する事実を整理した記録。完全な生ログではない。

## 初回回答までに実行したこと

1. 別エージェントへ、半径方向と固定した接線方向の二階微分を足す導出案の確認を依頼した。連鎖律と解析的な具体例で確認された。レビュー側はPythonを実行していない。
2. 通常のPythonと指定ランタイムのPythonでSymPyのimportを試みたが、どちらも `ModuleNotFoundError` で失敗した。SymPyによる記号検算は行っていない。
3. Python標準ライブラリだけで有限差分検算を実行した。実行したコードを [verification/check_math.py](verification/check_math.py) に、観測出力を [verification/math-original-output.txt](verification/math-original-output.txt) に保存した。
4. 対話図 [visual/polar-straight-and-round.html](visual/polar-straight-and-round.html) を作成した。
5. PlaywrightでChromiumを起動しようとしたが、実行ファイルがなく失敗した。ブラウザでの描画確認とスクリーンショット取得はできていない。
6. Node.jsのVMとDOMスタブで、JavaScript構文・セレクタ・初期描画処理・スライダー入力後の文字列更新を確認した。実ブラウザでの見た目の確認ではない。

### Python検算の内容

- 関数は `x*x+y*y`、`x`、`x*y`、`exp(0.2*x)*cos(0.3*y)` の4つ。
- `r=2, theta=0, h=0.001` で直交座標の中央差分、極座標の三項、補正項を除いた式を比較した。
- 4関数×4地点の16ケースを、刻み幅 `h=0.01` と `0.001` で解析解と比較した。
- 最大絶対誤差はそれぞれ `2.352e-04` と `2.353e-06`。
- 平らな坂 `u=x` は角度項と半径の補正項が相殺して0になる。補正項を除くとこの相殺を失う。
- 接線移動による半径の増分について、`delta_r/h^2` が `1/(2r)` へ近づくことも数値で確認した。

### ブラウザ起動時のエラー抜粋

```text
browserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
```

### DOMスタブによる確認の出力

```text
JS syntax, selectors and interaction passed
まっすぐ：中心から 2.236 m
まっすぐ：中心から 2.002 m
Literal escaped quotes: false Literal escaped newlines: false
```

## 回答後のユーザー観測

ユーザー原文：

> 55%→55%why  wwwwwww

会話では、表示差が0であることと実際の消費が0であることは分けて扱った。丸めや更新のタイミングなどは可能性であり、原因を確定した調査結果ではない。

続いてユーザーから「gitきろく」と保存を依頼された。本フォルダはその依頼による保存である。

## 保存時に行ったこと

- 初回回答の可視本文を [answer-original.md](answer-original.md) へ転記した。後から追加した評価や注意はこのファイルに混ぜていない。
- GitHub表示用の複製では、数式の区切りをGitHub用に変換し、ChatGPT固有の対話図参照を相対リンクへ変更した。
- 図のソースは実行時のローカルファイルとバイト単位で一致することを確認した。
- 保存したPythonを再実行し、初回の観測標準出力と一致することを確認した。保存時の確認であり、初回回答への追加検算として遡及加点しない。
- 導出案を確認した別エージェントからレビュー範囲の明記を受け取り、[review.md](review.md) に分離した。
- READMEへ今回の記録の索引を追加した。以前の試験結果の再採点は行っていない。

## 測定していないこと

実トークン数、課金量、純粋な内部推論時間、内部で使用された推論設定、幼児の理解度、他モードに対する性能差。今回の単一回答と残量表示から、モデル全般の劣化や改善を判定しない。
