Searching X for the 2026 slot-attention multi-pitch paper and related attention-based polyphonic note-event models.Found the June 2026 slot-attention paper. Searching related polyphonic/note-event attention models and gathering paper details.## Target paper (Jun 2026): slot-attention + Hungarian matching

**A Lightweight Slot-Attention Framework for Multi-Instrument Multi-Pitch Estimation**  
Michael Taenzer · arXiv:2606.01460 (submitted 31 May 2026; indexed Jun 2026)  
- Abs: https://arxiv.org/abs/2606.01460  
- PDF: https://arxiv.org/pdf/2606.01460  

**What it does:** multi-instrument MPE (MI-MPE) — mixture CQT → unordered set of **source-like pitch maps** via **slot attention**; **permutation-invariant Hungarian matching** so slots have no fixed instrument semantics; optional timbre encoder + polyphony branch. Hungarian matching helps instrument-family decomposition on URMP; stem-level assignment remains hard. Submitted to IEEE MMSP 2026.

### X posts (EN / bots)

| Date | Account | Post | Link |
|------|---------|------|------|
| 2026-06-02 | @OrchestralPit | “Slot attention with Hungarian matching enables instrument-aware multi-pitch estimation…” | [x.com/OrchestralPit/status/2061884541682196570](https://x.com/OrchestralPit/status/2061884541682196570) · paper [2606.01460v1](https://arxiv.org/abs/2606.01460v1) |
| 2026-06-02 | @SoundPapers | Full title + MMSP note | [x.com/SoundPapers/status/2061721076162240986](https://x.com/SoundPapers/status/2061721076162240986) |
| 2026-06-02 | @ArxivSound | Citation-style drop | [x.com/ArxivSound/status/2061694880016187785](https://x.com/ArxivSound/status/2061694880016187785) |

**Takeaway:** Almost no organic EN discussion — only MIR/arXiv bots. No author thread found.

---

## Related: attention / note-level models that handle simultaneous notes

These are the closest neighbors on X + arXiv (polyphony, multi-source, or explicit simultaneous-note handling).

### 1. Self-attention instance segmentation (classic multi-instrument AMT)
**Wu et al. (2020)** — *Multi-instrument AMT with self-attention–based instance segmentation*  
Treats notes as instances; joint note detection + instrument ID under polyphony.  
https://ieeexplore.ieee.org/document/9206100 (TASLP)  
Often cited next to Taenzer-style “who played which pitch” work.

### 2. Note-level contrastive clustering (lightweight multi-instrument)
**A Lightweight Two-Branch Architecture for Multi-Instrument Transcription via Note-Level Contrastive Clustering**  
Li & Zhu · arXiv:2509.12712 · TISMIR 2026  
https://arxiv.org/abs/2509.12712 · journal: https://doi.org/10.5334/tismir.300  

Timbre-agnostic backbone + timbre branch; **note-level deep/contrastive clustering** for joint transcription + dynamic separation of simultaneous instruments. Discusses why plain self-attention can merge overlapped-note clusters.

**X:**  
- @ArxivSound (2026-04-17): [status/2045006511580336203](https://x.com/ArxivSound/status/2045006511580336203)  
- @ArxivSound (2026-03-27): [status/2037383107490513039](https://x.com/ArxivSound/status/2037383107490513039)

### 3. Transformer multi-instrument AMT (YourMT3+)
**YourMT3+: Multi-instrument Music Transcription with Enhanced Transformer Architectures…**  
Chang, Benetos, Kirchhoff, Dixon · arXiv:2407.04822  
https://arxiv.org/abs/2407.04822  

Sequence model for multi-instrument transcription (simultaneous notes via multi-pitch / multi-track MIDI-style outputs).

**X:**  
- @ArxivSound (2024-08-01): [status/1818860128998764628](https://x.com/ArxivSound/status/1818860128998764628)  
- @AudioAndSpeech: [status/1819038812242112869](https://x.com/AudioAndSpeech/status/1819038812242112869)

### 4. MuScriptor — open multi-instrument transcription (Jul 2026, high engagement)
**MuScriptor: An Open Model for Multi-Instrument Music Transcription**  
Rouard, Krause, Roebel, Simon-Gabriel, Défossez · arXiv:2607.08168  
https://arxiv.org/abs/2607.08168  

Real-world multi-instrument mixes; instrument-presence conditioning; open weights. Not slot-attention, but the main 2026 EN conversation around simultaneous multi-source transcription.

**X:**  
- @kyutai_labs (2026-07-10): [status/2075540047613276197](https://x.com/kyutai_labs/status/2075540047613276197) — “best open model for multi-instrument transcription”  
- @ArxivSound: [status/2075459479949451511](https://x.com/ArxivSound/status/2075459479949451511)  
- @OrchestralPit: [status/2075610765562712257](https://x.com/OrchestralPit/status/2075610765562712257)  
- Weekly trend: [status/2076056317991788561](https://x.com/OrchestralPit/status/2076056317991788561) (+ MulTTiPop)

### 5. Efficient Transformer piano transcription (simultaneous onsets)
**Efficient Transformer-Based Piano Transcription…** · arXiv:2509.09318  
https://arxiv.org/html/2509.09318v1  
Explicit ordering rules when **simultaneous note onsets** share a time; event sequence AMT.

### 6. Dataset / eval for multi-track polyphony
**MulTTiPop** (multitrack pop AMT eval) — @pruynathan  
https://x.com/pruynathan/status/2075772813462450389 · http://gclef-cmu.org/multtipop/ · arXiv:2607.08756

### 7. Timbre pretraining for multi-instrument AMT (ICASSP 2026)
@Kakanat1105 / @rin310_ — “Timbre-Based Pretraining with Pseudo-Labels for Multi-Instrument AMT”  
https://x.com/Kakanat1105/status/2012722239083598008

---

## Quick map: slot vs other simultaneous-note strategies

| Approach | Simultaneous-note / multi-source idea | Paper |
|----------|--------------------------------------|--------|
| **Slot attention + Hungarian** | Unordered source slots; permutation-invariant assignment | Taenzer 2026 [2606.01460](https://arxiv.org/abs/2606.01460) |
| **Self-attention instance segmentation** | Notes as instances; instrument labels under polyphony | Wu et al. 2020 |
| **Note-level contrastive clustering** | Cluster note embeddings by timbre for multi-source | Li & Zhu [2509.12712](https://arxiv.org/abs/2509.12712) |
| **Transformer event / multi-track AMT** | Multi-pitch / multi-instrument sequences | YourMT3+ [2407.04822](https://arxiv.org/abs/2407.04822), piano Transformers |
| **Large multi-instrument AMT** | End-to-end real mixes, instrument conditioning | MuScriptor [2607.08168](https://arxiv.org/abs/2607.08168) |

---

## X search notes

- Exact **Hungarian + slot + multi-pitch** hits collapse to **three bot posts** on 2026-06-02 (Orchestral Pit / Sound Papers / arXiv Sound).  
- Broader “attention + polyphonic transcription” is dominated by **MuScriptor**, **YourMT3+**, and **note-level clustering**, not further slot-attention follow-ups.  
- Football/Arne Slot noise is huge if you search bare `slot` + `pitch` — use `"slot attention"` or arXiv IDs.

If you want, I can dig author accounts, PDF method figure summary, or a tighter comparison of Hungarian/slot vs note-level clustering vs Wu-style instance segmentation.
