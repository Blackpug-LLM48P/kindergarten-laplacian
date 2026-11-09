import re
units = """たけやぶやけた
わたしまけましたわ
だんすがすんだ
よのなかねかおかおかねかなのよ
たいやきやいた
にわのわに
るすになにする
かるいきびんなこねこなんびきいるか
なかきよのとおのねふりのみなめさめなみのりふねのおとのよきかな
いかたべたかい
まさかさかさま
よるにんじんにるよ
かんけいないけんか
ねつきいいきつね
わるいにわとりとわにいるわ
しなもんぱんもれもんぱんもなし
にしがひがしに
このこどこのこ
みがかぬかがみ
なつまでまつな
いろしろい
だんながなんだ
たしかにかした
しんぶんし
たぶんぶた
くいにいく
たいがいた
ぞうくんぱんくうぞ
よくきくよ
こねこ
とまと
やおや
きつつき""".split()
for u in units:
    assert u == u[::-1], u
    assert re.fullmatch(r'[ぁ-ん]+', u), u
assert len(set(units)) == len(units)
# 順序を保ったまま合計250文字になる部分列を選ぶ（なるべく多くの単位を使う）
best = {0: []}
for i, u in enumerate(units):
    new = dict(best)
    for s, idx in best.items():
        t = s + len(u)
        if t <= 250 and (t not in new or len(new[t]) < len(idx) + 1):
            new[t] = idx + [i]
    best = new
half = [units[i] for i in best[250]]
S = ''.join(half)
T = S + S[::-1]
assert len(S) == 250 and len(T) == 500
assert T == T[::-1]
assert re.fullmatch(r'[ぁ-ん]{500}', T)
print(T)
print('len', len(T), 'reverse_equal', T == T[::-1], 'units_in_half', len(half))
print(' / '.join(half))
print('unused:', [u for u in units if u not in half])
open('palindrome.txt', 'w').write(T + '\n')
