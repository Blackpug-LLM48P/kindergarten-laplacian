"""AI鑑識官v5 予備試験：スクリプト共通の小道具。"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

TOOL_VERSION = "kv5-pilot-0.2"

# rc.3 の29項目
FACES = {
    "S": [f"S{i:02d}" for i in range(1, 11)],
    "C": [f"C{i:02d}" for i in range(1, 7)],
    "R": [f"R{i:02d}" for i in range(1, 7)],
    "E": [f"E{i:02d}" for i in range(1, 8)],
}
ALL_IDS = [i for ids in FACES.values() for i in ids]
FACE_TOTAL = {k: len(v) for k, v in FACES.items()}

CAT_K = {"疑義", "機能", "未検出"}
CAT_U = {"不確定", "未評価", "観測不能"}
CAT_X = {"対象外"}
CATEGORIES = CAT_K | CAT_U | CAT_X


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def sha256_file(path: os.PathLike | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: os.PathLike | str) -> str:
    """UTF-8（BOM可）で読む。改行は変換しない。"""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return f.read()


def read_csv(path: os.PathLike | str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def append_csv(path: os.PathLike | str, row: dict, fieldnames: list[str]) -> None:
    p = Path(path)
    new = not p.exists() or p.stat().st_size == 0
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(row)


def round1(numer: int, denom: int) -> Decimal:
    """100×numer/denom を小数第1位へ四捨五入（0.5は上へ）。丸め前の分数から計算する。"""
    return (Decimal(100) * Decimal(numer) / Decimal(denom)).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )


def write_json(path: os.PathLike | str, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
        f.write("\n")


def split_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in re.split(r"[;；]", value) if v.strip()]
