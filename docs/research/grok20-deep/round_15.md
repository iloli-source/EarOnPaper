Researching commercial guitar transcription products across English, Chinese, and Japanese sources on X and the web, focusing on chord-accuracy claims.# Commercial guitar transcription (2026) — EN + CN + JP scan

Focus: who **claims** chord accuracy vs who **delivers** something measurable, plus recent posts/links. Snapshot as of **late Jul 2026**.

---

## Quick matrix: who actually talks about *chords*?

| Product | Primary output | Chord claim? | Hard accuracy number? | Verdict on chords |
|---|---|---|---|---|
| **Songsterr AI** | Full GP-style tab (G/B/D multi-track) | Soft: “accurate tabs”; **chords/lyrics are human** on catalog | **No %** | Strong for *notes/riffs*; not a chord-accuracy product |
| **Klangio Guitar2Tabs** | Tabs + sheet + MIDI/GP | **Yes** — “polyphonic & chord-aware”, chord identifier | **No %** (qualitative only) | Strongest commercial *claim* for guitar chords/polyphony; still “edit expected” |
| **Chordify** | Timed chords (not full tab) | **Yes** — product *is* chords | Official: **not 100%**; **no published %** | Only pure chord product in EN big three; honest about limits |
| **Fretiq** | String ID (which string), not chords | **No** | **Yes** — 97.1% / 87.8% (string class.) | Research prototype, **not** commercial tab/chord product |
| **MuScriptor apps** | Multi-inst MIDI | **No** (notes/instruments) | **Yes** — Multi-F1 **48.2** (vs 21.9 baseline) | Strong open MIDI stack; **not** fretting/chord labels |
| **国产扒谱** (爱扒谱 / 反谱 / Chord AI…) | 五线谱 / 六线谱 / 和弦 | **Yes**, aggressive | Marketing **80–98%** (unverified) | Loudest *chord accuracy %* claims; treat as ads unless you retest |

---

## 1. Songsterr AI — updates & “internals” (what’s public)

**What they sell now**  
- YT link or upload → AI draft for **guitar / bass / drums** (optional vocals, rhythm/lead splits, capo, tuning).  
- Marketing: “**accurate** guitar, bass, and drum tabs in minutes.”  
- Product: [songsterr.com/new](https://www.songsterr.com/new)  
- Help: AI draft from YT/audio; **“Chord signs and lyrics are added by transcribers”** (catalog ≠ AI chord engine).  

**Known 2025–26 product updates (public, not paper-internals)**  
- **Bend detection** announced by official account (Apr 2025) — “We Taught the AI to Bend!”  
- UI still exposes instrument roles (rhythm/lead/bass/drums), feel, pickup, tempo — multi-track AMT-style product, not a published model paper.

**Chord accuracy?**  
- They **do not** publish a chord-accuracy metric.  
- Delivery is **note-level multi-part tab**, not Chordify-style chord labels. Popular songs are human-polished; AI is the long-tail draft.

**X posts**  
- Official bend update: [x.com/songsterr/status/1915553879317516345](https://x.com/songsterr/status/1915553879317516345)  
- User positive (“surprisingly accurate”): [x.com/webprofusion/status/1919747065405407521](https://x.com/webprofusion/status/1919747065405407521) · [x.com/Opti__Fox/status/1926234195191386210](https://x.com/Opti__Fox/status/1926234195191386210)  
- User negative 2026 (“AI rubbish”, label missing): [x.com/TFCAguia/status/2080502208081150132](https://x.com/TFCAguia/status/2080502208081150132) · [x.com/xpekebackdoor13/status/2079391854139707516](https://x.com/xpekebackdoor13/status/2079391854139707516)  
- JP use (“Songsterrに採譜”): [x.com/project_ranfa/status/2080983479240520021](https://x.com/project_ranfa/status/2080983479240520021) · quality caveat: [x.com/nyan_moonlight/status/2079838166664822806](https://x.com/nyan_moonlight/status/2079838166664822806)  
- KR mild positive: [x.com/sonwonjin/status/2078514418535874801](https://x.com/sonwonjin/status/2078514418535874801)

**Community truth (EN forums/Reddit, not X):** notes often usable; fretting/voicing odd; rhythm sometimes off; needs human edit — matches “accurate draft,” not published chord %.

---

## 2. Klangio / Guitar2Tabs — commercial chord-aware guitar AMT

**Product**  
- [klang.io/guitar2tabs](https://klang.io/guitar2tabs/)  
- Sibling: [Transcription Studio](https://klang.io/transcription-studio/) (multi-inst rock mix → stems-ish notation + TABs)  
- Claims: **polyphony & chords**, strum/pick styles, multi-inst isolation for guitar/bass, export PDF/MIDI/MusicXML/GP.

**Accuracy language**  
- Marketing: “**unparalleled accuracy**,” “highly accurate.”  
- FAQ honesty: accuracy depends on signal; **if a human tabber struggles, so does the AI**; edit mode assumed.  
- Play Store long-standing disclaimer: not 100%; multi-inst simultaneous → bad results unless isolated.  
- Past update: **new guitar strumming model** (TikTok/Klangio) aimed at chord-rhythm accuracy.

**Chord accuracy?**  
- **Claims chord transcription** more explicitly than Songsterr.  
- **Does not** publish a chord-symbol accuracy % on a public benchmark.

**X / JP**  
- MusicRadar on multi-inst Transcription Studio: [x.com/MusicRadar/status/2036123324359778597](https://x.com/MusicRadar/status/2036123324359778597)  
- JP discovery (YT → TAB): [x.com/4444pochi/status/2023066956451266643](https://x.com/4444pochi/status/2023066956451266643)  
- Workflow (Suno → Klangio tab): [x.com/qualityguitar/status/2069269033283670473](https://x.com/qualityguitar/status/2069269033283670473)  
- ES industry note: [x.com/audiomusicadigi/status/2079574619107819973](https://x.com/audiomusicadigi/status/2079574619107819973)

---

## 3. Chordify — pure chord product (honest about ceiling)

**What it is**  
- Timed **chords** for guitar/ukulele/piano — **not** full note tab / lead lines.  
- Official support posts (X): algorithm **cannot guarantee 100% accuracy**; users can edit chords.  
- Scope limit: “mainly focused on extracting **chord data**… not… individual lead lines.”

**Chord accuracy?**  
- **Claims reliability as product category**, not a public % score.  
- **Most direct commercial chord deliverable** in EN; accuracy is crowd-edited + algorithm, not a peer-reviewed metric.

**X**  
- Official accuracy caveat: [x.com/chordify/status/2017263869467488493](https://x.com/chordify/status/2017263869467488493) · [x.com/chordify/status/1866435652591460355](https://x.com/chordify/status/1866435652591460355)  
- Scope (chords only): [x.com/chordify/status/1892523775528190405](https://x.com/chordify/status/1892523775528190405)  
- User: fun for practice; accuracy unknown if “tone deaf”: [x.com/DPR273/status/2076863420486316441](https://x.com/DPR273/status/2076863420486316441) · [x.com/kaaiyukitrojan4/status/2069840034149064773](https://x.com/kaaiyukitrojan4/status/2069840034149064773)

---

## 4. Fretiq — research, not a tab store

**What it is**  
- arXiv **Jul 2026**: *Fretiq: Browser-Native Electric Guitar String Classification…*  
- [arxiv.org/abs/2607.18303](https://arxiv.org/abs/2607.18303)  
- Problem: **which string** produced a monophonic pitch (string ambiguity), not chord symbols / full songs.

**Numbers they *do* publish**  
- **97.1%** shuffled frame-level validation (322k frames)  
- **87.8%** held-out free-play (~103k frames)  
- Browser-only; no hex pickup / camera

**X (paper bots)**  
- [x.com/SoundPapers/status/2079831436941549808](https://x.com/SoundPapers/status/2079831436941549808)  
- [x.com/ArxivSound/status/2079850643641254047](https://x.com/ArxivSound/status/2079850643641254047)

**Not** a commercial “Fretiq product” competing with Songsterr for song chords.

---

## 5. MuScriptor stack — open multi-inst MIDI (apps on top)

**Core (Jul 2026)**  
- Kyutai + Mirelo open model: full-mix → **per-instrument MIDI**  
- Blog: [kyutai.org/blog/2026-07-10-muscriptor](https://kyutai.org/blog/2026-07-10-muscriptor/)  
- Demo/host: [muscriptor.kyutai.org](https://muscriptor.kyutai.org)  
- Weights/code: HuggingFace MuScriptor · GitHub `muscriptor/muscriptor`  
- Reported: **Multi F1 48.2** vs YourMT3+ **21.9** on held-out set (note/instrument F1 family, **not chord-label accuracy**)

**Commercial / app layer**  
- **Mirelo**: best model behind **API** + free Audio-to-MIDI in Studio; OSS stays for self-host  
  - [x.com/MireloAI/status/2080342247418048750](https://x.com/MireloAI/status/2080342247418048750)  
- **ComfyUI-muscriptor** nodes: [x.com/jtydhr88/status/2081202247703134482](https://x.com/jtydhr88/status/2081202247703134482)  
- **Songbird** agent using MuScriptor then edit/arrange: [x.com/mohmedakamal/status/2077806526027419810](https://x.com/mohmedakamal/status/2077806526027419810)  
- CN praise (“多乐器也能扒得七七八八”): [x.com/YMike59492/status/2075840652064276520](https://x.com/YMike59492/status/2075840652064276520)

**Chord accuracy?**  
- Delivers **notes + instrument tracks**. Chord symbols would be a **downstream** post-process. No fretting/voicing guarantee for guitar.

---

## 6. 国产扒谱工具 — loudest % claims (marketing-heavy)

2026 Chinese roundups repeatedly name:

| Tool | Typical claim (media/site) | Notes |
|---|---|---|
| **爱扒谱** [aibapu.cn](https://www.aibapu.cn/) | 流行/民谣 **95%+**; some pages “平均识别率 96”; 六线谱 for 吉他/贝斯 | Also CNN+Transformer narrative; **98%** in Tencent News 实测 style pieces |
| **反谱** | 常规 ~**90%**; some tables **98%**; stem-then-transcribe | 一站式 + 分轨 |
| **音谱小助手 / StemSplit / AudioBatchPro** | Compared in same 2026 listicles | Split vs full-score tradeoffs |
| **Chord AI** (global app, huge CN presence) | Store: chord ID “**more precise than all other apps**”; Bilibili clips claim **95%+** | Chords-first; tabs “coming” historically |

**Sources**  
- 2026 five-tool 实测: [news.qq.com](https://news.qq.com/rain/a/20260709A03NE300) — 爱扒谱 “正确率可达 **98%** 以上” on pop/piano/gufeng  
- More cautious third-party: [smzdm](https://post.smzdm.com/p/axkggz44) — 爱扒谱 和弦 **80–90%** on pop (more believable band)  
- 反谱 marketing: ~90–98% depending on page  

**X (CN)**  
- Sparse brand-name chatter vs web SEO; MuScriptor/open tools get more tech Twitter.  
- 扒谱-as-workflow still common; few rigorous chord % posts.

**Treat CN % as marketing unless you own a labeled test set.** Same genre bias as everyone: solo/clean pop > dense rock/metal.

---

## Who *claims* chord accuracy vs who *delivers* something rigorous?

### Claims chord accuracy (marketing / product copy)
1. **国产 stack** — **highest numerical claims** (80–98%) with weakest independent verification  
2. **Chord AI** — “more accurate than all other apps” (qualitative superlative)  
3. **Klangio Guitar2Tabs** — “chord-aware / unparalleled” (no %)  
4. **Chordify** — product is chords; **explicitly refuses 100%**  
5. **Songsterr** — “accurate tabs”; **chords on catalog = humans**, AI = notes/parts  

### Delivers **published numeric** metrics (but not “chord %”)
| System | Metric | What it measures |
|---|---|---|
| **MuScriptor** | Multi-F1 **48.2** (vs 21.9) | Multi-instrument **note** transcription |
| **Fretiq** | **97.1%** / **87.8%** | **String classification**, monophonic electric |
| **Songsterr / Klangio / Chordify** | — | No public chord-symbol accuracy paper |

### Practical “who wins for chords” (field, not ads)
- **Need chord symbols only, any song URL:** **Chordify** (or **Chord AI** in CN/mobile) — edit expected.  
- **Need guitar chords *in tab/polyphony* from audio:** **Klangio Guitar2Tabs** (best commercial fretting-aware story).  
- **Need full band parts to play along:** **Songsterr AI** (notes/drums/bass; polish popular tabs).  
- **Need open, multi-stem MIDI to build your own app:** **MuScriptor + Mirelo API / ComfyUI**.  
- **Need which-string resolution R&D:** **Fretiq** paper only.  
- **CN zero-friction 六线谱 + big % claims:** **爱扒谱 / 反谱** — verify yourself; listicles inflate numbers.

---

## EN / CN / JP signal summary on X

| Lang | Temperature | Themes |
|---|---|---|
| **EN** | Songsterr polarized (impressive draft vs “AI slop”); Chordify support-thread accuracy caveats; MuScriptor/Mirelo wave Jul 2026; Fretiq paper bots | Accuracy = anecdotal |
| **CN** | 扒谱 SEO on web >> X; MuScriptor 本地开源 hype; few independent chord % threads | Web claims 90–98% |
| **JP** | Songsterr used as 採譜 tool casually; Klangio known as “YT→TAB”; less brand debate | Human 採譜 still default for 和音 confidence |

---

## Bottom line

- **Only Chordify (and Chord AI)** are *about* chord accuracy as the product. Neither ships a public, peer-reviewed chord %.  
- **Klangio** is the only major commercial guitar product that **openly markets chord/polyphony transcription** as a core AI feature.  
- **Songsterr** ships the most visible **multi-track tab** updates (e.g. bends) but **does not** own the chord-accuracy narrative.  
- **Hard numbers in 2026** land on **MuScriptor (MIDI F1)** and **Fretiq (string ID)** — useful stack layers, **not** chord-product scorecards.  
- **国产 tools** win the **claim war** (95–98% headlines); treat those as **marketing**, closer to **80–90%** chord utility in less boosterish writeups.

If you want a follow-up, I can build a **same-song EN/CN product bake-off checklist** (5 tracks × chord symbol F1 / voicing sanity) without touching paid APIs until you approve spend.
