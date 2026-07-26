I'll search X and the web in EN+JP for MuScriptor (Kyutai/Mirelo, MT3-successor AMT): guitar quality reports, setup, weights, license, VRAM, and weaknesses.Digging into official sources and guitar-specific user reports next.# MuScriptor deep dive (EN + JP X + official sources)

**What it is:** Open-weight multi-instrument AMT (audio → multi-track MIDI). **Kyutai × Mirelo**, paper **2026-07-09**, public release thread **2026-07-10**. Explicit **MT3 successor** (MT3-like tokens, mel-spectrogram → autoregressive note events), but **decoder-only Transformer** + **large real-data finetune + RL**, not just MT3-scale synth.

---

## 1. Model weights, code, license, VRAM

| Item | Detail |
|------|--------|
| **Code** | [github.com/muscriptor/muscriptor](https://github.com/muscriptor/muscriptor) — **MIT** |
| **Weights** | [huggingface.co/MuScriptor](https://huggingface.co/MuScriptor) (org) — **gated, CC BY-NC 4.0** + extra “must own rights to input audio” conditions |
| **Variants** | `small` ~103M · `medium` ~307M (default) · `large` ~1.3–1.4B |
| **HF repos** | [muscriptor-small](https://huggingface.co/MuScriptor/muscriptor-small) · [muscriptor-medium](https://huggingface.co/MuScriptor/muscriptor-medium) · [muscriptor-large](https://huggingface.co/MuScriptor/muscriptor-large) |
| **Demo** | [muscriptor.kyutai.org](https://muscriptor.kyutai.org) |
| **Paper** | [arXiv:2607.08168](https://arxiv.org/abs/2607.08168) |
| **Blog** | [mirelo.ai/blog/turning-audio-to-midi](https://mirelo.ai/blog/turning-audio-to-midi) (2026-07-09) |
| **API (closed, higher quality)** | Mirelo API announced ~2026-07-23; open weights remain |

**VRAM (no official table; practical numbers):**

| Variant | Params | FP16 weights (rule-of-thumb) | Practical note |
|---------|--------|------------------------------|----------------|
| small | ~100M | ~0.2 GB | CPU-OK per README |
| medium | ~300M | ~0.6 GB | Default trade-off |
| large | ~1.3–1.4B | ~2.6–2.8 GB weights; **~3 GB FP16 total** (weights+acts) on third-party GPU guides | “really wants a GPU”; Apple Silicon MPS f16 works RTF>1 |

Consumer 8–12 GB cards are ample for large. Disk for weights is small vs LLMs; gating + HF login is the real friction.

**License gotcha (real user + cards):** Code free; **weights non-commercial**. Commercial product on open weights is not allowed. Rights warranty on *input* audio is explicit on HF.

---

## 2. Setup guides (canonical + community)

### Official quick path

```bash
# HF account → accept license on a model page (e.g. medium)
# then:
uvx hf auth login   # or export HF_TOKEN=hf_...

# One-shot web UI
uvx muscriptor serve
# Windows GPU:
uvx --torch-backend=cu128 muscriptor serve

# CLI
uvx muscriptor transcribe audio.wav -o out.mid --model large
# Guitar-focused hard mask (example from README abbreviations):
muscriptor transcribe audio.wav --instruments "distorted_electric_guitar,electric_bass,drums" -o gtr.mid
# list groups:
muscriptor list-instruments
```

Python:

```python
from pathlib import Path
from muscriptor import TranscriptionModel
model = TranscriptionModel.load_model("large")  # or "medium" / "small"
Path("out.mid").write_bytes(model.transcribe_to_midi("audio.wav"))
```

### Community setup posts

| User | Gist | Link |
|------|------|------|
| **@aivandroid** | Docker + CUDA + `MUSCRIPTOR_MODEL=large` | [x.com/aivandroid/…](https://x.com/aivandroid/status/2077656790217712003) |
| **@jtydhr88** | ComfyUI nodes for MuScriptor | [github.com/jtydhr88/ComfyUI-muscriptor](https://github.com/jtydhr88/ComfyUI-muscriptor) · [post](https://x.com/jtydhr88/status/2081202247703134482) |
| **@lachinhan** | REAPER plugin path (Hosi MuScriptor) | [YouTube](https://www.youtube.com/watch?v=DjHoyeK71ak) · [post](https://x.com/lachinhan/status/2080888550426624333) |
| **@grmchn4ai** | Local serve + temporary public trial server; large local > official demo on same track | [post](https://x.com/grmchn4ai/status/2076190087017324581) |
| HOT-Step-CPP notes | Native C++/GGML port; code MIT / weights CC BY-NC | [github.com/scragnog/HOT-Step-CPP](https://github.com/scragnog/HOT-Step-CPP) |

**Install friction:** HF gate + token required before first download. Intel Mac: Python ≤3.12 / torch 2.2.2 path documented in README.

---

## 3. Guitar / chords / power chords / distortion — what exists vs what doesn’t

### Official (stronger than casual X chatter)

- Paper frames **electric-guitar distortion** as a core multi-instrument failure mode historically: overlapping spectra + FX.  
- Training claims **classical → heavy metal**; guitar/bass/drums/piano dominate long-tailed instrument distribution.  
- **Fig.1** is a **guitar piano-roll** on their test set (TP/FP/FN color-coded).  
- Tokenizer uses **MT3_FULL_PLUS** (~36 groups). CLI explicitly supports **`distorted_electric_guitar`** (abbrev. `dist`) — so “distorted guitar” is a first-class class, not just “acoustic_guitar”.  
- Outputs: **pitch + onset/offset + instrument group**. **No velocity.** No string/fret/tab. **No two simultaneous same-pitch/same-instrument notes** (power unisons / doubled parts collapse).  
- Chord/key/tempo appear in **Mirelo product UI**, not as core open-model MIDI tokens (product stack on top).

### Real user reports on *guitar* specifically

There is **almost no English X deep-dive** on power chords / high-gain metal rhythm quality yet (model is ~2 weeks old as of 2026-07-26). Japanese hands-on is denser.

| User | Lang | Gist (guitar-relevant) | Link |
|------|------|------------------------|------|
| **@Ektmlnum** | JP | Full mix failed: brass→bass dumps; **e-piano + guitar merged**; sparse note pickup. **“Guitar chords might be usable as a reference; not sure if correct.”** Later: “maybe genre explains why others say accuracy is great.” | [2079690663218872824](https://x.com/Ektmlnum/status/2079690663218872824) · [2080153123520409865](https://x.com/Ektmlnum/status/2080153123520409865) |
| **@kaki_GT** | JP | Strings→MIDI impressive; **higher accuracy if you stem-split first then run per stem**; good for phrase analysis / 耳コピ time-save | [2079552514689806661](https://x.com/kaki_GT/status/2079552514689806661) |
| **@mameshiba______** | JP | Built Audio→MIDI app; **“practical-level MIDI, shocked”** (genre not specified) | [2079609494930415780](https://x.com/mameshiba______/status/2079609494930415780) |
| **@Sub_Cha_Sub** | JP | “Pretty good **but piano MIDI is disappointing**” (not guitar, but quality cap) | [2080868304722506056](https://x.com/Sub_Cha_Sub/status/2080868304722506056) |
| **@mjr3gdmi1** | JP | **“Tried it — accuracy totally bad, unusable, not worth the hype”** | [2077917316600435004](https://x.com/mjr3gdmi1/status/2077917316600435004) |
| **@Qto6BshdBJYXdch** | JP | Strong positive for band/arranger use; high-accuracy MIDI of modern tracks | [2079873511284416967](https://x.com/Qto6BshdBJYXdch/status/2079873511284416967) |
| **@grmchn4ai** | JP | Dense vocal DnB “taken”; **local large better than official web demo** | [2076190087017324581](https://x.com/grmchn4ai/status/2076190087017324581) |
| **@sonic_field** | EN | Technical note: what tokens preserve/omit (not guitar A/B) | [2078880397920731383](https://x.com/sonic_field/status/2078880397920731383) · [article](https://sonicfield.org/muscriptor-audio-to-midi) |
| **@nikskld** | EN | License warning (MIT code / NC weights / rights on audio) | [2076316488529564070](https://x.com/nikskld/status/2076316488529564070) |
| **@kyutai_labs** | EN | Official: any genre including **metal**; MIDI per instrument | [2075540047613276197](https://x.com/kyutai_labs/status/2075540047613276197) |

**Working hypothesis from users + paper (not a formal bench):**

| Scenario | Expected behavior |
|----------|-------------------|
| Clean rhythm chords, sparse mix | Often “usable as chord reference” (Ekt-style) |
| Distorted power chords in full metal mix | Officially *in scope*; **few independent X validations**; dense spectra + no velocity + same-pitch collapse hurt realism |
| Doubled guitars (L/R same riff) | Risk of merged/ghosted notes (taxonomy + same-pitch limit) |
| Best guitar accuracy | Stem/source-separate first (`@kaki_GT`), then `--instruments distorted_electric_guitar` (or acoustic/electric group) |
| Tab / fingering / palm mute / pick scrapes | **Out of scope** — piano-roll notes only |

---

## 4. Known weaknesses (official + user-corroborated)

| Weakness | Source |
|----------|--------|
| **No velocity / dynamics** | HF model card, paper, Sonic Field |
| **Same pitch + same instrument simultaneous notes impossible** | Tokenizer; metrics drop if kept in eval |
| **36 instrument groups** — e-piano vs guitar, brass vs bass confusions | Users (@Ektmlnum); fixed taxonomy |
| **Dense / processed mixes** | Official “use with care”; users report misses |
| **Genre skew** — pop + Western classical over-represented; rare instruments worse | Model card |
| **Offsets harder than onsets**; choral/sustained styles weak on timing | Paper benchmarks |
| **5 s chunking** — instrument identity can flicker without conditioning / prelude forcing | README |
| **Batching trades boundary quality** | `--no-prelude-forcing --batch-size 4` |
| **Open weights ≠ best quality** | Mirelo API / Studio claimed better; @grmchn4ai: local **large** > public demo |
| **CC BY-NC + rights warranty** | Blocks commercial SaaS on open weights |
| **Real training set not released** | Only weights + inference code |

Headline **D_Test** (1.3B full pipeline): Onset F1 **60.4** · Frame **72.4** · Offset **48.6** · Multi **47.8** vs YourMT3+ Multi **~22** — large leap, still not score-quality.

---

## 5. Real posts list (user · gist · link)

**Official / product**

1. **@kyutai_labs** — Launch: multi-instrument MIDI, metal/jazz/etc. · [x.com/…/2075540047613276197](https://x.com/kyutai_labs/status/2075540047613276197)  
2. **@MireloAI** — Open 3 models + later **API better than open weights** · [2080342247418048750](https://x.com/MireloAI/status/2080342247418048750)  
3. **@cjsimongabriel** (co-author) — API version “even better” · [2080348718566367570](https://x.com/cjsimongabriel/status/2080348718566367570)  

**Hands-on quality**

4. **@Ektmlnum** — Instrument dump/merge; guitar chords maybe reference only · [2079690663218872824](https://x.com/Ektmlnum/status/2079690663218872824)  
5. **@mjr3gdmi1** — “精度全然ダメ 使えん” · [2077917316600435004](https://x.com/mjr3gdmi1/status/2077917316600435004)  
6. **@mameshiba______** — Practical MIDI quality · [2079609494930415780](https://x.com/mameshiba______/status/2079609494930415780)  
7. **@Sub_Cha_Sub** — Good overall, piano weak · [2080868304722506056](https://x.com/Sub_Cha_Sub/status/2080868304722506056)  
8. **@kaki_GT** — Stem-first better; analysis tool · [2079552514689806661](https://x.com/kaki_GT/status/2079552514689806661)  
9. **@grmchn4ai** — Local large works on dense DnB; > demo · [2076190087017324581](https://x.com/grmchn4ai/status/2076190087017324581)  
10. **@Qto6BshdBJYXdch** — Strong band/MIDI enthusiast positive · [2079873511284416967](https://x.com/Qto6BshdBJYXdch/status/2079873511284416967)  

**Setup / ecosystem / policy**

11. **@aivandroid** — Docker GPU recipe · [2077656790217712003](https://x.com/aivandroid/status/2077656790217712003)  
12. **@jtydhr88** — ComfyUI-muscriptor · [2081202247703134482](https://x.com/jtydhr88/status/2081202247703134482)  
13. **@nikskld** — “Everyone says open source; weights are NC” · [2076316488529564070](https://x.com/nikskld/status/2076316488529564070)  
14. **@sonic_field** — Tokenization deep note · [2078880397920731383](https://x.com/sonic_field/status/2078880397920731383)  
15. **@kazemaneki** (guitar player bio) — ChatGPT-guided setup; quantize MIDI to bars · [2079568520808178175](https://x.com/kazemaneki/status/2079568520808178175)  

---

## 6. Practical take for guitarists

**Use it for:** rough multi-track sketch of rhythm harmony, bass/drums scaffolding, “what’s the chord shape of this section?” after quantize.  
**Don’t expect:** tab, voicings under wall-of-gain, palm-mute timing nuance, velocity/groove dynamics, or perfect instrument attribution in busy metal/J-pop without stems.  
**Best pipeline for guitar:** demucs/stem → MuScriptor **large** → `--instruments distorted_electric_guitar` (or acoustic/electric group) → DAW quantize → human fix.  
**Rights:** NC weights + “you must own rights to the audio you feed it” — fan transcriptions of commercial tracks are legally on you.

---

### Bottom line

MuScriptor is a real MT3-era leap for **full-mix multi-instrument MIDI**, with **guitar (incl. distorted)** in the official taxonomy and metal in the training story — but **as of late July 2026, X has almost no rigorous power-chord/distortion A/B reports**. Independent JP hands-on is **polarized** (practical / life-changing vs unusable), with the most guitar-specific note being **“chords maybe as reference; e-guitar often entangled with keys.”** For metal rhythm work, treat open **large** as a starting piano-roll, prefer stems, and treat Mirelo’s paid/API stack as the higher-quality fork if local open isn’t enough.
