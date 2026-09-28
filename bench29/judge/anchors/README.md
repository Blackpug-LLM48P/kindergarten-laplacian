# アンカーセット（人手ラベル）

judge 較正用の固定セット。約 30 件を目安に、ここへ `*.jsonl` で置く。**いったん確定したら中身を変えない**
（変えると過去の κ と比較できなくなる。差し替える場合は別ファイル名で新しい版を作る）。

1 行の形式:

```json
{"trial": {"trial_id": "...", "model": "...", "model_version": "...", "surface": "chat", "lang": "ja",
           "response_text": "..."},
 "labels": {"kuropug": {"stretch_level": 1, "drift": false, "mismatch": false, "overextension": true,
                        "rhetorical_derivation_escape": true, "circular_verification": false,
                        "overproduction_closure": true}}}
```

- `labels` のキーはラベラー ID。複数ラベラーなら軸ごとに多数決で参照ラベルを作り、ラベラー間 κ も出す。
  同数で割れた軸はその件だけ κ 計算から外す。
- 選び方の目安: formula_status・verification_type・主比喩がばらけるように、既存記録から層化して選ぶ。
- 未決事項: ラベラーを単独にするか複数にするか（どちらの形式でも `calibrate.py` は動く）。

現時点ではアンカーは未作成。`records/` の 3 件だけでは足りないため、実データ取り込み後に作る。
