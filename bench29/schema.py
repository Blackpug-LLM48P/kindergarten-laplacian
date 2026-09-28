"""Layer 0: 生データスキーマ。

1 trial = 1 回の実行。モデルのバージョン文字列まで固定で記録する。
JSONL（1 行 1 trial）を正本とし、取り込み時に検証する。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

SURFACES = ("api", "chat", "agent")
LANGS = ("ja", "en")

_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})([^\n`]*)\n(.*?)^[ \t]*\1[ \t]*$", re.M | re.S)


@dataclass
class CodeBlock:
    language: str
    code: str
    # response_text 内の開始文字オフセット
    offset: int = 0


@dataclass
class Trial:
    trial_id: str
    model: str
    model_version: str
    surface: str
    lang: str
    response_text: str
    params: dict[str, Any] = field(default_factory=dict)
    timestamp: str | None = None
    code_blocks: list[CodeBlock] | None = None
    exec_log: str | None = None
    tokens_out: int | None = None
    # 由来・注記など自由記述（集計には使わない）
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.surface not in SURFACES:
            raise ValueError(f"{self.trial_id}: surface must be one of {SURFACES}, got {self.surface!r}")
        if self.lang not in LANGS:
            raise ValueError(f"{self.trial_id}: lang must be one of {LANGS}, got {self.lang!r}")
        if not self.model_version:
            raise ValueError(f"{self.trial_id}: model_version is required (use the exact version string)")
        if self.code_blocks is None:
            self.code_blocks = extract_code_blocks(self.response_text)
        else:
            self.code_blocks = [cb if isinstance(cb, CodeBlock) else CodeBlock(**cb) for cb in self.code_blocks]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Trial":
        known = {f for f in cls.__dataclass_fields__}
        extra = {k: v for k, v in d.items() if k not in known}
        d = {k: v for k, v in d.items() if k in known}
        if extra:
            d.setdefault("meta", {}).update(extra)
        return cls(**d)


def extract_code_blocks(text: str) -> list[CodeBlock]:
    """Markdown のフェンス付きコードブロックを抽出する。```math は数式なので除く。"""
    blocks = []
    for m in _FENCE_RE.finditer(text):
        lang = m.group(2).strip().split()[0].lower() if m.group(2).strip() else ""
        if lang in ("math", "latex", "tex"):
            continue
        blocks.append(CodeBlock(language=lang, code=m.group(3), offset=m.start()))
    return blocks


def make_trial_id(model: str, model_version: str, lang: str, surface: str, response_text: str) -> str:
    h = hashlib.sha256("\x1f".join([model, model_version, lang, surface, response_text]).encode()).hexdigest()
    return h[:16]


def read_jsonl(path: str | Path) -> list[Trial]:
    trials = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                trials.append(Trial.from_dict(json.loads(line)))
            except (ValueError, TypeError) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e
    _check_unique(trials)
    return trials


def write_jsonl(trials: Iterable[Trial], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for t in trials:
            fh.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")


def iter_cells(trials: Iterable[Trial], keys: tuple[str, ...]) -> Iterator[tuple[tuple, list[Trial]]]:
    groups: dict[tuple, list[Trial]] = {}
    for t in trials:
        groups.setdefault(tuple(getattr(t, k) for k in keys), []).append(t)
    yield from sorted(groups.items())


def _check_unique(trials: list[Trial]) -> None:
    seen = set()
    for t in trials:
        if t.trial_id in seen:
            raise ValueError(f"duplicate trial_id: {t.trial_id}")
        seen.add(t.trial_id)
