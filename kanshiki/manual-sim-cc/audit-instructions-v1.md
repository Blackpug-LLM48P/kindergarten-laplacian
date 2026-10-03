# 出力監査の実装指示 v1

これは凍結済み audit-rules-v1.md の実装用スキーマであり、採点規則を変更しない。出力は匿名ファイル名にしたが、書式や自己呼称から条件を推測できる。推測と確信を記録する。

指定されたQの本文・候補参照・2出力（付属台帳があればそれを含む）・採点規則を全文読む。操作意図・条件対応表・他監査者の票・論文・元注釈は読まない。初期参照を増減しない。出力へ修正要求を返さない。

JSONのトップは role=llm, auditor_id, context（既読・外部知識・条件推測可能性）, inputs の配列。各inputは input_id, outputs の配列。各outputは output_alias, acquisition_state=complete/partial/missing, audit_complete, condition_guess と次の配列を含む。

## correspondence

採択された全参照を各1票にする。ref_id, events, evidence_spans, reason, pend_checks を保存する。

- eventsは問題: DET/PEND/HOLD/MISS、機能: FUN/FPEND/FHOLD/FMISS/FERR。同じ関係で確定・保留や機能・誤疑義が同居すれば複数記録する。見つからないときのみMISS/FMISS。
- evidence_spansは {file, text} の配列。textはその出力から切り出した連続した完全一致文字列。引用と関係解釈が別箇所なら複数spanにする。初期参照の引用と同文でなくても、必要な比較側と関係を認識していれば対応可能。長い引用だけ・同じ項目IDだけでは対応しない。
- pend_checksは {relation_and_quotes:boolean, specific_material:boolean, decision_branch:boolean, reason:string}。保留のない場合も3値falseとし理由=not_applicable。PEND/FPENDは3値trueの場合だけ。具体資料に対して結果別の分岐を出力が書いていない場合は、その分岐を監査者が補わない。
- RULEは参照側の固定値を使う。split/rejectedはこの分母に入れず、関連判断があれば other_reference_mentions に別保存する。

## parents

原出力の全ての実質的な関係判断を親所見へ抽出する。番号・箇条書きの一項または未構造の判断段落を単位にする。台帳の参照のみ・見出し・算術・一般注意書きは数えない。台帳にだけ独自の実質判断があれば抽出する。同じ所見を要約や助言で言い直しただけなら duplicate_of を記録し分母から除く。異なる判断は保持する。

各親は parent_id, file, text（完全一致の連続文字列）, extraction_reason, duplicate_of（なければnull）, claims の配列。

各claimは claim_id, text（親内の完全一致連続文字列）, stance=P/K/U, support=SUP/UNSUP/SPLIT/UNRESOLVED, ref_ids（なければ空）, source_quotes（本文から完全一致、なければ空）, reason。

- Pは出力が問題・欠陥・不対応と判断した主張。Kは肯定的な機能・対応判断。Uは資料不足・判断保留。指摘対象の本文命題や引用だけを監査者の結論へ取り違えない。
- 複数の判断を一括支持しない。最低限の独立した判断へ分け、混在を残す。ただし同じ判断を意味を変えずに細分して水増ししない。
- SUPは提示本文が支える。UNSUPは本文が支えない確定判断・反証された判断。SPLITは恒久的な解釈分岐。UNRESOLVEDは監査者の未裁定。初期参照にないという理由だけでUNSUPにしない。必要資料が未提示というU自体を、資料の虚偽というPへ変換しない。
- 台帳がある出力とない出力で、親・主張の粒度を同じ規則で保つ。引用が省略・変形されている場合は quote_issues に記録し、必要な意味範囲の対応と別に扱う。

## 補助欄

other_reference_mentions, new_discoveries, quote_issues, extraction_notes を各outputへ保存する（なければ空配列）。新規発見で初期参照を増やさない。完了前に全採択参照の収容、原出力span完全一致、本文引用完全一致を検査する。オフセットは親側がPython文字位置として算出するので推測しない。監査のJSONを先に保存してから検査し、再生成せずspan転記ミスは監査記録に訂正を残す。
