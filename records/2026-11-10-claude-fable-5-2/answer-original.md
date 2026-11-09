**こたえ**

$$\Delta f=\frac{1}{r}\frac{\partial}{\partial r}\!\left(r\frac{\partial f}{\partial r}\right)+\frac{1}{r^2}\frac{\partial^2 f}{\partial\theta^2}$$

**ようちえんばん**

1. ラプラシアンは「じぶんのへやに、まわりからあったかさがどれだけ入ってくるか」をかぞえるもの。
2. まるいせかいのへやは、バームクーヘンのひときれ。そとのかべは長くて、うちのかべはみじかい。
3. あったかさの出入りは「かべの長さ × さかのきつさ」。かべが長いほど、たくさんとおる。
4. ぜんぶのかべの出入りを足して、へやの広さでわる。おしまい。

**おとなばん(同じことを式で)**

へやは $r\sim r+dr$、$\theta\sim\theta+d\theta$ の一切れで、広さは $r\,dr\,d\theta$。

- **そと・うちのかべ**: 長さ $r\,d\theta$、さかは $\partial f/\partial r$。そとから入る分とうちから出る分の差は
 $\dfrac{\partial}{\partial r}\!\left(r\dfrac{\partial f}{\partial r}\right)dr\,d\theta$
 かべの長さ $r$ が微分の中に入るのが、$1/r$ の項が出てくる理由です。
- **よこのかべ**: 長さ $dr$。角度が $d\theta$ 進んでも歩く距離は $r\,d\theta$ なので、さかは $\dfrac{1}{r}\dfrac{\partial f}{\partial\theta}$。差は
 $\dfrac{1}{r}\dfrac{\partial^2 f}{\partial\theta^2}\,d\theta\,dr$

足して広さ $r\,dr\,d\theta$ でわると、上の式になります。

**けんざん**

sympyで $x^3y-2xy^2+x^2$、$e^x\sin y$、$xe^{-(x^2+y^2)}$、$\log(x^2+y^2)$ の4つについて、$f_{xx}+f_{yy}$ と極座標の式の差を計算し、すべて 0 になりました。

幼稚園児に本当に通じるのは1〜4までで、式の部分は「かべが長いとたくさんとおる」の言いかえです。
