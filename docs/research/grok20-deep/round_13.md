Searching X for Japanese and English posts on TAB fingering playability, stretch limits, and auto-generated fingering complaints.Refining searches for auto-TAB fingering failures and pro heuristics in EN and JP.Pulling more English posts and pro fingering heuristics with simpler queries.# TAB fingering playability — X live scan (JP + EN)

Snapshot from X (JP heavy; EN thinner on this niche). Theme: **pitch-correct TAB can still be physically unplayable**.

---

## What makes generated fingerings unplayable

| Failure mode | What players report | Why auto-TAB fails |
|---|---|---|
| **Stretch / hand size** | 手が小さくて抑えられない; bass TABs “impossible for my hands” | Generators ignore span limits (≈4-fret box low neck; less high neck) |
| **Position jumps / 横移動** | “横移動ヤバすぎて無理” after finding a cool TAB | MIDI→TAB picks frets note-by-note, not phrase continuity |
| **Weird voicing / “謎運指”** | Correct pitches, wrong place on neck; same chord different shapes randomly | No tone / string-timbre model (open vs fretted, wound vs plain) |
| **Barre / セーハ feasibility** | F barre, half-barre, awkward partials | No force/angle model; no alternate “3-finger instead of barre” |
| **Technique false positives** | Fake slides / HOPO / slap misread | Audio/stem models invent articulations |
| **MIDI dump** | “やばすぎる運指…直すほうがめんどくさい” | Default “lowest fret / nearest frets” without economy of motion |

Core insight repeated on X: **TAB is not “notes on frets” — it is a fingering plan**. Pitch OK ≠ playable.

---

## Complaints about auto / AI / MIDI TAB (JP + EN)

### Auto-generated sense / quality

- **[@bonnisalt](https://x.com/bonnisalt/status/2074107950390477148)** (EN): flood of tabs for niche bands “smell auto-generated”; “made NO SENSE… different chord variations for the same-sounding chord.”
- **[@tarava777](https://x.com/tarava777/status/1943962948009177118)** (JP): algorithm TAB “指の長さとか運指の効率とかまったく考慮してない” + frequent wrong notes.
- **[@beefsoul](https://x.com/beefsoul/status/2080478156948181136)** (JP): pro hypothesis — sketchy tabs force people to grind “wrong hard” → accidental “バカテク” culture.

### MIDI → TAB software

- **[@Riku_lml](https://x.com/Riku_lml/status/2047843687082992013)**: MIDI auto-analysis → only weird fingerings (paid for one tool anyway).
- **[@IKIHKN](https://x.com/IKIHKN/status/1984316396973801895)**: stem→MIDI→TAB soft = “やばすぎる運指”; fixing is slower than writing TAB by hand.
- **[@0i_ra](https://x.com/0i_ra/status/2023797081312526458)**: every MIDI→TAB path → “運指カス”.
- **[@akira____0823](https://x.com/akira____0823/status/2051453849186255146)**: MIDI TAB is 100% weird; spends time shifting frets for playability (built macros).

### AI audio TAB

- **[@ossan20190315](https://x.com/ossan20190315/status/2035681764954513814)**: AI TAB “usable” but **謎運指 / 怪しいスライド・HOPO** (same as commercial tabs) — ear-check only.
- **[@M454Y05H1](https://x.com/M454Y05H1/status/2032085231327723775)**: AI tab for old solo — pitches good, **運指は多少怪しい**.
- **[@syouhiziri](https://x.com/syouhiziri/status/2014893984162930881)**: human-optimized TAB plays great; AI voicing “最適化してないと絶対弾けない（もしくはメチャ難しい運指）”.
- **[@Duffle_EEE](https://x.com/Duffle_EEE/status/1984228566113124779)** (guitarist): AI TAB is too “human-style-dependent” — “音は正しいけどこのトーンは出ないので運指を工夫して無理した奏法” loops forever; fixing that = human obsolete.
- **[@IKIHKN](https://x.com/IKIHKN/status/1984318360755265912)**: TAB without fingering thought is useless; harder than staff for AI (bass slap extract fails).
- **[@alard_ninja](https://x.com/alard_ninja/status/2075781609694130265)**: even AI can’t accurately capture Hirasawa’s fingering TAB.

### “Official / scored” still can be body-hostile

- **[@jh8jnf](https://x.com/jh8jnf/status/2035552775799726367)**: TAB or original fingering can be “無理” by finger length / joint flexibility → rewrite for “similar sound.”
- **[@p2tcgtr](https://x.com/p2tcgtr/status/2045885132834492690)**: cool TAB → **横移動ヤバすぎ** → sought easier fingering.
- **[@minomshi_](https://x.com/minomshi_/status/1932445007086288942)**: “タブあるしやる” → **初手の運指無理**.
- **[@RaiyaHiiragi](https://x.com/RaiyaHiiragi/status/1988927617593221625)**: game-music TAB from MIDI-ish source — “弾けないやつ…腕が死ぬ”.

### Hand size / stretch / barre

- **[@DeadstockToys](https://x.com/DeadstockToys/status/2081038607503278344)**: small hands → textbook shapes impossible → weird personal fingerings.
- **[@TenmaK_hobby](https://x.com/TenmaK_hobby/status/2045856702072000895)**: bass tab physically impossible for hand size → re-finger.
- **[@Y0synari](https://x.com/Y0synari/status/2064706663354183712)**: published fingerings may assume large hands.
- **[@oyakataguitar88](https://x.com/oyakataguitar88/status/2069027316865634575)**: for small hands, alternate stretch drills; stop if thumb/wrist pain.
- **[@lernlean](https://x.com/lernlean/status/2079592569420579289)**: classical F shape felt like “無理ゲー”.

---

## Heuristics pros / teachers actually use (from posts)

| Heuristic | Evidence / link |
|---|---|
| **Stay in a box; minimize position jumps** | Dark-memorization works better when “ポジション移動が少なければ” — [@haru_curiosity2](https://x.com/haru_curiosity2/status/2063652458942157000) |
| **Same shape × diagonal pairs (2-string unit)** | Fast ascending/descending economy — [@yosihik16039425](https://x.com/yosihik16039425/status/2022179508921807259) (654 likes) |
| **One finger per fret / chromatic lateral training** | 横移動: same fingering, shift 1 fret; unused fingers hover ~3 cm — [@thepocketguitar](https://x.com/thepocketguitar/status/2078388225392193591) |
| **Prefer playable rewrite over “faithful impossible”** | If stretch fails after honest try, change to “似てる感じ” — [@jh8jnf](https://x.com/jh8jnf/status/2035552775799726367); classical: after basics, adapt book fingerings — [@japanoldguitar](https://x.com/japanoldguitar/status/2007934235102138481) |
| **Tone can force “hard” fingerings** | Humans choose awkward frets for *tone*, not ease — [@Duffle_EEE](https://x.com/Duffle_EEE/status/1984228566113124779); Hirasawa: wrong fingering = wrong nuance — [@hirasawa](https://x.com/hirasawa/status/2073970188945670370) |
| **Barre vs multi-finger: context** | Sometimes barre easier; sometimes 3-finger for open string clarity (Stairway setup) — [@ayumi_hagiyama](https://x.com/ayumi_hagiyama/status/2067752054471430639) |
| **Hand-size-aware position choice** | Flexible fretting map for *your* hand — [@guitar_hakase](https://x.com/guitar_hakase/status/2031941520979607933) |
| **MIDI→TAB always needs human “ずらし”** | Shift frets for playability as a standard step — [@akira____0823](https://x.com/akira____0823/status/2051453849186255146), [@oshi_ent](https://x.com/oshi_ent/status/2021392902501679342) |
| **Horizontal roam is stylistic, not always optimal** | Transcribed solo “えっ…そこ行くの…？こっちが楽じゃね？” — [@junfukuda1](https://x.com/junfukuda1/status/1962787092985192643) |
| **Guitar ambiguity (same pitch many places)** | Sight-reading on frets “詰まる”; TAB can help — [@0qfikP5DMF7ssY2](https://x.com/0qfikP5DMF7ssY2/status/2079715071853514961) |

**Implicit pro cost function (from complaint patterns):**

1. Pitch correct  
2. Max simultaneous stretch ≤ ~4 frets (adjust for position / hand)  
3. Min hand travel between consecutive notes  
4. Prefer same string / adjacent string when phrasing wants it  
5. Barre only when finger budget or sustain needs it  
6. Prefer frets that match **timbre** of the recording  
7. Leave open strings when they simplify *or* match the track  
8. Prefer fingerings that leave a path into the **next** phrase (lookahead)

---

## Stretch / position / barre — player language map

| JP phrase | Rough EN | Physical issue |
|---|---|---|
| 押さえられない | can’t fretted / won’t sound | pressure, angle, barre collapse |
| 届かない / 手小さい | can’t reach / small hands | span |
| 横移動ヤバい | lateral position thrash | jumps, no guide finger |
| セーハ / バレー無理 | barre fails | index strength/angle |
| 変な運指 / 謎運指 | nonsense fingering | algorithm path |
| 音は合ってるけど… | pitches right, still wrong | wrong string set / position |

---

## Highest-signal posts (bookmark set)

**Auto-TAB broken**
- https://x.com/IKIHKN/status/1984316396973801895 — MIDI→TAB unusable  
- https://x.com/Duffle_EEE/status/1984228566113124779 — tone-driven “無理奏法” vs AI  
- https://x.com/syouhiziri/status/2014893984162930881 — unoptimized AI = unplayable  
- https://x.com/bonnisalt/status/2074107950390477148 — EN: auto tabs nonsense chords  
- https://x.com/tarava777/status/1943962948009177118 — no finger-length / efficiency  

**Physical limits**
- https://x.com/p2tcgtr/status/2045885132834492690 — 横移動  
- https://x.com/jh8jnf/status/2035552775799726367 — finger anatomy rewrite OK  
- https://x.com/DeadstockToys/status/2081038607503278344 — small hands  

**Pro heuristics**
- https://x.com/yosihik16039425/status/2022179508921807259 — diagonal shape economy  
- https://x.com/thepocketguitar/status/2078388225392193591 — lateral chromatics  
- https://x.com/japanoldguitar/status/2007934235102138481 — adapt fingerings after basics  
- https://x.com/hirasawa/status/2073970188945670370 — fingering = nuance  

---

## Takeaways for generators / scorers

1. **Pitch accuracy is table stakes**; users still dump tabs for **playability**.  
2. MIDI import without a **position continuity + stretch cost** is universally hated.  
3. AI that only matches audio pitch invents **wrong articulations** and **wrong positions**.  
4. “Correct” hard fingerings sometimes exist for **tone** — need a toggle: *easiest playable* vs *tone-faithful*.  
5. **Hand size / scale length** should be parameters, not constants.  
6. Output should invite **human ずらし** (shift frets), not pretend to be final.

---

**Coverage note:** JP discussion of AI/MIDI TAB + 運指 is active and concrete. EN hits more often as “this tab makes no sense / auto-generated smell” than deep stretch/barre mechanics; physical complaints are common in JP around 手が小さい / 横移動 / セーハ.

If useful next: a short **scoring checklist** (boolean tests for unplayable spans, jump size, barre density) you can drop into a TAB generator.
