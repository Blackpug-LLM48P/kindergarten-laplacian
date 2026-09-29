"""応答本文を「散文 / 数式 / コード」の区間に分ける共通処理。

各特徴量抽出器はここで得た区間を使い、同じ本文を別々の正規表現で切り分けない。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 順序が重要: 長い区切りを先に試す
_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})([^\n`]*)\n(.*?)^[ \t]*\1[ \t]*$", re.M | re.S)
_MATH_PATTERNS = [
    re.compile(r"\$\$(.+?)\$\$", re.S),
    re.compile(r"\\\[(.+?)\\\]", re.S),
    re.compile(r"\\begin\{(equation|aligned|align|gather|eqnarray|multline)\*?\}(.+?)\\end\{\1\*?\}", re.S),
    re.compile(r"\\\((.+?)\\\)", re.S),
    re.compile(r"(?<![\\$])\$(?!\$)([^$\n]+?)(?<!\\)\$(?!\$)"),
]
_INLINE_CODE = re.compile(r"`([^`\n]+)`")


@dataclass
class Span:
    kind: str  # "math" | "code" | "prose" | "inline_code"
    start: int
    end: int
    text: str  # 区切り記号を除いた中身
    lang: str = ""
    inferred: bool = False  # 区切り記号なしで推定した区間（アプリからのコピーで $$ や ``` が消えた本文）


def segment(text: str) -> list[Span]:
    """本文を重なりのない区間列に分ける（開始位置順）。"""
    taken: list[tuple[int, int]] = []
    spans: list[Span] = []

    def free(a: int, b: int) -> bool:
        return all(b <= s or a >= e for s, e in taken)

    for m in _FENCE.finditer(text):
        lang = (m.group(2).strip().split() or [""])[0].lower()
        kind = "math" if lang in ("math", "latex", "tex") else "code"
        spans.append(Span(kind, m.start(), m.end(), m.group(3), lang))
        taken.append((m.start(), m.end()))

    for pat in _MATH_PATTERNS:
        for m in pat.finditer(text):
            if free(m.start(), m.end()):
                body = m.group(m.lastindex)
                spans.append(Span("math", m.start(), m.end(), body))
                taken.append((m.start(), m.end()))

    for m in _INLINE_CODE.finditer(text):
        if free(m.start(), m.end()):
            spans.append(Span("inline_code", m.start(), m.end(), m.group(1)))
            taken.append((m.start(), m.end()))

    # 区切り記号が失われた段落（空行区切り）を、コード → 数式の順に推定する
    for m in _PARAGRAPH.finditer(text):
        a, b = m.start(), m.end()
        if not free(a, b):
            continue
        para = m.group(0)
        if _looks_like_python(para):
            spans.append(Span("code", a, b, para, "python", inferred=True))
            taken.append((a, b))
        elif _looks_like_latex(para):
            spans.append(Span("math", a, b, para, inferred=True))
            taken.append((a, b))

    taken.sort()
    pos = 0
    for s, e in taken:
        if s > pos:
            spans.append(Span("prose", pos, s, text[pos:s]))
        pos = max(pos, e)
    if pos < len(text):
        spans.append(Span("prose", pos, len(text), text[pos:]))
    spans.sort(key=lambda sp: sp.start)
    return spans


_PARAGRAPH = re.compile(r"(?:^[^\S\n]*\S[^\n]*(?:\n|$))+", re.M)
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff01-\uff5e、。]")
_PY_START = re.compile(r"^(?:def |class |import |from \S+ import |for |while |with |@|print\()")
_PY_LINE = re.compile(r"^(?:\s+\S|#|\)|\]|(?:def|class|import|from|for|while|with|if|elif|else|try|except|return|print)\b"
                      r"|[A-Za-z_][\w.\[\], ]*\s*(?:=|\+=|-=|\())")
_TEX_CMD = re.compile(r"\\[A-Za-z]+")


def _looks_like_python(para: str) -> bool:
    lines = [ln for ln in para.splitlines() if ln.strip()]
    if not lines or not _PY_START.match(lines[0]):
        return False
    for ln in lines:
        code_part = ln.split("#", 1)[0]
        code_part = re.sub(r"(['\"]).*?\1", "", code_part)
        if _CJK.search(code_part) or not _PY_LINE.match(ln):
            return False
    return True


def _looks_like_latex(para: str) -> bool:
    """\\text{...} の中身を除いて日本語がなく、LaTeX の制御語を含み、英文でもない段落。"""
    body = re.sub(r"\\(?:text|textrm|mathrm|mbox)\s*\{[^{}]*\}", " ", para)
    if _CJK.search(body) or not _TEX_CMD.search(body):
        return False
    words = re.findall(r"(?<![\\A-Za-z])[A-Za-z]{3,}(?![A-Za-z])", _TEX_CMD.sub(" ", body))
    return len(words) < 3


def prose_text(text: str, spans: list[Span] | None = None, keep_inline_code: bool = True) -> str:
    """数式・コードを空白に置き換えた本文（文字オフセットは元の本文と一致）。"""
    spans = spans if spans is not None else segment(text)
    out = list(text)
    for sp in spans:
        if sp.kind == "prose" or (keep_inline_code and sp.kind == "inline_code"):
            continue
        for i in range(sp.start, sp.end):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)
