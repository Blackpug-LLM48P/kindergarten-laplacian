"""Recheck the palindrome text in the saved answer. Standard library only."""
from hashlib import sha256
from pathlib import Path

root = Path(__file__).resolve().parent.parent
answer = (root / "palindrome-answer-original.md").read_text(encoding="utf-8")
fence = "\x60\x60\x60"
assert answer.count(fence) == 2
payload = answer.split(fence + "\n", 1)[1].split("\n" + fence, 1)[0]
assert len(payload) == 500, len(payload)
assert "\n" not in payload
assert all("ぁ" <= char <= "ゖ" for char in payload)
assert payload == payload[::-1]
assert payload[250:] == payload[:250][::-1]
print(f"length: {len(payload)} Unicode code points")
print(f"mismatched symmetric pairs: {sum(payload[i] != payload[-i-1] for i in range(250))}")
print("hiragana only: True")
print("halves mirrored: True")
print(f"SHA-256 (UTF-8, no trailing newline): {sha256(payload.encode('utf-8')).hexdigest()}")
print("PASS")
