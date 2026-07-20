# F-078 奏法検出 — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #73 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
detect_techniques(times, f0_hz) の実装は「cent領域での連続軌跡ルールベース分類」に一本化する（機械学習は新規重依存禁止のため不採用。TENTもbend以外はルールで実装しており妥当）。

前処理: (1) f0_hz を cents = 1200*log2(f0/ref) に変換（ref は各有声区間の中央値 or 440基準どちらでも可、区間内相対で扱う）。(2) NaN(無声)を区間境界とし、np.isnanで連続有声セグメントに分割。TENT準拠で0.1秒未満のセグメントはノイズ扱いで破棄。(3) 各セグメント内で軽く平滑化（移動中央値 or サイズ3-5のmedian filter）してからトレンド抽出。numpyのみで実装（scipyなくてもnp.convolve/np.diffで足りる）。

セグメント内トレンド抽出: np.diff(cents)/np.diff(times) で瞬時傾き(cents/sec)を出し、符号を+1/-1/0にラベル付け（TENTの α*pattern_slope 閾値方式=微小変動を0に潰す）。極大/極小で区分（pattern化）。

各kindの判定ルール（全てcents単位・閾値は定数化）:
- vibrato: セグメント内で「昇降が交互に4回以上(TENTは>3セグメント)」かつ変調の深さ(peak-to-peak)が概ね50-250cents、変調周波数が4-8Hz。ゼロ交差数/(区間長)でrate推定、np.fft.rfft(cents-mean)のピーク周波数で検証すると堅牢。周期性が4-8Hzバンド内・extent>=~30-50centsをvibratoとする。
- bend/slide(連続グライド): 単調(ほぼ一方向)に概ね半音(100cents)以上、最大でも全音〜3.5半音程度まで連続上昇/下降するアーク。上行/下行で kind は共通("bend"寄りとするか"slide"寄りは区別が曖昧—後述)。傾きの符号でascending/descendingを confidence/属性に反映。TENT: >3.5半音は"long"、0.2秒超のなだらかも長bend扱い。急峻さ(cents/sec)が高くグライド途中に定常部を挟まないものをslide、到達後に保持(定常)するものをbendと弱く区別。
- hammer_on/pull_off(急峻レガート跳躍): 隣接有声セグメント境界で、無声(再アタック)を挟まず、100〜約350cents(1〜3半音、TENTの3.5半音=人手/弦張力の物理限界)の階段状ジャンプが1-2フレーム(~10-30ms)で起きるもの。上行=hammer_on、下行=pull_off。連続グライド(bend/slide)との差は「遷移が離散的で中間ピッチを通過しない(数フレームで完了)」点。

Technique(frozen dataclass: kind:str, onset_sec:float, offset_sec:float, confidence:float) を各検出につき生成しlistで返す。confidenceは各ルールのマージン(閾値超過量を正規化)で算出し捏造しない。全区間NaN/短すぎ/無検出なら空listを返す(要件「拾えないものは正直に」)。

閾値定数(モジュール先頭にUPPER_SNAKE_CASE): CENTS_PER_SEMITONE=100, GLIDE_MIN_CENTS≈80-100, LEAP_MAX_CENTS≈350(3.5半音), VIBRATO_RATE_HZ=(4,8), VIBRATO_MIN_EXTENT_CENTS≈40-50, VIBRATO_MIN_CYCLES=3-4, MIN_SEG_SEC=0.1, TREND_ALPHA=0.05, LEAP_MAX_DUR_SEC≈0.03。

テスト(AAA/pytest): 合成f0で各kindを1本ずつ用意 — 直線ランプ(bend/slide)、正弦変調(vibrato: 6Hz,80cents)、階段ジャンプ(hammer/pull)、定常音(何も出ない)、NaN区間で分割される2音、空配列。各々でkind/上行下行/区間境界/confidence範囲(0-1)を検証。実装後 .venv/bin/python -m pytest <新規テスト> -q -p no:cacheprovider を実行し緑を確認。numpy 2.4.6・Python venvで動作確認済み。

## 落とし穴・失敗例(pitfalls)
1) bend と slide の音響的区別は原理的に困難（最重要限界）。TENTでもSlideのF-scoreは0.388で「SlideはBend/Releaseと容易に混同」と明記。連続グライドという同じピッチ軌跡を生むため、f0のみからの分離は信頼できない。実装では無理に断定せず、glide到達後の定常保持有無という弱シグナルで区別しつつ confidence を低めに出すか、要件が許すなら上行/下行の別で寄せる。過信して「slide確定」と言わない。

2) hammer-on/pull-off が bend/vibrato に誤分類される。TENTで「hammer-onがbendに誤判定され誤ってノート結合が起きる」と報告。境界の1-2フレームの跳躍を、平滑化しすぎると連続グライドに見え、平滑化しなさすぎるとf0推定ノイズを跳躍と誤検出する。平滑化窓とLEAP_MAX_DUR_SECのバランスが肝。

3) f0推定のオクターブエラー・倍音跳び。f0_hzに±1200centsのスパイクが混入すると偽のhammer/pull/大bendを生む。NaNだけでなく非現実的ジャンプ(>~700cents瞬間)は無効化 or セグメント境界扱いにするガードが必要。TENT/NIME論文とも「melody抽出誤差・pitch contourノイズへの感度」を限界に挙げる。

4) vibratoの誤検出。ゆっくりした意図的ピッチ変化や連続ビブラート付きロングトーンで、周波数バンド(4-8Hz)や交互回数の閾値が甘いとfalse positive。逆にrateが速い/depthが浅いと取りこぼす。FFT/ゼロ交差の両方で交差検証し、extentとrateの両条件ANDにする。単一cycleでvibrato宣言しない(最低3-4 half-cycle)。

5) NaN(無声)の扱い。np.isnan境界で分割は正しいが、区間内にポツポツ入る単発NaN(推定欠損)まで境界にすると過分割。短いNaNギャップは補間 or 無視し、一定長以上のNaNのみ真の境界とする閾値を設ける。QuantizedNoteのdocstringにある通りNaN==NaNは常にFalseなので比較で使わずnp.isnanを使う。

6) cents変換のゼロ/負値。f0_hz<=0やNaNをlog2に渡すとinf/nan伝播。変換前に有声マスクを取る。ref周波数を固定440にすると低音(ベース)で相対閾値の意味がずれるので区間相対中央値基準が無難だが、区間全体が単調グライドだと中央値基準がずれる—glide判定は絶対cents差(diffの累積)で行い中央値正規化に依存しないこと。

7) 時間軸の非等間隔・単位。timesが等間隔前提のコードにすると壊れる。傾きは必ずnp.diff(f0)/np.diff(times)で実時間微分する。offset_secはセグメント終端の実times値を使い、フレーム番号×hop等の推測値を使わない。

8) 境界条件: 空配列/全NaN/1サンプル/全区間短すぎ→空list返す。例外を投げず正直に空を返す（要件「動くと推測で言わない・拾えないものは拾えない」）。ベース(低周波f0)は推定が不安定で技法検出はギターより信頼低い旨をdocstringに限界として明記。

9) 「56.5%」問題: 完全な多クラス分類の実精度は先行研究でも56.5%程度(NIME/Springer)。堅牢=高精度ではない。confidenceを正直に低く出し、テストは合成理想信号で通す一方、docstringに「実録音では混同が多い」限界を明記して過大評価を防ぐ。

## 参考(prior_art)
中心的先行研究（実在確認済み）:

[EN] TENT: Technique-Embedded Note Tracking for Real-World Guitar Solo Recordings (TISMIR, transactions.ismir.net/articles/10.5334/tismir.23)。本機能の設計骨子。要点: f0/melody契約を「隣接フレームの周波数差>0.5半音で分割」してsub-melodyを作る/0.1秒未満は破棄/局所極大極小でpattern化(0.045秒未満除外)/傾き=両端周波数差の絶対値÷長さ/トレンドラベルはα×pattern_slope(既定α=0.05)超で±1。Vibrato=「sub-melody内で交互昇降が3セグメント超」+最小extent β1=0.3半音。Bend/Slideの長短境界=3.5半音(または0.2秒超のなだらか)。hammer-on/pull-off候補=隣接sub-melody間で3.5半音未満の遷移点(3.5半音は「人手サイズと弦張力の物理限界」由来)。Bendのみ短尺はCNN、Vibrato/Slideはルール。失敗例: SlideのF=0.388でBend/Releaseと混同、hammer-onがbendに誤判定されノート誤結合、melody抽出誤差への感度。

[EN] Electric Guitar Playing Technique Detection (ISMIR 2015, archives.ismir.net/ismir2015/paper/000119.pdf)。ピッチ軌跡の形状分類: bend=弧状/ねじれ、vibrato=正弦、slide=階段状の上行/下行、hammer-on/pull-off=F0の異なる2本の平行水平線(=急なF0段差)。bend/slide/vibratoは急激な周波数変化を伴わずsub-melody内で捉えられ傾きで識別、hammer/pullは急なF0変化で区別、という本仕様と一致する分類指針。

[EN] Reboursière et al., Left and right-hand guitar playing techniques detection (NIME 2012, nime.org/proceedings/2012/nime2012_213.pdf)。hammer/pull検出特徴=遷移の半音数、および「maximal relative pitch slope=連続10msフレーム間の最大ピッチ差÷開放弦ピッチ」。再アタックが無い(エネルギーオンセット無し)音は前ノートからのピッチ変化方向でhammer(上行)/pull(下行)にフラグ。spectral fluxでpull-off recall 88.0%(hammer-on 97.9%より低い=pull-offが難しい実証)。

[EN] Essentia std::Vibrato (essentia.upf.edu)。vibrato既定パラメータの実運用値: minFrequency=4Hz, maxFrequency=8Hz, minExtend=50cents, maxExtend=250cents, sampleRate=344.531（PitchMelodia出力の分析レートに対応）。vibrato不在フレームは出力0。→ VIBRATO_RATE_HZ=(4,8)/extent閾値の根拠に採用。

[EN] 一般的vibrato分析知見: 健全なvibratoは概ね4-8Hz・30-80cents深さ。周期性はF0軌跡(DC除去後)へのautocorrelationまたはFFTで測る。autocorrelationはFourierより急激なピッチ変化・vibratoでアーティファクトが少ない。→ ゼロ交差+FFT併用の交差検証方針の裏付け。

[EN] Playing Technique Detection by Fusing Note Onset (ISMIR 2022) / MERTech (arxiv 2310.09853) — 学習ベース。今回は重依存追加禁止のため不採用だが、ルールが不足する将来拡張の参照先。

[ZH] 中文技法定義（zhihu/feifanjita 等）で軌跡の物理的裏付けを確認: 推弦(bend)=半音/全音上げ, 滑音(slide)=同弦上を指がスライド・上行下行あり, 揉弦(vibrato)=弦を左右/上下に揺らしtensionを微変動させ波打つ効果, 击弦(hammer-on)=右手撥弦後に左手で高フレット打弦し高音を出す。→ vibratoが「tension微変動=浅い周期変調」、hammer/pullが「離散的な段差」であるという実装前提と整合。

契約整合: earpipe/contracts.py は frozen dataclass、Literalで値域固定、NaN==NaN=Falseゆえnp.isnan使用、という既存規約を踏襲すること（QuantizedNote.onset_sec/offset_sec 既定NaNの前例）。実装先は earpipe/services/notate/ 配下（spelling.py/chord.py/score.pyと同層）が自然。

## 実装上の限界・正直な注記(notes)
正直な注記(捏造なし・実測ベース):

1) 対象2ファイルは本セッション開始時点で既に存在・完成しており、pytestも既に緑だった。私は新規に何も書いていない。実行して 16 passed を実測確認したのみ。したがって「新規実装」ではなく「既存実装の検証完了」が実態。

2) テストは合成理想信号(直線ランプ/正弦変調/階段ジャンプ/定常/NaN分割/空)で全パスするが、これは実録音精度を保証しない。モジュールdocstringにも明記のとおり先行研究(NIME/Springer)で多クラス分類の実精度は56.5%程度。

3) 原理的限界(実装docstringに明記済み):
   - bend と slide は同一ピッチ軌跡を生むため f0 のみからの分離は困難(TENTでもSlide F値=0.388)。到達後の定常保持有無という弱シグナルで区別し confidence を低めに出すのみ。「slide確定」とは言わない設計。
   - hammer_on/pull_off は平滑化窓と LEAP_MAX_DUR_SEC のバランスに敏感で、実データでは bend/vibrato に誤分類されやすい。
   - オクターブエラー(±1200centsスパイク)は SPIKE_MAX_CENTS 境界化で無効化するが、これ未満の推定ノイズは残る。
   - ベース(低周波)はf0推定が不安定でギターより信頼が低い。

4) 未接続: pipeline/CLIおよび楽譜出力(score/tab)への配線は未実施(wiring欄参照)。本モジュール単体は検出listを返すのみ。
