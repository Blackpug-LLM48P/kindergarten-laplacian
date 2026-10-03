# script-changes.md — コピー側スクリプトの変更

元の `manual-sim/` のスクリプトは変更していない。以下は `manual-sim-cc/` 内のコピーだけの変更。
指標の定義・集計・分母・検証条件（aggregate.py / compare_audits.py / validate_*.py / integrity_check.py / prepare_packets.py）は**無変更**。

## 1. build_report.py（報告文の生成のみ）
理由：元のスクリプトには前回REPORTの数値・結論が固定文として埋め込まれていた（注釈83件、引用154件、45群、採択33群〔problem 1・function 32〕、split 3、棄却9、singleton 19群、「問題参照のあるQはQ007のみ」、T3の確認結果、本番前確認1〜4、Solウルトラ）。そのまま実行すると今回の報告に前回の値が混入するため、次のとおり変更した。
- 出力先を `REPORT.md` → `REPORT-cc.md` に変更（METRIC-DETAILS.md は同名だが cc 側に新規生成）。
- 注釈・候補参照節の固定文を、`annotation-validation.json` / `reference.json` / `agreement.json` から計算する文に置換。
- 「問題参照のあるQ」を reference.json から計算。
- T3節をスキップの記述に置換（対照版本文が無いため）。
- 形式検査節の前回固有の説明（4件の非passの原因）を一般的記述へ置換。値は structure/ から計算（変更なし）。
- 実行環境の記述を execution-context.json から生成。
- 「本番前に人が確かめる箇所」と注釈節の所見文は、今回の結果を見た後に `report-notes-cc.json` に書き、それを読み込む（前回の文は使わない）。
- 節立て（見出し）は前回と同じ。

## 2. package.py
- 存在確認を `REPORT.md` → `REPORT-cc.md`。
- 出力ZIP名を `kanshiki-v5-manual-rehearsal-cc-20261003.zip` に変更（前回ZIPの上書き防止）。

## 3. 実行順による対応（スクリプト無変更）
- `validate_reference.py` は outputs/*.md があると凍結を拒否するため、outputs/ と output-completions.json は凍結後に複製した（outputs-copied-at.txt）。

## 差分（unified diff）
```diff
--- /tmp/claude-0/-home-user-kindergarten-laplacian/885c9793-e40e-5441-b3d4-be6df0c57971/scratchpad/build_report.orig.py	2026-10-03 00:15:39.154000858 +0000
+++ build_report.py	2026-10-03 00:15:45.549214712 +0000
@@ -1,11 +1,17 @@
 from pathlib import Path
 import json,statistics,datetime
+from collections import Counter
 ROOT=Path(__file__).resolve().parent
 def read(name): return json.loads((ROOT/name).read_text())
 metrics=read('metrics.json'); assert metrics['primary_complete']
 agreement=read('agreement.json'); comparison=read('audit-comparison.json')
 assert comparison['outputs_compared']==8
-refs=read('reference.json'); completions=read('output-completions.json')
+refs=read('reference.json'); completions=read('output-completions.json'); ctx=read('execution-context.json')
+notes=read('report-notes-cc.json') if (ROOT/'report-notes-cc.json').exists() else {}
+ann=read('annotation-validation.json')
+all_groups=[dict(g,input_id=i['input_id']) for i in refs['inputs'] for g in i['groups']]
+acc=[g for g in all_groups if g['status']=='accepted']
+prob_q=sorted({g['input_id'] for g in acc if g['polarity']=='problem' and not g['rule_excluded']})
 lookup={(r['input_id'],r['condition']):r for r in metrics['primary_rows']}
 def fraction(x): return f"{x['n']}/{x['denominator']}" if x['denominator'] else 'NA（分母0）'
 def percent(x): return 'NA' if x is None else f'{x*100:.1f}%'
@@ -13,9 +19,9 @@
 labels={'Q005':'形・全文','Q008':'ごん狐・全文','Q010':'科学者とあたま・全文','Q012':'同・冒頭2段落',
         'Q013':'裁判文書・抜粋','Q019':'白書・原本文','Q007':'白書・低下結論追加','Q017':'白書・上昇結論追加'}
 order=read('plan.json')['selected']
-lines=['# AI鑑識v5：手動工程のAI代行リハーサル',
-       '', '作業日：2026年10月3日（日本時間）。記録の時刻はUTC。', '',
-       '本来人が行う関係注釈、注釈間の対応付けと裁定、操作成立確認、出力と参照の照合、親所見と個々の主張の支持裁定をLLMエージェントで実施した。5原作品群から目的選定した8本文版に、v5とB2を各1回適用した。以下は、この模擬経路と事前固定したLLM候補参照に対する記述的参考値である。独立した人間評価や一般母集団のモデル性能を測った値ではない。', '',
+lines=['# AI鑑識v5：手動工程のAI代行リハーサル（Claude Code再演）',
+       '', f"作業日：2026年10月3日。記録の時刻はUTC。実行：{ctx['claude_code_version']}、メイン・サブエージェントのモデルID {ctx['main_model_id']} / {ctx['subagent_model_id']}。評価対象の16出力は前回のものを無改変で再利用し、人の代わりをする側（注釈・裁定・監査）だけを入れ替えた。", '',
+       '本来人が行う関係注釈、注釈間の対応付けと裁定、出力と参照の照合、親所見と個々の主張の支持裁定をLLMエージェントで実施した。5原作品群から目的選定した8本文版に、v5とB2を各1回適用した。以下は、この模擬経路と事前固定したLLM候補参照に対する記述的参考値である。独立した人間評価や一般母集団のモデル性能を測った値ではない。', '',
        '## 得られた参考値', '', '| 指標 | v5 | B2 |', '|---|---:|---:|']
 pool=metrics['pooled_alternative']
 for label,key in [('問題関係の検出 DET','DET'),('機能関係の認識 FUN','FUN'),('機能関係への誤疑義 FERR','FERR'),
@@ -32,18 +38,18 @@
  den=sum(r['relations']['RP']+r['relations']['RF'] for r in metrics['primary_rows'] if r['condition']=='v5')
  lines.append(f"| {label} | {nums['v5']}/{den} | {nums['B2']}/{den} |")
 lines.append(f"| 疑義親内のSUPとUNSUP混在 | {fraction(pool['v5']['mixed'])} | {fraction(pool['B2']['mixed'])} |")
-lines += ['', '各条件の支持率の有効群が異なる場合、条件平均どうしの差は取っていない。差列は両条件で値が定義される同じQだけを比較する。問題参照のあるQはQ007のみで、他Qの検出率はNA。', '',
+lines += ['', '各条件の支持率の有効群が異なる場合、条件平均どうしの差は取っていない。差列は両条件で値が定義される同じQだけを比較する。'+(f"問題参照のあるQは{'・'.join(prob_q)}で、他Qの検出率はNA。" if prob_q else '問題参照のあるQはなく、検出率はすべてNA。'), '',
           '## 本文ごとの生件数', '', '| 本文 | RP / RF | v5 FUN | B2 FUN | v5 FERR | B2 FERR | v5 has_UNSUP / 疑義親 | B2 has_UNSUP / 疑義親 |', '|---|---:|---:|---:|---:|---:|---:|---:|']
 for q in order:
  v,b=lookup[(q,'v5')],lookup[(q,'B2')]
  lines.append(f"| {q} {labels[q]} | {v['relations']['RP']} / {v['relations']['RF']} | {fraction(v['relations']['FUN'])} | {fraction(b['relations']['FUN'])} | {fraction(v['relations']['FERR'])} | {fraction(b['relations']['FERR'])} | {fraction(v['parents']['flags']['has_UNSUP'])} | {fraction(b['parents']['flags']['has_UNSUP'])} |")
 lines += ['', 'RP＝採択した問題参照、RF＝採択した機能参照。各関係への必要な引用と比較条件・本文層に即した解釈が出力にあることを認識条件にした。台帳の項目ID一致や、引用が長く両側を含むだけの出力は認識にしていない。単なる所見の再参照は重複として除き、台帳にだけある具体的な判断は保持した。', '',
           '## 注釈と候補参照', '',
-          '3者の原注釈は83件。引用154件はすべて本文の完全一致・一意の出現を確認した。裁定で45関係群へ対応付け、33群（problem 1・function 32）を採択、3群を意味分岐、9群を採択対象から外した。対応不明群とRULE除外は0。採択33群のうち19群は1者だけの発見、2群は2者、12群は3者の発見であり、多数決を採択条件にしていない。', '',
+          f"3者の原注釈は{len(ann['normalized'])}件。引用{sum(x['required'] for r in ann['reports'] for x in r['quotes'])}件のうち本文と完全一致{sum(bool(x['exact']) for r in ann['reports'] for x in r['quotes'] if x['required'])}件・一意の出現{sum(x['occurrences']==1 for r in ann['reports'] for x in r['quotes'] if x['required'])}件。裁定で{len(all_groups)}関係群へ対応付け、{len(acc)}群（problem {sum(g['polarity']=='problem' for g in acc)}・function {sum(g['polarity']=='function' for g in acc)}）を採択、{agreement['group_status_counts']['split']}群を意味分岐、{agreement['group_status_counts']['rejected']}群を棄却、{agreement['group_status_counts']['alignment_ambiguous']}群を対応不明とした。RULE除外は{sum(g['rule_excluded'] for g in acc)}群。採択{len(acc)}群のうち"+'、'.join(f"{k}者の発見{v}群" for k,v in sorted(Counter(len(g['members']) for g in acc).items()))+"。多数決を採択条件にしていない。", '',
           '| 注釈者ペア | 関係数 | 対応数M | Dice | Jaccard | 対応後のpolarity一致 | 項目ID集合の完全一致 |', '|---|---:|---:|---:|---:|---:|---:|']
 for p in agreement['pairs']:
  lines.append(f"| {p['pair']} | {p['n_a']} / {p['n_b']} | {p['matches']} | {p['dice']:.3f} | {p['jaccard']:.3f} | {percent(p['polarity_agreement'])} | {percent(p['item_set_agreement'])} |")
-lines += ['', '同じ関係でも項目IDが一致しにくい。人手へ戻す際は、項目IDだけで照合せず、必要な両側根拠・対象・時点・条件・本文層を保存する必要がある。Q005などでは比較側を細かく区別したsingletonが多く、候補参照の粒度と採択を人が再点検する価値がある。', '',
+lines += ['', *notes.get('annotation_comment',['（所見は report-notes-cc.json で後記）']), '',
           '## 独立した第2AI監査', '',
           f"Q005・Q007・Q012・Q013の8出力を、主監査票を読まない別エージェントでも監査した。固定参照ごとの挙動フラグ集合は{comparison['event_set_agreement']}/{comparison['relation_votes']}票で一致（{percent(comparison['event_set_agreement_rate'])}）。これは監査者の一致であり、正解率ではない。主監査値を後から有利な票へ差し替えていない。", '',
           '| 本文・条件 | 主監査 has_UNSUP / 疑義親 | 第2監査 has_UNSUP / 疑義親 | 参照挙動の不一致 |', '|---|---:|---:|---:|']
@@ -58,28 +64,25 @@
   for d in c['disagreements']:
    lines.append(f"- {c['input_id']} {c['condition']} {d['ref_id']}: 主監査 {','.join(d['primary_events'])} ／第2監査 {','.join(d['secondary_events'])}。理由全文はaudit-comparison.json。")
 lines += ['', '## 操作成立の予備確認', '',
-          '別のAI確認者が3組の対照版を読んだ。白書の42.7→49.7に対する「低下／上昇」の方向操作は成立を確認した。「ごん狐」の「伝わる／伝わらない」は物理的到達と認識の意味が分かれ、意図したC02反転を確定できなかった。「形」は「腕だけ」の排他性は変わるが、C02の変化は確認しなかった。文学2組には共通して追加された回収文の継ぎ目があり、否定操作そのものの新規効果と分ける必要がある。この確認で本番の独立人間ゲートは完了していない。', '',
+          'T3（操作成立確認）は今回スキップした。対照版の本文がこのZIPに含まれず、元キット（482ファイル）を受け取っていないため。前回の確認結果は封印物に含まれ、本報告では参照していない。', '',
           '## 形式・引用と実行状態', '']
 selected=[read('structure/'+f'v5_{q}-selected.json') for q in order]
 automatic=[read('structure/'+f'v5_{q}.json') for q in order]
 quote_n=sum(x['checks']['quotes']['blocks'] for x in selected)
 quote_exact=sum(x['checks']['quotes']['exact'] for x in selected)
-lines += [f"v5は報告と付属台帳を連結した検査用派生ファイルで機械検査した。29IDの重複なし完全台帳は8/8、フェンス引用の完全一致は{quote_exact}/{quote_n}。自動選択のoverallはpass {sum(x['overall']=='pass' for x in automatic)}/8。現在値の最初のスコア・台帳・四面表を明示選択した検査ではpass {sum(x['overall']=='pass' for x in selected)}/8。4件の非passは代替の集計表を検査器が不正行として扱うことや、強調書式内の正確な分数の抽出に起因し、現在値の四面表と台帳の差分は8/8で空だった。厳密な形式合格に読み替えず、両検査記録を保持した。", '',
-          'B2に29行台帳要件は課していない。フェンス外の引用はkv5_verifyの対象外で、監査票が用いた本文引用と出力spanは別にPythonで完全一致検査した。各原出力は生成後に改善再生成せず、全16出力を取得・監査完了。ユーザー申告のモデル設定はSolウルトラ。新規会話はfork noneで、温度・最大出力トークン予算は制御・確認できていない。', '',
+lines += [f"v5は報告と付属台帳を連結した検査用派生ファイルで機械検査した。29IDの重複なし完全台帳は8/8、フェンス引用の完全一致は{quote_exact}/{quote_n}。自動選択のoverallはpass {sum(x['overall']=='pass' for x in automatic)}/8。現在値の最初のスコア・台帳・四面表を明示選択した検査ではpass {sum(x['overall']=='pass' for x in selected)}/8。機械検査は出力側の性質であり、今回の手動側入れ替えでは変わらない（同一出力・同一検査器で再実行）。厳密な形式合格に読み替えず、両検査記録を保持した。", '',
+          'B2に29行台帳要件は課していない。フェンス外の引用はkv5_verifyの対象外で、監査票が用いた本文引用と出力spanは別にPythonで完全一致検査した。各原出力は生成後に改善再生成せず、全16出力を取得・監査完了。出力生成時のモデル設定は前回記録（ユーザー申告）のままで、今回は出力を生成していない。今回の注釈・裁定・監査は各サブエージェントを新規起動（fork none）し、温度・最大出力トークン予算は制御・確認できていない。', '',
           '| 条件 | 報告＋台帳の総文字数 | 1出力あたり平均 |', '|---|---:|---:|']
 for condition in ['v5','B2']:
  vals=[sum(f['characters'] for f in r['files'].values()) for j,r in completions.items() if j.startswith(condition+'_')]
  lines.append(f"| {condition} | {sum(vals):,} | {statistics.mean(vals):,.1f} |")
 lines += ['', '文字数はPythonの文字数であり、トークン数・出力予算・人間作業時間ではない。v5は29行台帳を含む。条件間の出力長と形式の違い、共通モデル由来の誤り、注釈者内の同一作品別版の相互曝露、作品への既知感が残る。匿名監査も形式から条件を推測できた。', '',
           '## 本番前に人が確かめる箇所', '',
-          '1. 採択singleton19群の関係粒度と意味分岐3群を、両側引用・比較条件・本文層で再裁定する。',
-          '2. 対応しているように見える所見が、必要な両側の引用と関係解釈まで保存されているかを確認する。台帳のID登録と引用付き認識を区別する。',
-          '3. 疑義親に支持・不支持・意味分岐が混在する箇所を、原出力の親単位と個別主張で確認する。初期参照にない新発見を自動不支持にしない。',
-          '4. 文学対照版の操作成立を再確認し、共通追加文の継ぎ目と狙った反転を分ける。T4の追加資料による更新と反復実行は今回未実施。', '',
+          *notes.get('human_checks',['（report-notes-cc.json で後記）']), '',
           '## 記録の使い方', '',
-          'REPORT.mdが本報告。METRIC-DETAILS.mdは各Qの全挙動・親フラグの生件数、割合、v5−B2差と保留品質。metrics.jsonは本文別・原作品群別・群等重み平均、同居数と分母。annotations/は3者の原票、reference.jsonは出力前に凍結した候補参照。outputs/は無改変の16報告と8台帳。audits/は主監査8票と第2監査2票、audit-validation/は原出力のPython文字位置を付した派生票。audit-rules-v1.mdは固定規則。operator-output-map.jsonは実行者用対応表で、注釈・監査の読了対象ではない。', '',
-          '再集計はPython標準ライブラリで validate_reference.py、validate_audits.py、aggregate.py、compare_audits.py、build_report.py、integrity_check.py を順に実行できる。check_structure.pyは同梱した元キットの検査器を使う。初期凍結済み参照を再凍結することはない。final-integrity.jsonとSHA256SUMS.txtで記録の完全性を確認できる。元キット482ファイルはZIP内容と一致を確認し、公式human/independent完了状態と性能値を変更していない。', '',
-          '各値の一般化、信頼区間、統計的有意差、人間作業時間の推定は行っていない。8本文版・83注釈・33採択関係・エージェント数を独立標本数に置き換えない。']
+          'REPORT-cc.mdが本報告。METRIC-DETAILS.mdは各Qの全挙動・親フラグの生件数、割合、v5−B2差と保留品質。metrics.jsonは本文別・原作品群別・群等重み平均、同居数と分母。annotations/は3者の原票、reference.jsonは出力前に凍結した候補参照。outputs/は前回から無改変で再利用した16報告と8台帳。audits/は主監査8票と第2監査2票、agent-prompts/は全サブエージェントへの指示文、agent-self-reports/は既読ファイルの自己申告、audit-validation/は原出力のPython文字位置を付した派生票。audit-rules-v1.mdは固定規則。operator-output-map.jsonは実行者用対応表で、注釈・監査の読了対象ではない。', '',
+          '再集計はPython標準ライブラリで validate_reference.py、validate_audits.py、aggregate.py、compare_audits.py、build_report.py、integrity_check.py を順に実行できる。check_structure.pyは同梱した元キットの検査器を使う。初期凍結済み参照を再凍結することはない。final-integrity.jsonとSHA256SUMS.txtで記録の完全性を確認できる。元キット482ファイルは今回入手しておらず再検証していない（source-integrity.jsonは前回記録の転記）。公式human/independent完了状態と性能値を変更していない。', '',
+          '各値の一般化、信頼区間、統計的有意差、人間作業時間の推定は行っていない。8本文版・注釈数・採択関係数・エージェント数を独立標本数に置き換えない。前回の数値との比較はCROSS-RUN.mdに分離した。']
 details=['# 本文別の参考値詳細','','全値はLLM候補参照・AI監査に対する値。差は相対変化率でなく率の差（ポイント）。分母0の条件を0%として補わない。']
 paired={x['input_id']:x['v5_minus_B2'] for x in metrics['paired_by_input']}
 keys=['DET','PEND','HOLD','MISS','FUN','FPEND','FHOLD','FMISS','FERR','pure_SUP','has_UNSUP','mixed','branch','unresolved']
@@ -101,5 +104,5 @@
   details.append(f'| {key} | {cells[0]} | {cells[1]} |')
  details += ['', '保留品質の対象は固定した採択参照への保留。棄却・splitに対する言及は原票のother_reference_mentionsに別記録。']
 (ROOT/'METRIC-DETAILS.md').write_text('\n'.join(details)+'\n')
-(ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')
-print({'report_characters':len((ROOT/'REPORT.md').read_text())})
+(ROOT/'REPORT-cc.md').write_text('\n'.join(lines)+'\n')
+print({'report_characters':len((ROOT/'REPORT-cc.md').read_text())})
--- ../manual-sim/package.py	2026-10-02 22:16:28.000000000 +0000
+++ package.py	2026-10-03 00:15:39.177886829 +0000
@@ -2,7 +2,7 @@
 import json,hashlib,zipfile
 ROOT=Path(__file__).resolve().parent
 assert (ROOT/'final-integrity.json').exists()
-assert (ROOT/'REPORT.md').exists() and (ROOT/'METRIC-DETAILS.md').exists()
+assert (ROOT/'REPORT-cc.md').exists() and (ROOT/'METRIC-DETAILS.md').exists()
 assert json.loads((ROOT/'metrics.json').read_text())['primary_complete']
 def eligible(p):
  return p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='SHA256SUMS.txt' and not p.name.startswith('build-')
@@ -10,7 +10,7 @@
 manifest='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix() for p in files)+'\n'
 (ROOT/'SHA256SUMS.txt').write_text(manifest)
 files.append(ROOT/'SHA256SUMS.txt')
-archive=ROOT.parent/'kanshiki-v5-manual-rehearsal-20261003.zip'
+archive=ROOT.parent/'kanshiki-v5-manual-rehearsal-cc-20261003.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files: z.write(p,ROOT.name+'/'+p.relative_to(ROOT).as_posix())
 with zipfile.ZipFile(archive) as z: assert z.testzip() is None
```
