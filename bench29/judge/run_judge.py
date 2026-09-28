"""固定 judge で MSF と失敗モードを採点する。

- judge は差し替え可能（JudgeClient プロトコル）。同梱は Anthropic SDK 版のみ。
- judge_model はバージョンまで固定した ID を必ず明示する（既定値は置かない）。
- 出力には judge_model / judge_version / rubric_version を必ず付ける。
- 根拠スパンは応答本文に実在するかを機械的に照合し、実在しない引用は evidence_unverified に分ける。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Protocol

from ..schema import Trial

HERE = Path(__file__).parent
RUBRIC_FILES = ("rubric_msf.md", "rubric_failures.md")

BINARY_AXES = ("drift", "mismatch", "overextension",
               "rhetorical_derivation_escape", "circular_verification", "overproduction_closure")
# 失敗モードのうち MSF から写すもの
DERIVED = {"metaphor_drift": "drift", "metaphor_diagram_mismatch": "mismatch",
           "metaphor_overextension": "overextension"}
LABELS = ("stretch_level",) + BINARY_AXES + tuple(DERIVED)

_AXIS_SCHEMA = {
    "type": "object",
    "properties": {
        "present": {"type": "boolean"},
        "evidence": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["present", "evidence"],
    "additionalProperties": False,
}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "stretch_level": {"type": "integer", "enum": [0, 1, 2, 3]},
        "stretch_evidence": {"type": "array", "items": {"type": "string"}},
        **{axis: _AXIS_SCHEMA for axis in BINARY_AXES},
    },
    "required": ["stretch_level", "stretch_evidence", *BINARY_AXES],
    "additionalProperties": False,
}

SYSTEM = """あなたはベンチマークの観測器です。回答の良し悪しを総合評価したり点数をつけたりしません。
与えられたルーブリックの各軸について、回答本文に書かれていることだけを根拠に判定します。
根拠（evidence）は回答本文からそのまま切り出した文字列にし、言い換えないでください。

{rubrics}"""


def rubric_text() -> str:
    return "\n\n".join((HERE / f).read_text(encoding="utf-8") for f in RUBRIC_FILES)


def rubric_version() -> str:
    """宣言版 + 内容ハッシュ。文言を 1 文字でも変えれば別版になる。"""
    text = rubric_text()
    declared = re.findall(r"rubric_version:\s*(\S+)", text)
    return "+".join(declared) + "#" + hashlib.sha256(text.encode()).hexdigest()[:12]


def build_prompt(trial: Trial, l1: dict[str, Any] | None = None) -> str:
    hints = ""
    if l1:
        hints = (
            "\n\n<layer1_hints>\n"
            f"circular_verification_candidate: {l1.get('circular_verification_candidate')}\n"
            f"verification_type: {l1.get('verification_type')}\n"
            f"metaphor_categories: {l1.get('metaphor_categories')}\n"
            "</layer1_hints>"
        )
    return (
        "次の回答を、システムプロンプトのルーブリックに従って判定してください。"
        f"{hints}\n\n<response>\n{trial.response_text}\n</response>"
    )


class JudgeClient(Protocol):
    model: str

    def judge(self, system: str, prompt: str, schema: dict) -> tuple[dict, str]:
        """(判定 JSON, 実際に応答したモデル ID) を返す。"""
        ...


class AnthropicJudge:
    """Anthropic Messages API の構造化出力で判定する。

    model はバージョンを固定した ID を渡す（例: "claude-opus-5"）。エイリアスで世代が動く ID は避ける。
    """

    def __init__(self, model: str, effort: str = "high", max_tokens: int = 16000):
        import anthropic  # 任意依存

        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens

    def judge(self, system: str, prompt: str, schema: dict) -> tuple[dict, str]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"judge refused: {response.stop_details}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("judge output truncated (max_tokens)")
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text), response.model


def _verify_spans(spans: list[str], text: str) -> tuple[list[str], list[str]]:
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    body = norm(text)
    ok = [s for s in spans if norm(s) and norm(s) in body]
    return ok, [s for s in spans if s not in ok]


def normalize_output(raw: dict, trial: Trial) -> dict[str, Any]:
    row: dict[str, Any] = {"stretch_level": int(raw["stretch_level"])}
    ok, bad = _verify_spans(raw.get("stretch_evidence", []), trial.response_text)
    row["stretch_level_evidence"] = ok
    unverified = {"stretch_level": bad} if bad else {}
    for axis in BINARY_AXES:
        ok, bad = _verify_spans(raw[axis].get("evidence", []), trial.response_text)
        row[axis] = bool(raw[axis]["present"])
        row[f"{axis}_evidence"] = ok
        if bad:
            unverified[axis] = bad
        # 真なのに実在する根拠が 1 つもない判定は要確認に回す
        row[f"{axis}_needs_review"] = row[axis] and not ok
    for derived, src in DERIVED.items():
        row[derived] = row[src]
    row["evidence_unverified"] = unverified
    return row


def judge_trial(trial: Trial, client: JudgeClient, l1: dict[str, Any] | None = None) -> dict[str, Any]:
    raw, served_model = client.judge(SYSTEM.format(rubrics=rubric_text()), build_prompt(trial, l1), OUTPUT_SCHEMA)
    row = normalize_output(raw, trial)
    row.update({
        "trial_id": trial.trial_id,
        "judge_model": client.model,
        "judge_version": served_model,
        "rubric_version": rubric_version(),
    })
    return row


def run(trials: list[Trial], client: JudgeClient, l1_by_id: dict[str, dict] | None = None,
        out_path: str | None = None) -> list[dict]:
    """全 trial を採点。out_path があれば 1 行ずつ JSONL に追記し、既存 trial_id はスキップ（再開可能）。"""
    done: set[str] = set()
    if out_path and Path(out_path).exists():
        with open(out_path, encoding="utf-8") as fh:
            done = {json.loads(line)["trial_id"] for line in fh if line.strip()}
    rows = []
    for t in trials:
        if t.trial_id in done:
            continue
        row = judge_trial(t, client, (l1_by_id or {}).get(t.trial_id))
        rows.append(row)
        if out_path:
            with open(out_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows
