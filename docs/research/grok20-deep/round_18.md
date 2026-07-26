Searching X and the web for implementable write-ups on missing-fundamental / GCD pitch grouping (HPS, subharmonic summation, tuner/tracker approaches).Semantic X hits were noisy; tightening search toward DSP implementers, GitHub, and core papers.Checking Slack tools for the work-log post, then compiling the digest.# Missing-fundamental / GCD pitch grouping — implementable map

**X live search (EN):** almost no high-signal implementer threads on HPS / SHS / GCD partial-grouping right now. Hits skew to psychoacoustics metaphors, additive-synth partials, or unrelated “missing fundamental” rhetoric. The durable material is **papers + open code**, not tweets.

Below is a practical map: **what the problem is**, **the spectral “GCD-like” families**, **how tuners/trackers actually recover f0 from partials only**, and **copy-pasteable implementations**.

---

## 1. Problem in one sentence

If the ear (or a tuner) only sees partials at ~200, 300, 400, 500 Hz, the **perceived / reported pitch is ~100 Hz** even when 100 Hz energy is weak or absent — the **missing fundamental**. Spectral methods that “group harmonics” are effectively searching for an **f0 whose integer multiples best explain the peaks** (soft GCD / harmonic template match), not “largest FFT bin.”

**Why raw FFT peak-picking fails on guitar/bass:** low E (~82 Hz) often has stronger upper harmonics; the fundamental is not the tallest peak. Tuner blogs and forums restate this constantly.

---

## 2. Algorithm families (partials → f0)

| Family | Core idea | Missing-f0? | Octave risk | Best starting code |
|--------|-----------|-------------|-------------|--------------------|
| **HPS** (Harmonic Product Spectrum) | Multiply spectrum by downsampled copies so energy stacks at f0 | **Yes** | Low if harmonics rich | `@audio/pitch-hps`, gists |
| **HSS** (Harmonic *Sum* Spectrum) | Same geometry, **add** instead of multiply | Yes (softer) | Medium | Noll 1969; HPS code with `prod→sum` |
| **SHS** (Subharmonic Summation, Hermes) | On log-freq, compress spectrum by 2,3,… and **sum** (subharmonic folding) | **Yes** (designed for it) | Medium | MATLAB `pitch(...,'Method','SHS')`, PitchTrack |
| **SWIPE / SWIPE′** | Correlate spectrum vs **sawtooth (prime-harmonic) template** | **Yes** | Low (primes cut even-harmonic bias) | Camacho code ports |
| **TWM** (Two-Way Mismatch) | Peak list ↔ harmonic series: predicted↔measured error both ways | **Yes** | Low if peaks clean | Maher–Beauchamp paper + SMS ports |
| **GCD / harmonic spacing** | Discrete peaks → differences / GCD of freqs | Yes (naive) | High without voting | Wu-style spacing; HDM paper |
| **Time-domain** (YIN / pYIN / MPM) | Periodicity of waveform, not partial geometry | Weak / indirect | Controlled by heuristics | librosa, aubio — **not** the spectral “GCD story” |

`@audio/pitch`’s comparison table is unusually honest: **YIN/McLeod do not solve missing fundamental; HPS / cepstrum / SWIPE do.**

---

## 3. HPS variants (implementable)

### Classic HPS (Schroeder / Noll lineage)

**Recipe:**
1. Window → FFT → magnitude (optionally log-compress mildly).
2. For downsampling factors \(r = 2..R\) (often \(R=5\)): resample spectrum so bin \(k\) multiplies with bin \(\lfloor k/r \rfloor\) energy.
3. \(P(k) = \prod_{r=1}^{R} |X(\lfloor k \cdot r \rfloor)|\) (or product of downsampled spectra aligned at candidate f0).
4. Peak of \(P(k)\) in \([f_{\min}, f_{\max}]\) = f0; parabolic interp for cents.

**Why it finds a missing fundamental:** if only 2f, 3f, 4f exist, they still **align under compression** at bin of f. Pure sine (one partial) → product collapses → HPS fails.

**Code / writeups**
- JS monorepo (HPS + SWIPE + YIN side-by-side): https://github.com/audiojs/pitch  
- Clear mono HPS gist (Python): https://gist.github.com/carlthome/1e7244e31bd628a0dba233b6dceebaef  
- Polyphonic HPS note detector: https://github.com/joaocarvalhoopen/Polyphonic_note_detector_using_Harmonic_Product_Spectrum  
- Web Audio real-time HPS tuner: https://github.com/VeDaNsH-D/Swar  
- RN pitch lib (AMDF vs HPS notes): https://github.com/rnheroes/react-native-pitchy  
- Classic pitfalls (octave errors, weak fundamentals): DSP.SE “HPS limitations” — https://dsp.stackexchange.com/questions/572/harmonic-product-spectrum-limitations-in-pitch-detection  
- Guitar HPS debugging: https://stackoverflow.com/questions/43964139/harmonic-product-spectrum-for-single-guitar-note-python  

**Useful variants people actually ship**
| Variant | Change | When |
|---------|--------|------|
| **HSS** | Product → sum | Sparse / noisy partials (multiply kills missing bins) |
| **Log-HPS** | Work in log-mag or log-freq | Wide pitch range, equal weight per octave |
| **Soft / weighted HPS** | \(w_r\) decay for higher \(r\); skip empty bins | Real instruments with missing harmonics |
| **Peak-only HPS** | Product on peak list, not full FFT | After peak picking (closer to GCD story) |
| **mHPS (multi-pitch)** | Iterative cancel / residual HPS | Polyphony (research grade) |

---

## 4. Subharmonic summation (Hermes SHS)

**Paper:** Dik J. Hermes, *Measurement of pitch by subharmonic summation*, JASA 83(1), 1988 — designed explicitly around the missing-fundamental / harmonic-sieve story.

**Intuition (different bookkeeping from HPS):**
1. Map spectrum to **log-frequency** (ERB/constant-Q style optional).
2. For each candidate pitch, **compress** the spectrum along frequency by integers 2, 3, … (fold energy onto subharmonics).
3. **Sum** compressed spectra (with decreasing weights for higher compression).
4. Argmax over candidate f0.

Related speech PDAs: **Subharmonic-to-Harmonic Ratio (SHR)** — Sun (ICSLP 2000) — https://www.isca-archive.org/icslp_2000/sun00d_icslp.pdf  

**Code / product hooks**
- MATLAB Audio Toolbox: `pitch(x,fs,'Method','SHS')` documents Hermes SHS — https://www.mathworks.com/help/audio/ref/pitch.html  
- Multi-algorithm pack citing SHS: https://github.com/PitchTrack/PitchTrack  
- Internal report on SHS-style PDA (KU Leuven PDF): https://homes.esat.kuleuven.be/~spch/flavor/reports/InternalReportSHS.pdf  
- Modern harmonic-summation pitch in noise (2025 survey-ish paper + method): https://arxiv.org/html/2509.16480v1  

**SHS vs HPS (implementer view)**  
- Both are **spectral folding / alignment** methods.  
- HPS: **linear-freq FFT bins × decimation** — cheap, guitar-tuner friendly.  
- SHS: **log-freq subharmonic folding + sum** — closer to psychoacoustic pitch models; often better on speech/missing-f0 demos in literature.

---

## 5. How tuners & pitch trackers infer f0 from partials only

There is no single “industry GCD” — products pick a **template match** or **periodicity** layer:

### A. Spectral template / GCD-like (what you asked for)

1. **Peak pick** strong partials \(\{f_i\}\).  
2. Propose candidate fundamentals:
   - \(f_i / n\) for small \(n\), or  
   - differences \(\Delta f_{ij} = |f_i - f_j|\) (first-difference “GCD proxy”), or  
   - dense grid in cents.  
3. Score each candidate \(f_0\):
   - **HPS/HSS/SHS** score on full spectrum, or  
   - **TWM**: sum of (measured peak → nearest \(n f_0\)) + (predicted harmonic → nearest peak) errors (Maher & Beauchamp 1994). PDF: https://www.montana.edu/rmaher/publications/maher_jasa_0494_2254-2263.pdf  
   - **SWIPE′**: correlation with **prime-harmonic sawtooth** spectrum (kills many octave traps).  
4. Pick max score; **refine** with parabolic / Quinn / phase-vocoder interp; **smooth** over frames (median / HMM / Viterbi).

**SWIPE code**
- C + MATLAB (Camacho lineage): https://github.com/kylebgorman/swipe  
- Python ports: https://github.com/dishagarg/SWIPE  
- JS: package in https://github.com/audiojs/pitch  

**GCD-of-peaks folklore (fragile but educational)**  
Wu-style: take strongest peaks, compute GCD / spacing table (cited in HDM survey). Works only when partials are **nearly integer-related and well resolved**. Inharmonic piano / bent guitar → breaks. HDM (harmonic *differences* voting) is a modern cousin: https://onlinelibrary.wiley.com/doi/10.1155/2021/6658951  

### B. What many *guitar tuners* actually ship

Cheap/mobile tuners often use **time-domain** (autocorrelation / AMDF / YIN / McLeod MPM), not explicit HPS:

- Autocorrelation peak ≈ period → f0 even when fundamental is weak *if* the waveform still has period T (partials phase-lock).  
- Blog walkthrough (FFT fail → ACF tuner): https://29a.ch/2020/04/15/guitar-tuner  
- “FFT alone is not enough” explainer: https://hackernoon.com/guitar-tuner-pitch-detection-for-dummies-ok8e35o9  
- KVR: “need algorithm for missing fundamental; FFT is only part of it” — https://www.kvraudio.com/forum/viewtopic.php?t=350251  

So: **missing-f0 in perception ≠ must use HPS**. Time-domain period detectors also “hallucinate” the fundamental when the signal is still periodic at T.

### C. Speech trackers that stay spectral / residual-harmonic

| Method | Idea | Link |
|--------|------|------|
| **PEFAC** | Noise-robust spectral comb / filter for F0 | EUSIPCO PDF: https://www.eurasip.org/Proceedings/Eusipco/Eusipco2011/papers/1569423085.pdf |
| **SRH** (Summation of Residual Harmonics) | Harmonic sum on residual spectrum | Variants + code table in https://pmc.ncbi.nlm.nih.gov/articles/PMC9414051/ → e.g. https://github.com/deshengwang001/SRH_Variant |
| **YAAPT / Praat / YIN comparisons** | Production speech PDAs | Habré-style writeups; librosa `yin`/`pyin` |

Columbia pitch-tracking lecture (TWM, sinusoid tracks, classic refs): https://www.ee.columbia.edu/~dpwe/e4896/lectures/E4896-L08.pdf  

CCRMA survey of PDA zoo: https://ccrma.stanford.edu/~pdelac/154/m154paper.htm  

---

## 6. Minimal implementable cores (pseudo)

**HPS (spectral product):**
```python
# X = |FFT(window * x)| ; work on bins up to Nyquist
P = X.copy()
for r in range(2, R+1):
    # decimate: compare P[k] with X[k*r]
    L = len(X) // r
    P[:L] *= X[::r][:L]
f0 = bin_to_hz(argmax(P[fmin_bin:fmax_bin]) + fmin_bin)
```

**Soft GCD / peak spacing (educational, not production):**
```python
peaks = peak_pick(X)  # Hz
cands = set()
for f in peaks:
    for n in range(1, Nmax+1):
        cands.add(f / n)
# score: how many peaks fall near n*f0 within cents tolerance
f0 = max(cands, key=lambda f0: score_harmonic_fit(peaks, f0))
```

**SHS sketch:** log-freq interpolate magnitude → for each candidate f0, sum `w_r * X_log(log(r*f0))` over r → argmax.

---

## 7. X / social (EN) — thin but real

| Post / thread | Why it matters |
|---------------|----------------|
| [YhatHQ share of Carl Thome HPS gist](https://x.com/YhatHQ/status/797100720898080768) | Direct “implement HPS in Python” pointer (2016, still the right gist) |
| [Karen Berryhill — lists HPS among freq-domain PDAs](https://x.com/AsIhaveforgiven/status/1790873614398668825) | Sparse modern mention of HPS as a named algorithm |
| [Jeff Yu — missing fundamental + harmonics explainer](https://x.com/Jeff_Yu/status/2063460695979823135) | Psychoacoustics, not code |
| [Bazil Cromer — missing fundamental as “auditory pareidolia”](https://x.com/Cromerbazil/status/2077410547885121629) | Perception framing only |
| [sudara — partial mapping / additive harmonics](https://x.com/sudara/status/1957960073541496836) | Partial control, not f0 inference |
| [Ewan Bristow — fundamental-aware spectral stretch](https://x.com/BristowEwan/status/2080404994491088915) | Product DSP; assumes you already know f0 |

**Gap on X:** almost nobody posts **SHS code**, **TWM scorers**, or **GCD peak voters**. If you want implementable discourse, GitHub + DSP.SE + JASA still win.

---

## 8. Recommended build order (if you implement)

1. **Baseline HPS** on monophonic guitar WAV (`@audio/pitch-hps` or carlthome gist).  
2. Switch product→sum (**HSS**) and add **per-harmonic weights** when partials drop out.  
3. Add **peak-list TWM** scorer for comparison on the same frames.  
4. Port **SWIPE′** for studio-clean instruments (prime harmonics).  
5. Only then try **SHS on log-freq** (Hermes) if you care about speech / psychoacoustic demos.  
6. For low-latency tuners, **benchmark against YIN/MPM** — often wins latency; loses the “partials-only geometry” story when the waveform is aperiodic.

---

## 9. Canonical citations (bookmark)

| Ref | Role |
|-----|------|
| Schroeder 1968 — period histogram / product spectrum | HPS ancestor |
| Noll 1969 — HPS, HSS, ML pitch | Classic speech PDA paper |
| Hermes 1988 — subharmonic summation | SHS |
| Maher & Beauchamp 1994 — two-way mismatch | Peak↔harmonic f0 for music |
| Camacho & Harris 2008 — SWIPE | Sawtooth / prime-harmonic template |
| de Cheveigné & Kawahara 2002 — YIN | Time-domain production default |
| Sun 2000 — SHR | Subharmonic-to-harmonic ratio PDA |

---

### Bottom line

- **Missing fundamental / GCD grouping** in software ≈ **harmonic template scoring** (HPS/HSS/SHS/SWIPE/TWM), not literal integer GCD of noisy peak Hz.  
- **HPS** is the shortest path from “I have an FFT” to “I recover weak/missing f0 on guitar.”  
- **SHS** is the classic **subharmonic-sum** formalization of the same idea (Hermes; MATLAB `Method='SHS'`).  
- **Tuners** often cheat with **time-domain period** detectors; **spectral** trackers are what match the “partials-only → fundamental” story.  
- **X is sparse** for this niche; use the GitHub/paper links above as the implementable corpus.

---

*Note: Slack `#倉田_ログ` auto-post was skipped — no Slack MCP server is connected in this session (only freee / gdrive / wordpress). If you want that log sent, enable Slack MCP or paste the channel token path.*
