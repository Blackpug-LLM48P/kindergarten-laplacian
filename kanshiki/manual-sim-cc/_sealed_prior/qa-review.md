# AI手動代行リハーサル：方法・実装QA

確認日：2026-10-02 UTC。独立した別AIによるコード・方法の点検であり、独立人間検証ではない。主監査の残票が進行中の時点で行った。原注釈・凍結参照・原出力・原監査票の意味裁定は変更していない。

## 判定

確認した範囲で、固定参照の分母、同居挙動の非相殺、群内Q等重み、原作品群等重み、同じQに限定したpaired差の計算は通過した。未監査QをMISSや0%へ置換する処理は認めなかった。終了直前に主16行と8出力の第2比較が揃い、REPORT.mdとMETRIC-DETAILS.mdの生成版も点検した。全10監査票の終了報告・完成記録の最終完結検査は親側に残る。このメモは意味裁定の正解性や実証性能への承認ではない。

## 読了対象と実施した確認

指定されたplan.json、audit-rules-v1.md、reference-freeze.json、reference.json、agreement.json、execution-context.json、aggregate.py、compare_audits.py、build_report.py、integrity_check.py、source-integrity.jsonを読んだ。補助的にvalidate_reference.py、validate_audits.py、check_structure.py、audit-instructions-v1.md、operator-output-map.json、source-provenance.json、完成記録・途中集計・派生監査票を確認した。

元ディレクトリを一時ディレクトリへコピーし、別のcwdからvalidate_reference.py → validate_audits.py → aggregate.py → compare_audits.py → build_report.py → integrity_check.pyを実行した。前4本は成功し、凍結したreference.json・agreement.json・audit-rules-v1.mdは実行前後で不変だった。コピー時点では主5Q・10出力が完了し、Q010/Q017/Q019は未監査、第2比較は6出力・22参照票だった。build_report.pyはprimary_completeのassertで、integrity_check.pyは全10完成票のassertで停止した。これは途中データに対する想定どおりの停止であり、再計算失敗とは扱わない。

さらに一時的な合成票で、FUNとFERRの同居、分母0、支持率の条件別有効Q集合が異なる場合、群等重みを検査した。FUN+FERRの同じ参照は両分子に1ずつ、RF=2に対して両率0.5、同居数1となった。RP=0はnull。群内に「v5支持率NA/B2=1」のQと「v5=1/B2=0」のQを置くと、条件平均は1と0.5、paired差は1だった。別群のpaired差−1を加えると群等重みpaired差0となり、条件平均差−0.25とは区別された。

## 通過した点

- 採択・非RULE参照だけをRP/RFに使用し、split/rejectedを照合分母へ入れていない。参照側のRULE固定値を使い、出力の自己申告で分母を変えない。現在の凍結参照はproblem 1、function 32、split 3、rejected 9、alignment_ambiguous 0、RULE除外0である。
- 各関係はvalidate_audits.pyで1参照1票・全採択参照収容を確認し、aggregate.pyはeventsを集合化して各挙動へ最大1を計上する。MISS/FMISSと他挙動の併記はvalidatorで拒否する。FUN/FERR等を優先順位で相殺するコードはない。
- QA中の親側改訂でmetricsへcoexistenceとpaired_by_inputが追加された。複数eventsの参照ID、FUN+FERR、認識+保留の同居数を派生保存し、各Qのv5−B2差は両率が定義される場合だけ計算する。原裁定を変える改訂ではない。
- QA終了前の親側改訂で、全親フラグも各Qのpaired差に収容され、hold_qualityへ率と対象scopeが追加された。build_report.pyは同居件数表に加え、METRIC-DETAILS.mdへ各Qの全挙動・親フラグの件数/分母・率・ポイント差と保留品質を出力する。保留0はNA、支持差は相対変化率ではなくポイント差として表示するコードを再読した。
- 疑義親はP主張を1件以上含む親を分母にする。全主張分母と疑義親分母は区別され、P/K/U×支持ラベルの件数も別保存する。mixedをhas_UNSUPへ加算し直さず、branch/unresolvedとの重なりを保つ。疑義親0なら率はnullである。FERRとhas_UNSUPを独立2誤りに足す総合誤り数は作っていない。
- 群内はQ率の等重み、全体は原作品群平均の等重みである。Q010/Q012はW10、Q019/Q007/Q017はW12へ束ねられ、別版で群数を増やしていない。法的・行政的制作主体を独立作者へ置換していない。pooled_alternativeは別集計と明記される。
- 注釈のDice/Jaccardは対応後の一対一Mと各関係数から算出する。polarity・項目ID一致を対応条件へ混ぜない。採択33群は1者発見19群・2者2群・3者12群であり、単純な多数決を採択条件にしていない。参照・規則・注釈の凍結ハッシュは一致した。
- compare_audits.pyは固定参照IDごとのevents集合比較と、親・主張の支持件数を区別する。QA中の親側改訂で同文辞書の縮約を廃し、一意の原出力位置・親境界・主張境界をキーにCounterで票数を保持する実装になった。曖昧な位置は件数付きで除外する。主監査値を第2監査の有利な値へ差し替える処理はない。
- build_report.pyの冒頭・制約説明は、模擬経路と事前固定LLM候補参照への記述的参考値と位置づける。人間評価、一般母集団のモデル性能、信頼区間、有意差、人間作業時間を推定していない。設定はユーザー申告と実行環境で未確認の項目を分け、予算同一の比較を主張していない。
- 再計算コードのROOTは__file__を基準にした相対解決であり、別cwdでも動く。検査用の同梱verification/を使用するcheck_structure.pyも相対解決である。履歴のJSONに残る旧絶対パスは実行依存パスではない。

## 具体的な問題・残る限定

1. **途中集計のcoverage。** NA_Q/NA_groupsは到着したmetric_rowsだけに対する数で、未到着Qや未到着の群を欠測件数として数えていない。初回読取りの4Q・8出力ではW01が未到着のため、FUNはvalid_groups=4・NA_groups=0だった。これは5群完了を意味しない。primary_complete=falseと実際の収容Q一覧を必ず併読する必要がある。未到着を0にする問題ではないが、途中値を単体で転載するとcoverageを誤読しうる。
2. **未完了票の防御。** 現在の収容票は全てaudit_complete=trueだが、aggregate.pyはfalseの票を明示除外せず、値を算出したうえでprimary_complete=falseにする。再利用時には未完了票の値を公表しないことが必要。現在の主監査未到着分は行自体が存在しないため、0/MISSへ補完されていない。
3. **支持一致の粒度。** 完全同一境界の補助支持比較は、意味上の主張を別途一対一対応した全体支持一致率ではない。同一spanから複数の意味対象を切り出した主張も存在する（主Q007のO1-P02-C3/C4/C5等）。Counterのラベル交差数は同じ境界のラベル多重集合の一致であり、それを全主張の一致率・正解率へ一般化しない。現在のreport説明とexact_span_only_noteはこの限定を保持する必要がある。
4. **保留品質の範囲。** hold_qualityは採択参照へのcorrespondenceでPEND/HOLD/FPEND/FHOLDを表した関係だけを分母にする。採択外・新規発見の保留を含む全出力の保留品質ではない。当初不足していた率欄・保留0のNA表示・対象範囲の明記は、QA終了前にaggregate.pyとMETRIC-DETAILS.md生成コードへ反映された。
5. **最終完結記録。** 初期点検時はREPORT.mdとMETRIC-DETAILS.mdが未生成だったが、終了直前に生成された。主16行のQ×条件集合が期待集合と一意に一致すること、原ディレクトリの2報告ファイルが別cwdでの再生成結果とバイト一致することを確認した。原票の終了報告と完成記録がまだ進行中だったため、親側による全完成票hashと最終派生票検査は必要である。
6. **完成集合の検査。** integrity_check.pyは完成票数・出力監査数・metric行数をチェックする。別の再利用で余分な同名種別票を追加する場合は、件数だけでなく期待Q×条件集合の一意性も確認すべきである。現時点の読取りでは重複主出力キーは認めなかった。
7. **元ZIPの整合性証拠。** source-integrity.jsonの482元ファイル一致は先行検査の保存結果であり、このQAで元ZIP482件の比較自体を独立再実行したわけではない。再計算時のintegrity_check.pyはこのJSONを読込み、8コピー入力と凍結ファイル・原出力のハッシュを直接検査する。元ZIP比較の再実施と、その保存証拠の点検を区別する。

## ハッシュ読取りの訂正

初回にaudit-validation-summary.jsonの古いsha256とaudit-completions.jsonの値が異なっていた状態を、原票の現ハッシュ不一致と表現した。原票を計算せずそう表現した点はQA側の誤りである。直後にread_bytes()で現原票5件のSHA256を計算し、完成記録と全件一致を確認した。原監査票改変の問題とは判断しない。親側はその後integrity_check.pyへsummary記載hashと現原票hashの一致検査を追加した。この改訂を確認した。

## このQAの限界

関係の採択、各主張のSUP/UNSUP/SPLIT裁定、親所見抽出の意味上の正しさを、人間の独立票へ置換して検証したものではない。新たな多数決参照を作らず、指標を改善するための再裁定もしていない。final-integrity.json、SHA256SUMS.txtと全原票の終了報告・完成記録の完結性は別途最終確認が必要である。

## 終了直前の生成版確認

原票が揃ったスナップショットを別cwdで検査・再集計し、REPORT.md全文を読んだ。機能認識はv5=17/32、B2=23/32、DETは各1/1、has_UNSUPは0/1と3/28で、集計との矛盾は認めなかった。群等重みの機能認識率差は−14.9ポイントとして表示され、支持率の比較はv5有効1群・B2有効4群とpaired有効1群を区別する。第2監査の32/32は参照挙動票の一致であり正解率ではないと明記される。原出力位置での支持ラベル比較をラベル多重集合の交差数と限定した説明も確認した。

METRIC-DETAILS.mdには8Qの全挙動・親フラグと保留品質の表が生成され、採択参照の保留0をNAにする。原ディレクトリのREPORT.mdとMETRIC-DETAILS.mdはこの別cwd再生成結果とバイト一致した。模擬経路の参考値、独立人間ゲート未完了、既読・同一モデル・予算非同一等の限定は保持され、論文の実証値として誤認させる表現は認めなかった。
