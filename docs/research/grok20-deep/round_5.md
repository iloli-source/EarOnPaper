Researching HARP and related harmonic-aware transcription methods, including how they allocate energy across notes that share partials.HARP is a neural-codec method, not transcription. Pulling the paper and classic harmonic-aware transcription representations next.## Short answer

**HARP (2026-07) is not a transcription method.** It is a **neural audio codec** training strategy that partitions **RVQ residual stages by frequency band**. It does **not** allocate energy among co-active notes that share partials.  
**HCQT / harmonic stacking** (transcription) re-arrange the spectrogram so harmonics line up for CNN kernels; they also **do not** solve shared-partial energy ownership.  
True “who owns this bin?” partitioning is mostly classical **NMF / multi-pitch spectral models**; modern neural AMT largely **learns around** collisions instead of explicitly splitting bins.

---

## 1. HARP (July 2026) — residual partition for **codecs**, not notes

**Paper:** [HARP: Harmonic-Aware Residual Partitioning for Neural Audio Codecs](https://arxiv.org/abs/2607.16657) (Yang, He, Deng, Zhao; Interspeech 2026)  
**PDF:** https://arxiv.org/pdf/2607.16657  
**HTML:** https://arxiv.org/html/2607.16657v1  
**Code:** https://github.com/QiaoyuYang/harp-codec  

### What “partitioning” means here

Standard RVQ (SoundStream / EnCodec / DAC-style) is **frequency-agnostic**: each residual stage grabs whatever reduces error most → **spectral entanglement** (early stages mix bass/mids/treble unpredictably).

HARP instead:

| Piece | Mechanism |
|--------|-----------|
| **Stage groups** | Default 9 RVQ stages → 4 groups: bass (0–1 kHz), low-mid (1–4), high-mid (4–10), treble (10–22) |
| **Cumulative decoding** | Group \(k\) is decoded from \(\hat z_{\le k}\) so **overtones see fundamentals** already in the latent |
| **Subband contribution** | Supervises each group’s **waveform increment** \(\hat x_k = G(\mathrm{sg}[\hat z_{\le k-1}] + \hat z_k) - \mathrm{sg}[\hat x_{\le k-1}]\) with stop-grad so gradients stay on that group |
| **Soft band weights** | Learnable Gaussian over **mel bins** (floor \(\beta=0.3\)) — soft preference, not hard split |
| **Inference** | Same as vanilla RVQ; hierarchy is only in learned codebooks |

So HARP partitions **coding residual capacity across frequency**, preserving **cross-band harmonic coherence** vs parallel band codecs (e.g. BSCodec).  
It is **not** “note A vs note B both exciting 880 Hz.”

### X posts (live / recent)

- [@SoundPapers](https://x.com/SoundPapers/status/2079527063652831461) — paper drop + Interspeech 2026 note  
- [@ArxivSound](https://x.com/ArxivSound/status/2079500298238976289) — arXiv pointer  

Little technical discussion on X so far; mostly bot/paper bots.

---

## 2. HCQT & harmonic stacking — **alignment**, not energy ownership

### HCQT (Deep Salience)

**Paper:** Bittner et al., *Deep Salience Representations for F0 Estimation in Polyphonic Music*, ISMIR 2017  
**PDF:** https://archives.ismir.net/ismir2017/paper/000085.pdf  

- Build CQTs starting at \(f_{\min}, 2f_{\min}, 3f_{\min}, \ldots\)  
- Stack → tensor \((t, f, h)\) so partial \(h\) of pitch \(f\) sits at the same \(f\)-index across channel \(h\)  
- CNN learns **salience** of \(f_0\), not a soft mask that splits bin energy among notes

### Harmonic stacking (Basic Pitch / NMP)

**Paper:** Bittner et al., *A Lightweight Instrument-Agnostic Model for Polyphonic Note Transcription and Multipitch Estimation*, 2022  
**arXiv:** https://arxiv.org/abs/2203.09893  
**Code:** https://github.com/spotify/basic-pitch  

Efficient HCQT approx:

1. Compute one CQT (e.g. 3 bins/semitone)  
2. **Copy and vertically shift** by bin offsets for harmonics \(1,2,3,\ldots\) (+ optional subharmonic)  
3. Stack as channels (Basic Pitch: 7 harmonics + 1 subharmonic)

**Ablation:** dropping stacking hurts note F-measure hard when kernels stay small — stacking is the inductive bias that replaces large receptive fields.

### Shared partials: what they **do not** do

If C4 and G4 both put energy at ~784 Hz (G5 ≈ 3rd of C / 2nd of G):

| Representation | Behavior |
|----------------|----------|
| **HCQT / stacking** | That bin appears in **multiple** harmonic channels for **each** candidate \(f_0\); still **one magnitude**, duplicated by shift |
| **Energy partition** | **None** — no rule like “60% to C, 40% to G” |
| **Downstream** | Softmax / multi-label pitch posteriors; collisions resolved by **learned patterns**, not residual spectral unmixing |

Same class of idea: **HPPNet** (harmonic dilated conv for piano AMT) — models harmonic structure in the network, still not explicit partial ownership  
https://archives.ismir.net/ismir2022/paper/000085.pdf · arXiv: https://arxiv.org/abs/2208.14339  

---

## 3. Methods that **do** partition energy among notes sharing partials

These are closer to your energy-allocation question (mostly **pre-/early deep** multipitch):

### Adaptive / harmonic NMF multipitch

**Vincent, Bertin, Badeau** — *Adaptive harmonic spectral decomposition for multiple pitch estimation*  
https://inria.hal.science/inria-00544094v1/document  

- Each pitch ≈ weighted sum of **narrowband templates** for adjacent partials  
- Spectrum ≈ sum over active pitches of (template × amplitude)  
- **Multiplicative updates** allocate observed power so overlapping partials **compete** for the same bin (NMF-style residual / factorization)

Related: harmonic/inharmonic NMF for piano multipitch — https://hal.science/inria-00544183  

### Multi-pitch streaming / peak–nonpeak models

- Duan, Pardo, Zhang — multipitch via spectral peaks + non-peak regions  
- Duan, Han, Pardo — *Multi-pitch streaming of harmonic sound mixtures*  
  https://labsites.rochester.edu/air/publications/DuanHanPardo_MultiPitchStreaming_TASLP.pdf  

Partials are **linked into streams**; shared bins are handled by likelihood / assignment, not by HCQT geometry.

### Conceptual residual chain (if you want an analogy to HARP’s “residual”)

Classical greedy multipitch often:

1. Detect strongest \(f_0\)  
2. **Subtract / suppress** its harmonic series  
3. Iterate on residual  

That **is** residual energy partitioning — but **HARP’s residual** is **RVQ codebook residual in a codec latent**, not spectral residual between notes.

---

## 4. Side-by-side: what is being partitioned?

| Method | Domain | What is partitioned | Shared partials (two notes, one bin)? |
|--------|--------|---------------------|----------------------------------------|
| **HARP (2026)** | Neural codec RVQ | **Bitrate / residual stages × frequency bands** | N/A — reconstructs full mixture; coherence via cumulative decode |
| **Parallel band codecs** (BSCodec, etc.) | Codec | **Independent bands** | Harmonics split across bands; **no** low-band context → phase/amp incoherence HARP criticizes |
| **HCQT** | Transcription front-end | **Channels = harmonic index** | Bin **reused** per channel; **no** energy split |
| **Harmonic stacking** | Same | Same via CQT shifts | Same |
| **HPPNet / harmonic dilations** | Network architecture | Receptive field along harmonic series | Implicit; learned |
| **Harmonic NMF / adaptive spectral decomp** | Multipitch model | **Basis amplitudes / templates** | **Yes** — factorization assigns bin mass |
| **Greedy residual multipitch** | Signal residual | **Energy after subtracting estimated harmonics** | Explicit subtractive residual |
| **Modern AMT** (Onsets&Frames, Basic Pitch, transformers) | Labels | Pitch/onset **posteriors** | Soft multi-label; no physical energy ledger |

---

## 5. Practical takeaway for transcription research

1. **Don’t read HARP as AMT residual unmixing.** Use it if you care about **token codecs for music models** with **graceful low-bitrate** and **harmonic coherence**.  
2. **HCQT / stacking** answer: “How do I let a small CNN see harmonics?” — not “How do I unmix overlapping partials?”  
3. For **explicit shared-partial energy**, look at **harmonic NMF / adaptive spectral decomposition** and streaming multipitch; neural AMT usually **avoids** that layer.  
4. Open research gap: **combine** harmonic-aligned front-ends with **soft spectral unmixing** or **source-aware residual** so C4/G4 collisions are physically accountable, not only classification-friendly.

---

## 6. Link pack

| Resource | URL |
|----------|-----|
| HARP arXiv | https://arxiv.org/abs/2607.16657 |
| HARP code | https://github.com/QiaoyuYang/harp-codec |
| X: SoundPapers | https://x.com/SoundPapers/status/2079527063652831461 |
| X: ArxivSound | https://x.com/ArxivSound/status/2079500298238976289 |
| Deep Salience (HCQT) | https://archives.ismir.net/ismir2017/paper/000085.pdf |
| Basic Pitch / stacking | https://arxiv.org/abs/2203.09893 · https://github.com/spotify/basic-pitch |
| HPPNet | https://arxiv.org/abs/2208.14339 |
| Adaptive harmonic spectral decomp (Vincent et al.) | https://inria.hal.science/inria-00544094v1/document |
| Multi-pitch streaming (Duan et al.) | https://labsites.rochester.edu/air/publications/DuanHanPardo_MultiPitchStreaming_TASLP.pdf |

If you want a follow-up, I can dig specifically into (a) **HARP vs MUFFIN MBS-RVQ / BSCodec** on harmonic metrics, or (b) a math sketch of **how NMF updates split one STFT bin** between two active pitches.
