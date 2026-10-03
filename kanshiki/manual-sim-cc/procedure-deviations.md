# procedure-deviations.md — 手順書との差・記録事項

1. **追加封印**：書簡に列挙の15項目に加え、前回の手動側判断や対応表を含む7項目（audit-packets/、annotations-freeze.json、audit-completions.json、audit-q008-work.py、final-integrity.json、execution-context.json、operator-output-map.json）を `_sealed_prior/` に封印した。operator-output-map.json は prepare_packets.py で同じ決定的規則から再生成し、O1/O2割り当てが前回と一致することだけを機械的に確認した（中身の条件対応は実行者のみ保持）。
2. **実行者の既読**：setup-log.json の orchestrator_exposure を参照。build_report.py に前回の結論が固定文で入っていたため、実行者は前回の件数（注釈83、採択33群等）を封印解除前に知った。サブエージェントへの指示文には転記していない（agent-prompts/ 参照）。
3. **裁定者への追加資料**：書簡は「3票・本文・audit-rules-v1.md §1〜2」。reference.json の必須欄 `rule_excluded` を出力前に固定するため、§3 のRULE段落（1段落、原文のまま）と ITEM-DEFINITIONS-rc.3.md（注釈者にも渡した資料。出力や前回結果を含まない）を追加で渡した。
4. **作業場所の分離**：各サブエージェントには scratchpad 内の専用ディレクトリ（ws/annot-A 等）に許可ファイルだけを複製して渡した。ファイルシステム上の物理的な遮断ではなく、指示と自己申告（agent-self-reports/）による遮断である。
5. **作業用スクリプトの置き場所**：注釈者A・B、裁定者は票の組み立て用スクリプトを専用ディレクトリ外の scratchpad 直下（annotA_tmp/、buildB.py、build/）に置いた。他のエージェントが読んだ記録はない（自己申告）。agent-helper-scripts/ に保存。
6. **裁定者の解釈（要確認）**：全注釈者が polarity=unresolved とした関係（または本文で問題とも機能とも確定できない関係）を、split ではなく rejected とした。規則 §1 は明示していない。split は「本文から両方の読みを排除できない解釈対立」に限定された。棄却18群はすべて unresolved。採点分母（採択群のみ）には影響しないが、split件数・棄却件数の比較に影響する。
7. **第2監査の分担**：secondary-audit-plan.json の4Q（Q005・Q007・Q012・Q013）を、S1＝Q005・Q007、S2＝Q012・Q013 に分けた（計8出力。build_report.py は比較出力数=8を要求）。主監査結果を見る前に決めた。前回の分担は封印物の中にあり確認していない。
8. **T3** はスキップ（対照版本文なし）。
9. **structure/** は出力側の機械検査であり、cc側で check_structure.py を再実行した（各Qのoverall判定は前回 manual-sim/structure と同一。JSONのバイト列はパス等で異なる）。
