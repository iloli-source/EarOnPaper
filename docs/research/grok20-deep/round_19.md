Searching X in English and Japanese for AMT low-string octave errors, guitar E/A misdetection, and fixes.Refining searches toward MIR/AMT technical terms and Japanese pitch-detection discussion.Pulling more targeted posts on AMT, f0 priors, and guitar low-string detection.## X live search: low-string octave errors in AMT / pitch tracking (EN + JP)

**Bottom line:** X has more *adjacent* discussion than pure “AMT paper” threads. The useful cluster is: **pitch trackers latching onto the 2nd harmonic**, **weak/missing fundamentals on low strings**, **virtual pitch / missing fundamental**, and **post-hoc octave correction / range priors**. Below: why it happens, on-X posts + links, then practical fixes.

---

### Why detectors put low E / A an octave high (or low)

| Mechanism | What happens on guitar low E (~82 Hz) / A (~110 Hz) |
|-----------|------------------------------------------------------|
| **Weak fundamental** | Small speakers, DI, heavy EQ HPF, and many guitar bodies put more energy at 2f, 3f… than at f0. Detector picks the strongest peak → **+1 octave**. |
| **Harmonic periodicity** | Autocorrelation / YIN / HPS see period *T/2* as almost as good as *T* when even harmonics dominate. |
| **Inharmonicity** | Stiff bass strings shift partials → harmonic-template methods mis-score f0. |
| **Range bias** | Models trained on voice/mid instruments “prefer” mid f0; low guitar notes look out of prior → jump up. |
| **Polyphony / distortion** | Overdriven E/A + chords → false peaks at octaves/fifths (same family as multipitch octave errors). |
| **Notation quirk (JP-adjacent)** | Classical guitar is often **written an octave higher** than concert pitch — humans *and* bad pipelines can confuse sounding pitch. |

**Direction of error:**  
- **Most common:** note reported **one octave too high** (locked on 2nd harmonic).  
- **Also seen:** **too low** if subharmonic / envelope / vibrato confuses lag domain (rarer on clean monophonic bass).

---

### English posts (links)

**1. Pitch-tracking research — “magically correct the octave errors”**  
[@yoyolicoris](https://x.com/yoyolicoris) (MIR / pitch-tracking PhD-side work)  
> “Sometimes, it can magically correct the **octave errors** and I didn't add any constraint regarding this.”  
🔗 https://x.com/yoyolicoris/status/1796947010362179786  
Related salience-curve work: https://x.com/yoyolicoris/status/1446857255689719811  

**2. Production tool failure — Melodyne picks wrong octave**  
[@ThunderBird2678](https://x.com/ThunderBird2678)  
> “melodyne kinda shitting the bed with its pitch detection… those 4 notes… are actually **an octave higher**”  
🔗 https://x.com/ThunderBird2678/status/1621567029076525057  
Celemony reply (Note Assignment): same thread.  

**3. Virtual pitch vs spectral bass energy (why “heard” pitch ≠ strongest low peak)**  
[@jyzg](https://x.com/jyzg)  
> Bass often sits at **virtual pitch / first octave up** from pure spectral interpolation; 5th and 2-octaves also common.  
🔗 https://x.com/jyzg/status/2074471349611905226  
Related: overtones in bass https://x.com/jyzg/status/2074540569724948604  

**4. Missing fundamental (psychoacoustic twin of the bug)**  
[@Cromerbazil](https://x.com/Cromerbazil) — remove bass fundamental, brain still “hears” it:  
🔗 https://x.com/Cromerbazil/status/2077410547885121629  
[@gsalvadi](https://x.com/gsalvadi): https://x.com/gsalvadi/status/1957646201458757681  

**5. Pitch algo ladder (YIN → pYIN → HPS → CREPE)**  
[@Bosnianballoon1](https://x.com/Bosnianballoon1)  
🔗 https://x.com/Bosnianballoon1/status/1936527503872381423  

**6. Related “octave error” family — tempo (same integer-ratio trap)**  
[@BeiciLiang](https://x.com/BeiciLiang): TempoCNN/madmom still have **octave error** by nature:  
🔗 https://x.com/BeiciLiang/status/1625272513654853633  
[@cubesol_greg](https://x.com/cubesol_greg): beat path includes **octave error correction** (140 vs 70 BPM):  
🔗 https://x.com/cubesol_greg/status/2011091081497374727  

**7. Guitar string inharmonicity / stretch (partials not exact harmonics)**  
[@its_adamneely](https://x.com/its_adamneely) on piano stretch tuning:  
🔗 https://x.com/its_adamneely/status/1354538984689565699  

---

### Japanese posts (低音弦 / オクターブ誤検出 周辺)

**1. Pitch algorithm may first pick octave-down then correct (karaoke / pitch pick-up)**  
[@KuruwaKaigan](https://x.com/KuruwaKaigan)  
> ピッチの拾い方…「まずは**オクターブ下と誤検出**したのち、正しい音階…合格」もあり得る。男性は特にオクターブ下の音もうっすら…  
🔗 https://x.com/KuruwaKaigan/status/2033381589271675128  

**2. エレキはピッチ推定が難しい（倍音だらけ）**  
[@ga_ya_kamo](https://x.com/ga_ya_kamo)  
> ピアノやアコギは綺麗にピッチ推定…**問題はエレキ。バッキングが倍音沢山**…コードから推定するしか…  
🔗 https://x.com/ga_ya_kamo/status/2075898004838768703  

**3. アコギ低音弦（特に4弦ルート）が薄く、オクターブ下を足す**  
[@shikaosuga](https://x.com/shikaosuga) — same physics that makes detectors jump *up*: weak low fundamental  
🔗 https://x.com/shikaosuga/status/1946961655696695754  

**4. ギターは記譜が実音より1オクターブ高い（移調）**  
[@fukushinsanchan](https://x.com/fukushinsanchan)  
> ギターは実際の音より**オクターブ高く記譜**…思っているより低音寄り…  
🔗 https://x.com/fukushinsanchan/status/702287249367441409  

**5. 「オクターブエラー」as known pitch phenomenon (human + systems)**  
[@_llre](https://x.com/_llre) / [@huuchi](https://x.com/huuchi) thread on absolute pitch octave errors + register:  
- https://x.com/_llre/status/1924671691646763343  
- https://x.com/huuchi/status/1924803813074206750 (本の参照)  
- https://x.com/huuchi/status/1924659139961299416  

**6. 低音ベースは耳コピが難しく、昔は倍速＝オクターブ上げで拾っていた**  
[@y_sasano](https://x.com/y_sasano)  
🔗 https://x.com/y_sasano/status/2059540636337164788  

**7. ケプストラム / 基本周波数・倍音ピーク（f0推定の古典的見方）**  
[@hasea_teikoku](https://x.com/hasea_teikoku)  
🔗 https://x.com/hasea_teikoku/status/2078099568370335822  

---

### Fixes that match both research practice and what X hints at

| Fix | Idea | When it helps low E/A |
|-----|------|------------------------|
| **f0 range prior** | Constrain search (e.g. guitar open E–12th: ~80–700 Hz; bass ~40–400 Hz). Soft prior in CREPE/pYIN Viterbi. | Stops mid-band harmonic wins. |
| **Octave correction post-process** | If note *n* and *n±12* both candidates, prefer the one consistent with: instrument range, previous frame, harmonic residual energy at f0. | Classic AMT cleanup. |
| **Harmonic residual / HPS** | Compare energy at f0 vs 2f0; if 2f0 >> f0 but residual at f0 exists, force down an octave. | Weak-fundamental cases. |
| **Temporal smoothing** | HMM/Viterbi: huge cost on ±12 jumps unless onset supports it. | Contour flicker. |
| **Instrument-conditioned model** | Guitar/bass-specific AMT or multi-pitch with string priors. | Poly + distortion. |
| **Pre-processing** | Avoid aggressive HPF; use full-band or mild shelf; mono DI if possible. | Don’t erase ~82 Hz before detection. |
| **Melodyne-style note assignment** | Manual/forced octave in tools when detection fails (Celemony’s reply pattern). | Production rescue. |

**Minimal post-process sketch (common pattern):**
```text
for each note event:
  candidates = {f0, 2*f0, 0.5*f0} ∩ instrument_range
  score(c) = detector_confidence(c)
            + λ_range * log p_inst(c)
            + λ_time  * continuity(prev, c)
            + λ_harm  * residual_at_fundamental(c)
  pick argmax score
```

---

### Coverage note

X is **sparse** on full “AMT + low-string octave error + paper” discourse; dense clusters are:

1. **MIR pitch-tracking / tempo octave errors**  
2. **Tool failures (Melodyne)**  
3. **JP: ピッチ推定 × エレキ倍音 / 絶対音感オクターブエラー / 低音が薄い**  
4. **Psychoacoustics: missing fundamental / virtual pitch**

If you want a second pass, I can dig **academic handles** (ISMIR authors, Basic Pitch / Spotify, mt3, guitarset) or arXiv paper threads specifically.
