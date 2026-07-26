Researching English posts and papers on beat-frequency / phase-coherence methods for separating coincident partials.Promising leads found (especially Maher on beat-cycle partials). Digging into implementable methods and more targeted X/web sources.## Verdict on X (EN live/semantic)

**Almost nothing implementable on X.** Keyword and semantic searches for coincident/overlapping partials + beat frequency / phase coherence / difference-frequency AM mostly return noise (sports “partial tracking,” Demucs stem separation, binaural beats, number-theory “phase,” etc.).

Closest *tangential* posts (not recipes):

| Post | Why it’s only adjacent |
|------|------------------------|
| [Natalie Schaworonkow](https://x.com/nschawor/status/1346148824457179137) — two same-frequency oscillators; phase relation flips measured traveling-wave direction | Neural/EEG analogy, not string partial reallocation |
| [sudara](https://x.com/sudara/status/1957960073541496836) — many sines at one pitch with per-partial pitch/volume modulation | Synthesis side of “dense coincident partials,” no separation math |
| Demucs / hybrid spectrogram–waveform posts | Data-driven stems; ignore physical beat/phase cues |

**Actionable material lives in papers and lab pages, not X.**

---

## Physical model (what the three cues actually are)

Two near-coincident partials:

\[
s(t)=A_1\cos(2\pi f_1 t+\phi_1)+A_2\cos(2\pi f_2 t+\phi_2)
\]

equivalent to a single carrier with **slow AM + FM** at the difference frequency:

\[
f_b = |f_1-f_2|
\]

| Cue | Observable | When it works |
|-----|------------|---------------|
| **Beat-frequency analysis** | Envelope max ≈ \(A_1+A_2\), min ≈ \(\|A_1-A_2\|\); period \(1/f_b\) | \(f_b\) small but non-zero; \(A_i\) quasi-constant over several beat cycles |
| **Phase / IF wobble** | Instantaneous frequency/phase of the summed peak oscillates at \(f_b\); phase of envelope extremum vs IF says which partial is higher | Same as above; needs good IF/phase tracking |
| **Difference-frequency AM (CAM extension)** | Shared source → correlated envelopes on *non-overlapped* siblings; use them as templates for the collided bin | Exact or near-exact coincidence (unison, octaves, 5ths…); needs multi-F0 + partial labels |

**Exact coincidence** (\(f_1=f_2\)): no beats — only a single phasor sum. You *must* bring external structure: common amplitude modulation across harmonics, predicted phase from F0, vibrato/tremolo (AM/FM) diversity, spatial cues, or onsets.

Two piano strings on one note are the textbook case: slight detuning → slow beats; tracking those beats is how tuners and analysis tools “split” the doublet.

---

## Implementable papers (best → supporting)

### 1. Classic beat-envelope split (directly your three cues)

**R. C. Maher** — *Evaluation of a Method for Separating Digitized Duet Signals*, JAES 1990  
PDF: https://www.montana.edu/rmaher/publications/maher_jaes_1290_956-979.pdf  

**R. C. Maher** — UIUC dissertation (1989)  
PDF: https://www.montana.edu/rmaher/publications/maher_uiuc_dissertation_0489.pdf  

**Core algorithm (highly implementable):**
1. Sinusoidal / STFT peak tracking per frame.
2. When two partials share a resolution cell but \(\Delta f\) is non-zero, form the **complex sum** and track **amplitude envelope** over several cycles of \(f_b\).
3. Recover  
   \(A_1,A_2\) from envelope max/min:  
   \(A_{1,2}=\frac{\max\pm\min}{2}\).
4. Use **phase of max/min relative to instantaneous frequency** (or real/imag trajectory of the beat) to assign which amplitude belongs to which \(f\).
5. Assumes envelopes slow vs \(f_b\) (“constant for several cycles of the beat frequency” — explicit in the thesis).

This is the purest “beat frequency + phase + AM at difference frequency” recipe for **near-miss** coincident partials (detuned strings, mistuned unisons).

---

### 2. Exact/near-exact overlap via CAM + phase prediction (least squares)

**Woodruff, Li, Wang** — *Resolving Overlapping Harmonics for Monaural Musical Sound Separation Using Pitch and Common Amplitude Modulation*, ISMIR 2008  
PDF: https://ismir2008.ismir.net/papers/ISMIR2008_139.pdf  

**Assumptions:**
- **CAM:** amplitude envelopes of harmonics of the *same* source are highly correlated.
- **Phase coherence with F0:** phase advance of harmonic \(h\) ≈ \(2\pi\, h\, F_0\, \Delta t\) (predictable from pitch track).

**Algorithm sketch:**
1. Multi-F0 (paper assumes known pitches as proof of concept).
2. Label bins as overlapped vs exclusive.
3. From exclusive harmonics of each source, estimate a **common envelope shape** (and relative gains).
4. In overlapped bins, fit complex sinusoid parameters \(S_{n,h}=\frac{a}{2}e^{j\phi}\) by **least squares** under CAM + predicted phase evolution (eqs. in §2–3 of the paper).
5. Resynthesize by additive synthesis / inverse STFT.

**Related journal version:** Li, Woodruff, Wang, *Monaural musical sound separation based on pitch and common amplitude modulation*, IEEE TASLP 2009.

This is the best “implementable paper” for **true coincident** partials (integer-ratio intervals), not just detuned beats.

---

### 3. Unison case: same pitch, separate by AM/FM (vibrato/tremolo)

**Stöter et al.** — *Unison Source Separation*, DAFx 2014  
Paper: https://www.dafx14.fau.de/papers/dafx14_fabian-robert_stoter_unison_source_separation.pdf  
**Demo + audio + refs:** https://www.audiolabs-erlangen.de/resources/2014-DAFx-Unison  

Two instruments on the **same note** → full partial collision. Separation uses:
- **AM path:** NTF on modulation spectrograms (tremolo rate differences) — builds on Barker & Virtanen *modulation NTF* (Interspeech 2013).
- **FM path:** informed **time warping** from pitch-variation estimates so vibrato trajectories unmix in a warped domain (related lineage: Avery Wang *frequency-warped* ASSP 1995).

**Follow-up:** Stöter et al., *Common Fate Model for Unison Source Separation*, ICASSP 2016 (TF modulation / common fate).

---

### 4. Spectral-smoothness fallback (no beats required)

| Work | Idea | Limit |
|------|------|--------|
| **Every & Szymanski**, DAFx / related (“spectral filtering,” concurrent harmonics) | Linear interpolate overlapped harmonic amplitude from neighbors | Breaks on formants / strong inharmonicity |
| **Virtanen & Klapuri** | Nonlinear spectral smoothness | Same |
| **Virtanen** harmonic basis smoothness | Fixed smooth bases for harmonic amplitudes | Real instruments often violate smoothness (Woodruff Fig. 1) |

Use as **prior** when \(f_b\approx 0\) and CAM siblings are missing (e.g. only one strong partial).

---

### 5. Extra implementable / useful refs

| Ref | Why care |
|-----|----------|
| **Parsons (1976)** overlapping speech partials | Peak symmetry, spacing, “well-behaved phase” tests to *detect* collision (fails under strong modulation) |
| **de León & Beltrán**, *Blind separation of overlapping partials…*, EURASIP 2012 | Amplitude + phase reconstruction for harmonic notes |
| **Yeh multi-F0 PhD (IRCAM)** | § on partial beating; appendix on expected amplitude of overlaps; cites Viste–Evangelista, Virtanen, Every–Szymanski |
| **Muševic et al.**, distribution-derivative generalized sinusoid | Explicit beating / complex AM in the model — good for tracking modulated coincident peaks |
| **LECAM** (localized extended CAM) | Unison / heavily overlapped pitched sources |
| **J. O. Smith PARSHL / SASP notes** | Practical STFT hop vs fastest beat from mistuned strings / overlapping keys — engineering constraint, not a separator |

---

## Minimal implementable pipeline (strings → split coincident partials)

```text
1. STFT or MQ/SMS peak pick → (f, a, φ) tracks
2. Multi-F0 + harmonic assignment
3. For each frequency collision:
   if |f1-f2| > ~ few bins or measurable envelope cycle:
       → Maher beat path: track |z(t)| and arg/IF of complex peak
          A1,A2 from max/min; assign via phase of beat
   else:  # true coincidence / within one bin
       → Woodruff CAM+phase LS using sibling harmonics of each F0
       → optional: Stöter AM/FM if vibrato/tremolo differs
       → fallback: spectral smoothness interpolate
4. Reassign energy / resynthesize two partial tracks
5. Optional: NMF/Demucs only after physical reallocation (or as residual cleaner)
```

**Practical stack:** `librosa` / `scipy` STFT + peak pick; or SMS-tools / Loris / `sms-tools` style sinusoidal analysis; F0 from pYIN / CREPE / multi-F0 (e.g. `basic-pitch` is single-melody — prefer multi-F0 for polyphony).

**Detuned two-string note:** start with Maher envelope math on a narrow bandpass around the partial — often works with <50 lines of numpy if you already have analytic signal / Hilbert on the band.

**Perfect octave / fifth collision:** CAM + phase-from-F0 least squares (ISMIR 2008) is the right default.

---

## Bottom line

| Need | Go to |
|------|--------|
| Near-coincident partials, audible beats (two strings, chorus, slight detune) | **Maher JAES 1990 + dissertation** — beat max/min + phase |
| Exact harmonic collisions in polyphony | **Woodruff/Li/Wang ISMIR 2008** (+ TASLP 2009) — CAM + F0-predicted phase, LS |
| Same pitch, different instruments | **Stöter DAFx 2014** (+ Common Fate 2016) — AM-NTF / FM warp; demo page with audio |
| X live EN posts with code-level recipes | **None found** — treat X as empty for this niche |

I can turn Maher’s beat recovery or the ISMIR CAM least-squares into a short numpy reference implementation next if you want that as a concrete artifact.
