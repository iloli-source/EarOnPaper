I'll search X (English) for real complaints about AI guitar transcription failures across Basic Pitch, NeuralNote, MT3, AnthemScore, and Guitar2Tab.First pass was too generic. Narrowing to each tool name and the specific failure modes you listed.# AI guitar transcription failures on X (English)

**Scope note:** Live English X discussion of *named* tools (Basic Pitch / NeuralNote / MT3 / AnthemScore / Guitar2Tab) is thin. Most concrete complaints land on **Songsterr AI**, **RipX**, and generic **audio→MIDI / AI tab** tools. The four micro-failure modes you listed (chord→single note, harmonics→ghost notes, power-chord missing 5th, octave errors) are **rarely named that precisely** on X; the closest public failures are polyphony collapse, wrong tuning/register, missing notes, and instrument bleed.

---

## Real posts (username + gist)

### Named tools: Basic Pitch / NeuralNote / AnthemScore / MT3

| User | Gist |
|------|------|
| **@eleventhturning** | Songscription & AnthemScore exist, but results are **“hit or miss”** depending on how **complicated / polyphonic** the piece is. |
| **@4em11wa4** | Use AnthemScore for auto MIDI as a **base** — **“not 100% accurate”**; better if you have **vocal-only** stems. |
| **@ArtDuggy** | Workflow: **AI track split → AnthemScore → Online Sequencer**, then brute-force stretch/BPM align. Frames AI as a **start**, not finished. |
| **@for_the_chill** | Records guitar riff → **Basic Pitch → MIDI → Claude** for tab/theory. Positive use-case, not a failure report. |
| **@DanKornas** | Promo for **NeuralNote** (Basic Pitch via RTNeural/ONNX): polyphonic + pitch-bend — marketing, not field failure. |
| **@kyutai_labs** | Automatic music transcription has been **data-bottlenecked since MT3 (2022)**; implies polyphony/accuracy still limited by training data. |
| **@saen_dev** | “Audio-to-MIDI space has been dominated by **mediocre tools** for a decade”; asks if new models really solve **polyphony on real recordings** (e.g. jazz). |
| **@longestsoloever** | Melodyne/autotune tip for guitar: **“monophonic, not chord”** lines only — implicit that **chord polyphony** is the hard case. |

### Songsterr AI / AI guitar tabs (closest active complaint cluster)

| User | Gist |
|------|------|
| **@GreyFoxWeezterr** | Queue songs already have **Songsterr AI** tabs that are **inaccurate**; revision history shows “by Songsterr AI”. Follow-up: **drums/bass a mess** in choruses; **Drop-D tuning seems wrong**. |
| **@yuya_kev** | Tried **Songsterr AI** score generation — **“disappointing”**. |
| **@sonicfanctt** | Asks for human bass part because the only online option is **“songsterr ai slop”**. |
| **@PandaButt_** | Dadaroma tabs on Songsterr are AI; **“generalized and dumb down slop”** — learning by ear instead. |
| **@dkaygee** | Songsterr is a starting point but **“the tab is horrendously bad.”** |
| **@perfectsoundwtv** | Songsterr tab for *Venus as a Boy* **wrong** — needs **C# tuning**, not standard E. |
| **@sillyenthused** | Someone changed Songsterr tab for *How to Disappear Completely* — **“IT’S ALL FUCKING WRONG.”** |
| **@b2step_** | “Every single metal guitar tab on Songsterr is wrong.” |
| **@mbtmpro** | Fingerstyle (*Blackbird*) tabs often **inaccurate** — **missing notes**, rhythms, nuances. |

### Stem / separation tools used in the same pipeline

| User | Gist |
|------|------|
| **@markjklawrence** | First impressions of **RipX DAW** on Benson/Cobham: **pretty awful**; **mixes drums/percussion**, **can’t differentiate organ / Rhodes / guitar**, **horrible artifacts**. |
| **@rights_wrong** | Used **RipX AI** as help for bass — still had to **play and verify** by ear. |

---

## Failure modes (mapped from posts)

### 1. Polyphony / chord collapse (closest to “chords → single notes”)
- **@eleventhturning**: accuracy drops as music gets **more polyphonic**.
- **@longestsoloever**: pitch tools OK on **mono lines**, not **chords**.
- **@saen_dev**: industry baseline is **mediocre polyphony** on real mixes.
- **@PandaButt_ / @mbtmpro**: AI tabs **simplify / drop notes** (“dumbed down”, “missing notes”).

**Not found as explicit X English complaints:** power chords **losing the fifth** specifically.

### 2. Wrong tuning / register (closest to octave / pitch-class errors)
- **@GreyFoxWeezterr**: AI tab in **Drop-D that “seems wrong”**.
- **@perfectsoundwtv**: AI/human Songsterr tab fails **alternate tuning** (needs **C#**).
- These are **global pitch-frame errors** (tuning/register), not always classic ±1 octave, but same user-facing class as octave mistakes.

**Not found as explicit X English complaints:** systematic **octave error** named for Basic Pitch / NeuralNote / MT3.

### 3. Extra / wrong / messy notes (closest to harmonics → ghost notes)
- **@GreyFoxWeezterr**: AI drums/bass **“a bit of a mess”** in choruses.
- **@markjklawrence**: RipX **instrument bleed + artifacts** (ghost energy that isn’t the guitar).
- **@dkaygee / @sonicfanctt / @PandaButt_**: output is **slop** — untrustworthy note content.

**Not found as explicit X English complaints:** **natural harmonics** mis-tagged as **ghost notes**.

### 4. Full-mix / multi-instrument failure
- **@markjklawrence**: can’t separate **guitar vs keys vs drums**.
- Common implied fix in Japanese/English workflows: **stem first**, then transcribe.

### 5. “Draft only” quality (meta-failure)
- **@4em11wa4**, **@ArtDuggy**, vendor posts from Songscription: treat AI output as **base / cleanup target**, not ground truth.

---

## Workarounds people actually mention

| Workaround | Who / where | Why |
|------------|-------------|-----|
| **Stem first, then A2M** | @ArtDuggy (AI track split → AnthemScore); also common Demucs/UVR + Basic Pitch stacks in MIR Twitter | Full mixes confuse polyphony models |
| **Isolate the target part** (e.g. vocal-only or guitar-only) | @4em11wa4 | Cleaner input → fewer false notes |
| **Use AI as scaffold, then hand-edit** | @4em11wa4, Songscription’s own “clean up AI transcriptions” framing | Accept imperfect draft |
| **Time-align / BPM fix after export** | @ArtDuggy (stretch selection, adjust BPM) | Rhythm drift is common post-A2M |
| **Mono lines only for pitch tools** | @longestsoloever | Avoid chord polyphony in Melodyne-class tools |
| **Don’t trust AI tabs; learn by ear / wait for human tab** | @PandaButt_, @sonicfanctt, @GreyFoxWeezterr | Especially metal / dense arrangements |
| **Check tuning before believing frets** | @perfectsoundwtv, @GreyFoxWeezterr | Wrong global tuning → every fret wrong |

---

## Tool-by-tool summary (from this X pass)

| Tool | English X signal | Dominant complaint flavor |
|------|------------------|---------------------------|
| **Basic Pitch** | Mostly workflows / praise / infra mentions; few English failure posts | Used as step in pipeline; not a complaint magnet on X |
| **NeuralNote** | Mostly launches/promos | Almost no field failure posts |
| **MT3** | Research/history (“bottleneck since MT3”) | Data/accuracy ceiling, not guitar-specific horror stories |
| **AnthemScore** | Small but real: hit-or-miss, not 100%, good base | **Polyphony / piece-dependent accuracy** |
| **Guitar2Tab AI** | **No solid English product complaints found** under that name | — |
| **Songsterr AI** | **Loudest English complaint cluster** | Inaccurate tabs, wrong tuning, dumbed-down parts, “AI slop” |
| **RipX** (adjacent) | Clear negative field report | Instrument confusion + artifacts |

---

## Bottom line

On **live English X**, the failure story is less “named MIR models hallucinate harmonics as ghost notes” and more:

1. **Polyphony is the wall** (chords / dense parts degrade hard).  
2. **AI tabs oversimplify or invent** (missing notes, wrong tuning, messy rhythm section).  
3. **Full mixes need stems** before A2M.  
4. **Everything is a draft** — manual cleanup is assumed.

If you want a second pass, I can target **Reddit / GitHub issues / forums** (where Basic Pitch octave errors and AnthemScore polyphony bugs are usually documented more precisely than on X), or widen X to **Japanese** (there is more Basic Pitch field chatter there, e.g. speed/accuracy tradeoffs and stem→MIDI pipelines).
