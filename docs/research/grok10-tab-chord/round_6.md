Searching X for practitioner posts on polyphonic guitar transcription engines and chord accuracy comparisons.Digging deeper into commercial tools and guitar-specific models.# Polyphonic guitar transcription on X (2025–2026): what people actually say

**Caveat:** X has almost **no hard chord F1 numbers** from independent users. What follows is ranked by **reported perceived quality + how often practitioners actually use the tool for chords/polyphony**, not lab benchmarks. Academic engines (TabCNN, GuitarSet-trained models, EGDB, CREPE/PESTO, pure Klapuri DSP) barely show up in practitioner talk.

---

## Headline (2026)

| Rank | Engine | Chord / polyphony signal on X | Who uses it for guitar-ish work |
|------|--------|-------------------------------|--------------------------------|
| **1** | **MuScriptor** (Kyutai + Mirelo, Jul 2026) | Explicit **chord + key + tempo** from full mix; positioned as successor to MT3-era AMT | Producers, app builders, chord-chart hobbyists |
| **2** | **YourMT3+ / MR-MT3 / MT3 family** | Still “strongest general multi-instrument” pre-MuScriptor; mixed quality reports | MIR builders, guitar-tab app fine-tuners |
| **3** | **Melodyne (polyphonic / DNA)** | Practitioners use stems → Melodyne for **chord reference** | Working musicians, mix engineers |
| **4** | **Basic Pitch** (Spotify) + stem split | Default free poly A2M; good on simple/medium chords, weak alone on dense mixes | DTM, riff→tab pipelines, NeuralNote users |
| **5** | **AnthemScore / Chordify / commercial A2M** | Convenience tools; sparse quality debate | Casual learners, “one-click score” users |
| **6** | **Onsets & Frames, CREPE/PESTO, Klapuri, TabCNN/EGDB/GuitarSet** | History / papers only — almost **no “I use this for guitar chords”** posts | Researchers |

---

## Real posts (with links)

### 1. MuScriptor — current hype leader (full-mix, chords built-in)

**Kyutai** claims best open multi-instrument transcription; frames data (not architecture) as the fix since MT3 (2022): 170k recordings / 11k hours.  
→ [kyutai_labs](https://x.com/kyutai_labs/status/2075540047613276197) · Jul 10, 2026 · ~1.3k likes, ~298k views

**Mirelo** same launch: full mix → per-instrument MIDI + **chords, key, tempo**.  
→ [MireloAI](https://x.com/MireloAI/status/2075536492177354771) · Jul 10, 2026 · ~4.8k likes, ~767k views

Architecture note (MT3-like tokens, 5s chunks, 100M–1.3B, RL post-train):  
→ [thread continuation](https://x.com/kyutai_labs/status/2075540049337155964)

**Practitioner build:** self-hosted MuScriptor → per-instrument MIDI + chords for an LLM “DAW”.  
→ [mochi_mochi_lab](https://x.com/mochi_mochi_lab/status/2077075103779840129)

**Chord-app intent:** rebuild fake-book chords from MuScriptor MIDI for piano.  
→ [andfanilo](https://x.com/andfanilo/status/2076246773467619391)

**Skeptic (fair):** “What’s the accuracy on complex jazz?” — unanswered with numbers on X.  
→ [saen_dev](https://x.com/saen_dev/status/2075895527124631928)

**Hybrid system (important for chords):** Japanese chord-tool builder: MuScriptor base + **Basic Pitch** for dynamics/pitch bend + **ISMIR 2019 LVCR** for chord progressions, then pick best fusion.  
→ [2zn01v](https://x.com/2zn01v/status/2079554048135704732)

### 2. MT3 / YourMT3+ / MR-MT3 — still the pre-2026 workhorse

**Hands-on ranking** (openmirlab / Bo-Yu Chen, Jan 2026):

- **mrmt3** — most stable  
- **yourmt3** — often best results, struggles on dense/fast material  
- **mt3-pytorch** — instrument leakage  

→ [Chen_Paul_u](https://x.com/Chen_Paul_u/status/2008489419876298894)

**Electric guitar (速弾き / shred):** custom MT3 trained with monophonic-instrument label assembly “much higher accuracy” than stock MT3 / YourMT3+ (instrument ID still weak).  
→ [2zn01v](https://x.com/2zn01v/status/2053065373671678290) · May 2026

**Guitar-tab product:** fine-tuning **yourMT3+** for audio→guitar tabs.  
→ [code_smore](https://x.com/code_smore/status/2012147077682430064) · Jan 2026

**Independent eval (not guitar-specific):** MT3 fails consistent multi-part arrangement; YourMT3+ oversimplifies rhythms.  
→ [pruynathan](https://x.com/pruynathan/status/2075772818457813478) · Jul 2026

**MR-MT3 paper** (memory retention vs instrument leakage vs baseline MT3):  
→ [GoodGood014](https://x.com/GoodGood014/status/1783695856463728641) · Apr 2024

**Classic take:** poly AMT is mostly a **data problem**; MT3 is “okay.”  
→ [kamath_harish](https://x.com/kamath_harish/status/1901319546339791115) · Mar 2025

### 3. Basic Pitch — what most people actually *run*

**NeuralNote** (Jul 2026): DAW plugin wrapping Basic Pitch; marketed for **melody or chord** → editable MIDI, poly + pitch bend.  
→ [DanKornas](https://x.com/DanKornas/status/2079357160400580624)

**Japanese DTM stack (Jun 2026):** Demucs/UVR stems → **Basic Pitch or Neural Note** (or WaveTone / NPlay24).  
→ [RE_DO](https://x.com/RE_DO/status/2061750659163275580)

**Same pattern (May 2025):** “Demucs then Spotify Basic Pitch”; Logic Flex Pitch works for notes, **not chords**.  
→ [kurogedelic](https://x.com/kurogedelic/status/1919559418582036517)

**Guitar tab workflow:** riff photos → Claude suggests Basic Pitch → MIDI → tab.  
→ [for_the_chill](https://x.com/for_the_chill/status/2033650673125122106) · Mar 2026

**Producer tool roundup:** Basic Pitch = free browser A2M, “high accuracy even on somewhat complex phrases.” Prism / Fadr / Chordify also listed.  
→ [BeatzChiva](https://x.com/BeatzChiva/status/2050337381413474681) · May 2026

**Voice-memo chords/melodies → MIDI** (Basic Pitch as daily helper).  
→ [OtyaP3939](https://x.com/OtyaP3939/status/1718067617288818725)

### 4. Melodyne — production chord reference, not bulk AMT

**Chord reference from a stem:**  
→ [danihadimusic](https://x.com/danihadimusic/status/2075336999892869248) · Jul 2026

Celemony still positions **Polyphonic Decay** among algorithm modes:  
→ [Celemony](https://x.com/Celemony/status/2066846175412601216)

Patent chatter around polyphonic note extraction when new A2M tools launch:  
→ [MrJohnny_5](https://x.com/MrJohnny_5/status/2075655634092020117)

### 5. Commercial / convenience layer

| Tool | X signal |
|------|----------|
| **AnthemScore** | Mentioned as one-stop A2S + MIDI (mostly in bot/assistant answers; low organic debate) |
| **Chordify** | Chord charts from YouTube — progression learning, not note-level polyphony |
| **Eldoraudio “Guitar Audio to MIDI”** | Jul 2026 guitar-specific web product launch ([rekkerd](https://x.com/rekkerd/status/2076935393249751434), [mixing_mag](https://x.com/mixing_mag/status/2078001695804490181)) — too new for accuracy consensus |
| **semedo NOTES** | Free A2M VST tagged guitar/piano/voice ([LEGAL_VST](https://x.com/LEGAL_VST/status/2062212730782691770)) |
| **TuxGuitar plugins** | **No meaningful hits** in this search |

### 6. Legacy / academic (named in your list)

| Engine | X reality 2025–26 |
|--------|-------------------|
| **Onsets & Frames** | Historical Magenta piano baseline ([fjord41, 2018](https://x.com/fjord41/status/963165268330536960)); not a current guitar-chord default |
| **CREPE / PESTO** | Almost no MIR discussion (name collisions drown signal). Treated as **monophonic pitch** stack, not chord engines |
| **Klapuri-style DSP** | Only via **FretNet** paper co-authorship (guitar *tablature* streaming) — arXiv bots, not “I use this for chords” |
| **TabCNN, GuitarSet-trained, EGDB-trained** | Essentially **zero practitioner posts**. Academic/GitHub niche only |
| **Velocity / AGT papers** | e.g. “Velocity Prediction in Automatic Guitar Transcription” (Jun 2026 arXiv bots) — research, not product adoption |

---

## What practitioners use *for guitar chords* (behavioral answer)

Three distinct jobs get conflated as “chord accuracy”:

### A. **Chord symbols / progressions** (strummer learning)
1. **Chordify** / similar chart sites  
2. Increasingly: **MuScriptor** (or hybrids that fuse MuScriptor + dedicated chord models like LVCR)  
3. Not Basic Pitch alone (pitch bag ≠ clean Roman/chord labels)

### B. **Note-level polyphony** (which frets / which MIDI notes in a voicing)
1. **Isolate guitar** (Demucs / UVR / StemDeck / Logic Stem Splitter)  
2. Then **Basic Pitch / NeuralNote**, or **Melodyne polyphonic**, or **MT3-family / MuScriptor** on the stem  
3. Manual cleanup still assumed  

### C. **Guitar-specific tablature** (string assignment)
- Still rare as a drop-in product. Closest X signal: **yourMT3+ fine-tunes** for tab apps, custom MT3 for shred, FretNet/TabCNN in papers — **not** what working guitarists post about day-to-day.

---

## Ranked by *reported* chord-relevant accuracy (X-only)

| Rank | Engine | Reported chord / poly strength | Confidence of ranking |
|------|--------|--------------------------------|----------------------|
| **1** | **MuScriptor** | Full-mix multi-instrument + **native chord/key/tempo**; “best open AMT to date”; builders already shipping chord UIs | High *hype*, medium *verified* (few independent fail reports yet) |
| **2** | **YourMT3+** (esp. fine-tuned) | Strong multi-instrument MIDI; used for guitar-tab products; can oversimplify dense material | Medium-high among MIR practitioners |
| **3** | **MR-MT3 / curated mt3-infer** | Better stability / less leakage than raw MT3 forks | Medium (one detailed practitioner comparison) |
| **4** | **Melodyne poly** | Trusted for **listening-quality chord reference** on clean stems; not free, not batch AMT | High for studio use-case, N/A for bulk AMT |
| **5** | **Basic Pitch** | Best *default* free poly note detector; solid on simple–medium chords after stem split; not sold as best dense jazz/metal chords | High adoption, medium absolute accuracy |
| **6** | **Custom / domain-trained MT3** | One JP report: **beats stock MT3/YourMT3+ on electric shred** | Low sample size, high for that niche |
| **7** | **AnthemScore / Eldoraudio / Prism / Fadr** | Convenience; sparse accuracy discourse | Low evidence |
| **8** | **Onsets & Frames** | Historical piano AMT | Legacy only |
| **9** | **CREPE / PESTO** | Monophonic pitch; wrong tool for poly chords | N/A for this task |
| **10** | **Klapuri DSP / TabCNN / GuitarSet / EGDB models** | Paper-class; almost absent from practitioner X | Unrankable from social data |

---

## Practical takeaway (aligned with X consensus)

**If you want guitar chords in 2026:**

| Goal | Stack people describe |
|------|------------------------|
| Fast chord chart from a song | MuScriptor (or Chordify); hybrid MuScriptor + LVCR for symbols |
| Editable poly MIDI of a guitar part | Stem split → Basic Pitch / NeuralNote **or** Melodyne poly |
| Best open multi-instrument MIDI (incl. guitar in a mix) | **MuScriptor** first; fallback **YourMT3+ / mrmt3** |
| Guitar tabs with fretting | Research models / fine-tuned YourMT3+ — not a settled consumer winner on X |
| Dense jazz / metal voicings | Still treated as unsolved; demand human ears |

**Bottom line:** On X in 2025–2026, the conversation shifted from “Basic Pitch or MT3?” to **“MuScriptor for full mixes + chords; Basic Pitch/NeuralNote for cheap stem→MIDI; Melodyne when you need production-grade note surgery.”** Guitar-specific academic models (TabCNN, GuitarSet, EGDB) and classic DSP (Klapuri, Onsets&Frames, CREPE/PESTO) are almost invisible in practitioner posts compared to those three.
