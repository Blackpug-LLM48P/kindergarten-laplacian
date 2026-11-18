"""Check the unmodified line between the numbered headings of the supplied answer."""

from hashlib import sha256
from pathlib import Path
import re


root = Path(__file__).resolve().parents[1]
answer = (root / "palindrome-answer-original.txt").read_text(encoding="utf-8")
lines = answer.splitlines()
begin = lines.index("1. ひらがな500文字（完全回文）") + 1
end = lines.index("2. 読み下し文（漢字かな交じり）")
(text,) = lines[begin:end]

n = len(text)
hiragana = sum("ぁ" <= char <= "ゖ" for char in text)
mismatches = sum(text[i] != text[-1-i] for i in range(n // 2))
print("Unicode code points:", n)
print("Hiragana code points:", hiragana)
print("Equals reverse:", text == text[::-1])
print("Compared symmetric pairs:", n // 2)
print("Mismatched pairs:", mismatches)
print("Characters 250 and 251:", text[249:251])
print("SHA-256 (UTF-8, no trailing newline):", sha256(text.encode("utf-8")).hexdigest())
assert n == hiragana == 500
assert text == text[::-1] and mismatches == 0
assert text[249:251] == "よよ"

# Validate the five examples as printed, including their positions in the payload.
examples = re.findall(r"「([ぁ-ゖ]+)（[^）]*）」⇄「([ぁ-ゖ]+)（[^）]*）」", answer)
assert len(examples) == 5
for left, right in examples:
    start = text.index(left, 0, n // 2)
    mirrored_start = n - start - len(left)
    assert right == left[::-1] == text[mirrored_start:mirrored_start + len(left)]
    print(f"{left} <-> {right}: positions {start+1} and {mirrored_start+1}")
print("PASS")
