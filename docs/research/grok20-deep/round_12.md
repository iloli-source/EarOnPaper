XとWebの両方で、TABのリズム表記（Guitar Pro / Songsterr、不満点、ハイブリッド表示のベストプラクティス）を英語・日本語で調べます。公式の読み方ガイドと、TABのリズム表示に関する不満・実装ディテールを深掘りします。# TAB + Rhythm Notation — Live Research Brief (EN + JP)

## 1. How Songsterr / Guitar Pro render stems, beams, rests

### Songsterr (“Tabs with Rhythm”)

Songsterr’s own guide is the clearest public spec of **TAB + standard-style rhythm hybrid**.

| Element | Rendering rule |
|--------|----------------|
| **Core idea** | Plain TAB only encodes **pitch (string/fret)**. Rhythm is layered on top, “very similar to sheet music.” |
| **Stems / noteheads** | Duration changes the **visual of the rhythmic element** attached to the fret number (not a full 5-line staff on TAB alone). |
| **Beams** | Short values (8th/16th…) are **grouped with beams**, typically **one beat per group**. **Rests are never beamed.** |
| **Rests** | Full rest symbols for silence (same fractional names as notes). |
| **Dots / double-dots** | Dot right of note/rest = +½; double-dot = +½ + ¼ of original. |
| **Ties** | Extend duration across notes; **rests are never tied**. |
| **Triplets** | Group of 3 in space of 2, often with “3” under the group. |
| **Swing** | Documented as unequal subdivision (not pure straight beams). |
| **Grace notes** | Outside bar duration / rhythm display math. |

Official: [songsterr.com/howtoreadtab](https://www.songsterr.com/howtoreadtab) · Home branding: [Songsterr — Guitar Tabs with Rhythm](https://www.songsterr.com/)

### Classic “rhythmic tablature” symbol system (print / theory)

Standard teaching table (stems/flags *on fret numbers*):

| Value | TAB graphic |
|-------|-------------|
| Whole | Ellipse around fret, **no stem** |
| Half | Ellipse + **stem** |
| Quarter | Fret + **stem** |
| Eighth | Stem + **flag/beam** |
| 16th | Stem + **2 flags/beams** |
| Whole rest | Rectangle hanging from ~3rd string |
| Half rest | Rectangle on ~4th string |
| Quarter rest | Curved rest glyph |
| 8th/16th rest | Flagged rest glyphs |

Source: [guitar.ch — Rhythmic Tablature](https://www.guitar.ch/en-us/guitar/theory/theory-rhythmic-tablature.html)

### Guitar Pro (product behavior)

GP is **notation-first**: one musical voice drives **Standard + TAB (+ optional Slash)** together.

- **Track → Musical Notation**: toggle **Tablature / Standard / Slash** independently ([GP support](https://support.guitar-pro.com/hc/en-us/articles/115005499245-GP7-6-Display-and-hide-notations)).
- Default **TAB stems/beams mirror the standard staff** (same rhythm engine). Many users treat stems on TAB as “noise” when standard is also shown.
- To strip TAB stems: **Stylesheet → Notation → Position in Tablature → Voice 1 = Hidden** ([study-guitar walkthrough](https://www.study-guitar.com/blog/2024-04-06-remove-stems-from-tab-guitar-pro/)).
- JP user guide (GP8): beam break, force beam on tuplets, freeze beams, auto stem flip, etc. ([GP8 ユーザーガイド PDF](https://www.guitar-pro.jp/content/files/GP8_user_guide.pdf)).

**Mental model**

```
Standard staff:  noteheads + stems + beams + rests  → primary rhythm grammar
TAB staff:       fret digits on string lines        → primary fingering
Hybrid (Songsterr / GP TAB+stems): digits act as noteheads; stems/beams attach above/through TAB
GP dual-staff:   full standard above, TAB below, shared timing
```

Dorico’s JP docs also describe TAB stems/flags/beams defaulting **up** so they clear bends/dives ([Dorico TAB リズム](https://www.steinberg.help/r/dorico-pro/6.1/ja/dorico/topics/notation_reference/notation_reference_tablature/notation_reference_tablature_rhythms_c.html)).

---

## 2. Complaints about rhythm display in TAB

### Product / engraving complaints (forums & how-tos)

| Complaint | Where |
|-----------|--------|
| **Beams on TAB clutter** after converting from standard → want TAB digits only | [r/GuitarPro — Hide Note Beams for Tab?](https://www.reddit.com/r/GuitarPro/comments/18jc4ir/hide_note_beams_for_tab/) |
| **Can’t hide rhythmic info** for absolute beginners | [Facebook Guitar Pro group](https://www.facebook.com/groups/626737842052242/posts/925651242160899/) |
| **Want stems on TAB** when only TAB is shown (opposite problem — Sibelius) | [r/Sibelius](https://www.reddit.com/r/Sibelius/comments/1iat3af/how_can_i_give_guitar_tabs_stems_so_that_the/) |
| **Bad beaming** hides the beat / syncopation | [UG forum — Beaming and Readability](https://www.ultimate-guitar.com/forum/showthread.php?t=1922145) |
| Swing/triplets hard to express in ASCII-style tabs | [Music.SE — Swing rhythm in tabs](https://music.stackexchange.com/questions/78829/how-to-write-a-swing-rhythm-using-tabs) |

### Structural complaint (culture, not one app)

Plain TAB **does not encode duration** unless you add rhythmic stems or a second staff. Songsterr states this explicitly.

### X (JP) — rhythm / TAB readability

| Post | Takeaway |
|------|----------|
| [@umi_gorilla0901](https://x.com/umi_gorilla0901/status/2074123975622578202) | TAB is “defective”: inverted string order, hard to know pitch, **音価がわかりづらい**, theory doesn’t stick |
| [@8wWqIs6cKH73767](https://x.com/8wWqIs6cKH73767/status/2066493249326600411) | “TABの見方は分かっても**リズムがわからない**から一生進まない” |
| [@8wWqIs6cKH73767](https://x.com/8wWqIs6cKH73767/status/2066198968145723652) | Same thread: rhythm + technique from TAB alone is a wall |
| [@maru_uuu1](https://x.com/maru_uuu1/status/2050177869121519997) | Scrolling TAB: many numbers + motion → **読めない**; pause → forget rhythm; slow → senseless |
| [@NikitaJazzBass](https://x.com/NikitaJazzBass/status/2035681431788363978) | Many TAB users **memorize with the track**; people who can read rhythm can sight-read any notation |
| [@lpg0415](https://x.com/lpg0415/status/2037848295440306675) | Guitarist who reads TAB but **can’t parse standard note values** |
| [@singasongform](https://x.com/singasongform/status/2069977139127123973) | Can read pitch from scores, **almost never rhythm**; TAB gives positions, not timing |
| [@akitsuki801](https://x.com/akitsuki801/status/2074499400425222479) | Disputes whether a Metallica TAB enters on **downbeat vs upbeat** |
| [@Love22089019416](https://x.com/Love22089019416/status/2075132534418190547) | Author admits **リズム若干ズレ** even when frets are right |
| [@yume_VT](https://x.com/yume_VT/status/2080278046385562001) | TAB shows wild meters (e.g. 23/16, 25/8) → shock |
| [@italyguccikov](https://x.com/italyguccikov/status/2079141519932743991) | Long tab, **右手鬼早い**, rhythm-keeping alone exhausts |

### X (EN / product branding)

| Post | Takeaway |
|------|----------|
| [@neko_moriandy](https://x.com/neko_moriandy/status/2065770208070173174) | Discovers **“Songsterr Tabs with Rhythm”** as escape from TAB scarcity |
| [@FretGhoul](https://x.com/FretGhoul/status/1977864801620459596) | Practice tip: **rhythm cheat sheet + TAB with rhythmic notation above** (Guitar Pro dual view) |
| [@GreyFoxWeezterr](https://x.com/GreyFoxWeezterr/status/2022777266284171706) | Songsterr editor notes **rhythm-heavy** chart (syncopation, PM bass, drums) |
| [@syua20090927](https://x.com/syua20090927/status/2030604764657090635) | Making GP tabs deepens **rhythm understanding** |
| [@hiro7418_guitar](https://x.com/hiro7418_guitar/status/2017115930632102067) | GP autoplay for **rhythm check** + up/down strokes |
| [@Renshutyu](https://x.com/Renshutyu/status/2056691339581165679) | Cultural list: **“TAB譜が世界を支配”** + 五線読めないプロもいる |

**X pattern:** Songsterr is marketed/shared as **“Tabs with Rhythm”** (product name is the value prop). Complaints are less “Songsterr stems look wrong” and more **“TAB without duration is incomplete”** / **“dual attention (digits + motion) kills readability”**.

---

## 3. Best practices for TAB + rhythm hybrid

Synthesized from Songsterr rules, rhythmic-TAB convention, Japanese pedagogy (エレキギター博士), engraving complaints, and dual-staff workflow.

### A. Choose a display mode by audience

| Audience | Prefer |
|----------|--------|
| Absolute beginners | **Digits only** (hide stems) *or* video/playhead; optional slash rhythm above |
| Self-learners without audio | **Stems/beams on TAB** *or* full standard + TAB |
| Intermediate / band | **Standard above + TAB below** (GP default hybrid) |
| Pros / dense polyphony | Standard primary; TAB for positions only |

### B. Engraving rules that improve “where is the beat?”

1. **Beam by the beat** (Songsterr: groups usually = one beat; rests never beamed).  
2. **8-beat charts:** often beam **beats 1–2 vs 3–4** so mid-bar is obvious (JP pedagogy).  
3. **16ths:** beam **per quarter** so the bar still reads as four beats.  
4. Prefer **ties that show crossed beats** over one long value that hides the bar skeleton (same JP source).  
5. **Rests are intentional cutoffs** (not “let ring”) — GP/Songsterr both treat rest as silence length.  
6. **Don’t beam rests**; don’t tie rests.  
7. **Tuplets:** always show number (3/5/6/7); for swing, prefer global “swing” annotation over writing every triplet if house style allows.  
8. **Stem direction on TAB:** default **up** keeps frets + bend/dive graphics clear (Dorico practice).  
9. If both standard and TAB show **identical stems**, offer a **stylesheet hide** on TAB to cut visual double-duty (GP).  
10. **Polyphony:** Songsterr greys secondary voice frets — keep secondary stems lighter or on separate voice so primary rhythm isn’t noisy.

### C. Hybrid layouts (implementation checklist)

```
┌─────────────────────────────────────┐
│  [optional] Chord names / slash rhythm staff   │
│  Standard staff: full noteheads, beams, rests  │  ← rhythm truth
│  TAB: frets only  OR  frets + stems (if alone)  │  ← fingering truth
│  Playhead / audio sync (Songsterr-style)         │  ← learning scaffold
└─────────────────────────────────────┘
```

- **Spatial alignment:** same x-position for simultaneous events across staves.  
- **Collision:** stems above TAB, not through 6th-string digits; leave air for PM/let-ring dashes.  
- **Grace notes:** draw small; exclude from measure arithmetic (Songsterr).  
- **Pickup bars:** allow incomplete duration without error flag.  
- **Export modes:** “print pro” (standard+TAB) vs “web beginner” (TAB+stems or TAB+audio).

### D. Learning / content best practices (from X + JP teaching)

- Teach **count syllables** with the chart: 8-beat `1と2と…`, 16 `1 e + a`.  
- Admit **user tabs skew rhythm** even when frets are right — always A/B with recording.  
- Use **playback + loop** (Songsterr/GP) as training wheels, then wean to silent reading.  
- For beginners: hide beams; for rhythm study: show only rhythm (slash/rhythm notation) without frets.

---

## 4. Key links (bookmark set)

| Topic | URL |
|-------|-----|
| Songsterr how-to (rhythm, beams, rests) | https://www.songsterr.com/howtoreadtab |
| Songsterr home | https://www.songsterr.com/ |
| Rhythmic TAB symbol table | https://www.guitar.ch/en-us/guitar/theory/theory-rhythmic-tablature.html |
| GP show/hide notation | https://support.guitar-pro.com/hc/en-us/articles/115005499245-GP7-6-Display-and-hide-notations |
| GP hide TAB stems | https://www.study-guitar.com/blog/2024-04-06-remove-stems-from-tab-guitar-pro/ |
| GP8 JP user guide (beams) | https://www.guitar-pro.jp/content/files/GP8_user_guide.pdf |
| JP: 音符・休符・TABでの棒/旗 | https://guitar-hakase.com/254/ |
| UG beaming readability | https://www.ultimate-guitar.com/forum/showthread.php?t=1922145 |
| Reddit hide beams | https://www.reddit.com/r/GuitarPro/comments/18jc4ir/hide_note_beams_for_tab/ |
| Dorico TAB rhythms (JP) | https://www.steinberg.help/r/dorico-pro/6.1/ja/dorico/topics/notation_reference/notation_reference_tablature/notation_reference_tablature_rhythms_c.html |
| GP academy rhythm basics | https://www.guitar-pro.com/academy/m/2318-fundamentals-of-rhythm-and-musical-notation |

### Representative X links

- JP frustration (no rhythm in TAB): https://x.com/8wWqIs6cKH73767/status/2066493249326600411  
- JP structural critique: https://x.com/umi_gorilla0901/status/2074123975622578202  
- JP “rhythm readers can sight-read”: https://x.com/NikitaJazzBass/status/2035681431788363978  
- Songsterr “Tabs with Rhythm” discovery: https://x.com/neko_moriandy/status/2065770208070173174  
- EN dual-staff teaching tip: https://x.com/FretGhoul/status/1977864801620459596  
- GP for rhythm check: https://x.com/hiro7418_guitar/status/2017115930632102067  

---

## 5. One-line synthesis

**Songsterr** productizes hybrid TAB as “Tabs with **Rhythm**” (stems/beams/rests/ties/tuplets on fret digits). **Guitar Pro** uses a **shared rhythm engine** across standard + TAB and lets you hide stems or whole staves. **User pain** is rarely exotic beam bugs — it’s that **ASCII/plain TAB omits duration**, **stem clutter doubles when both staves show rhythm**, and **learners can’t map frets to time without audio or standard counting**. Best hybrid: **beat-aligned beams, rests as silence, dual staff when dense, hide TAB stems when standard is present, playback for scaffolding.**

---

*Note: Slack `#倉田_ログ` posting is configured in local Claude rules, but no Slack MCP tool is connected in this session, so the work log could not be auto-sent. I can paste a ready-to-post log if you want.*
