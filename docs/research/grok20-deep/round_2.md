I'll search X for MuScriptor / Basic Pitch / MT3 comparisons and for practitioner posts on multi-model AMT ensemble patterns.Found one practitioner ensemble report; digging deeper for head-to-heads and more multi-model merge patterns.## Bottom line

**No solid public 3-way bench of MuScriptor vs Basic Pitch vs MT3 on X.** People almost never put Basic Pitch in the same table as multi-instrument models—different job (pitch/bend/velocity on general polyphony vs full-mix multi-track MIDI).

What *does* show up: **MuScriptor vs MT3/YourMT3+** (paper + CMU MulTTiPop), and **one clear practitioner ensemble** that literally merges MuScriptor + Basic Pitch + a chord model.

---

## 1. Benchmarks / comparisons (closest thing)

### Official / paper-side (MuScriptor vs YourMT3+, not Basic Pitch)

| Source | Claim | Link |
|--------|--------|------|
| **@Marktechpost** (summarizes Kyutai/Mirelo paper) | Multi F1 **48.2 vs 21.9** for YourMT3+; Onset 60.4 vs 32.5; Frame 73.3 vs 45.5 | [x.com/Marktechpost/status/2075689501855457545](https://x.com/Marktechpost/status/2075689501855457545) |
| **@kyutai_labs** | “Best open model for multi-instrument transcription” | [x.com/kyutai_labs/status/2075540047613276197](https://x.com/kyutai_labs/status/2075540047613276197) |
| **@MireloAI** launch | Full-mix multi-instrument MIDI; no stems required | [x.com/MireloAI/status/2075536492177354771](https://x.com/MireloAI/status/2075536492177354771) |

### Independent eval: MulTTiPop (MT3 / YourMT3+ / MuScriptor)

CMU G-CLef lab’s multitrack pop eval set is the best **third-party** thread on X:

| Post | Takeaway | Link |
|------|----------|------|
| **@pruynathan** (thread) | MulTTiPop: 3.5h / 572 segments aligned pop multitrack | [x.com/pruynathan/status/2075772813462450389](https://x.com/pruynathan/status/2075772813462450389) |
| same thread | **MT3**: inconsistent arrangement across parts; **YourMT3+**: oversimplifies arrangements/rhythms | [x.com/pruynathan/status/2075772818457813478](https://x.com/pruynathan/status/2075772818457813478) |
| same thread | **MuScriptor**: most coherent of models tested; still inconsistent instrument parts across chunks | [x.com/pruynathan/status/2075772820190003374](https://x.com/pruynathan/status/2075772820190003374) |
| same thread | Quant: SOTA when instruments reduced to **harmonic/percussive**; **mid-pack** if exact instrument labels required | [x.com/pruynathan/status/2075772822211756101](https://x.com/pruynathan/status/2075772822211756101) |
| **@chrisdonahuey** | MuScriptor SotA on MulTTiPop, “plenty of headroom” | [x.com/chrisdonahuey/status/2075810524609101972](https://x.com/chrisdonahuey/status/2075810524609101972) |
| Paper / data | arXiv + HF | [arxiv.org/abs/2607.08756](https://arxiv.org/abs/2607.08756) · [gclef-cmu.org/multtipop](http://gclef-cmu.org/multtipop/) · [HF multtipop](https://huggingface.co/datasets/gclef-cmu/multtipop) |

### Practitioner head-to-heads (qualitative)

| Author | Report | Link |
|--------|--------|------|
| **@__j_v_a__** | Tried MuScriptor vs **YourMT3+**: good overall; better with fewer instruments; complex tracks “50/50, sometimes loses slightly” but more stable | [x.com/__j_v_a__/status/2077051103490060699](https://x.com/__j_v_a__/status/2077051103490060699) |
| **@anime_magic_2** | Same hang/stretch errors as MT3 / YourMT3+ | [x.com/anime_magic_2/status/2075725579387859048](https://x.com/anime_magic_2/status/2075725579387859048) |
| **@mjr3gdmi1** | “Accuracy useless, not worth the hype” | [x.com/mjr3gdmi1/status/2077917316600435004](https://x.com/mjr3gdmi1/status/2077917316600435004) |
| **@komonogame** | Far better than some DAW built-in MIDI conversion | [x.com/komonogame/status/2076548258097484239](https://x.com/komonogame/status/2076548258097484239) |
| **@mameshiba______** | “Shockingly practical MIDI” | [x.com/mameshiba______/status/2079609494930415780](https://x.com/mameshiba______/status/2079609494930415780) |
| **@Ektmlnum** | “Good accuracy tweets may be genre-dependent” | [x.com/Ektmlnum/status/2080153123520409865](https://x.com/Ektmlnum/status/2080153123520409865) |

### Basic Pitch in the multi-instrument conversation

Almost no side-by-side with MuScriptor/MT3. Closest practitioner takes:

| Author | Report | Link |
|--------|--------|------|
| **@EzraSandzer** (2023) | Basic Pitch polyphony **poor for multi-instrument**; prefers Samplab 2 **with stem separation** | [x.com/EzraSandzer/status/1681876129551093760](https://x.com/EzraSandzer/status/1681876129551093760) |
| **@DanKornas** | NeuralNote = Basic Pitch in a plugin (poly + pitch-bend), not multi-track AMT | [x.com/DanKornas/status/2079357160400580624](https://x.com/DanKornas/status/2079357160400580624) |

**Why the gap:** Basic Pitch ≈ general polyphony + bend/velocity; MT3/YourMT3+/MuScriptor ≈ multi-instrument full-mix token AMT. Apples/oranges on X.

---

## 2. Ensemble / merge patterns (real practitioner reports)

### A. True multi-model **output merge** (best match to your question)

**@2zn01v** — YouTabs (`youtabs.com`): explicit complementary ensemble

> Base = **MuScriptor**; velocity + pitch bend = **Basic Pitch**; chords = **ISMIR2019 LVCR**; then **pick the “significant” results** across analyses (confidence-style select, not naive union).

| Post | Content | Link |
|------|---------|------|
| Product launch | Browser AMT → MIDI / TAB / chords; local processing | [x.com/2zn01v/status/2079546304473301048](https://x.com/2zn01v/status/2079546304473301048) |
| **Architecture** | MuScriptor + Basic Pitch + LVCR, significance merge | [x.com/2zn01v/status/2079554048135704732](https://x.com/2zn01v/status/2079554048135704732) |

This is the only clear **union/vote/confidence-style multi-AMT merge** report found on X for these models.

### B. Pipeline ensembles (separation → transcription)

Not multi-model voting, but what most practitioners actually ship:

| Author | Pattern | Link |
|--------|---------|------|
| **@fffiloni** | Gradio MuScriptor demo with **Demucs split** as prep | [x.com/fffiloni/status/2078128083995963779](https://x.com/fffiloni/status/2078128083995963779) |
| **@kaki_GT** | Stem-split in Logic **per instrument first** → higher accuracy than full-mix alone | [x.com/kaki_GT/status/2079552514689806661](https://x.com/kaki_GT/status/2079552514689806661) |
| **@EzraSandzer** | Stem separation + transcription (Samplab) beats bare Basic Pitch on multi-instrument | [x.com/EzraSandzer/status/1681876129551093760](https://x.com/EzraSandzer/status/1681876129551093760) |
| **@apt_hq** | Uses **Basic Pitch + Demucs** as a known stack | [x.com/apt_hq/status/2073379388326851013](https://x.com/apt_hq/status/2073379388326851013) |

### C. What was *not* found

On X (EN-focused search + JP hits that are still relevant):

- No practitioner **majority-vote / note-union** across MT3 + Basic Pitch + MuScriptor
- No open “MIDI note confidence fusion” write-ups for these three specifically
- LLM-style ensemble posts (majority vote across GPT/Claude/etc.) do **not** map to AMT note merge here

---

## 3. Practical map (from the posts above)

| Model | Strengths people cite | Weak spots people cite |
|-------|----------------------|------------------------|
| **MuScriptor** | Full-mix multi-instrument; coherence; paper Multi F1 >> YourMT3+; SotA on MulTTiPop coarse labels | Chunk-level instrument inconsistency; exact program labels; genre variance; hang errors |
| **MT3 / YourMT3+** | Established multi-instrument baseline | Arrangement drift (MT3); oversimplification (YourMT3+); lower F1 vs MuScriptor on Kyutai set |
| **Basic Pitch** | Velocity, pitch bend, lightweight polyphony | Weak multi-instrument full mix; people pair it as a *detail* model, not the backbone |

**Dominant real-world pattern:**  
`stem separation (Demucs/UVR/Logic) → multi-instrument AMT (MuScriptor/MT3) → optional Basic Pitch for dynamics/bends → separate chord model`  
with **attribute-level merge** (as in YouTabs), not note-level voting.

---

## 4. Highest-signal links (shortlist)

**Comparisons**
1. [MulTTiPop thread (MT3 / YourMT3+ / MuScriptor)](https://x.com/pruynathan/status/2075772813462450389)  
2. [Chris Donahue: MuScriptor SotA on MulTTiPop](https://x.com/chrisdonahuey/status/2075810524609101972)  
3. [Marktechpost: MuScriptor Multi F1 vs YourMT3+](https://x.com/Marktechpost/status/2075689501855457545)  
4. [JP practitioner MuScriptor vs YourMT3+](https://x.com/__j_v_a__/status/2077051103490060699)  

**Ensemble / merge**
5. [YouTabs: MuScriptor + Basic Pitch + LVCR significance merge](https://x.com/2zn01v/status/2079554048135704732)  
6. [Demucs + MuScriptor Gradio](https://x.com/fffiloni/status/2078128083995963779)  
7. [Stem-split first for higher accuracy](https://x.com/kaki_GT/status/2079552514689806661)  

If you want a follow-up, I can dig for non-X sources (papers/GitHub issues on note-level fusion / onset voting for AMT) or re-run X for Japanese-only bench threads only.
