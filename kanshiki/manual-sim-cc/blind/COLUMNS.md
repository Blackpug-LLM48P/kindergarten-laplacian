# 注釈票の列

| 列 | 書き方 |
|---|---|
| input_id | 入力ID |
| annotator_id | 注釈者ID（実名でなくてよい） |
| annotator_role | `independent`（規約の設計に関わっていない）/ `developer`（規約の所有者・設計者）/ `llm`（補助） |
| relation_id | 注釈者内の通し番号（`A1`, `A2`…） |
| item_ids | 対応すると考えるv5の項目（`C02` 、複数なら `;` 区切り） |
| polarity | `problem`（問題となる関係）/ `function`（機能として認める関係） |
| quote_a / loc_a | 関係の一方の側の**完全一致引用**と位置（段落番号など） |
| quote_b / loc_b | 関係のもう一方の側（両側が必要な関係のみ） |
| relation | 何と何の関係が、なぜ問題（または機能）か |
| alternative_explanations | 検討した別説明 |
| missing_material | 判断に足りない資料（あれば） |
| confidence | `high` / `mid` / `low` |
| minutes | かかった時間（分） |
| notes | 備考 |


input_idは本文のQ番号。完了票completions.csvでは、0関係でもstatus=completedと時刻（タイムゾーン付き）を記録する。ハッシュと正式IDへの変換は運用者が行い、本人が内容を確認してから確定する。
