"""辞書ベースの比喩カテゴリ抽出（ja / en）。

散文部分（数式・コードを除く）だけを走査する。辞書は lexicon/{ja,en}.yaml。
英語応答に日本語の語が混ざることもあるため、既定では両言語の辞書を合わせて使う。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from .textspans import Span, prose_text, segment

LEXICON_DIR = Path(__file__).parent / "lexicon"
NONE = "none"


@dataclass(frozen=True)
class Lexicon:
    version: str
    # (category, group, compiled pattern, literal length)
    entries: tuple


@lru_cache(maxsize=None)
def load_lexicon(langs: tuple[str, ...] = ("ja", "en"), lexicon_dir: str | None = None) -> Lexicon:
    base = Path(lexicon_dir) if lexicon_dir else LEXICON_DIR
    entries = []
    versions = []
    for lang in langs:
        data = yaml.safe_load((base / f"{lang}.yaml").read_text(encoding="utf-8"))
        versions.append(f"{lang}:{data['version']}")
        for cat, spec in data["categories"].items():
            for term in spec["terms"]:
                if lang == "en":
                    words = r"\s+".join(re.escape(w) for w in term.split())
                    pat = re.compile(rf"(?<![A-Za-z]){words}(?:e?s)?(?![A-Za-z])", re.I)
                else:
                    pat = re.compile(re.escape(term))
                entries.append((cat, spec.get("group", cat), pat, len(term)))
    return Lexicon(";".join(versions), tuple(entries))


def category_groups(lexicon: Lexicon | None = None) -> dict[str, str]:
    lexicon = lexicon or load_lexicon()
    return {cat: grp for cat, grp, _, _ in lexicon.entries}


@dataclass
class MetaphorFeatures:
    lexicon_version: str
    metaphor_primary: str = NONE
    metaphor_primary_group: str = NONE
    metaphor_count: int = 0  # 出現したカテゴリ数
    metaphor_hits_total: int = 0
    metaphor_first_pos: float | None = None
    metaphor_categories: list[str] = field(default_factory=list)  # 初出順
    metaphor_offsets: list[int] = field(default_factory=list)


def find_hits(text: str, lexicon: Lexicon) -> list[tuple[int, int, str, str]]:
    """(start, end, category, group)。重なりは長い語を優先して解消する。"""
    raw = []
    for cat, grp, pat, _ in lexicon.entries:
        for m in pat.finditer(text):
            raw.append((m.start(), m.end(), cat, grp))
    kept: list[tuple[int, int, str, str]] = []
    for h in sorted(raw, key=lambda h: -(h[1] - h[0])):
        if all(h[1] <= k[0] or h[0] >= k[1] for k in kept):
            kept.append(h)
    return sorted(kept)


def metaphor_features(text: str, spans: list[Span] | None = None, lexicon: Lexicon | None = None) -> MetaphorFeatures:
    lexicon = lexicon or load_lexicon()
    spans = spans if spans is not None else segment(text)
    hits = find_hits(prose_text(text, spans, keep_inline_code=False), lexicon)
    feats = MetaphorFeatures(lexicon_version=lexicon.version)
    if not hits:
        return feats
    order: list[str] = []
    for _, _, cat, _ in hits:
        if cat not in order:
            order.append(cat)
    feats.metaphor_primary = hits[0][2]
    feats.metaphor_primary_group = hits[0][3]
    feats.metaphor_count = len(order)
    feats.metaphor_hits_total = len(hits)
    feats.metaphor_first_pos = hits[0][0] / max(len(text), 1)
    feats.metaphor_categories = order
    feats.metaphor_offsets = [h[0] for h in hits]
    return feats
