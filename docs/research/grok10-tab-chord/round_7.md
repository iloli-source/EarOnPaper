Searching X for MIR/DSP posts on harmonic masking and related separation techniques.Broad semantic search missed the niche. Targeting known MIR accounts and precise DSP terms.Found stronger leads (inverse harmonic clustering, multipitch papers). Digging into those threads and related MIR accounts.## Findings (X live, English)

**Bottom line:** There is almost no practitioner thread on X that walks through “detect a chord tone whose partials sit under the root’s harmonics.” Named MIR researchers rarely post implementable recipes for **P5 vs 3rd-harmonic** masking. What does exist is (1) arXiv bots + a few audio/DSP accounts flagging papers, (2) instrument builders on **inharmonicity**, and (3) one clear **inverse harmonic clustering / optimal transport** cluster. Below: real posts, then techniques you can implement.

---

### Real posts / threads worth keeping

| Who | When | What they said | Link |
|-----|------|----------------|------|
| **@korguchi** (audio/DSP practitioner) | Aug 2025 | “Optimal transport is suddenly trending in pitch estimation” + two papers, including **inverse harmonic clustering** for multipitch | [post](https://x.com/korguchi/status/1953644316263690627) |
| **@korguchi** | Feb 2023 | OT for **inharmonic** pitch estimation (already done in lit) | [post](https://x.com/korguchi/status/1626496897883185154) |
| **@GeoffroyPeeters** (Telecom Paris, MIR/audio) | Feb 2024 | Flags ICASSP paper: *Unsupervised Harmonic Parameter Estimation Using Differentiable DSP and Spectral Optimal Transport* (Torres / Peeters / Richard) | [post](https://x.com/GeoffroyPeeters/status/1753039431009734936) |
| **@ArxivSound** / **@AudioAndSpeech** | Aug 2025 | Same OT pitch papers (PESTO + translation-equivariant SSL) | e.g. [post](https://x.com/ArxivSound/status/1952891331363389727) |
| **@OrchestralPit** / **@ArxivSound** / **@SoundPapers** | Jun 2026 | Slot-attention **multi-instrument multipitch** (source-aware pitch maps; Hungarian matching) | [post](https://x.com/OrchestralPit/status/2061884541682196570) · [paper post](https://x.com/SoundPapers/status/2061721076162240986) |
| **@ArxivSound** / **@SoundPapers** | Jul 2026 | **HARP: Harmonic-Aware Residual Partitioning** for neural codecs (partition residual energy by harmonic structure) | [post](https://x.com/ArxivSound/status/2079500298238976289) |
| **@ArxivSound** | Sep 2025 | **Harmonic summation** robust pitch (NAMDF + integer-period aggregation + Viterbi continuity) | [post](https://x.com/ArxivSound/status/1970669310051016751) |
| **@korguchi** | Jul 2025 | Cwitkowitz & Duan: degeneration / overfitting in self-supervised multipitch | [post](https://x.com/korguchi/status/1940986364209910186) |
| **@helloLizZhang** | Jul 2026 | “Polyphony is the hard part — *n* instruments fighting over the same spectrum” (problem statement, no method) | [post](https://x.com/helloLizZhang/status/2075615962091729343) |
| **@nightingalemap** | Apr 2026 | Benchmark failures: **flute octave/harmonic confusion**, polyphonic onset collapse, dense-mix pitch confusion | [post](https://x.com/nightingalemap/status/2046915111198036190) |
| **@sudara** (additive synth / DSP) | Jun 2023 | String **inharmonicity**: successive partials go sharp vs exact integers — makes “harmonic = chord tone” ambiguous | [post](https://x.com/sudara/status/1665089881092096001) |
| **@gssp_acc** / **@svigalae** | May 2025 | Measured piano inharmonicity curve; DSP prototype for tuning apps | [post](https://x.com/gssp_acc/status/1919327980439887912) · [reply](https://x.com/svigalae/status/1919334193911263359) |
| **@its_adamneely** | Jan 2021 | Stretch tuning as compensation for string inharmonicity | [post](https://x.com/its_adamneely/status/1354538984689565699) |
| **@Bosnianballoon1** | Jun 2025 | Practical pitch stack: ZCR → autocorr → YIN/pYIN → **Harmonic Product Spectrum** → phase vocoder → CREPE | [post](https://x.com/Bosnianballoon1/status/1936527503872381423) |
| **@ricardmp** (audio ML prof) | Jun 2025 | Harmonicity / SNR diversity makes F0 hard; MIR F0 transfer to bioacoustics | [post](https://x.com/ricardmp/status/1936033151463440771) |
| **@jyzg** | Jul 2026 | Training-time **harmonicity objective** is fragile (too strong kills consonance/dissonance motion) | [post](https://x.com/jyzg/status/2072932990594748506) |

**Not found on X (English, live search):** detailed threads on spectral-subtraction residual analysis for chords, classic NMF harmonic-template recipes, phase/onset unmasking of coincident partials, or explicit “P5 vs 3rd harmonic” separation from MIR lab accounts. That discussion lives almost entirely in papers, not tweets.

---

### Implementable techniques (mapped from those posts → practice)

#### 1. Inverse harmonic clustering (optimal transport) — best match to your topic
**From:** @korguchi + Björkman & Elvander, arXiv:2508.02471  
**Core idea:** Treat the spectrum as a measure on the circle. **Transport** observed partial energy onto a small set of candidate harmonic combs (each defined by \(f_0\)). Shared bins (root’s 3rd harmonic vs fifth’s fundamental) become an **assignment** problem, not a binary peak pick.

**Implement:**
1. Peak-pick or use full magnitude spectrum \(S(f)\).
2. Candidate \(f_0\) grid (e.g. MIDI 21–96 or log-f bins).
3. Cost: distance of energy mass at \(f\) to nearest partial \(k\cdot f_0\) (or \(k\cdot f_0\sqrt{1+B k^2}\) with inharmonicity \(B\)).
4. Solve OT / unbalanced OT (Sinkhorn) so residual energy can stay unassigned.
5. Rank \(f_0\) by mass received; **coincident partials get split mass**, not winner-take-all.

**Why it hits P5 masking:** Root \(C\) partial 3 and fifth \(G\) partial 1 land near the same bin; OT can put mass on both combs if higher partials of \(G\) support a second series.

Related OT posts from **@GeoffroyPeeters** / Torres et al. (ICASSP 2024): fit a **harmonic template** by minimizing spectral energy displacement (spectral OT loss) with a differentiable harmonic synth — same family of ideas for unsupervised \(f_0\) + harmonic amplitudes.

---

#### 2. Inharmonicity as a disambiguation cue
**From:** @sudara, @gssp_acc, @svigalae, @its_adamneely, @korguchi (inharmonic OT thesis)  
**Physics:** Real strings: \(f_k \approx k f_0 \sqrt{1 + B k^2}\). A **true fifth** has its own \(B\) and its own \(f_0\); a pure integer 3rd harmonic of the root does not follow the fifth’s stretch.

**Implement:**
1. Fit \(B\) per hypothesized note (or instrument prior: piano ~ \(10^{-3}\)–\(10^{-4}\) by register).
2. Score candidate pitches with **inharmonic comb** match, not pure harmonic comb.
3. At the collision bin (~\(3f_0\) of root / \(1f_5\) of fifth): residual peak **offset** toward the stretched fifth is evidence of a real chord tone.

**Practical flag:** If residual after fitting an ideal harmonic root comb still has a peak **slightly sharp of \(3f_0\)**, treat it as candidate fifth (or another note with its own \(B\)), not leftover root energy.

---

#### 3. Harmonic summation / product spectrum (baseline + multipitch extension)
**From:** @ArxivSound (Singh & Demuynck), @Bosnianballoon1 (HPS list)  
**Classic multipitch extension of HPS/salience:**

```text
for each f0 candidate:
  salience[f0] = Σ_k w(k) · S(k·f0)     # or product Π_k S(k·f0)
```

**Against masking:**
1. Pick top \(f_0\) (root).
2. **Cancel** estimated harmonic envelope (see residual analysis below).
3. Re-run salience on residual → recover fifth / third if they had exclusive higher partials.

**NAMDF variant (paper):** convert difference function → likelihood; **sum likelihood over integer multiples of period** (harmonic aggregation); Viterbi with continuity constraint. Monophonic-first, but the multi-period aggregation idea ports to multipitch residual loops.

---

#### 4. Spectral residual / harmonic cancellation loop (spectral subtraction family)
**Not tweeted as a recipe**, but implied by residual partitioning (HARP posts) and standard multipitch practice.

**Implementable Klapuri-style loop:**
1. Estimate spectrum \(S\).
2. Detect strongest \(f_0\) via harmonic salience.
3. Estimate harmonic amplitudes \(a_k\) (least squares under comb support, or Wiener-like \(a_k = S(k f_0)\)).
4. Subtract: \(S \leftarrow \max(S - g\cdot \hat{H}_{f_0}, 0)\) (soft mask \(g \in [0.5,1]\)).
5. **Analyze residual** peaks: any peak near \(3f_0\) that **survives** after subtracting a smooth spectral envelope of the root is a candidate separate note.
6. Repeat until residual energy / salience below threshold.

**Residual diagnostics for “masked fifth”:**
- After canceling root, residual energy **ratio** at ~\(1.5 f_0\) vs neighboring bins.
- **Spectral smoothness** of residual: a real note leaves a **second comb**; noise leaves unstructured residue.
- Compare residual energy with vs without assuming a second \(f_0 = 1.5 f_0\).

---

#### 5. NMF / harmonic templates
**Sparse on X** (NMF tweets are mostly “New Music Friday”). Still the standard MIR approach your query names.

**Implement:**
1. Dictionary columns = harmonic templates \(W_{f_0}\) (or inharmonic templates with \(B\)).
2. Factor \(V \approx WH\) (KL or β-divergence); optionally **convolutive** NMF for time-varying amplitudes.
3. Overlapping partials: shared bins get **additive** contributions from two columns; activations \(H\) reveal whether both notes are needed.
4. Sparsity on \(H\) (one active pitch set) + **minimum-length** or Markov priors reduces false extra notes.

**Detection of shared-harmonic notes:** for root pitch \(r\), check activation of pitch at +7 semitones after fitting; if \(H_{r+7}\) remains high under joint fit, accept fifth even if fundamental is weak/masked.

---

#### 6. Source-aware multipitch (slots) — when polyphony is multi-instrument
**From:** @OrchestralPit / Taenzer arXiv:2606.01460  
**Technique:** Map CQT → unordered **slots** (source-like pitch maps); **Hungarian matching** for permutation-invariant training; optional timbre embedding + polyphony regularizer.

**Use for masking:** if root and fifth are different instruments, slot separation can break spectral ownership of the shared bin via timbre, not just harmonic geometry.

---

#### 7. Phase / onset cues for coincident partials
**Almost no English X depth.** Implementable cues used in the literature (aligned with failure modes @nightingalemap flags):

| Cue | How to use |
|-----|------------|
| **Common onset** | Onset detection function per band; if energy at \(3f_0\) rises **with** root attack only → likely harmonic of root. If a second onset appears at that band without low-band energy → likely new note. |
| **Group delay / phase derivative** | Instantaneous frequency of the collision bin: if IF locks to \(3f_0\) of root vs \(1\cdot f_5\), assign ownership. Beats / AM at difference frequency suggest **two** nearby partials. |
| **Transient vs steady-state** | Early frames: partials less perfectly locked → multipitch peaks clearer; late sustain: masking worse. Run multipitch on **attack residual** separately. |
| **Intermodulation / beating** | Slow envelope modulation at \(\lvert 3f_0 - f_5\rvert\) after just intonation detuning is evidence of two physical partials. |

---

#### 8. Harmonic-aware residual partitioning (codec-inspired, adaptable)
**From:** HARP posts (arXiv:2606.16657)  
**Idea:** Partition quantization / residual stages so harmonic structure and residual structure are handled separately.

**Adapt for analysis:** split spectrogram into (A) harmonic projection onto active \(f_0\) combs, (B) residual. Chord-tone detection = significant structured energy in (B) that fits **another** comb.

---

### Practical mini-pipeline (chord note under root harmonics)

```text
1. CQT or high-res STFT → magnitude S
2. Harmonic salience → f_root (and optional B_root)
3. Fit / subtract root comb (soft spectral subtraction)
4. Residual S_res:
     a) OT or second-pass salience for f_candidates in {fifth, third, octave…}
     b) Inharmonicity score if instrument known
     c) Onset/phase consistency at collision bins
5. Accept secondary pitch if:
     - exclusive higher partials exist, OR
     - residual mass at collision + own partials beats pure-root model (BIC / likelihood ratio)
6. Optional: joint NMF or OT with both combs for final amplitude split
```

**Decision rule for P5 vs 3rd harmonic of root:**
- Pure root model: energy at \(3f_0\) explained by \(a_3\) only.
- Root+fifth model: energy at \(3f_0 \approx a_3^{(\text{root})} + a_1^{(\text{fifth})}\), plus energy at \(2f_5, 3f_5, \ldots\).
- Prefer two-note model if residual after one-note fit still has a harmonic series at \(1.5 f_0\), or OT assigns mass to that series.

---

### Where X is thin vs literature

| Your topic | On X English | Best signal |
|------------|--------------|-------------|
| P5 vs 3rd harmonic | Almost none | Derive from multipitch residual + OT posts |
| Spectral subtraction residual | HARP residual partitioning only | Classic iterative multipitch (not tweeted) |
| NMF harmonic templates | Effectively none (NMF = music marketing) | Papers / textbooks |
| Inverse harmonic clustering | **Yes** (@korguchi + arXiv) | arXiv:2508.02471 |
| Inharmonicity cues | **Yes** (synth/tuning people) | @sudara, piano-tuning threads |
| Phase/onset coincident partials | Almost none | Failure-mode post @nightingalemap only |

---

### Follow accounts that actually surface this work
- **@GeoffroyPeeters** — Telecom Paris MIR  
- **@korguchi** — high-signal pitch/OT paper spotting  
- **@ArxivSound**, **@SoundPapers**, **@AudioAndSpeech**, **@OrchestralPit** — daily paper firehose  
- **@sudara**, synth/DSP builders — inharmonicity intuition in practice  

If you want a next step, I can turn the residual + OT + inharmonicity decision rule into a concrete Python sketch (numpy/librosa) aimed specifically at root vs perfect-fifth collision bins.
