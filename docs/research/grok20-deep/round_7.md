Searching X and the web (EN+JP) for onset/attack cues in chord detection: strum grouping, simultaneous onsets, and power-chord attack analysis.Found a Japanese onset+chord paper and MIR leads. Digging into papers and more targeted X/web queries.# Onset / Attack Cues for Chord Detection  
**“One strike = N strings”** — EN + JP research & practitioner notes

---

## Core problem

A guitar **strike** (pick strum, finger rake, power-chord chop) is not N independent monophonic notes. It is:

1. **One gestural event** (hand motion / pick path)  
2. **N near-simultaneous string onsets** with micro-timing skew (typically **~5–40 ms** across the set)  
3. A shared **attack transient** (pick scrape + broadband inharmonic energy) then **steady-state** harmonics  

Chord systems that frame-wise chroma-classify without grouping onsets often:

- double-count a single strum as many chord changes  
- split one power chord into root-then-fifth “events”  
- fail under distortion (extra partials look like extra pitches)

The practical decision is: **group energy bursts that share an attack envelope into one chord event, then estimate pitch content (and string count) inside that group.**

---

## 1. Strum detection (event = strike)

### Research

| Work | Idea | Relevance |
|------|------|-----------|
| **Joint Transcription of Acoustic Guitar Strumming Directions and Chords** (arXiv 2508.07973, 2025) | CRNN: log-Mel → regress **up/down strum onsets** + classify chord at those times | Explicitly argues classical note-trackers fail on **dense polyphony of strums**; unit of analysis is the **strum event**, not each string |
| Annotation pipeline | **Spectral flux** on pickup + IMU accel derivative for direction | Spectral flux remains the workhorse ODF for labeling “when did the strike hit” |
| **Bello & Mayol (2019)** | CNN/LSTM on MFCC slices → up vs down stroke (~70–72%) | Direction as a latent of attack shape |
| **Murgul & Heizmann (ISMIR LBD 2022)** | Multimodal: motion sensor + pickup | Ground truth for “one gesture = one onset group” |
| **Matsushita / Freire et al.** | Wearable / mocap of down-strums | Gesture-level onset, not spectral multipitch |

**Takeaway:** For rhythm guitar / power-chord progressions, treat **strum action detection** first, **chord label second**. Evaluate with **~50 ms** onset tolerance (`mir_eval` style).

### Practitioner (X)

- Building guitar practice tools: monophonic pitch alone is not enough — **“Pitch detection says A4 but not ‘a new A4 just started’”** → add **RMS onset**. Guitar note-to-note ratio is often only **~1.5×** vs decay, so classic 3× energy gates miss half the notes.
- Game/controller “strum detection” is usually **gesture**, not audio multipitch — useful mental model: **one strike event, then N fretted pitches**.

---

## 2. Simultaneous onset grouping  
**(N string attacks → 1 strike)**

There is less “named product” literature than for drums, but the pattern is consistent:

### Algorithmic pattern (what people actually implement)

```
1. Compute ODF (spectral flux / superflux / sparsity / complex-domain)
2. Peak-pick local onsets
3. Cluster onsets whose times fall in a grouping window τ
   - τ ≈ 20–50 ms for full strums
   - τ ≈ 5–15 ms for “simultaneous” power-chord chops / palm mutes
4. Inside each cluster:
   - multipitch / chroma / template match
   - optional: count active partials → estimate N strings
5. Emit ONE chord event at cluster start (or energy centroid)
```

### Why grouping is mandatory on guitar

- **Pick sweep** spreads string attacks in time (downstrum: low→high; upstrum: reverse).  
- Shared harmonics (esp. **power chord root+5th+oct**) make successive spectral-flux peaks look like “new notes” even when energy is one gesture.  
- Stack Exchange multipitch discussion: **onset co-timing reduces F0 ambiguity** when one partial could belong to several fundamentals.

### Related formal work (not always guitar-branded)

- **NINOS²** (Mounir et al., EUSIPCO 2016): guitar **melodies and chord progressions**; attacks are **spectrally less sparse** than sustain → ODF that doesn’t rely only on frame-to-frame magnitude growth (helps repeated chords / shared harmonics).  
- **SuperFlux / ComplexFlux / LogFiltSpecFlux**: designed for vibrato/tremolo false peaks — relevant when chords ring and ODF chatters.  
- **TENT** (Su et al., TISMIR 2019): technique-aware **note merging** after F0 contour (bend/vibrato false splits). Polyphonic strums are out of scope, but the **merge-after-attack-analysis** idea transfers.

---

## 3. Attack transient analysis  
**(decide “one strike”, then read N strings)**

### What the attack carries

| Phase | Spectral character | Use in pipeline |
|-------|--------------------|-----------------|
| **Transient / attack** (~5–40 ms) | Broadband, inharmonic, low sparsity, pick noise | **Onset localization**, strum direction cues, mute vs open |
| **Steady state** | Sparse harmonics, clearer F0s | **Chord identity**, multipitch, chroma |

### Research cues

1. **Spectral sparsity (NINOS²)**  
   Attack needs many sinusoids; sustain is sparse. ODF = sparsity of **low-energy** bins (after dropping strong harmonics) so attacks pop even when F0 energy is continuous. Reports large gains vs LogFiltSpecFlux on guitar chords.

2. **Spectral flux (JP + EN standard)**  
   近藤ら (秋田大), 東北地区音響学研究会 2023:  
   - SF onset → take **5 frames after onset** → harmonic-peak chord matching (PSI vs CTI) → **majority vote**  
   - Isolated ideal chords ~94%; continuous performance much harder  
   - Onset timing error ~**27 ms** in their setup  
   - Explicit pipeline: **onset gate → short post-attack window → chord**, not full-track frame classification  
   PDF: https://asj-tohoku.acoustics.jp/tohoku-meeting/06/6-10.pdf

3. **Skip-attack for steady chroma**  
   Mazhar (Tampere thesis, acoustic guitar chords): jump past the attack into sustain for cleaner templates — opposite of onset detection, same phase split.

4. **CCRMA guitar real-time** (Krishnamurthy): Peak envelope ODF vs spectral flux; guitar-tuned attack/release peak followers.

5. **Patent-class idea**: “attack transient detector” = moment string is plucked from instrument signal — industrial cousin of the MIR ODF.

### Estimating **N strings** from one strike

Heuristic stack used in practice / papers:

- After grouping window, **count F0 peaks** (or pitch-class peaks above threshold) that **onset within τ**  
- Require **coherent ADSR**: similar attack time, common energy envelope  
- For **power chords (1–5–1')**: expect **2–3 F0s** with strong 3:2 / octave locking; distortion adds **sum/diff products** that must **not** be counted as extra strings  
- Optional: high-band pick noise energy as “pluck present” binary before multipitch

---

## 4. パワーコードのアタック解析 (power-chord attack)

### Signal facts

- Voicing: **root + perfect 5th** (± octave). Weak 3rd → chroma “major/minor” is unreliable; treat as **dyad/triad template** (1–5–8).  
- **Distortion** (clipping): intermodulation → new spectral lines; classic rock “power chord fatness” is partly **nonlinear products**, not fretted notes.  
- Attack of a muted power-chord **chug** is closer to **percussive ODF** (HFC / flux / sparsity) than to slow piano onsets.  
- Open ringing power chords: long sustain → ODF must suppress **false re-onsets** from amplitude modulation / feedback.

### Research-adjacent

- Aalto / rock guitar distortion literature studies **power chords as the canonical nonlinear test signal** (interval + heavy drive). Detection systems that assume linear harmonic stacks undercount/overcount under gain.  
- Perception papers (e.g. distortion-product pleasantness in triads) use power chords as the main stimulus — useful if your “N strings” estimator confuses **distortion products with fretted strings**.

### JP practitioner (tone / mix, not MIR — still useful priors)

- アタックの定義（コンプ）: “threshold を超えてから ratio 到達までの時間” — mix discourse, but reminds that **attack time ≠ onset time**.  
- パワーコード録音: **ミュート時のアタック**がキャラの本体になりやすい（5150/Soldano 系の語り）.  
- テレキャスで端正なパワーコード: **アタックをどう抑えるか**が音色差の中心.  
- 日米のパワーコードの“ゴー vs ガー”: アタックより **ボディ／倍音バランス**の話も多い — detection では **attack shape + spectral tilt** を分けて扱う根拠.

### Design implication for detectors

```
Power chord strike classifier (sketch)
  if ODF peak + broadband attack
     and multipitch peaks ≈ {f, 1.5f, 2f} within tolerance
     and no strong major/minor 3rd
  then label: power_chord (N≈2–3)
  else if many simultaneous F0s in τ → open_chord / full_strum
  else if single F0 → single_note
```

Distortion path: **pre-emphasis / mild highpass before multipitch**, or template-match in **log-freq** after a simple nonlinear model, so 3rd-order products don’t inflate N.

---

## 5. Practical pipeline (research-backed)

```
Audio
  → ODF: SuperFlux or NINOS² (guitar chords) / Spectral Flux (simple)
  → Peak pick (adaptive threshold; don’t use 3× RMS on guitar)
  → Onset clustering window τ (strum-aware, tempo-adaptive optional)
  → Per cluster:
       a) attack features (sparsity, HFC, MFCC of first 20–40 ms)
          → strike type: strum / mute-chop / arpeggio / single
       b) steady window after attack (or 5 frames like 近藤ら)
          → multipitch / chroma / chord template
       c) optional: up/down from attack spectral shape or CRNN
  → One symbol per cluster: (time, chord, N_strings, direction?)
```

**Baselines to beat:** spectral flux / superflux / CD-ODF alone (strum paper reports ~74–79% F1 on pickup; learned model ~98% on pickup, ~90%+ on mic with hybrid data).

---

## 6. Key sources (bookmark list)

### Research / papers
| Lang | Source |
|------|--------|
| EN | [Joint strum + chord transcription (arXiv 2508.07973)](https://arxiv.org/html/2508.07973v1) |
| EN | [NINOS² guitar onset / sparsity (EUSIPCO 2016 PDF)](https://eurasip.org/Proceedings/Eusipco/Eusipco2016/papers/1570256369.pdf) |
| EN | [TENT technique-embedded note tracking (TISMIR)](https://transactions.ismir.net/articles/10.5334/tismir.23) |
| EN | CCRMA: guitar peak vs spectral-flux onset + pitch |
| EN | SuperFlux / ComplexFlux (Böck & Widmer, DAFx) — ODF family |
| JP | [オンセット検出を用いたギターコード演奏楽音の認識（近藤ら, 2023）](https://asj-tohoku.acoustics.jp/tohoku-meeting/06/6-10.pdf) |
| JP | Spectral flux 発音検出 + 押弦フォーム制約（矢澤ら, 京大/IPSJ 周辺） |

### Practitioner / product adjacent
- Chordify / Yamaha Chord Tracker / Chord AI — product-level chord AI; rarely document onset grouping publicly  
- X: RMS onset thresholds for real guitar note starts; attack-length fairness in rhythm games (~50 ms soft attacks)  
- Mix side: pick-transient extraction (Physion / entropy EQ class tools) as **attack-only features** for “strike present?”

---

## 7. Gaps (honest)

| Gap | Status |
|-----|--------|
| Named “simultaneous onset grouping for guitar strings” paper | Thin — usually buried inside multipitch / strum / AMT systems |
| Explicit **N-string counter** from one attack | Mostly heuristics; few public benchmarks |
| Distorted power chords as multipitch test set | Used for *effects* research more than *chord N* estimation |
| JP X “パワーコードのアタック解析” as DSP | Mostly **tone/mix** talk, not MIR; formal JP work is **SF onset → short-window chord vote** (近藤ら) |

---

## Bottom line

For **chord detection driven by attack cues**:

1. **Detect strikes**, not notes: spectral flux / sparsity ODF + **cluster in τ**.  
2. **One cluster = one chord decision** (majority vote over a few post-onset frames).  
3. Use the **transient** for “did a strike happen / mute? / strum direction?” and the **sustain** for “which chord / how many strings?”.  
4. For **パワーコード**, constrain templates to **1–5–(8)** and **suppress distortion products** so they don’t inflate N.  
5. State of the art for rhythm guitar is moving to **joint strum-event + chord models** (CRNN), with classical ODFs still best for labeling and lightweight real-time.

If you want a follow-up, I can turn this into a concrete algorithm card (thresholds, feature list, evaluation metrics) or a short JP/EN reading pack ordered by implementation priority.
