Researching analysis-by-synthesis transcription verification (EN+JP) and sweeping related threads from prior rounds. Searching X and the web in parallel.Digging into papers, tools, and tighter X queries on analysis-by-synthesis note verification.# Analysis-by-Synthesis for Transcription Verification  
**X live (EN+JP) · papers · tools · final sweep (rounds 1–19 adjacency)**

---

## Core idea (what you asked for)

**Analysis-by-synthesis (AbS) for AMT / 採譜検証** means:

1. **Analyze** audio → candidate notes / MIDI / score  
2. **Synthesize** those notes back to audio (or a spectrogram)  
3. **Compare** re-synthesis vs original (spectral distance, residual energy, multi-resolution STFT loss, etc.)  
4. Use the residual to **accept / reject / edit** notes (or to train the model end-to-end)

Japanese keywords that match the literature and craft practice: **再合成 / リシンセシス**, **残差スペクトル**, **検証**, **採譜 / 自動採譜 / 耳コピ**, **MIDI音源で鳴らして聴き比べ**, **スペクトログラム重ね合わせ**.

This is **not** the same as “render a pretty demo of your MIDI.” The verification loop is: **notes that don’t explain residual energy are wrong or incomplete.**

---

## Who does this (research map)

### A. Classic generative AbS (pre–deep boom)

| Line | Who / what | Role of resynthesis |
|------|------------|---------------------|
| **NMF multipitch** | Smaragdis et al.; many follow-ups | Factor spectrum → reconstruct mixture; residual drives rank / pitch hypotheses |
| **Unsupervised piano transcription** | Berg-Kirkpatrick, Andreas, Klein (NIPS 2014) | Probabilistic generative model of piano audio; optimize latent notes so synthesis matches recording |
| **Residual / spectral modeling** | Goodwin (CNMAT) residual modeling; harmonic+noise analysis–synthesis | Partials explain harmonic energy; residual is the “unexplained” part |
| **JP multipitch / AMT** | 亀岡弘和 et al. (NTT / IPSJ) | 採譜 → 再構成で編集・聴取用途を明示; multipitch as generative inverse problem |

**Links**  
- Berg-Kirkpatrick unsupervised piano: [NIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2014/file/e51e118b28def0cabd5237b4e1fec499-Paper.pdf)  
- NMF multipitch (Smaragdis): [MERL TR](https://www.merl.com/publications/docs/TR2003-139.pdf)  
- 亀岡「多重音解析と自動採譜」: [PDF](https://www.kecl.ntt.co.jp/people/kameoka.hirokazu/publications/Kameoka2009IPSJMagazine08.pdf)

### B. Deep AMT with reconstruction as *training signal* (not just post-check)

| Work | AbS mechanism | Notes |
|------|---------------|-------|
| **Cheuk et al. ICPR 2020** | Aux **spectrogram reconstruction** head improves AMT accuracy | Reconstruction as regularizer / alternate objective, not full MIDI→audio loop |
| **ReconVAT (Cheuk et al.)** | Reconstruction + virtual adversarial training for semi-supervised AMT | Same family |
| **Choi & Cho – unsupervised drum transcription (ISMIR 2019)** | Differentiable audio reconstruction from drum events | Explicit analysis–synthesis training |
| **Inverse Drum Machine (Torres, Peeters, Richard 2025)** | Joint **ADT + one-shot sample synth**; convolve hits like a drum machine; train on mixture reconstruction | Strong modern “transcription + AbS” paper; no isolated stems needed |
| **DDSP / DDSP-inv (Engel et al.)** | Predict synth params so resynth matches audio → self-supervised **f0 / pitch** | AbS for pitch, not full poly AMT |
| **PESTO / related** | Survey cites analysis–synthesis family for self-supervised pitch | Continuity of DDSP-style AbS |
| **DDSP-Piano (Renault, Mignot, Roebel)** | Differentiable MIDI→piano audio | **Enabler** for gradient AbS loops on piano notes |
| **Kelz / interpretable poly transcription** | Cites prior **transcription–resynthesis** systems (transcription + language model + resynth) | Frames AMT as inverse problem |
| **Simonetta et al. 2022** | Perceptual eval of **resynthesized AMT MIDI** under instrument/room change | AbS for *evaluation*, not note-fix |

**Links**  
- Cheuk spectrogram reconstruction: https://arxiv.org/abs/2010.09969  
- Inverse Drum Machine: https://arxiv.org/abs/2505.03337  
- Simonetta perceptual resynthesis of AMT: https://arxiv.org/abs/2202.12257 · [HAL PDF](https://hal.science/hal-03208235v1/file/Perceptual_Evaluation_of_Resynthesized_Automatic_Music_Transcriptions-3.pdf)  
- DDSP-Piano: https://github.com/lrenault/ddsp-piano · [DAFx PDF](https://dafx2020.mdw.ac.at/proceedings/papers/DAFx20in22_paper_48.pdf)  
- DDSP: https://magenta.withgoogle.com/ddsp · https://arxiv.org/abs/2001.04643  
- Unsupervised drums (Choi): https://archives.ismir.net/ismir2019/paper/000020.pdf  
- Kelz interpretable AMT: https://arxiv.org/pdf/1909.01622  
- JP survey mentioning 再合成比較 as idea: [Zenn – ピアノ自動採譜](https://zenn.dev/nicopin/articles/1a6d58a1b6de68) (explicitly proposes differentiable piano + residual feedback)

### C. Practical craft loop (not always published as “AbS”)

Japanese / DAW practice already does a **manual AbS verification**:

1. audio2midi / 耳コピ → MIDI  
2. Play with GM / SC / VST  
3. **スペクトル比較** + 聴感 for volume/timing  
4. Fix wrong notes  

Documented on X:

- **@friskenzht** — explicit pipeline: *audio2midi → score check → **スペクトル比較で音量調整***  
  https://x.com/friskenzht/status/1692981896022835308  
- **@mdpc___** — SC-8850 repair verified by **曲を演奏してスペクトル比較**  
  https://x.com/mdpc___/status/1711654586321412460  
- **@mylikelist** — spectrogram overlay for 耳コピ  
  https://x.com/mylikelist/status/2078404055785947353  
- **@ticonacyan** — AMT MIDI usable for pitch fix but **MIDI音源として音を外す** → still near full 耳コピ  
  https://x.com/ticonacyan/status/2080670865856065613  

That craft loop is exactly the verification idea, with **human residual judgment** instead of a spectral loss.

---

## Tools you can actually run

### Synthesis side (notes → audio / spectrum)

| Tool | Use in AbS loop |
|------|-----------------|
| **FluidSynth / TiMidity / SC-series / DAW GM** | Cheap MIDI bounce for residual / A/B listen |
| **DDSP-Piano** | Differentiable / trainable piano for closed-loop training |
| **Magenta MT3 inverse / notes2audio (Hawthorne et al.)** | Diffusion **notes→spectrogram/audio** for multi-instrument; inverse of MT3 |
| **Pretty MIDI + librosa STFT** | DIY residual: `|S_orig| − |S_resynth|` |
| **mir_eval** | Symbolic note metrics *after* you trust residual regions |

**X / product anchors**  
- Hawthorne notes2audio diffusion: https://x.com/fjord41/status/1564347901031043072  
- MuScriptor multi-instrument A2M (full mix): https://x.com/MireloAI/status/2075536492177354771 · API: https://x.com/MireloAI/status/2080342247418048750 · writeup: https://sonicfield.org/muscriptor-audio-to-midi  
- NeuralNote (Basic Pitch in-plugin): https://x.com/DanKornas/status/2079357160400580624  
- YouTabs browser band/TAB transcription: https://youtabs.com/ · https://x.com/2zn01v/status/2079546304473301048  
- Stem-first then A2M improves accuracy (JP user on MuScriptor): https://x.com/kaki_GT/status/2079552514689806661  

### Distance metrics people use

| Metric | Typical role |
|--------|----------------|
| **Multi-scale STFT / spectral convergence** | Training loss (DDSP-style) |
| **L1/L2 on log-mel or CQT** | Residual map for “unexplained” energy |
| **Onset residual energy** | Localize missing/extra notes in time |
| **Perceptual MOS / listening** | Simonetta-style eval of resynth MIDI |
| **Note F1 / onset-offset F1** | Standard AMT score (not spectral AbS) |

**Caveat (important):** spectral residual ≠ note truth when **timbre of synthesizer ≠ original instrument**, room, pedals, FX. AbS verification is strongest when:
- instrument is known (piano / drum kit / chiptune), or  
- synth is **matched / learned** (DDSP-Piano, Inverse Drum Machine one-shots), or  
- you only trust residual **within harmonic templates** (NMF / score-informed).

---

## Recipe: spectral AbS note check (operator view)

```
audio x  →  AMT / human MIDI  →  notes n# Analysis-by-synthesis for transcription verification  
**X live (EN+JP) + literature synthesis · final sweep**

Core idea: **採譜結果を音に戻し、原音とスペクトル／波形で比較してノートの正誤を決める** — *render MIDI/score → audio → spectral (or perceptual) distance → accept / reject / correct notes*.

---

## 1. What “analysis-by-synthesis verification” actually is

| Stage | What happens |
|--------|----------------|
| **Analysis** | Audio → multipitch / AMT / drum onsets → symbolic notes |
| **Synthesis** | Notes → render (GM, sample player, DDSP, drum machine, notes2audio) |
| **Compare** | STFT/CQT residual, multi-scale spectral loss, SI-SDR, or listening |
| **Act** | Residual energy → missing notes; excess energy → false positives; local peaks → fix pitch/onset/velocity |

**Important split:**
- **Training-time AbS** — reconstruction loss *trains* the model (NMF, DDSP-inv, Inverse Drum Machine).
- **Inference-time verification** — post-hoc “does this MIDI explain the audio?” (practitioners; score-informed residual; under-productized as a standalone tool).

The second is what people mean by **再合成検証 / 採譜の妥当性確認**.

---

## 2. Who does this (lineages)

### A. Classic MIR / multipitch (spectral residual is the objective)
- **NMF / PLCA multipitch** (Smaragdis et al., later constrained NMF): dictionary of note spectra × activations; **reconstruction error = residual spectrum** drives which notes stay.  
  PDF: https://www.merl.com/publications/docs/TR2003-139.pdf  
- **亀岡弘和** — 多重音解析・自動採譜; explicitly discusses **楽譜→音響再構成** as utility of AMT:  
  https://www.kecl.ntt.co.jp/people/kameoka.hirokazu/publications/Kameoka2009IPSJMagazine08.pdf  
- **Residual / analysis–synthesis audio models** (Goodwin, CNMAT):  
  https://cnmat.berkeley.edu/sites/default/files/attachments/1996_Residual_Modeling_In_Music_Analysis.pdf  

### B. Unsupervised / generative transcription (AbS as supervision)
- **Berg-Kirkpatrick, Andreas, Klein (NeurIPS 2014)** — *Unsupervised Transcription of Piano Music*: generative piano model, transcription via explaining the signal.  
  https://proceedings.neurips.cc/paper_files/paper/2014/file/e51e118b28def0cabd5237b4e1fec499-Paper.pdf  
- **Choi & Cho** — unsupervised **drum** transcription via differentiable reconstruction (ISMIR lineage; cited as AbS drum prior).  
- **Inverse Drum Machine (Torres, Peeters, Richard, 2025)** — joint **ADT + one-shot synthesis**, train by reconstructing the mix (AbS end-to-end).  
  https://arxiv.org/abs/2505.03337  
  X: https://x.com/ArxivSound/status/1919966459024851162  

### C. Deep AMT with reconstruction / resynthesis loops
- **Cheuk, Luo, Benetos, Herremans (ICPR 2021)** — *The Effect of Spectrogram Reconstruction on Automatic Music Transcription*: multi-task **reconstruct spectrogram while transcribing** → better note accuracy.  
  https://arxiv.org/abs/2010.09969  
- **ReconVAT** (Cheuk et al.) — reconstruction + VAT for semi-supervised AMT:  
  https://arxiv.org/pdf/2107.04954  
- **Kelz et al. (ISMIR 2019)** — interpretable piano transcription; cites **transcription–resynthesis** systems (transcribe → LM → resynth stack):  
  https://arxiv.org/pdf/1909.01622  
- **Simonetta et al. (2022)** — *Perceptual measure for evaluating the **resynthesis** of AMT outputs* (not spectral distance for note fixing, but “MIDI back to audio” as evaluation axis):  
  https://arxiv.org/abs/2202.12257  

### D. Differentiable synthesis (closes the AbS gradient loop)
- **DDSP** (Engel / Magenta) — analysis/synthesis with spectral losses:  
  https://magenta.withgoogle.com/ddsp · https://arxiv.org/abs/2001.04643  
- **DDSP-Piano** (Renault et al.) — MIDI→audio differentiable piano:  
  code https://github.com/lrenault/ddsp-piano · paper https://doi.org/10.17743/jaes.2022.0102  
- **PESTO** review of AbS pitch estimators (DDSP-inv, spectral OT losses):  
  https://arxiv.org/html/2508.01488v2  
- **Zenn (JP)** explicitly proposes **差分駆動 analysis-by-synthesis** for piano AMT (MIDI → differentiable synth → residual → fix duration/velocity):  
  https://zenn.dev/nicopin/articles/1a6d58a1b6de68  

### E. Notes→audio (the render half of the pipeline)
- **Hawthorne / Magenta notes2audio** (MIDI multi-instrument → diffusion spectrograms) — inverse of MT3:  
  https://x.com/fjord41/status/1564347901031043072  
  Paper/code thread: listen/play/code links in that post.

### F. Japanese craft practice (not papers, same epistemology)
| Who | What |
|-----|------|
| [@friskenzht](https://x.com/friskenzht/status/1692981896022835308) | Explicit loop: **audio2midi → score align → スペクトル比較で音量** |
| [@mdpc___](https://x.com/mdpc___/status/1711654586321412460) | SC-8850 repair check: **MIDI演奏してスペクトル比較** |
| [@mylikelist](https://x.com/mylikelist/status/2078404055785947353) | Spectrogram overlay for 耳コピ |
| [@kaki_GT](https://x.com/kaki_GT/status/2079552514689806661) | MuScriptor MIDI + stem split for analysis (not full AbS, but same workflow family) |
| 亀岡 / NTT 解説 | 採譜 → 再構成 → テンポ・楽器・編曲変更 |

---

## 3. Tools (usable stack for verify/fix notes)

| Layer | Tools |
|--------|--------|
| **AMT (analysis)** | Spotify **Basic Pitch**, **NeuralNote** (Basic Pitch in-app) https://x.com/DanKornas/status/2079357160400580624 · **MT3** · **MuScriptor** (Mirelo×Kyutai) https://x.com/MireloAI/status/2075536492177354771 · API https://x.com/MireloAI/status/2080342247418048750 · https://github.com/muscriptor/muscriptor · **YouTabs** browser TAB/MIDI https://youtabs.com/ |
| **Render (synthesis)** | Fluidsynth / SoundFont; DAW MIDI bounce; **DDSP-Piano**; Magenta **notes2audio**; sample-based drum one-shots (Inverse Drum Machine style) |
| **Compare** | librosa STFT/CQT residual; multi-resolution spectral loss (DDSP-style); mir_eval note F1 *if* you have GT; **SDR/SIR/SAR** for stem-level; Adobe Audition / Spek / Sonic Visualiser for manual residual hunting |
| **Score-informed residual** | Align score/MIDI to audio → synthesize → subtract (classical score-informed separation stack; Ewert/Müller/Duan lineage) |

**Product gap:** almost no consumer “one-click **MIDI 再合成検証**” tool. People do it **by hand** (JP ear-copy) or **inside research training loops**. Closest modern end-to-end productized *philosophy*: Inverse Drum Machine (research) + MuScriptor/NeuralNote (analysis only).

---

## 4. Papers (priority reading list)

1. **Inverse Drum Machine** — joint transcription + AbS separation (2025)  
   https://arxiv.org/abs/2505.03337  
2. **Cheuk et al.** — spectrogram reconstruction improves AMT  
   https://arxiv.org/abs/2010.09969  
3. **Berg-Kirkpatrick et al.** — unsupervised piano transcription via generative AbS  
   NeurIPS 2014 PDF (above)  
4. **Simonetta et al.** — perceptual evaluation of AMT **resynthesis**  
   https://arxiv.org/abs/2202.12257  
5. **DDSP** + **DDSP-Piano** — differentiable resynthesis for residual training  
6. **Ycart et al. (TISMIR)** — perceptual validity of AMT metrics (why note F1 ≠ “sounds right”)  
   https://transactions.ismir.net/articles/10.5334/tismir.57  
7. **Benetos et al.** AMT overview (error types: octave/harmonic extras that AbS residual catches well)  
   https://labsites.rochester.edu/air/publications/benetatos19automaticmusic.pdf  
8. **Kameoka 多重音解析と自動採譜** (JP framing of 再構成)  
   NTT PDF above  

---

## 5. Practical recipe (verify/fix notes)

```
audio
  → AMT (Basic Pitch / MT3 / MuScriptor)
  → MIDI
  → render with matched timbre budget (same instrument class if possible)
  → align (onset DTW / score following)
  → residual = |STFT(x)| − α |STFT(ŷ)|   (or multi-scale log-mel L1)
  → residual peaks:
       +energy unexplained → likely missed note / wrong velocity low
       −energy over-explained → false positive / wrong pitch / octave
  → local search: toggle candidate notes, keep if residual ↓
```

**Caveats (why spectral distance alone fails):**
- Timbre mismatch dominates residual → false “errors.”
- Reverb / mix / FX not in MIDI → residual floor.
- Harmonics of true notes look like octave false positives in residual unless constrained.
- Velocity / pedaling wrong → large residual with correct pitches.

**Best regimes:** monophonic or isolated piano/drums; dry multi-track; score-informed classical. **Worst:** full commercial mix (need stem split first — exactly what JP users say for MuScriptor).

---

## 6. Final sweep — topics from rounds 1–19 worth one more pass

| Topic (likely R1–19 cluster) | Status now | One-link update |
|------------------------------|------------|-----------------|
| **Full-mix multi-instrument AMT** | Hot: MuScriptor open models + API | https://x.com/MireloAI/status/2075536492177354771 · writeup https://sonicfield.org/muscriptor-audio-to-midi |
| **Audio→MIDI plugins** | NeuralNote + Basic Pitch still the practical baseline | https://x.com/DanKornas/status/2079357160400580624 |
| **Browser / privacy-first 採譜** | YouTabs (client-side TAB/MIDI) | https://youtabs.com/ · https://x.com/2zn01v/status/2079546304473301048 |
| **Notes→audio / inverse of AMT** | Magenta notes2audio still the canonical “render MIDI realistically” research | https://x.com/fjord41/status/1564347901031043072 |
| **AbS for drums** | **New 2025 SOTA-style path**: Inverse Drum Machine | https://arxiv.org/abs/2505.03337 |
| **Spectrogram reconstruction multi-task** | Cheuk still the go-to citation for “reconstruction helps AMT” | https://arxiv.org/abs/2010.09969 |
| **Perceptual vs note metrics** | Simonetta + Ycart — still underused in product QA | arxiv 2202.12257 · TISMIR 57 |
| **DDSP / differentiable piano** | Enabler for *trainable* note verification | github.com/lrenault/ddsp-piano |
| **JP 耳コピ + スペクトル** | Craft loop explicit (audio2midi + spectrum compare) | https://x.com/friskenzht/status/1692981896022835308 |
| **Stem split → per-stem AMT** | Consensus for accuracy (JP + EN) | e.g. https://x.com/kaki_GT/status/2079552514689806661 |
| **Suno Advanced Split / “再合成” bleed reduction** | Product “re-synthesis” for stems (not AMT verify) | https://x.com/YUJIRO34160841/status/2065759910588231771 |
| **Spectrogram as ear-copy UI** | Still the main JP verification affordance | https://x.com/mylikelist/status/2078404055785947353 |

**Worth one more research bet after this series:**  
**AbS note-level “accept/reject” product** on top of MuScriptor/Basic Pitch + Fluidsynth/DDSP residual map — research pieces exist; **no dominant open tool** does toggle-note residual search for end users.

---

## 7. Key posts + links (bookmark set)

**EN research / product**
- MuScriptor launch: https://x.com/MireloAI/status/2075536492177354771  
- MuScriptor API: https://x.com/MireloAI/status/2080342247418048750  
- NeuralNote: https://x.com/DanKornas/status/2079357160400580624  
- notes2audio: https://x.com/fjord41/status/1564347901031043072  
- Inverse Drum Machine (bots): https://x.com/ArxivSound/status/1919966459024851162  
- Sonic Field on MuScriptor: https://sonicfield.org/muscriptor-audio-to-midi  

**JP craft / tools**
- スペクトル比較で音量調整: https://x.com/friskenzht/status/1692981896022835308  
- MIDI音源スペクトル比較: https://x.com/mdpc___/status/1711654586321412460  
- スペクトログラム重ね 耳コピ: https://x.com/mylikelist/status/2078404055785947353  
- YouTabs: https://x.com/2zn01v/status/2079546304473301048  
- MuScriptor 試用: https://x.com/kaki_GT/status/2079552514689806661  
- ピアノ採譜 + AbS アイデア: https://zenn.dev/nicopin/articles/1a6d58a1b6de68  

**Core papers**
- https://arxiv.org/abs/2505.03337  
- https://arxiv.org/abs/2010.09969  
- https://arxiv.org/abs/2202.12257  
- https://arxiv.org/abs/2001.04643 (DDSP)  
- https://github.com/lrenault/ddsp-piano  

---

## Bottom line

| Question | Answer |
|----------|--------|
| **Who does spectral AbS for note verification?** | Classic multipitch/NMF; unsupervised generative AMT; Cheuk-style reconstruction multi-task; Inverse Drum Machine; DDSP-inv pitch; **JP ear-copy craft** with spectrum overlays. |
| **Who ships a product that “resynthesizes MIDI and spectral-checks notes”?** | Essentially **nobody as a first-class product**. Analysis tools (MuScriptor, NeuralNote) and synthesis tools (notes2audio, DDSP-Piano) exist **separately**. |
| **Best modern paper for the full loop** | **Inverse Drum Machine (2025)** for drums; **Cheuk 2020** for reconstruction-aided AMT; **DDSP-Piano + residual** for piano research paths. |
| **JP keywords that work** | `再合成` + `採譜` / `耳コピ` / `スペクトル比較` / `スペクトログラム` — not “analysis-by-synthesis” as a phrase. |

---

*Note: Slack `#倉田_ログ` post was not available in this session (no Slack MCP tools connected). If you want that logged, re-enable Slack MCP or paste this summary there.*
