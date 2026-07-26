Researching string inharmonicity coefficient (B) estimation in practice — English and Japanese sources, plus X posts and tuner techniques.Digging into tuner implementations and the partial-sharpness identification technique.Checking Slack tools for the required work log, then delivering the research brief.# String inharmonicity coefficient \(B\) — practice guide (EN + JP)

Live X + web scan on **estimating \(B\) from partial sharpness**, using that signature to **tell which string/course produced a note**, and how **piano/guitar tuners** actually do it.

---

## 1. Core model (what \(B\) is)

Stiff-string partials (Fletcher 1964; standard in piano tech):

\[
f_n = n\,f_0\sqrt{1 + B\,n^2}
\]

- \(f_n\): measured frequency of partial \(n\)
- \(f_0\): ideal (zero-stiffness) fundamental
- \(B\): **inharmonicity coefficient** (dimensionless)

Physical form (JP Wikipedia / RIST):

\[
B = \left(\frac{\pi}{L}\right)^2\frac{EI}{T}
\]

Short, thick, low-tension, high-stiffness strings → larger \(B\). Small upright bass ≈ large \(B\); long concert grand ≈ small \(B\).

**Progressive sharpness:** partial \(n\) is sharp of \(n f_0\) by roughly

\[
\Delta f_n / f_n \approx \tfrac12 B n^2 \quad\Rightarrow\quad \text{cents} \approx 600\,B\,n^2/\ln 2
\]

Higher partials run **progressively sharp** — the classic signature Schuck & Young measured on piano (1943).

---

## 2. Practical \(B\) estimation pipeline

### A. From isolated notes (lab / tuner “measure” mode)

1. **Single string only** — mute other strings of a unison (critical; mixed unisons smear \(B\)).
2. Record ~0.5–6 s after attack (partials settle; avoid heavy noise floor).
3. Peak-pick partials \(f_1,f_2,\ldots,f_N\) (often \(N=6\)–12 in bass; fewer in treble).
4. Fit \((f_0, B)\) by nonlinear LS, or rearrange:

\[
\left(\frac{f_n}{n}\right)^2 = f_0^2 + (B f_0^2)\,n^2
\]

Plot \((f_n/n)^2\) vs \(n^2\) → intercept \(f_0^2\), slope \(B f_0^2\).  
TuneLab literally shows **partial offsets** (cents sharp of pure harmonics) and fits one **inharmonicity constant** from that pattern.

5. Reject outliers (false peaks, phantom partials, wound-string anomalies).

**Code starting points**

| Resource | Link |
|----------|------|
| Piano note \(F_0 + B\) estimator | https://github.com/beiciliang/estimate-f0-inharmonicity |
| Rigaud et al. parametric piano model (NMF, chords too) | https://www.institut-langevin.espci.fr/biblio/2020/3/5/916/files/2013_a_parametric_model_and_estimation_techniques_for_the_inharmonicity_and_tuning_of_the_piano.pdf |
| Dixon/Mauch/Tidhar harpsichord \(B\) + temperament from real music | https://webspace.eecs.qmul.ac.uk/s.e.dixon/pub/2012/JASMAN1311878_1.pdf |
| Student / experimental \(B\) (theory + Audacity) | https://journals.ed.ac.uk/esjs/article/download/9815/12844/35937 |

### B. From polyphonic / in-performance audio

Dixon et al. (JASA 2012): conservative transcription → high-res partial frequencies → robust \(B\) per note even when notes overlap. Hard case: partials of one note land near fundamentals of another; inharmonicity helps **disambiguate** assignment because pure-harmonic templates fail systematically.

Klapuri multi-F0 work also estimates an **inharmonicity factor with each source**.

### C. Guitar fretting / automatic fretboard maps

Barbancho et al.: estimate \(B\) from any played note (assuming known rough \(f_0\)), then use inharmonicity model to generate fretting/tuning corrections — stopped notes go **sharp** vs pure geometric frets.

---

## 3. Using partial sharpness as a **string / course fingerprint**

This is the practical trick behind “which string did this note come from?”

### Why it works

Different strings have different \((L, \text{gauge}, T, \text{wound vs plain})\), hence **different \(B\)**.  
The **shape** of partial offset vs \(n\) (not just \(f_0\)) is a fingerprint.

| Scenario | What \(B\) / partial sharpness tells you |
|----------|------------------------------------------|
| **Piano unisons** (bi/tri-chord) | Left/center/right strings often differ slightly in diameter or speaking length → slightly different \(B\). Measuring a full unison averages / corrupts \(B\); mute to one string. Unison “false” beating can be inharmonic mismatch, not only \(f_0\) mismatch. |
| **Same pitch, different courses** (12-string, mandolin, lute, octave pairs) | Octave course: thinner string → usually **higher \(B\)** → high partials much sharper. Unison courses: two strings same nominal pitch, different wear/gauge → separable by partial stretch. |
| **Guitar multi-string same pitch** (e.g. fretted note vs open on another string; harmonics) | Different gauge/tension → different \(B\). A note at ~196 Hz on G-string vs fretted D-string can be separated by partial stretch even when \(f_0\) matches. |
| **Open vs fretted** | Fretting shortens \(L\) → \(B \propto 1/L^2\) **rises** → same string fretted is more inharmonic; stopped notes pull sharp (classic guitar intonation pain). |
| **Wound vs plain** | Wound cores lower effective stiffness → often **lower \(B\)** than solid of same mass; scale breaks on piano show step changes in measured \(B\). |

### Practical discriminator (implementation sketch)

1. For each candidate string \(s\) with prior \((f_0^{(s)}, B^{(s)})\) (from open-string calibration or manufacturer scale data).
2. Predict partial template: \(f_n^{(s)} = n f_0^{(s)}\sqrt{1+B^{(s)} n^2}\).
3. Score observed peaks against templates (sum of log-likelihood or cents error).
4. Pick \(\arg\min_s\) residual — **partial sharpness curve** breaks ties when \(f_0\) alone cannot.

**Caveats**

- Attack noise / body resonances / phantom partials (harp, piano) bias high-\(n\) peaks.
- Bass piano: weak fundamental; people fit on partials 2–8, not always \(f_1\).
- Bowed strings mode-lock → partials nearly harmonic; **pluck/strike** needed for \(B\).
- Guitar: dirty/worn strings increase effective inharmonicity and wreck open-vs-fret consistency.

---

## 4. Piano / guitar tuner implementations

### Piano ETDs that measure \(B\) (or equivalent)

| Tool | How it uses inharmonicity | Notes |
|------|---------------------------|--------|
| **[TuneLab](https://www.tunelab-world.com/)** | Explicit **inharmonicity constant** per measured note; fits partial offsets; recommend measure ~C1–C5 (mute unisons); interpolates full scale | Manual: measure mode, partial offset graph, “if it looks reasonable → Save” |
| **[pianoscope](https://pianoscope.app/manual/en/pianoscope.html)** | Measures inharmonicity **and** partial intensities A0–C7 (~1 s/note); builds custom stretch | Fine vs coarse measurement modes |
| **[PianoMeter](http://pianometer.com/)** | Samples inharmonicity A0–C7; best-fit stretch / Railsback curve; shows live spectrum + \(B\) graph | Free midrange / paid full; multi-partial model resists one bad partial |
| **[Verituner](https://www.veritune.com/features.html)** | Measures inharmonicity **while tuning** every note (no separate pass); accumulates whole-scale map | Strong on small pianos / scaling quirks |

Generic chromatic tuners ignore \(B\) → well-tuned piano looks “flat bass / sharp treble.” That is the whole point of stretch.

**Field recipe (piano)**

1. Mute to **one string** of the unison.
2. Measure 4–6 notes across the compass (or full A0–C7 if the app wants it).
3. Inspect \(B\) vs note number: typical U-shape / rise toward extreme bass and treble; discard wild outliers.
4. App builds stretch (Railsback-like) so that **partials** of bass/treble match midrange, not pure 2:1 octaves.

### Guitar / fretted

- Cheap tuners: \(f_0\) only → inharmonic fretted notes and harmonics disagree.
- Guitarist folklore (JP X included): 5th/7th-fret harmonic tuning walks sharp ~2 ¢/string from inharmonicity; thick low E needs slight flat bias.
- Research / pro tools: estimate \(B\) per string, then set intonation / compensated saddles / stretch frets.
- Synthesis (Karplus–Strong + stiffness): \(B \sim 10^{-4}\) order for guitar, larger for piano bass.

---

## 5. Japanese sources & discussion

| Source | Content |
|--------|---------|
| [JP Wikipedia — インハーモニシティ](https://ja.wikipedia.org/wiki/インハーモニシティ) | Definition, elastic partial formula, \(B=\pi^2 EI/(L^2 T)\), stretch + multi-string unisons as mitigation |
| [ピアノパッサージュ — インハーモニシティー データ](https://pianopassage.jp/posts/post-9677/) | Wire-maker coefficients → predicted \(B\) tables by note |
| [西口 — ピアノの音響とその物理モデル (RIST)](https://www.rist.or.jp/rnews/56/56s4.pdf) | Physical model section on bending stiffness / inharmonicity |
| [岸 — 音律とピアノ調律 (PDF)](https://ehime-u.repo.nii.ac.jp/record/1021/files/AA11987685_2007_54-21.pdf) | Stretch vs partial choice in aural tuning |
| YouTube: [ピアノの最大の魅力：インハーモニシティ](https://www.youtube.com/watch?v=9k0a-aSdzMA) | Tuner’s explanation (JP) |

**X (JP) highlights**

- [@shell_waywise](https://x.com/shell_waywise/status/2059521889350176872) — bass tuned by matching **partials** to midrange → fundamentals sit slightly flat (stretch intuition; 65k+ views).
- [@kamado__](https://x.com/kamado__/status/2059586556382662855) — high-tension piano strings; A2/A3 via A2’s 2nd partial vs A3 fundamental beats; [small uprights = high \(B\)](https://x.com/kamado__/status/2059590843850510357); [per-piano “custom ET”](https://x.com/kamado__/status/2059612200520798258).
- [@DonsukeEarendel](https://x.com/DonsukeEarendel/status/2059610045772648608) — “インハーモニシティ… ordinary tuners can’t tune pianos.”
- [@ASHaka79612537](https://x.com/ASHaka79612537/status/2070728222346711109) — concrete partials: 440 → 881, 1325, 1772…
- [@tomoya_k](https://x.com/tomoya_k/status/2037388131079733474) — guitar: partials not integer → low strings need slight flat.
- [@mikio158cm](https://x.com/mikio158cm/status/834817471022403585) — harmonic-chain guitar tuning drifts ~6 ¢ by 3rd string.
- [@gah0316](https://x.com/gah0316/status/2073403337857548371) — piano not strict ET because of inharmonicity.

---

## 6. English X / popular posts

- [@sudara](https://x.com/sudara/status/1665089881092096001) — demo: successive partials of a string run sharp; “why piano tuning is art.”
- [@its_adamneely](https://x.com/its_adamneely/status/1354538984689565699) — stretch tuning explained for a general audience.
- EN Wikipedia + PTG threads: progressive partial sharpness demo with TuneLab scrolling partials of A2.

---

## 7. Technique cheat-sheet (implementers)

| Step | Detail |
|------|--------|
| Spectrum | Long FFT or parabolic/quadratic interpolated peaks; or time-domain high-res (phase vocoder / ESPRIT) for cents-level \(B\) |
| Fit | Linearize \((f_n/n)^2\) vs \(n^2\), or joint NLLS on \((f_0,B)\); robust loss (Huber) for bad peaks |
| Units | Piano \(B\) often quoted ~\(10^{-4}\)–\(10^{-2}\) depending on note/scale; TuneLab UI constants are scaled display units — don’t mix raw \(B\) with app “constants” without calibration |
| Unison | Always one string for \(B\); then tune mates to that string’s **partials**, not only fundamental |
| String ID | Calibrate open-string \(B_s\) per course; classify events by template match of partial stretch |
| Guitar | Re-estimate \(B\) after string change; fretted \(B\) rises with \(1/L^2\); harmonics for tuning are systematically sharp of fretted notes |
| Validation | Compare measured \(B\) to Fletcher solid/wound formulas from scale design (length, diameter, tension) — good sanity check |

---

## 8. Key links (bookmark list)

**Theory / defs**  
- https://en.wikipedia.org/wiki/Inharmonicity  
- https://ja.wikipedia.org/wiki/インハーモニシティ  
- https://www.phys.unsw.edu.au/jw/harmonics.html  

**Tuners**  
- https://www.tunelab-world.com/mtuner/MeasureInharmonicityButton.html  
- http://pianometer.com/  
- https://pianoscope.app/manual/en/pianoscope.html  
- https://www.veritune.com/features.html  

**Papers / code**  
- Dixon et al. 2012 (harpsichord \(B\) from music): PDF above  
- Rigaud et al. 2013 (piano \(B\) + tuning parametric model)  
- https://github.com/beiciliang/estimate-f0-inharmonicity  
- Barbancho guitar fretting via \(B\): https://riuma.uma.es/rest/api/core/bitstreams/89ab6cc3-f197-4c4e-8876-e44e5fc87905/content  
- Harp phantom-partial \(B\) estimation (JASA 2025): https://pubs.aip.org/asa/jasa/article/158/4/3187/3368787  

**JP practice blogs**  
- https://pianopassage.jp/posts/post-9677/  
- https://hpiano.main.jp/1449/  

---

### Bottom line

In practice, \(B\) is **not** guessed from pitch alone: you **measure partial frequencies**, fit \(f_n = n f_0\sqrt{1+Bn^2}\), and use the **progressive sharpness curve** both to (1) compute custom stretch for that instrument and (2) **fingerprint which string/course** produced a note when several candidates share similar \(f_0\). Piano ETDs (TuneLab, PianoMeter, pianoscope, Verituner) productize this; guitar work is thinner in commercial apps but well covered in papers and player folklore (harmonics vs frets, thick strings sharp).

If you want a follow-up, I can sketch a minimal Python pipeline (peak pick → linearized \(B\) fit → string classifier) or a comparison table of typical \(B\) ranges (guitar plain/wound vs piano bass/mid/treble).
