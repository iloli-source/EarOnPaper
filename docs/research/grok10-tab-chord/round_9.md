I'll search X for recent English posts on guitar tablature transcription research—papers, open-source models, Basic Pitch variants, and AMT benchmarks.Keyword hits were sparse; broadening searches to known paper names, researchers, and related AMT terms.Found a few research hits (e.g. Fretiq). Digging deeper for papers, models, and benchmarks.Strong paper hits (GOAT, GuitarFlow, Fretiq). Searching those titles plus more transcription-specific work.# Guitar tablature transcription on X (2025–2026)

English X discussion is **thin for pure audio→tab research**, but arXiv bots and C4DM researchers surface a clear paper trail. Below are **real posts** with links and paper names, grouped by topic.

**Coverage note:** Almost no English posts on **dyad/power-chord datasets** or **published Basic Pitch guitar fine-tunes**. Those gaps are real on X, not just search noise.

---

## 1. Audio-to-tab / technique-aware tab

### **TART** — *Technique-Aware Audio-to-Tab Guitar Transcription*
- **Paper:** [arxiv.org/abs/2510.02597](https://arxiv.org/abs/2510.02597)
- **Post:** [@ArxivSound](https://x.com/ArxivSound/status/1975340265180447047) — 6 Oct 2025  
  > Akshaj Gupta, Andrea Guzman, Anagha Badriprasad, Hwi Joo Park, Upasana Puranik, Robin Netzorg, Jiachen Lian, Gopala Krishna Anumanchipalli, "TART: A Comprehensive Tool for Technique-Aware Audio-to-Tab Guitar Transcription," https://arxiv.org/abs/2510.02597  
- Closest direct hit for **audio → tab** on X.

### Practitioner note (not a paper)
- [@Chromamancer](https://x.com/Chromamancer/status/2047322635852194106) — 23 Apr 2026  
  > “There are some audio to tab papers but I've seen any practical products based on them.”

---

## 2. String / fret estimation & fretting (MIDI→tab, string ID)

### **Fretiq** — *Browser-Native Electric Guitar String Classification*
- **Paper:** [arxiv.org/abs/2607.18303](https://arxiv.org/abs/2607.18303)
- **Posts:**
  - [@ArxivSound](https://x.com/ArxivSound/status/2079850643641254047) — 22 Jul 2026  
  - [@SoundPapers](https://x.com/SoundPapers/status/2079831436941549808) — 22 Jul 2026  
  > Fretiq: Browser-Native Electric Guitar String Classification via Engineered Spectral Features and Held-Out Free-Play Evaluation — Aadi Garg

### **Fretting-Transformer** — *Encoder-Decoder MIDI → Tablature*
- **Paper:** [arxiv.org/abs/2506.14223](https://arxiv.org/abs/2506.14223)
- **Posts:**
  - [@ArxivSound](https://x.com/ArxivSound/status/1935186892401577985) — 18 Jun 2025  
  - [@MultimediaPaper](https://x.com/MultimediaPaper/status/1935251509534392496) — 18 Jun 2025  
  > Fretting-Transformer: Encoder-Decoder Model for MIDI to Tablature Transcription (Hamberger, Murgul, Schmidt, Heizmann)

### **MIDI-to-Tab** (ISMIR 2024; still cited as the fretting backbone)
- **Paper:** [arxiv.org/abs/2408.01769](https://arxiv.org/abs/2408.01769) *(Edwards, Riley, Sarmento, Dixon — title confirmed via X)*
- **Posts:**
  - [@drooby_doo](https://x.com/drooby_doo/status/1825919015094726907) — 20 Aug 2024 — audio→MIDI→tab demo (High-Res guitar AMT + MIDI-to-Tab Transformer)
  - [@c4dm](https://x.com/c4dm/status/1856117350795489652) — 11 Nov 2024 — MIDI-to-TAB poster session
  - [@dadabots](https://x.com/dadabots/status/1826536569974485414) — 22 Aug 2024 — “audio-to-midi-to-tab chain is complete”
  - [@ArxivSound](https://x.com/ArxivSound/status/1822846492228415856) — 12 Aug 2024

### **MIDI → Guitar Tablature (ML conversion)**
- **Paper:** [arxiv.org/abs/2510.10619](https://arxiv.org/abs/2510.10619)
- **Post:** [@ArxivSound](https://x.com/ArxivSound/status/1978123624302473690) — 14 Oct 2025  
  > "A Machine Learning Approach for MIDI to Guitar Tablature Conversion" (Kaliakatsos-Papakostas et al., incl. Dorien Herremans)

---

## 3. Datasets (paired audio–tab / guitar AMT data)

### **GOAT** — *Paired Guitar Audio + Tablatures*
- **Paper:** [arxiv.org/abs/2509.22655](https://arxiv.org/abs/2509.22655)
- **Posts:**
  - [@ArxivSound](https://x.com/ArxivSound/status/1972882115244281927) — 30 Sep 2025  
    > Jackson Loth, Pedro Sarmento, Saurjya Sarkar, Zixun Guo, Mathieu Barthet, Mark Sandler, "GOAT: A Large Dataset of Paired Guitar Audio Recordings and Tablatures"
  - [@TeachableAI](https://x.com/TeachableAI/status/1973187042830884993) — 1 Oct 2025 — plain-language summary of GOAT (amps, styles, paired tabs)

### **GAPS** — *Classical guitar dataset + benchmark AMT model* (ISMIR 2024 baseline, still the cited GuitarSet SOTA train set)
- **Paper:** [arxiv.org/abs/2408.08653](https://arxiv.org/abs/2408.08653)  
- **Download:** [zenodo.org/records/13962272](https://zenodo.org/records/13962272)
- **Posts:**
  - [@xavriley](https://x.com/xavriley/status/1808111608247287821) — 2 Jul 2024 — ISMIR 2024: **91.2% note-onset F1 on GuitarSet**
  - [@nicolasguozixun](https://x.com/nicolasguozixun/status/1870101359036424382) — 20 Dec 2024 — ~14h classical guitar, 200+ performers, MIDI + MusicXML; **zero-shot GuitarSet F1 88.1%** with GAPS-trained model
  - [@ArxivSound](https://x.com/ArxivSound/status/1825383344688726133) — 19 Aug 2024
  - [@itsdrevo](https://x.com/itsdrevo/status/1868038643442479366) — 14 Dec 2024 — lists GAPS under “better transcription data → better models”

### **Dyad / power-chord datasets**
- **No English research posts found** naming a dedicated dyad/power-chord guitar dataset in 2025–2026.  
- Closest adjacent: GOAT (paired tab, rock/electric friendly) and general guitar AMT papers — not dyad-specific on X.

---

## 4. Guitar AMT (pitch/velocity; not always full tab)

### **Velocity Prediction in Automatic Guitar Transcription**
- **Paper:** [arxiv.org/abs/2606.24912](https://arxiv.org/abs/2606.24912)
- **Posts:**
  - [@ArxivSound](https://x.com/ArxivSound/status/2070681391252357149) — 27 Jun 2026  
  - [@SoundPapers](https://x.com/SoundPapers/status/2070051833997939091) — 25 Jun 2026  
  > Jackson Loth, Xavier Riley, Simon Dixon, Emmanouil Benetos

### **GuitarFlow** (tab → audio synthesis; reverse of transcription, same data stack)
- **Paper:** [arxiv.org/abs/2510.21872](https://arxiv.org/abs/2510.21872)
- **Post:** [@ArxivSound](https://x.com/ArxivSound/status/1983066260406710308) — 28 Oct 2025  
  > "GuitarFlow: Realistic Electric Guitar Synthesis From Tablatures via Flow Matching and Style Transfer"

### **Robustness with real electric tones/effects**
- **Post:** [@cackerman21](https://x.com/cackerman21/status/1840714278325612847) — 30 Sep 2024  
  > "LEVERAGING REAL ELECTRIC GUITAR TONES AND EFFECTS TO IMPROVE ROBUSTNESS IN GUITAR TABLATURE TRANSCRIPTION MODELING"  
- [@ArxivSound](https://x.com/ArxivSound/status/1813061958511296537) — 16 Jul 2024 (same line of work)

### **audio2chart** (audio → Guitar Hero charts — game-tab adjacent)
- **Paper:** [arxiv.org/abs/2511.03337](https://arxiv.org/abs/2511.03337)
- **Post:** [@ArxivSound](https://x.com/ArxivSound/status/1986299736199209435) — 6 Nov 2025

---

## 5. Open-source models / systems (mentioned on X)

| System | What it is | Post / links |
|--------|------------|--------------|
| **MuScriptor** (Kyutai + Mirelo) | Open multi-instrument **audio→MIDI** (guitar in full mix), MT3-like tokens; **not fret/tab** | [@kyutai_labs](https://x.com/kyutai_labs/status/2075540047613276197) — 10 Jul 2026: demo site, [github.com/muscriptor/muscriptor](https://github.com/muscriptor/muscriptor), [arxiv.org/abs/2607.08168](https://arxiv.org/abs/2607.08168); 170k recordings / 11k hrs; models 100M–1.3B; [@MireloAI API follow-up](https://x.com/MireloAI/status/2080342247418048750) |
| **MIDI-to-Tab + high-res guitar AMT** (C4DM) | Open research chain **audio→MIDI→tab** | [@drooby_doo](https://x.com/drooby_doo/status/1825919015094726907) |
| **GAPS benchmark model** | Classical-guitar AMT trained on GAPS | [@nicolasguozixun](https://x.com/nicolasguozixun/status/1870101360970018832) |
| **TART** | “Comprehensive tool” for technique-aware audio-to-tab | [@ArxivSound](https://x.com/ArxivSound/status/1975340265180447047) |
| **FretBench** | Open **LLM tab-reading** benchmark (not audio AMT) | [@JaidenCapra](https://x.com/JaidenCapra/status/2030826324735201425) — [fretbench.tymo.ai](https://fretbench.tymo.ai/) |

**License caveat (MuScriptor):** [@nikskld](https://x.com/nikskld/status/2076316488529564070) — 12 Jul 2026 — code MIT, **weights CC-BY-NC**.

---

## 6. Basic Pitch (guitar-related) — usage, not fine-tunes

X has **product/workflow chatter**, not research posts about guitar-specific fine-tunes:

| Post | Date | Content |
|------|------|---------|
| [@for_the_chill](https://x.com/for_the_chill/status/2033650673125122106) | 16 Mar 2026 | Basic Pitch → MIDI → agent outputs **guitar tab** suggestions |
| [@jakemclain_](https://x.com/jakemclain_/status/2020205162460246430) | 7 Feb 2026 | Port of Basic Pitch for simple melodies |
| [@gothok_](https://x.com/gothok_/status/2081130439595704686) | 25 Jul 2026 | Spotify Basic Pitch free/API |
| [@everolivares](https://x.com/everolivares/status/1998886251672318319) | 10 Dec 2025 | Basic Pitch install friction; mentions Aud2Stm2Mdi repo |

**No English posts found** in this sweep that name a **public fine-tuned Basic Pitch guitar checkpoint** with paper + GitHub release.

---

## 7. Benchmarks (as discussed on X)

| Benchmark | Metric / claim | Source post |
|-----------|----------------|-------------|
| **GuitarSet** (via GAPS model) | 91.2% note-onset F1 (Riley et al.); 88.1% zero-shot F1 (GAPS-trained) | [@xavriley](https://x.com/xavriley/status/1808111608247287821), [@nicolasguozixun](https://x.com/nicolasguozixun/status/1870101360970018832) |
| **GAPS** itself | Dataset + “benchmark transcription model” | [arxiv.org/abs/2408.08653](https://arxiv.org/abs/2408.08653) |
| **MuScriptor** (multi-instrument AMT) | “Best open multi-instrument transcription”; real-data fine-tune ≫ synthetic | [@kyutai_labs thread](https://x.com/kyutai_labs/status/2075540047613276197), [@vplandtweets](https://x.com/vplandtweets/status/2078200721539838383) |
| **FretBench** | LLMs reading written tab (not audio) | [@JaidenCapra](https://x.com/JaidenCapra/status/2030695415205835220) |

---

## Snapshot: 2025–2026 SOTA shape (from what X actually posts)

```text
Audio ──► pitch/MIDI AMT ──► fretting / tab
           │                    │
    GAPS, GuitarSet,      MIDI-to-Tab (2024)
    Velocity Pred (2026)  Fretting-Transformer (2025)
    MuScriptor (mix, 2026) ML MIDI→Tab (2025)
           │
    TART (2025): audio→tab + technique (end-to-end tool)
    GOAT (2025): paired audio↔tab data for both directions
    Fretiq (2026): string classification only
```

**Research community signal on X:** Queen Mary **C4DM** (`@xavriley`, `@nicolasguozixun`, `@drooby_doo`, `@c4dm`) and arXiv bots (`@ArxivSound`, `@SoundPapers`) dominate. Viral English discussion is mostly **MuScriptor** (general AMT), not fretted tab.

**Honest gaps from this live English search:**
1. **Dyad / power-chord datasets** — no named research posts.  
2. **Basic Pitch guitar fine-tunes** — usage only, no paper releases.  
3. **Consumer-grade audio→tab products** — practitioners still say papers exist, products lag.

If you want a follow-up, I can pull the arXiv abstracts for TART/GOAT/Fretiq into a comparison table (architecture, data, metrics) without relying on X.
