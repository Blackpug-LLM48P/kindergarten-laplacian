"""構造特徴量と「5歳児制約」の代理指標。

- 文字数・見出し数・ステップ数・数式ブロック数
- セクション種別の系列（metaphor → derivation → code → summary …）をタグ列で保存
- 比喩より先に専門用語が出るか、平均文長、記号密度
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .textspans import Span, prose_text, segment

SECTION_TAGS = ("intro", "metaphor", "derivation", "code", "verification", "caveat", "summary", "question", "other")

_HEADING = re.compile(r"^(#{1,6})\s+\S|^\*\*[^*\n]{1,60}\*\*\s*$|^[0-9０-９]+[.)．]\s*\*\*", re.M)
# 区切り線（コピーで Markdown の --- が ⸻ になることがある）もセクション境界にする
_RULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,}|⸻+|—{2,})\s*$", re.M)
_STEP = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*(?:ステップ|手順|Step|STEP|step)\s*[0-9０-９①-⑩]+"
    r"|^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*[0-9０-９]+[.)．]\s+\S"
    r"|^\s*(?:#{1,6}\s*)?[①-⑩]",
    re.M,
)

JARGON = {
    "ja": ["偏微分", "連鎖律", "合成関数の微分", "ヤコビ", "発散", "勾配", "二階微分", "2階微分"],
    "en": ["partial derivative", "chain rule", "jacobian", "divergence", "gradient", "second derivative"],
}
_JARGON_SYMBOL = re.compile(r"∂|\\partial|\\nabla|∇")

_KEYWORDS = {
    "summary": r"まとめ|要約|結論|おさらい|summary|in short|recap|conclusion|tl;?dr|覚えて帰",
    "verification": r"検算|検証|確認|確かめ|一致|チェック|verify|verification|check|sanity|numerical|numerically|agree",
    "caveat": r"原点|注意|特異|r\s*=\s*0|caveat|singular|origin|careful|note",
    "question": r"[?？]\s*$",
    "metaphor": None,  # 比喩辞書でヒットした場合
    "derivation": r"導出|連鎖律|偏微分|代入|展開|derive|derivation|chain rule|substitut|expand",
}


@dataclass
class StructureFeatures:
    n_chars: int
    n_headings: int
    n_steps: int
    n_math_blocks: int
    n_inline_math: int
    n_code_blocks: int
    section_tags: list[str] = field(default_factory=list)
    section_sequence: str = ""
    jargon_first_pos: float | None = None
    jargon_before_metaphor: bool | None = None
    avg_sentence_len: float = 0.0
    symbol_density: float = 0.0


def _sections(text: str) -> list[tuple[int, int, str]]:
    """見出し位置で本文を区切る。見出しがなければ全体を 1 区間とする（前置き部も 1 区間）。"""
    starts = sorted({m.start() for m in _HEADING.finditer(text)} | {m.end() for m in _RULE.finditer(text)})
    if not starts or starts[0] != 0:
        starts = [0] + starts
    bounds = starts + [len(text)]
    return [(a, b, text[a:b]) for a, b in zip(bounds, bounds[1:]) if text[a:b].strip()]


def _tag_section(sec_text: str, spans_in: list[Span], metaphor_hits: int, is_first: bool) -> str:
    first = sec_text.lstrip("\n").splitlines()[0] if sec_text.strip() else ""
    # 見出しに明示されていればそれを優先（見出しのない前置き部の 1 行目は見出し扱いしない）
    if _HEADING.match(first):
        for tag in ("summary", "verification", "caveat", "derivation"):
            if re.search(_KEYWORDS[tag], first, re.I):
                return tag
    elif is_first and not any(s.kind == "code" for s in spans_in):
        return "intro"
    if any(s.kind == "code" for s in spans_in):
        return "code"
    math_chars = sum(len(s.text) for s in spans_in if s.kind == "math")
    total = max(len(sec_text), 1)
    if metaphor_hits and math_chars / total < 0.25:
        return "metaphor"
    if math_chars / total >= 0.25 or re.search(_KEYWORDS["derivation"], sec_text, re.I):
        return "derivation"
    # 末尾が読者への問いかけで終わる節は、「確認」等の語を含んでも question
    if re.search(_KEYWORDS["question"], sec_text.strip(), re.I):
        return "question"
    if re.search(_KEYWORDS["verification"], sec_text, re.I):
        return "verification"
    if is_first:
        return "intro"
    return "other"


def _is_block(text: str, s: Span) -> bool:
    if s.inferred:
        return True
    head = text[s.start : s.start + 6].lstrip()
    return head.startswith(("$$", "\\[", "\\begin", "```", "~~~"))


def _sentences(prose: str) -> list[str]:
    parts = re.split(r"[。．！？!?\n]+|(?<=[a-z0-9)])\.\s+", prose)
    return [p.strip() for p in parts if len(p.strip()) >= 2 and not re.fullmatch(r"[\s#*|\-:>]+", p.strip())]


def structure_features(text: str, lang: str, metaphor_offsets: list[int] | None = None,
                       spans: list[Span] | None = None) -> StructureFeatures:
    spans = spans if spans is not None else segment(text)
    metaphor_offsets = sorted(metaphor_offsets or [])
    n = max(len(text), 1)

    tags = []
    for i, (a, b, sec) in enumerate(_sections(text)):
        inside = [s for s in spans if a <= s.start < b]
        hits = sum(1 for o in metaphor_offsets if a <= o < b)
        tags.append(_tag_section(sec, inside, hits, i == 0))
    collapsed = [t for i, t in enumerate(tags) if i == 0 or t != tags[i - 1]]

    prose = prose_text(text, spans, keep_inline_code=False)
    lowered = prose.lower()
    jpos = [lowered.find(w.lower()) for w in JARGON.get(lang, []) + JARGON["en"]]
    jpos = [p for p in jpos if p >= 0]
    sm = _JARGON_SYMBOL.search(text)
    if sm:
        jpos.append(sm.start())
    jfirst = min(jpos) if jpos else None
    if jfirst is None:
        before = False if metaphor_offsets else None
    elif not metaphor_offsets:
        before = True
    else:
        before = jfirst < metaphor_offsets[0]

    sents = _sentences(prose)
    avg = sum(len(s) for s in sents) / len(sents) if sents else 0.0
    math_chars = sum(len(s.text) for s in spans if s.kind == "math")
    sym_chars = len(re.findall(r"[∂∇θ²³=+^_\\/∫Σ√]", prose))

    return StructureFeatures(
        n_chars=len(text),
        n_headings=len(_HEADING.findall(text)),
        n_steps=len(_STEP.findall(text)),
        n_math_blocks=sum(1 for s in spans if s.kind == "math" and _is_block(text, s)),
        n_inline_math=sum(1 for s in spans if s.kind == "math" and not _is_block(text, s)),
        n_code_blocks=sum(1 for s in spans if s.kind == "code"),
        section_tags=collapsed,
        section_sequence=">".join(collapsed),
        jargon_first_pos=(jfirst / n) if jfirst is not None else None,
        jargon_before_metaphor=before,
        avg_sentence_len=round(avg, 2),
        symbol_density=round((math_chars + sym_chars) / n, 4),
    )
