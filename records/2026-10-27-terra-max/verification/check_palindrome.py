"""Recheck the actual text in the saved original response."""
from hashlib import sha256
from pathlib import Path

root = Path(__file__).resolve().parent.parent
answer = (root / "palindrome-answer-original.txt").read_text(encoding="utf-8")
prefix = "\x60\x60\x60text\n"
suffix = "\n\x60\x60\x60"
assert answer.count(prefix) == 1
payload = answer.split(prefix, 1)[1].split(suffix, 1)[0]
expected_hash = "0b64b24dcc19e42bf73dc153a6aa51425ef592ccb5605f5485f69fa93042a868"
digest = sha256(payload.encode("utf-8")).hexdigest()
assert len(payload) == 500, len(payload)
assert "\n" not in payload
assert all("\u3041" <= char <= "\u3096" for char in payload)
assert payload == payload[::-1]
assert payload[250:] == payload[:250][::-1]
assert digest == expected_hash, digest
print(f"length: {len(payload)} Unicode code points")
print(f"mismatched symmetric pairs: {sum(payload[i] != payload[-i-1] for i in range(250))}")
print("hiragana only: True")
print("halves mirrored: True")
print(f"SHA-256 (UTF-8, no trailing newline): {digest}")
print("PASS")
