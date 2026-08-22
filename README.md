# 幼稚園児にもわかる極座標ラプラシアン 🌀

「極座標のラプラシアン、どうして急に `1/r` が生えるの？」

その疑問を、数式を隠さず、できるだけやさしく解説する小さな教材です。Pythonによる数値検算も付いています。

## 結論

直交座標では

```math
\nabla^2 f=
\frac{\partial^2 f}{\partial x^2}
+\frac{\partial^2 f}{\partial y^2}
```

極座標 `(r,\theta)` では

```math
\boxed{
\nabla^2 f=
\frac{\partial^2 f}{\partial r^2}
+\frac{1}{r}\frac{\partial f}{\partial r}
+\frac{1}{r^2}\frac{\partial^2 f}{\partial\theta^2}
}
```

になります。

## まずイメージ

円の中心近くで少し回るのと、外側で同じ角度だけ回るのでは、実際に進む距離が違います。半径 `r` の場所で角度を `d\theta` だけ進む距離は

```math
r\,d\theta
```

です。外側ほど円周も、細い扇形の面積も大きくなります。極座標では「ものさしの長さ」が場所によって変わる。この補正が `1/r` と `1/r^2` の正体です。

## 導出

極座標では

```math
x=r\cos\theta,\qquad y=r\sin\theta
```

スカラー場 `f` の勾配は

```math
\nabla f=
\mathbf e_r\frac{\partial f}{\partial r}
+\mathbf e_\theta\frac{1}{r}\frac{\partial f}{\partial\theta}
```

です。また、ベクトル場 `\mathbf A=A_r\mathbf e_r+A_\theta\mathbf e_\theta` の発散は

```math
\nabla\cdot\mathbf A=
\frac{1}{r}\frac{\partial}{\partial r}(rA_r)
+\frac{1}{r}\frac{\partial A_\theta}{\partial\theta}
```

です。`\mathbf A=\nabla f` を代入すると、

```math
\nabla^2f=
\frac{1}{r}\frac{\partial}{\partial r}
\left(r\frac{\partial f}{\partial r}\right)
+\frac{1}{r^2}\frac{\partial^2f}{\partial\theta^2}
```

積の微分を展開して、

```math
\nabla^2f=
\frac{\partial^2f}{\partial r^2}
+\frac{1}{r}\frac{\partial f}{\partial r}
+\frac{1}{r^2}\frac{\partial^2f}{\partial\theta^2}
```

が得られます。

## いちばん簡単な検算

`f(x,y)=x^2+y^2=r^2` とします。

直交座標：

```math
\nabla^2f=2+2=4
```

極座標：

```math
\frac{\partial^2(r^2)}{\partial r^2}
+\frac1r\frac{\partial(r^2)}{\partial r}
+\frac1{r^2}\frac{\partial^2(r^2)}{\partial\theta^2}
=2+2+0=4
```

両方とも4になりました。

## Pythonで数値検算

```bash
pip install -r requirements.txt
python polar_laplacian.py
```

`f(r,\theta)=r^2\cos(2\theta)` の極座標ラプラシアンを有限差分で計算します。この関数は `x^2-y^2` と同じなので、理論値は0です。

## 原点の注意

式には `1/r` があるため、`r=0` では極座標表示が特異になります。これは座標の問題であり、関数そのものが必ず壊れているという意味ではありません。コードでは原点を避けて計算します。

## License

MIT License

制作：黒パグ 🐾
