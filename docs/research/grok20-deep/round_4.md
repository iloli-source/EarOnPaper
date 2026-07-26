I'll search X and the web for both papers—code availability, follow-ups, applications, and any GitHub links.Found the Torres SOT repo; next I'll dig into Björkman/Elvander follow-ups, author accounts, and tighter X keyword searches.## Summary

**Code reality check**
| Paper | Public code? |
|--------|----------------|
| Björkman & Elvander (arXiv:2508.02471) | **No** public GitHub / PapersWithCode link found |
| Torres / Peeters / Richard (ICASSP 2024) | **Yes** — official repo + PyPI |
| Torres et al. follow-up (arXiv:2508.01493) | **Yes** — via PESTO codebase |

---

## 1. Inverse harmonic clustering (Björkman & Elvander)

**Paper:** *Inverse harmonic clustering for multi-pitch estimation: an optimal transport approach*  
**arXiv:** https://arxiv.org/abs/2508.02471 · PDF: https://arxiv.org/pdf/2508.02471  
**Posted:** 2025-08-04 (eess.SP)

### Idea (short)
Multi-pitch as recovering a **harmonically structured measure on the unit circle**. OT-based regularizers **transport / assign** observed spectral mass onto a small set of harmonic series (one per \(f_0\)). Decouples dictionary design from regularization (vs. classic CS multi-pitch), and is more robust to **inharmonicity**. Two estimators (stochastic + deterministic) with efficient numerical solvers. Beats classical SP baselines; competitive with nets unless the nets are heavily specialized + data-rich at inference.

### Code availability
- **No official/public implementation found** (no GitHub under authors’ names, no CatalyzeX/PapersWithCode hit).
- Algorithms are described in the paper; reimplementation would be from the math/algorithms section only.

### Author follow-ups (same lab: Aalto, Structured & Stochastic Modeling / AESIR)
1. **Robust Multi-Pitch Estimation via Optimal Transport Clustering** — **ICASSP 2025** (conference precursor; cited as [31] in the arXiv long paper).  
   Open PDF (Aalto): https://research.aalto.fi/files/176931403/Robust_Multi-Pitch_Estimation_via_Optimal_Transport_Clustering.pdf
2. **Off-The-Grid Multi-Pitch Estimation Using Optimal Transport** — **ICASSP 2026** (Barcelona).  
   Uses OT + block coordinate descent alternating spectrum estimate vs. \(f_0\); init from their prior estimator; better under small harmonic-model deviations / inharmonicity.  
   - Portal: https://research.aalto.fi/en/publications/off-the-grid-multi-pitch-estimation-using-optimal-transport/  
   - IEEE: https://ieeexplore.ieee.org/document/11460968/  
   - Open PDF: https://research.aalto.fi/files/218097647/Off_The-Grid_Multi-Pitch_Estimation_Using_Optimal_Transport.pdf  
3. Broader context: **AESIR** project (Acoustic Estimation, Sampling, and Interpolation; PI Filip Elvander, 2024–2028) — multi-pitch OT sits inside that agenda.

### Applications (as framed by authors)
- Multi-pitch / multi-\(f_0\) estimation from noisy mixtures (synthetic + real)
- Classical SP alternative when you want **inharmonicity robustness** without a fixed pitch grid (especially the off-grid ICASSP 2026 follow-up)
- Downstream-adjacent: music transcription stacks, analysis-by-synthesis, any pipeline needing several truncated harmonic series

### Related concurrent pitch+OT work (not the same authors)
Same week on arXiv: **Translation-Equivariant SSL for Pitch Estimation with OT** (Torres et al.) — see §2 follow-up.

---

## 2. Spectral OT for harmonic parameter estimation (Torres / Peeters / Richard)

**Paper:** *Unsupervised Harmonic Parameter Estimation Using Differentiable DSP and Spectral Optimal Transport*  
**Venue:** ICASSP 2024  
**arXiv:** https://arxiv.org/abs/2312.14507  
**Poster:** https://bernardo-torres.github.io/documents/Torres_ICASSP_2024_poster.pdf  
**Author page:** https://bernardotorres.net/

### Idea (short)
Spectral reconstruction loss from **1-D optimal transport** (minimize displacement of spectral energy) so a lightweight encoder + differentiable harmonic synthesizer can jointly learn \(f_0\) + harmonic amplitudes **without** an external pitch tracker. Aimed at unsupervised / DDSP-style neural audio parameter estimation.

### GitHub / install (official)
| Resource | URL |
|----------|-----|
| **Main package repo** | https://github.com/bernardo-torres/spectral-optimal-transport |
| **Paper reproduction branch** | https://github.com/bernardo-torres/spectral-optimal-transport/tree/paper |
| **PyPI** | `pip install sot-loss` → https://pypi.org/project/sot-loss/ |
| **Author homepage code link** (alias/old name) | https://github.com/bernardo-torres/1d-spectral-optimal-transport |

Core API: `Wasserstein1DLoss`, `MultiResolutionSOTLoss` (STFT / mel / CQT / custom 2-D maps).

### Follow-ups / lineage (Torres line)
1. **Translation-Equivariant Self-Supervised Learning for Pitch Estimation with Optimal Transport**  
   - arXiv: https://arxiv.org/abs/2508.01493  
   - ISMIR 2025 LBD  
   - OT objective for 1-D translation-equivariant systems → single-pitch SSL  
   - **Code:** https://github.com/SonyCSLParis/pesto (PESTO stack; also used for the related TISMIR PESTO paper)
2. Broader Torres lab: Inverse Drum Machine, linear audio autoencoders, etc. (different tasks; same “analysis-by-synthesis + structured losses” vibe) — see bernardotorres.net.

### Applications
- Unsupervised harmonic \(f_0\) / amplitude estimation  
- Differentiable DSP training losses (DDSP, synthesizer fitting)  
- Drop-in spectral comparison metric (pip package is loss/metric oriented, not only pitch)  
- Self-supervised pitch trackers (follow-up + PESTO)

---

## 3. X posts + links (EN-relevant hits)

X discussion is **thin** on Björkman/Elvander (no author accounts found; almost no English commentary). Stronger signal for Torres ICASSP + the Aug 2025 “OT for pitch” cluster.

| Date | Author | What | Link |
|------|--------|------|------|
| 2025-08-08 | @korguchi | Notes OT is “trending” for pitch; links **both** Aug papers (2508.01493 + **2508.02471**) | https://x.com/korguchi/status/1953644316263690627 |
| 2025-08-06 | @ArxivSound | Announces Torres et al. translation-equivariant OT pitch (2508.01493) | https://x.com/ArxivSound/status/1952891331363389727 |
| 2025-08-05 | @AudioAndSpeech | Same 2508.01493 bot drop | https://x.com/AudioAndSpeech/status/1952850734912868850 |
| 2024-02-01 | @GeoffroyPeeters | ICASSP 2024 ADASP list; **Paper #1 = Torres spectral OT harmonic params** | https://x.com/GeoffroyPeeters/status/1753039431009734936 |
| 2024-01-17 | @ArxivSound | arXiv update for Torres SOT paper (2312.14507v3) | https://x.com/ArxivSound/status/1747487250718318659 |
| 2023-12-25 | @mlsp4audio | DailyAudioPapers pick: Torres unsupervised harmonic params + SOT | https://x.com/mlsp4audio/status/1739245865020338519 |
| 2023-12-25 | @Memoirs | ML-papers bot listing of same paper | https://x.com/Memoirs/status/1739337781443228134 |

**Not found on X:** author threads from Björkman/Elvander; GitHub release posts for IHC; English deep-dives beyond bots + the one community note from @korguchi.

---

## 4. GitHub checklist (copy-paste)

```
# Torres et al. ICASSP 2024 — Spectral OT losses (OFFICIAL)
https://github.com/bernardo-torres/spectral-optimal-transport
  → pip install sot-loss
  → paper branch: .../tree/paper

# Torres et al. follow-up / PESTO SSL pitch (related OT objective)
https://github.com/SonyCSLParis/pesto

# Björkman & Elvander inverse harmonic clustering
(no public repo as of this search)
```

---

## 5. Practical takeaway

- **Need runnable OT spectral losses / unsupervised harmonic fitting →** Torres stack (`sot-loss` + paper branch).  
- **Need multi-pitch OT clustering / off-grid SP estimators →** Björkman–Elvander papers only (ICASSP 2025 → arXiv long form 2508.02471 → ICASSP 2026 off-grid); **code not released** — contact `anton.bjorkman@aalto.fi` / Elvander via Aalto if you need it.  
- **Need self-supervised single-pitch with OT training objective →** https://github.com/SonyCSLParis/pesto + arXiv:2508.01493.

If you want, I can next pull method tables (IHC vs SOT vs PESTO) or skim the ICASSP 2026 off-grid PDF for algorithm pseudocode differences from 2508.02471.
