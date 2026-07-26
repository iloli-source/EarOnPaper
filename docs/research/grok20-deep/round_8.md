I'll search X (English) and the web for who used IDMT-SMT-Guitar, GuitarSet, EGDB, DadaGP, and SynthTab for chord recall — and for any power-chord-specific training data work.Narrowing searches per dataset and for power-chord / dyad training work.## Bottom line

**Almost nobody is using these five datasets for classic ACR “chord recall” (root / maj–min / seventh label F1).**  
The shared research thread is **guitar tablature transcription (GTT)** — frame-level string–fret / multipitch F1, which *implicitly* recovers dyads and full chords as simultaneous frets.

The **one paper that ties IDMT + GuitarSet + EGDB + DadaGP + SynthTab into a clear “pretrain → better recall” story** is **SynthTab (Zang et al., ICASSP 2024)**.

---

### Who used what for improvements

| Dataset | Primary use | Who improved metrics with it | Metric type |
|--------|-------------|------------------------------|-------------|
| **IDMT-SMT-Guitar** | GTT + techniques; **subset 4 = chords / rhythm** | Kehling/Abeßer (origin); **Nadar et al. 2019** (7th-chord ACR); **SynthTab** as cross-set eval | Chord ACR (Nadar); Tab/pitch F1 (SynthTab) |
| **GuitarSet** | Solo acoustic hexaphonic; **instructed + performed chords** | Xi et al. baseline ACR; **TabCNN** (Wiggins & Kim 2019); **Byambatsogt MTL chords**; **GAPS** zero-shot SOTA; **SynthTab** pretrain+FT | Chord labels *and* tab F1 |
| **EGDB** | Electric DI + amp renders, tab-aligned | **Chen et al. 2022** multi-loss Transformer; **SynthTab** cross-set; Pedroza tone/FX robustness | Tab / multipitch F1 |
| **DadaGP** | Symbolic GuitarPro tokens (26k songs) | Sarmento generation (ProgGP, GTR-CTRL…); **source tabs for SynthTab**; chord-diagram work at SMC | Generation / synthesis source — not audio chord recall |
| **SynthTab** | ~6.7k–13k h synth audio from DadaGP | **Zang/Zhong/Cwitkowitz/Duan** — pretrain TabCNNx4 → better same-set **and** cross-set tab F1 on GuitarSet / IDMT / EGDB | **Tab F1 + multipitch F1** (the real “recall lift”) |

#### SynthTab is the key “chord/dyad recall improvement” result
Cross-dataset TabCNN without pretrain overfits hard (e.g. train GuitarSet → test IDMT/EGDB drops badly). Pretrain on SynthTab then fine-tune improves **both** matched and unmatched settings.

Pipeline: **DadaGP tabs → string-accurate VST render → SynthTab → pretrain GTT → fine-tune real sets**.

Site: [synthtab.dev](https://synthtab.dev/) · Paper: [arXiv:2309.09085](https://arxiv.org/abs/2309.09085) · Code: [github.com/yongyizang/SynthTab](https://github.com/yongyizang/SynthTab)

#### Chord-label (ACR) usage (secondary)
- **GuitarSet**: built-in instructed/performed chords; paper baseline ACR ≈ Humphrey-era numbers.  
- **IDMT**: chord-oriented eval subset; **Nadar, Abeßer, Grollmisch (SMC 2019)** — CNN for **seventh** chords. [PDF](https://www.smc2019.uma.es/articles/S8/S8_05_SMC2019_paper.pdf)  
- **Byambatsogt et al. 2020** — multi-task guitar chord sensing (+ robot aug); uses GuitarSet-style chord vocab. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7663498/)  
- **DadaGP**: not audio ACR; used for tab generation and (via SynthTab) audio pretraining. [arXiv:2107.14653](https://arxiv.org/abs/2107.14653)

#### Related SOTA path (GuitarSet note F1, not chord labels)
**Riley, Guo, Dixon — GAPS classical guitar → SOTA on GuitarSet** (~91% note-onset F1 / ~88% zero-shot in their posts).

---

### Power-chord-specific training data?

**No clear dedicated power-chord (open-fifth dyad) training effort** showed up in papers or X.

| Finding | Detail |
|--------|--------|
| Explicit “power chord dataset / curriculum” | **Not found** for IDMT / GuitarSet / EGDB / DadaGP / SynthTab |
| Closest content | IDMT isolated **chords**; Pedroza et al. electric set: **triads + sevenths** (not 5ths as a class) [arXiv:2501.03720](https://arxiv.org/pdf/2501.03720) |
| Implicit coverage | **DadaGP / SynthTab rock–metal tabs** contain many root+5 (and octave) shapes as **simultaneous frets**, but labels are **string–fret**, not `C5` / `power` ACR classes |
| Classic ACR corpora | Billboard / Isophonics etc. also **under-represent** power chords as a quality class |

If your goal is **power-chord recall**, you’d likely need: (1) GTT multipitch + rule “root+5(+oct)” from frets, or (2) a synthetic **dyad-labeled** layer on SynthTab/DadaGP — that curriculum does not appear published yet.

---

### X posts + links (EN / MIR-relevant)

| Who | Post | Link |
|-----|------|------|
| **@dadabots** | DadaGP v1.0 launch (26k GuitarPro, 115M tokens) | [x.com/dadabots/status/1299692519920480257](https://x.com/dadabots/status/1299692519920480257) |
| **@umpedronosapato** (Pedro Sarmento) | Rochester SynthTab synthesizes **#DadaGP** for tab transcription | [x.com/umpedronosapato/status/1704060964943884730](https://x.com/umpedronosapato/status/1704060964943884730) · paper [arxiv.org/abs/2309.09085](https://arxiv.org/abs/2309.09085) |
| **@ArxivSound** | SynthTab paper drop | [x.com/ArxivSound/status/1706115293787959602](https://x.com/ArxivSound/status/1706115293787959602) |
| **@umpedronosapato** | SMC: guitar **chord diagram** work + **#DadaGP** reuse | [x.com/umpedronosapato/status/1808877728881373445](https://x.com/umpedronosapato/status/1808877728881373445) |
| **@dadabots** | DadaGP lives on in audio→MIDI→tab (midi2tab) | [x.com/dadabots/status/1826536569974485414](https://x.com/dadabots/status/1826536569974485414) |
| **@xavriley** | GAPS → SOTA GuitarSet note F1 (ISMIR 2024) | [x.com/xavriley/status/1808111608247287821](https://x.com/xavriley/status/1808111608247287821) |
| **@nicolasguozixun** | GAPS train → GuitarSet zero-shot F1 88.1% | [x.com/nicolasguozixun/status/1870101360970018832](https://x.com/nicolasguozixun/status/1870101360970018832) |
| **@cackerman21 / arXiv bots** | Pedroza: real electric tones/FX → more robust **GTT** | e.g. [x.com/cackerman21/status/1840714278325612847](https://x.com/cackerman21/status/1840714278325612847) |

Little X chatter uses the phrase **“chord recall”** with these corpora; discourse is **tab F1 / multipitch / generation**.

---

### Dataset quick links

| Resource | Link |
|----------|------|
| IDMT-SMT-Guitar | [idmt.fraunhofer.de … guitar](https://www.idmt.fraunhofer.de/en/publications/datasets/guitar.html) · [Zenodo](https://zenodo.org/records/7544110) |
| GuitarSet | [ISMIR 2018 paper](https://archives.ismir.net/ismir2018/paper/000188.pdf) |
| EGDB | [arXiv:2202.09907](https://arxiv.org/abs/2202.09907) · [demo page](https://ss12f32v.github.io/Guitar-Transcription/) |
| DadaGP | [arXiv:2107.14653](https://arxiv.org/abs/2107.14653) · [github.com/dada-bots/dadaGP](https://github.com/dada-bots/dadaGP) |
| SynthTab | [synthtab.dev](https://synthtab.dev/) · [arXiv:2309.09085](https://arxiv.org/abs/2309.09085) |
| TabCNN | [ISMIR 2019](https://archives.ismir.net/ismir2019/paper/000033.pdf) · [github.com/andywiggins/tab-cnn](https://github.com/andywiggins/tab-cnn) |

---

### Practical takeaway for your stack

1. **Want measurable “recall” lifts with these names** → follow **SynthTab pretrain → fine-tune on GuitarSet / IDMT / EGDB** (tab F1, not Billboard-style chord symbols).  
2. **Want chord-symbol ACR** → GuitarSet chord tracks + Nadar/IDMT-style seventh work; these five are not a full ACR ecosystem.  
3. **Want power chords** → **gap**: no published power-chord-specific set; best bet is **dyad extraction from DadaGP/SynthTab frets** or custom synth of root–fifth labels.

I can dig next into (a) exact SynthTab F1 deltas from the paper figures, or (b) a minimal power-chord labeler design on top of DadaGP/SynthTab if that’s the product goal.
