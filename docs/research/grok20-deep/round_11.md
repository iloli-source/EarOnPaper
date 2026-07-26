Compiling the research brief and posting the work log.# Demucs guitar stems vs 2025–2026 alternatives (EN + JP)

**Bottom line:** Stock Demucs (esp. `htdemucs_6s`) is still fine for practice/karaoke-style “guitar-ish” isolation, but **distorted / metal / wall-of-sound guitar is a known weak case**. For guitar-specific quality in 2025–2026, community consensus and MVSEP leaderboards point to **BS-RoFormer SW / MelBand RoFormer / MDX23C guitar models (often ensembled)** over stock Demucs.

---

## Demucs: known issues on distorted guitar

| Issue | Detail |
|--------|--------|
| **Upstream archived** | Meta `facebookresearch/demucs` archived **2025-01-01** — maintenance is forks only. |
| **Guitar is experimental** | Official note: 6-stem adds guitar/piano; **guitar “okay”, piano lots of bleed/artifacts**. |
| **MVSEP labels quality “so-so”** | On MVSEP: `htdemucs_6s` “quality for [piano/guitar] is still so-so.” Guitar val SDR **5.22 dB** vs stronger specialized models. |
| **6-stem quality tradeoff** | Harder multi-class task → lower per-stem quality vs best 4-stem `htdemucs_ft`. |
| **Distortion + cymbals** | Broadband high-gain guitar overlaps cymbals/hi-hats → **cymbal wash bleed**, muddy “other” leftovers. Guitar-ft model still calls this the hardest case. |
| **Multi-guitar** | Lead + rhythm + acoustic usually **collapse into one stem** — no layer split. |
| **User reports** | Experimental guitar/piano “inconsistent”; Demucs can sound thin/artifacty vs newer models. |

**Why distortion hurts:** High-gain tone fills mid/high spectrum like noise + percussion; models trained mostly on cleaner/multi-genre stems under-separate harmonic “fuzz” from cymbals and dense layers.

---

## Guitar SDR ladder (MVSEP guitar validation)

Higher SDR = better. From MVSEP Guitar algorithms page:

| Model / pipeline | Guitar SDR (dB) | Other SDR |
|------------------|-----------------|-----------|
| Demucs4HT 6 stems | **5.22** | 12.19 |
| MDX23C (2023.08) | 4.78 | 11.75 |
| MDX23C (2024.06) | **6.34** | 13.31 |
| MelRoformer (2024.06) | **7.02** | 13.99 |
| BSRoformer (viperx) | **7.16** | 14.13 |
| Ensemble MDX23C + Mel | **7.18** | 14.15 |
| Ensemble BSRo + Mel | **7.51** | 14.48 |
| **BS Roformer SW (6-stem)** | **9.05** | 16.02 |

**Takeaway:** Best single-shot guitar numbers on this board are **~+3.8 dB** over Demucs6s (`9.05` vs `5.22`) for BS-RoFormer SW.

BS Roformer SW Multisong-style stem SDRs (MVSEP): vocals 11.30 · bass 14.62 · drums 14.11 · **guitar 9.05** · piano 7.83 · other 8.71.

---

## Alternatives (what to use when)

### 1. BS-RoFormer family (incl. SW / MelBand / community weights)
- **ByteDance BS-RoFormer** — SOTA band-split + RoPE attention; open reimpl: [lucidrains/BS-RoFormer](https://github.com/lucidrains/BS-RoFormer).
- **BS Roformer SW** — true **6-stem** (vocals/bass/drums/guitar/piano/other); often called best multi-stem package for guitar+piano in 2025–26 community writeups.
- **MelBand RoFormer** — strong vocals/instrum; used in guitar ensembles.
- **Community checkpoints** (Viperx 1296/1297, unwa, Revive, jarredou SW, etc.) via UVR / MVSEP / Hugging Face.
- **JP X note (Jun 2025):** BS Roformer SW “明らかにきれいに分離できる” for piano/guitar vs older ensembles.  
  https://x.com/haru_1564AP/status/1932223838097662224

### 2. UVR + MDX23C
- UVR remains the main **local** multi-model GUI (MDX, Demucs, Roformers, ensembles).
- **MDX23C** = full-band kuielab/SDX23-style nets; UVR “HQ” inst/voc models still popular; guitar-specific MDX23C on MVSEP beats Demucs6s after 2024 retrain.
- JP: BS-Roformer Revive 2 praised as large jump over UVR-MDX-NET Inst HQ5 defaults.  
  https://note.com/namanamanamazun/n/n71abd740c7b3

### 3. SCNet (Sparse Compression Network)
- Competitive quality with **far fewer params** than BS-RoFormer; good ensemble member for vocals/drums/instrum.
- Not primarily “guitar-named,” but **SCNet XL / IHF** appear in MVSEP top ensembles (2024.12–2025.06).
- **JP:** SCNet study deck (まつ/Kenmatsu4, Jul 2025)  
  https://speakerdeck.com/kenmatsu4/lun-wen-shao-jie-yin-yuan-fen-li-scnet-sparse-compression-network-for-music-source-separation  
  X: https://x.com/Kenmatsu4/status/1942522379902804417

### 4. Guitar-specific / guitar-first models
| Tool | Role | Link |
|------|------|------|
| **MVSep Guitar** | Dedicated guitar vs other; MDX23C + Mel + BSRo (+ ensembles) | https://mvsep.com/algorithms/17 · https://mvsep.com/en/algorithms |
| **Guitar leaderboard** | Live SDR ranking | https://mvsep.com/quality_checker/leaderboard/guitar |
| **HTDemucs-6s Guitar Expert (ft)** | MoisesDB fine-tune; +0.31 SDR / **+0.89 SIR** vs stock 6s; still weak on extreme metal + cymbals | https://huggingface.co/adityalakhani/htdemucs-6s-guitar-ft |
| **Ensemble All-In** | Slow multi-stem path; guitar/piano from filtered intermediate stems | https://mvsep.com/algorithms/47 |

### 5. Practical Japanese workflow notes (X)
- Use **`htdemucs_6s` only when you need guitar**; otherwise `htdemucs_ft` 4-stem for bass/practice, try UVR.  
  https://x.com/hachi_vm/status/2039626922658058308
- Demucs GUI / Melissa for ear-copy + tempo; 6-stem for guitar practice.  
  https://x.com/okiraku_san/status/1901195603193020759  
  https://x.com/masaki_xmas/status/1885949184362295474
- 4-stem Demucs can’t do keyboard; need other models.  
  https://x.com/poTTer_5893/status/1955556825077784587

---

## ギター分離 モデル比較 (quick JP matrix)

| 用途 | 第一候補 | 第二候補 | コメント |
|------|----------|----------|----------|
| **歪みギター抽出（品質優先）** | MVSep Guitar ensemble / BS-RoFormer SW | MelRo + MDX23C ensemble | Demucs6sより明確に上 |
| **6stem一括（歌/ベース/ドラ/ギ/ピ）** | BS Roformer SW | htdemucs_6s / Guitar-ft | SWがSDR上優勢 |
| **ローカル・無料GUI** | UVR5 + Roformer weights | Demucs-GUI / Melissa | Roformer導入で差が出る |
| **軽量・速度** | SCNet XL | htdemucs (non-ft) | SOTAには少し届かないがコスパ良 |
| **メタル高ゲイン+シンバル** | Ensemble + 聴感でA/B | Guitar-ft as Demucs path | 完全分離は未解決 |
| **耳コピ練習（十分）** | htdemucs_6s / Melissa | — | 品質より手軽さ |

---

## Recommended pipelines (2025–2026)

1. **Best guitar stem (web):**  
   [MVSEP Guitar](https://mvsep.com/algorithms/17) → prefer **Ensemble (BSRo+Mel)** or **BS Roformer SW** if you also want other stems.

2. **Best local:**  
   **UVR5** with latest **BS-RoFormer / MelBand** checkpoints; optional ensemble with MDX23C Inst. Avoid relying on stock Demucs for final guitar quality.

3. **Demucs-only path:**  
   Prefer **`htdemucs-6s-guitar-ft`** over stock 6s for clearer guitar and less bleed; still expect metal+cymbal limits.  
   https://huggingface.co/adityalakhani/htdemucs-6s-guitar-ft

4. **Dense rock/metal practice tip:**  
   Vocals first with best vocal RoFormer → instrumental → **guitar-only model** often cleaner than one-shot 6-stem.

---

## Key links

| Resource | URL |
|----------|-----|
| MVSEP algorithms (all models + guitar table) | https://mvsep.com/en/algorithms |
| MVSEP Guitar | https://mvsep.com/algorithms/17 |
| Guitar leaderboard | https://mvsep.com/quality_checker/leaderboard/guitar |
| BS-RoFormer (paper impl) | https://github.com/lucidrains/BS-RoFormer · arXiv:2309.02612 |
| Mel-Band RoFormer paper | arXiv:2310.01809 |
| SCNet paper | arXiv:2401.13276 |
| Demucs (archived) | https://github.com/facebookresearch/demucs |
| UVR GUI | https://github.com/Anjok07/ultimatevocalremovergui |
| Guitar-ft Demucs | https://huggingface.co/adityalakhani/htdemucs-6s-guitar-ft |
| JP SCNet deck | https://speakerdeck.com/kenmatsu4/lun-wen-shao-jie-yin-yuan-fen-li-scnet-sparse-compression-network-for-music-source-separation |
| JP UVR / BS-Roformer note | https://note.com/namanamanamazun/n/n71abd740c7b3 |
| JP “local strongest vocal models” | https://zenn.dev/unwa/articles/0b6525bb6d4f9f |

---

## X posts worth saving

| Lang | Summary | Link |
|------|---------|------|
| JP | BS Roformer SW cleaner piano/guitar than old ensembles | https://x.com/haru_1564AP/status/1932223838097662224 |
| JP | SCNet paper intro (guitar/vocal separation) | https://x.com/Kenmatsu4/status/1942522379902804417 |
| JP | htdemucs_6s only when guitar needed; UVR trial | https://x.com/hachi_vm/status/2039626922658058308 |
| JP | Melissa + Demucs for guitar practice | https://x.com/okiraku_san/status/1901195603193020759 |
| JP | demucs.cpp-JUCE / Melissa guitar stems | https://x.com/masaki_xmas/status/1885949184362295474 |
| EN | Demucs overview + fork note (Jul 2026) | https://x.com/DanKornas/status/2079368487781208484 |

---

**Practical verdict for distorted guitar:** Treat stock **Demucs guitar as “good enough for learning”**, not production isolation. Prefer **MVSep Guitar / BS-RoFormer SW / Mel+MDX ensembles** (and UVR with those weights). For metal wall-of-sound, budget for **residual cymbal bleed** no matter the model—ensembles + A/B per track still win.
