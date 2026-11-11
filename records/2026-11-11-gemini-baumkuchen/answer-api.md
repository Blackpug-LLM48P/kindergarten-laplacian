幼稚園のお友だちに読み聞かせるようなスタイルで、**「バウムクーヘン」**を使って極座標（きょくざひょう）のラプラシアンをみちびき出してみましょう！

おうちのひとや先生といっしょに、最後に**Python（パイソン）のまほう**で絵をかいたり、答えあわせをしたりできるようにしてあります。

---

### 1. 「ラプラシアン」ってなあに？
お砂場で、大きなお山をつくったところを想像してみてね。
自分が立っている場所が、まわりの「まえ・うしろ・みぎ・ひだり」と比べて、**どれくらいペコッとへこんでいるかな？（それともポコッと出っぱっているかな？）** を調べる虫めがねのことだよ！

ふつうは、四角いブロックの上をロボットみたいに「たて・よこ」に歩いて調べるんだけど……
もし、みんなが **まるいバウムクーヘン** の上に乗っていたらどうなるかな？

---

### 2. まるい世界の歩きかた（極座標）
まるいバウムクーヘンの上では、場所を２つのルールできめるよ。
1. **$r$（アール）くん**：まんなかの穴から、外に向かって**「何歩あるいたか」**
2. **$\theta$（シータ）ちゃん**：ぐるっと**「どれくらい回ったか」**

---

### 3. どうして不思議なカタチになるの？（導出のひみつ！）
バウムクーヘンを、ひとくちサイズに切ったところを思い浮かべてね！
じつは、四角いケーキとちがって、バウムクーヘンの切れっぱしは**「ちょっと曲がった台形みたいなカタチ」**をしているよね。ここから**３つのひみつ**が見つかるよ！

#### ひみつ①：まえ・うしろのチェック！ $\left( \frac{\partial^2}{\partial r^2} \right)$
まんなかから外へ向かう道は、まっすぐ！
だから「まえ」と「うしろ」を比べるのは、四角いブロックのときとまったくおなじだよ。

#### ひみつ②：外側のほうがちょっと広い！ $\left( + \frac{1}{r}\frac{\partial}{\partial r} \right)$
ひとくちサイズのバウムクーヘンをよく見てみて！
**まんなかに近い「内側のかべ（青）」より、端っこに近い「外側のかべ（赤）」のほうが、なが〜くなっているよね！**
だから、外側のお友だちからの影響が、内側よりもちょっとだけ強くなるんだ。まんなかから離れる（$r$が大きくなる）ほどその差は気にならなくなるから、分数にして $\frac{1}{r}$ のぶんだけオマケを足してあげるよ！

#### ひみつ③：外に行くほど、お隣さんが遠くなる！ $\left( + \frac{1}{r^2}\frac{\partial^2}{\partial \theta^2} \right)$
メリーゴーランドを思い出してね。
まんなかの近くにいるときは、ちょっと回る（$\theta$）だけで、すぐお隣さんにタッチできるよね。
でも、**いちばん外側にいるときは、おなじだけ回っても、お隣さんまでうーんと歩かないといけない！**（距離が $r$ 倍になるよ）。
「みぎ」と「ひだり」で２回ぶん遠くなるから、下（分母）に $r$ を２回かけた $\frac{1}{r^2}$ で小さくわり算してあげるんだ！

---

### 4. 合体！これがバウムクーヘンのラプラシアンだ！
３つのひみつをぜんぶ足すと、おとなの人もびっくりするカッコいい呪文のできあがり！

$$\nabla^2 = \underbrace{\frac{\partial^2}{\partial r^2}}_{\text{①まえ・うしろ}} + \underbrace{\frac{1}{r}\frac{\partial}{\partial r}}_{\text{②外側がひろいオマケ}} + \underbrace{\frac{1}{r^2}\frac{\partial^2}{\partial \theta^2}}_{\text{③よこが遠くなるわり算}}$$

---

### 5. Pythonのまほうで見てみよう！🐍✨

#### まほう①：バウムクーヘンの「ひみつ」を絵にかこう！
このプログラムを動かすと、どうして「②外側がひろい」のかと、「③外に行くとよこが遠い」のかが一目でわかる絵が出てくるよ！

```python
import matplotlib.pyplot as plt
import numpy as np

# まるいキャンバスを用意するよ
fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(6, 6))

# バウムクーヘンの線をかくよ
r_grid = np.linspace(1, 4, 4)
theta_grid = np.linspace(0, 2 * np.pi, 13)

for r in r_grid:
    ax.plot(np.linspace(0, 2 * np.pi, 100), [r] * 100, color='peru', lw=1.5)
for t in theta_grid:
    ax.plot([t, t], [1, 4], color='peru', lw=1.5)

# ひとくちサイズのバウムクーヘンを黄色くぬるよ（r=2〜3, 角度=30度〜60度）
t_piece = np.linspace(np.pi / 6, np.pi / 3, 50)
ax.fill_between(t_piece, 2, 3, color='gold', alpha=0.6, label='ひとくちバウム')

# ひみつ②：内側（青・みじかい）と 外側（赤・ながい！）
ax.plot(t_piece, [2] * 50, color='blue', lw=5, label='うちがわ（みじかい）')
ax.plot(t_piece, [3] * 50, color='red', lw=5, label='そとがわ（ながい！）')

# 見た目をきれいにするよ
ax.set_ylim(0, 4.5)
ax.set_yticklabels([])
ax.set_xticklabels([])
ax.grid(False)
ax.legend(loc='upper right', fontsize=10)
plt.title("バウムクーヘンのひみつ！", fontsize=16)
plt.show()
```
*(※実行すると、黄色いバウムクーヘンの「赤い線」が「青い線」より長いことがはっきり見えます！これが $\frac{1}{r}\frac{\partial}{\partial r}$ が生まれる理由です)*

---

#### まほう②：けいさんロボットに「答えあわせ」をしてもらおう！
おとなの人が紙とエンピツでやると大汗をかく計算も、Pythonの計算ロボット（`sympy`）にたのめば、四角い世界 $(x, y)$ からまるい世界 $(r, \theta)$ へ一瞬で変身させてくれるよ！さっきの「３つのひみつ」と本当に同じになるかな？

```python
import sympy as sp

# ロボットに文字をおしえるよ
r, theta = sp.symbols('r theta', positive=True)
f = sp.Function('f')(r, theta)  # お山のたかさ

# 四角い世界(x, y)と まるい世界(r, theta)のへんしんルール（ヤコビアン計算）
# ロボットが一生懸命「合成関数の微分」をしてくれるよ！
df_dx = (
    sp.cos(theta) * sp.diff(f, r) - (sp.sin(theta) / r) * sp.diff(f, theta)
)  # よこの傾き
df_dy = (
    sp.sin(theta) * sp.diff(f, r) + (sp.cos(theta) / r) * sp.diff(f, theta)
)  # たての傾き

# もう1回傾きをしらべて足す（これが四角い世界のラプラシアン！）
d2f_dx2 = sp.cos(theta) * sp.diff(df_dx, r) - (sp.sin(theta) / r) * sp.diff(
    df_dx, theta
)
d2f_dy2 = sp.sin(theta) * sp.diff(df_dy, r) + (sp.cos(theta) / r) * sp.diff(
    df_dy, theta
)

# ぜんぶ足して、スッキリ整理（simplify）してもらうと…？
laplacian = sp.simplify(d2f_dx2 + d2f_dy2)

print("✨ロボットが計算したこたえ✨")
sp.pprint(laplacian)
```

**ロボットが出してくれるこたえ：**
```text
✨ロボットが計算したこたえ✨
  2                    2          
 ∂                    ∂           
───(f(r, θ))   ∂     ───(f(r, θ)) 
  2            ──(f)   2          
∂r             ∂r    ∂θ           
──────────── + ──── + ────────────
     1          r          2      
                          r       
```
左から順番に、**「①まえ・うしろ」「②外側のオマケ（下に $r$）」「③よこのわり算（下に $r^2$）」** が出てきたね！大せいかい！🎉

---

### おうちのひと・先生向けメモ（種明かし）
このバウムクーヘンのお話は、数学・物理学における**「微小面積要素でのフラックス（流量）の収支（ガウスの発散定理 $\nabla^2 f = \nabla \cdot \nabla f$）」**による厳密な導出そのものを言語化しています。
* 微小バウムクーヘンの面積は $r \, dr \, d\theta$。
* 動径方向の壁の長さ $r \, d\theta$ が $r$ に比例して広がるため、$\frac{1}{r}\frac{\partial}{\partial r}\left(r \frac{\partial f}{\partial r}\right) = \frac{\partial^2 f}{\partial r^2} + \frac{1}{r}\frac{\partial f}{\partial r}$ の第2項（オマケ）が出現します。
* 角度方向の弧長は $r \, d\theta$ なので、微小変化の2階微分で $\frac{1}{(r \, d\theta)^2}$ となり、$\frac{1}{r^2}$ がつきます。