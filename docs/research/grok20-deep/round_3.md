Researching chord-conditioned transcription ("先定和弦再定音") via X live search (EN+CN) and complementary sources for papers, pipelines, and implementable recipes.Digging into papers, code repos, and practitioner Chordify+pitch pipelines.# Chord-conditioned transcription: “先定和弦再定音”

**X live search (EN+CN) + papers/code synthesis.**  
Core idea: estimate harmony first (or jointly with a strong harmonic prior), then **constrain** multi-pitch / note decoding so non-chord (or out-of-scale) pitches are suppressed, reweighted, or snapped.

---

## 1. What X actually surfaces

### English (high signal)

| Signal | Source | Takeaway |
|--------|--------|----------|
| **Chord-aware AMT vs data-scale transformers** | [@jxmnop](https://x.com/jxmnop) (May 2025, ~4k likes): months of explicit chord structure in a piano CNN → beaten by Google **MT3** (transformer + lots of data, *no* explicit chords). Classic “bitter lesson” meme. | Structure helps small-data regimes; SOTA AMT mostly abandoned hand-built chord graphs. |
| **Counter-take** | [@ObjRandom](https://x.com/ObjRandom): pure scale may still hallucinate; “something good” remains in chord-aware models; asks WAV→MIDI vs score. | Practitioner tension: structure vs scale. |
| **Chordify as “the” consumer chord pipeline** | Long history from [@chordify](https://x.com/chordify) (algorithm updates, hackathons) through musicians using it for rough lead-sheet harmony. | Chords-only product; people *want* to pair it with pitch tools but accuracy complaints are common. |
| **Commercial “chord → constrain pitch” UX** | [@Celemony](https://x.com/Celemony) Melodyne training: Note Assignment + Chord Track; white lanes = chord tones, gray = foreign; **Chord Snap**. | Closest mass-market implementation of 先定和弦再定音 for *editing*, not just analysis. |
| **Seq. optimization for harmony** | Practitioner: simulated annealing + **Viterbi** over chord paths (least-cost progression). | Same decoder pattern you want for note lattices. |

### Chinese (lower density on ML pipelines)

CN keyword/semantic hits rarely name “先定和弦再定音” as an AMT architecture. Closer content:

- **教学/扒谱习惯**: “先确定和弦最高音，再扩展另外两个键” (voicing/practice order, not audio ML).
- **工具层**: Chord AI、Klangio、Songscription、Logic Chord ID、听音识谱小程序 — chords and notes as *parallel products*, not a documented two-stage constraint graph.
- **乐理长文** (音阶/微分音等): high engagement, not implementable AMT.

**Net:** the *phrase* is more Chinese craft language; the *pipeline pattern* is clearer in EN research + Melodyne + open MIR stacks.

---

## 2. Papers & research map (what is real vs adjacent)

### Directly on-theme (harmony constrains multi-pitch / AMT)

| Work | Role |
|------|------|
| **Benetos & Weyde, ISMIR 2013** — EDHMM multi-instrument AMT | Pitch-wise duration HMMs + spectrogram factorization + **two-stage** cleanup of spurious pitches. Future work explicitly: *“integrating … chord and key detection for improving multi-pitch detection.”* Recipe ancestor of “pass1 notes → pass2 re-estimate under tighter set.” |
| **Benetos & Dixon (related HMM/PLCA AMT line)** | Temporal constraints on note evolution; natural place to plug key/chord as global priors. |
| **Template / chromagram ACE lineage** (e.g. Oudre et al.; Stark/Plumbley harmonic energy) | Usually **multipitch/chroma → chords**. Invertible: once you have chords, use **templates as soft masks** on pitch activations. |
| **madmom CNN + CRF chords** (Korzeniowski & Widmer) | Best open *frame→label* chord stack; CRF = sequence smoothing before you freeze a chord timeline for note decoding. |
| **BTC — Bi-directional Transformer for Chord Recognition (ISMIR 2019)** | Single-phase transformer ACE; used as teacher in ChordMini-style distillation. |
| **music-x-lab Large-Vocabulary Chord Recognition (ISMIR 2019)** | Pretrained large-vocab chord models (structure decomposition). |

### Adjacent (often confused in search)

| Work | Why it appears | Not the same as |
|------|----------------|-----------------|
| MidiNet, MelodyDiffusion, Magenta chord-conditioned RNNs | **Chord → generate** notes | Transcription (audio → notes) |
| Onsets & Frames | **Onset → frames** conditioning | Chord conditioning (same *two-head* idea, different prior) |
| MT3 / large AMT transformers | SOTA multi-instrument AMT | Explicit chord graph (bitter lesson target) |
| InstructME chord matrix for edit | Harmony-preserving *editing* | Note detection |

### Practitioner “paper-shaped” products

- **Chordify**: production ACE + beat alignment; public narrative is chord transcription for play-along, not open multipitch decoder.
- **Melodyne Chord Track + Pitch Grid (Chord / Chord Scale)**: analyze chords → constrain edit/snap grid.
- **ChordMini** ([chordmini.me](https://www.chordmini.me), [ptnghia-j/ChordMiniApp](https://github.com/ptnghia-j/ChordMiniApp)): beats (Beat-Transformer / madmom) + chords (CNN-LSTM, BTC-*) + piano visualizer + **experimental melody** — closest open *app* stacking harmony + pitch UI.

---

## 3. Open implementations you can wire today

| Stack | What you get | Use in 先定和弦再定音 |
|-------|--------------|------------------------|
| [CPJKU/madmom](https://github.com/CPJKU/madmom) `CNNChordRecognition` | Framewise chords + CRF decoding | Freeze chord segments |
| [jayg996/BTC-ISMIR19](https://github.com/jayg996/BTC-ISMIR19) | Transformer ACE | Higher-quality chord timeline |
| [music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition](https://github.com/music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition) | Large-vocab chords | Jazzier labels (7ths, etc.) |
| [sevagh/chord-detection](https://github.com/sevagh/chord-detection) | Classical multipitch → chroma → key/chord (ESACF, Klapuri iterative F0, …) | Classic DSP path; also reverse-engineerable templates |
| Spotify **Basic Pitch** | Instrument-agnostic note MIDI | Unconstrained note candidates |
| Magenta **Onsets & Frames** / piano AMT | Strong piano MIDI | Post-filter with chords |
| Google **MT3** | Multi-instrument AMT | Soft re-score notes with chord prior (don’t retrain first) |
| Chordino (vamp) / Chordino-from-MIDI | Symbolic or audio chords | Align MIDI roll to labels |
| **Melodyne** (closed) | Chord Track + Chord Snap | Gold UX reference |

Chordify has **no open decoder**; treat as black-box chord track (UI/export) unless you have a private partnership API.

---

## 4. Implementable recipes

### Recipe A — Cheap & robust: **chords first, hard/soft pitch mask** (production default)

```
audio
  ├─► Chord model (madmom / BTC / Chordify export)
  │     → segments: [(t0,t1, "Am7"), ...]
  │     → optional key + beat grid
  └─► Note model (Basic Pitch / OaF / MT3)
        → candidates: [(onset, offset, midi, conf), ...]

for each note n at time t:
  C = chord_at(t)                    # pitch-class set + optional extensions
  S = scale_from(key, C)             # diatonic or chord-scale (e.g. Dorian over IIm7)
  score = log conf(n)
        + λ_chord * 1[pc(n) ∈ C]     # hard: drop if not in C when conf < τ
        + λ_scale * 1[pc(n) ∈ S]     # allow passing tones if conf high
        - λ_odd   * distance_to_chord_tone(n, C)

emit notes with score > θ; merge overlaps; quantize to beat grid
```

**Defaults that work on pop/rock:**

- λ_chord ≈ 2–4 (nats if conf is log-prob), λ_scale ≈ 0.5–1  
- Allow **non-chord tones** if `conf > 0.85` and duration short (< 120 ms) → ornaments  
- Bass (MIDI < 48): prefer chord roots / fifths only  
- Melody track (highest voice): prefer chord tones on strong beats; freer on weak beats  

**Chordify variant:** export chord CSV → same mask over Basic Pitch MIDI. Quality ceiling = Chordify errors × pitch model errors.

---

### Recipe B — **Viterbi chord path, then lattice re-decode** (classic MIR)

```
1. Frame chroma / DNN chord posteriors P(c|t)
2. Transition matrix T(c→c') from theory or data
   - self-loop high
   - circle-of-fifths / relative major-minor cheap
   - random jump expensive
3. Viterbi → global chord sequence ĉ_t
4. Build pitch lattice from multipitch or AMT frames
5. Path cost for pitch set Y_t:
     cost = -log P_acoustic(Y_t|audio)
          + α * ||Y_t \ chord_tones(ĉ_t)||   # foreign pitch penalty
          + β * duration / continuity terms
6. Second Viterbi / beam search over Y_t
```

Matches practitioner “Viterbi for least-cost chord changes” + note tracking literature.

---

### Recipe C — **Two-pass AMT** (Benetos-style, modernized)

```
Pass 1: unconstrained AMT → piano-roll R1
Pass 2: estimate chords from R1 (or from audio ACE in parallel)
        restrict active pitch set per bar to:
          chord tones ∪ top-k acoustic peaks ∪ melody peaks
        re-run decoder / NMF / frame thresholding only on that set
```

Good when Pass 1 has many harmonic ghosts (piano/guitar).

---

### Recipe D — **Melodyne-shaped post-edit API** (UI + batch)

```
AnalyzeChords(audio) → ChordTrack
PitchGrid = { Chord | ChordScale | Chromatic }
for note in NoteAssignment(audio):
  if mode == ChordSnap:
    note.pitch = nearest(note.pitch, white_lanes(ChordTrack, t))
  elif mode == SoftGrid:
    note.pitch_score *= chord_affinity(...)
```

Implement white/gray lanes as MIDI pitch-class masks for human-in-the-loop or auto-snap export.

---

### Recipe E — **Separation → per-stem chords → constrained transcription**

```
Demucs / HT-Demucs
  → drums | bass | other | vocals
bass  → monophonic pitch (CREPE/pYIN)  # anchors roots
other → chords (ACE) + multipitch
vocals → melody; constrain to chord-scale on strong beats
merge with voice leading rules
```

Best for full mixes; Chordify-like apps often skip separation and pay for it in accuracy.

---

### Recipe F — **LLM as chord-aware post-processor** (2025-style)

From recent ACE work that feeds MIR tool outputs into GPT-style reasoners:

```
tools = {chords, key, beats, basic_pitch_notes, optional lyrics}
prompt 5-stage CoT: consistency, theory repair, conflict resolve
output corrected chord list + flagged illegal notes
```

Use only as **post-process** on structured JSON, not as primary pitch estimator.

---

## 5. Concrete stack combinations (pick one)

| Goal | Stack |
|------|--------|
| Fast open MVP | madmom chords + Basic Pitch + Recipe A mask |
| Better pop chords | BTC / large-vocab ACE + Basic Pitch + beat-sync (BeatNet / madmom) |
| Piano solo quality | Onsets & Frames / piano model + chords-from-MIDI (Chordino) + soft mask |
| Multi-instrument | MT3 notes + independent ACE timeline + soft re-score (don’t expect MT3 internals) |
| Guitar tabs | multipitch + fretting constraints + chord templates (guitar literature) |
| DAW-grade UX reference | Melodyne Chord Track / Logic Chord ID + Session Players |

---

## 6. Chord → pitch-class masks (drop-in)

```python
PC = {"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,
      "F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}

QUAL = {
  "maj":  (0,4,7), "min": (0,3,7), "dim": (0,3,6), "aug": (0,4,8),
  "7":    (0,4,7,10), "maj7": (0,4,7,11), "min7": (0,3,7,10),
  "m7b5": (0,3,6,10), "sus2": (0,2,7), "sus4": (0,5,7),
}

def chord_pcs(label: str) -> set[int]:
    # parse "Am7", "F#maj7", "Bb" → root + quality
    ...
    return { (root + i) % 12 for i in QUAL[quality] }

def note_score(midi, conf, chord_label, key_pcs, *,
               l_chord=3.0, l_scale=0.7, tau=0.85):
    pc = midi % 12
    in_c = pc in chord_pcs(chord_label)
    in_s = pc in key_pcs
    if not in_c and conf < tau:
        return -1e9  # hard drop weak non-chord tones
    return conf + l_chord * in_c + l_scale * in_s
```

Beat-sync: snap chord boundaries to nearest downbeats before applying masks.

---

## 7. Evaluation & failure modes

| Metric | Notes |
|--------|--------|
| Frame / note F1 (mir_eval) | Always report **with and without** chord constraint |
| Chord-tone precision | Did you kill real tensions (9, #11)? |
| Melody continuity | Hard mask often shreds non-chord melody notes |

**Failures:**

1. Wrong chord → systematic wrong notes (error cascades). Mitigate with soft λ, not hard delete.  
2. Jazz / modal / chromatic music: need ChordScale, not triad-only.  
3. Dense polyphony: ACE collapses; separation first.  
4. Bitter lesson: for pure accuracy with enough data, end-to-end AMT may win; **constraints still win** for playable lead sheets, pedagogy, and low-data instruments.

---

## 8. Minimal 1-day build plan

1. `CNNChordRecognition` → `.lab` chord file  
2. Basic Pitch → MIDI  
3. Align on time; Recipe A soft scores  
4. Export MIDI + chord symbols; listen on 10 pop tracks  
5. Tune λ / τ; add beat grid; optional Demucs bass root check  

---

## 9. Bottom line

- **X (EN):** strongest narrative is Jack Morris’s chord-aware AMT vs MT3; Chordify as consumer chord layer; Melodyne as the practical “chord then constrain pitch” product.  
- **X (CN):** little open ML discourse on 先定和弦再定音; more 扒谱 craft and commercial chord/score apps.  
- **Science:** full joint chord→multipitch models are thinner than chord *generation* or pure ACE; Benetos-style two-stage + CRF/Viterbi chords + modern pitch nets is the implementable synthesis.  
- **Best recipe today:** **ACE timeline (madmom/BTC) + unconstrained AMT candidates + soft chord/scale re-score (Recipe A/B)**, with Melodyne-like optional hard snap for export cleanliness.

I don’t have a working Slack integration in this session, so the #倉田_ログ post couldn’t be sent automatically—paste this summary there if you need the log.
