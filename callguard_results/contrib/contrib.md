# Was bringt was: Beitrag der Komponenten

Generated 2026-10-10T12:10:07+0200 by `callguard contrib` from `/home/bl/repos/hackathon/sprintd/.claude/worktrees/agent-a16a203b1c36e3d18/runs/experiments` (spec `/home/bl/repos/hackathon/sprintd/.claude/worktrees/agent-a16a203b1c36e3d18/experiments/contrib/contrib.yaml`, 2000 bootstrap resamples, seed 13). Every row is a **paired** comparison B − A on the same calls; 95% percentile bootstrap CI over twin groups/dialogues; **bold** = CI excludes 0 (real). AUC = flag AUC from the scores; FAR / miss / acc / review recall at the `cv` threshold (out-of-fold CV unless the row says `fixed`), differences in percentage points. Verdict: gain / loss = some decision metric (AUC, FAR, miss, 3-class acc) really better / worse, mixed = both, noise = nothing real; review recall is shown but does not decide (6 dev calls / 3 dialogues). Status: exact = only the factor differs, caveat = near-exact (note), confounded = something else differs too.

## Factors

| factor | comparison (A → B) | status | n | Δ flag AUC | Δ FAR (pp) | Δ miss (pp) | Δ 3-class acc (pp) | Δ review recall (pp) | flips | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| Prüfungsdesign: freier Richter + G-Eval (v1) → Fakten | v1 → nur Fakten (Turbo, 7B) | caveat | 48 | **+0.16 [+0.05, +0.28]** | **-68 [-92, -38]** | +12 [-6, +31] | **+35 [+12, +57]** | -50 [-100, +0] | 29 | gain |
| Prüfungsdesign: freier Richter + G-Eval (v1) → Fakten | v1 → Stichwörter/Muster + Fakten (Turbo, 7B) | caveat | 48 | +0.11 [-0.01, +0.24] | **-68 [-92, -38]** | +12 [-6, +31] | +21 [-4, +46] | -33 [-100, +0] | 29 | gain |
| Prüfungsdesign: freier Richter + G-Eval (v1) → Fakten | v1 → nur Fakten (synthetisch, 14B, ORACLE-Text) | exact | 74 | -0.01 [-0.13, +0.10] | **-46 [-68, -26]** | **+28 [+13, +43]** | +0 [-11, +12] | **-52 [-74, -30]** | 42 | mixed |
| ASR: Turbo → large-v3 (MIT) | Champion-Prüfungen: Turbo (ohne Prompt) → large-v3 | exact | 48 | +0.02 [-0.02, +0.05] | +0 [+0, +0] | -8 [-19, +0] | +6 [-8, +24] | +67 [+0, +100] | 13 | noise |
| ASR: Turbo → large-v3 (MIT) | Nur Fakten, 7B: Turbo → large-v3 | caveat | 48 | +0.05 [+0.00, +0.11] | -5 [-14, +0] | -12 [-25, +0] | +6 [-5, +20] | +33 [+0, +100] | 12 | noise |
| ASR: Turbo → large-v3 (MIT) | Nur Fakten, 14B: Turbo → large-v3 | exact | 48 | -0.02 [-0.08, +0.05] | +5 [-12, +21] | +0 [-12, +10] | -10 [-23, +0] | +0 [+0, +0] | 15 | noise |
| ASR: Turbo → large-v3 (MIT) | v1-Prüfungen: Turbo → large-v3 | confounded | 48 | -0.02 [-0.16, +0.11] | **+41 [+15, +71]** | -19 [-50, +12] | -15 [-35, +7] | +0 [-100, +100] | 28 | loss |
| Transkript-Obergrenze: ASR → ORACLE-Referenzskript | 7B Fakten: large-v3 → ORACLE | confounded | 48 | **-0.13 [-0.27, -0.02]** | +5 [-12, +28] | **+31 [+8, +58]** | -17 [-38, +0] | -67 [-100, +0] | 16 | loss |
| Transkript-Obergrenze: ASR → ORACLE-Referenzskript | 14B Fakten: large-v3 → ORACLE | confounded | 48 | +0.05 [-0.04, +0.14] | -18 [-40, +0] | +0 [-17, +21] | **+23 [+8, +39]** | +67 [+0, +100] | 13 | gain |
| LLM-Grösse: 7B → 8B → 14B (Fakten) | 7B → 14B (large-v3, nur Fakten) | exact | 48 | -0.04 [-0.09, +0.00] | +5 [+0, +15] | +8 [+0, +19] | -15 [-33, +0] | -67 [-100, +0] | 9 | noise |
| LLM-Grösse: 7B → 8B → 14B (Fakten) | 7B → 14B (Turbo, nur Fakten) | caveat | 48 | +0.03 [-0.03, +0.10] | -5 [-15, +0] | -4 [-17, +9] | +2 [-10, +11] | -33 [-100, +0] | 8 | noise |
| LLM-Grösse: 7B → 8B → 14B (Fakten) | Qwen2.5-7B → Qwen3-8B (Turbo, nur Fakten) | confounded | 48 | **-0.10 [-0.20, -0.02]** | -9 [-42, +22] | +23 [-0, +50] | -4 [-15, +4] | -33 [-100, +0] | 15 | loss |
| LLM-Grösse: 7B → 8B → 14B (Fakten) | Champion 7B → Champion 14B | confounded | 48 | -0.05 [-0.11, +0.00] | +5 [+0, +15] | +8 [+0, +19] | -15 [-33, +0] | -67 [-100, +0] | 9 | noise |
| Fragen-Formulierung / Dev-Anpassung | abgestimmt → Paraphrase 1 (7B) | exact | 48 | **-0.15 [-0.31, -0.02]** | +9 [+0, +23] | **+23 [+4, +45]** | -12 [-31, +2] | -67 [-100, +0] | 15 | loss |
| Fragen-Formulierung / Dev-Anpassung | abgestimmt → Paraphrase 2 (7B) | exact | 48 | **-0.13 [-0.29, -0.01]** | +9 [+0, +22] | +15 [+0, +38] | -8 [-24, +4] | -67 [-100, +0] | 13 | loss |
| Fragen-Formulierung / Dev-Anpassung | abgestimmt → Ensemble 3 Formulierungen (7B) | exact | 48 | **-0.12 [-0.28, -0.00]** | +5 [+0, +14] | +15 [+0, +38] | -4 [-20, +7] | -67 [-100, +0] | 11 | loss |
| Fragen-Formulierung / Dev-Anpassung | abgestimmt → Ensemble ohne abgestimmte Formulierung (7B) | exact | 48 | -0.11 [-0.28, +0.00] | +5 [+0, +14] | +15 [+0, +38] | -6 [-23, +6] | -67 [-100, +0] | 12 | noise |
| Fragen-Formulierung / Dev-Anpassung | abgestimmte → blinde Tabelle (7B, large-v3) | exact | 48 | -0.10 [-0.24, +0.00] | +5 [-13, +29] | **+27 [+6, +50]** | **-21 [-40, -6]** | -67 [-100, +0] | 15 | loss |
| Fragen-Formulierung / Dev-Anpassung | abgestimmt → Paraphrase 1 (14B, large-v3) | caveat | 48 | +0.03 [-0.04, +0.09] | -9 [-22, +0] | +4 [+0, +12] | +12 [+0, +26] | +0 [+0, +0] | 9 | noise |
| Fragen-Formulierung / Dev-Anpassung | abgestimmte → blinde Tabelle (14B, large-v3) | exact | 48 | +0.00 [-0.08, +0.07] | +9 [+0, +22] | -12 [-23, +0] | -6 [-20, +6] | +0 [+0, +0] | 12 | noise |
| Fragen-Formulierung / Dev-Anpassung | abgestimmt → Paraphrase 1 (synthetisch, 7B) | exact | 74 | **-0.11 [-0.18, -0.03]** | **+14 [+4, +28]** | +11 [+0, +23] | **-11 [-17, -5]** | -5 [-16, +0] | 14 | loss |
| Fragen-Formulierung / Dev-Anpassung | abgestimmt → Ensemble 3 (synthetisch, 7B) | exact | 74 | +0.00 [-0.03, +0.04] | +4 [+0, +12] | +0 [-9, +9] | -4 [-10, +1] | -5 [-16, +0] | 8 | noise |
| Sprache: Deutsch → Englisch | Fakt-Fragen Deutsch → Englisch (Champion) | exact | 48 | **+0.13 [+0.01, +0.29]** | +0 [+0, +0] | **-27 [-50, -5]** | +8 [-7, +29] | +67 [+0, +100] | 13 | gain |
| Sprache: Deutsch → Englisch | Transkript Deutsch → englische Übersetzung (7B, Turbo) | caveat | 48 | -0.01 [-0.08, +0.03] | +0 [-14, +14] | +4 [-15, +25] | -2 [-15, +9] | -33 [-100, +0] | 10 | noise |
| Rollen Berater/Kunde sichtbar | Rollen verborgen → sichtbar (Champion) | exact | 48 | +0.06 [+0.00, +0.15] | -5 [-14, +0] | -12 [-23, +0] | **+12 [+2, +27]** | +67 [+0, +100] | 10 | gain |
| Stichwörter/Muster mit leichtem Gewicht | nur Fakten → + leichte Stichwörter/Muster (Champion) | exact | 48 | -0.02 [-0.06, +0.00] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | 0 | noise |
| Stichwörter/Muster mit leichtem Gewicht | nur Fakten → + leichte Stichwörter/Muster (Turbo, 7B) | caveat | 48 | **-0.03 [-0.08, -0.00]** | +0 [+0, +0] | +0 [+0, +0] | -2 [-7, +0] | +0 [+0, +0] | 1 | loss |
| Stichwörter/Muster mit leichtem Gewicht | v1 ohne Stichwörter → mit Stichwörtern | exact | 48 | -0.01 [-0.03, +0.00] | **-27 [-55, -5]** | +15 [-5, +39] | +4 [-10, +23] | +33 [-50, +100] | 19 | gain |
| Fusion: Schwelle, Prüfband, Eskalation | Schwelle 0.55 → 0.45 (feste Schwelle) (fixed) | exact | 48 | +0.00 [+0.00, +0.00] | +0 [+0, +0] | +0 [+0, +0] | -2 [-20, +11] | -67 [-100, +0] | 10 | noise |
| Fusion: Schwelle, Prüfband, Eskalation | Schwelle 0.55 → 0.65 (feste Schwelle) (fixed) | exact | 48 | +0.00 [+0.00, +0.00] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | 0 | noise |
| Fusion: Schwelle, Prüfband, Eskalation | Prüfband 0.15 → 0.25 (Champion) | exact | 48 | +0.00 [+0.00, +0.00] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | 0 | noise |
| Fusion: Schwelle, Prüfband, Eskalation | Unsicherheits-Eskalation an → aus (Champion) | exact | 48 | +0.00 [+0.00, +0.00] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | 0 | noise |
| Fusion: Schwelle, Prüfband, Eskalation | Unsicherheits-Eskalation an → aus (v1) | exact | 48 | +0.00 [+0.00, +0.00] | +23 [+0, +50] | -15 [-36, +0] | +0 [-17, +14] | -33 [-100, +0] | 16 | noise |
| Fusion: Schwelle, Prüfband, Eskalation | Stichwörter enthalten sich ohne Treffer (v1) | exact | 48 | -0.03 [-0.12, +0.04] | +23 [+0, +50] | -15 [-36, +0] | -2 [-19, +11] | -33 [-100, +0] | 16 | noise |
| Policy-Tabelle v1 → v2 / v3 | Tabelle v1 → v2 (Dev) | exact | 48 | +0.00 [-0.10, +0.12] | +23 [+0, +54] | -8 [-25, +0] | -15 [-35, +0] | -33 [-100, +0] | 9 | noise |
| Policy-Tabelle v1 → v2 / v3 | Tabelle v1 → v3 (Dev) | exact | 48 | +0.05 [+0.00, +0.17] | +0 [+0, +0] | -8 [-25, +0] | +4 [+0, +14] | +33 [+0, +100] | 2 | noise |
| Policy-Tabelle v1 → v2 / v3 | Tabelle v1 → v3 (neu aufgenommenes Audio) | exact | 48 | +0.05 [+0.00, +0.18] | +0 [+0, +0] | -8 [-25, +0] | +0 [+0, +0] | +0 [+0, +0] | 2 | noise |
| Policy-Tabelle v1 → v2 / v3 | Tabelle v1 → v3 (synthetisch, 7B) | exact | 74 | +0.02 [+0.00, +0.06] | +0 [+0, +0] | -7 [-13, +0] | +0 [+0, +0] | +0 [+0, +0] | 3 | noise |
| Robustheit: Dev → andere Bedingungen | Dev-Audio → neu aufgenommen (Tempo 0.96, -3 dB) | exact | 48 | -0.04 [-0.11, +0.01] | +0 [+0, +0] | +8 [+0, +18] | -6 [-24, +8] | -67 [-100, +0] | 12 | noise |
| Robustheit: Dev → andere Bedingungen | Dev-Audio → neu aufgenommen (Tabelle v3) | exact | 48 | -0.04 [-0.10, +0.00] | +0 [+0, +0] | +8 [+0, +18] | -10 [-30, +6] | **-100 [-100, -100]** | 14 | noise |
| Robustheit: Dev → andere Bedingungen | Dev → synthetisch out-of-sample (nur Fakten, 7B) | unpaired | 48 / 74 | 0.89 vs 0.80 | 14% vs 7% | 15% vs 43% | – | – | – | unpaired |
| Weitere geprüfte Ideen | S3 'keine stille Entlastung' (Champion) | exact | 48 | +0.02 [-0.03, +0.10] | +36 [+0, +70] | -8 [-25, +0] | -17 [-36, +0] | +0 [+0, +0] | 10 | noise |
| Weitere geprüfte Ideen | S1 Ja/Nein erst ab p ≥ 0.8 (Champion) | exact | 48 | -0.01 [-0.03, +0.00] | +5 [+0, +15] | +4 [+0, +12] | -2 [-17, +11] | -33 [-100, +0] | 10 | noise |
| Weitere geprüfte Ideen | Fakten auch auf Präfixen (prefix-max) | exact | 48 | +0.00 [+0.00, +0.00] | +5 [+0, +15] | +0 [+0, +0] | -2 [-7, +0] | +0 [+0, +0] | 1 | noise |
| Weitere geprüfte Ideen | S2 Few-Shot-Beispiele pro Fold | caveat | 48 | -0.07 [-0.20, +0.01] | +0 [+0, +0] | +12 [+0, +29] | -8 [-24, +2] | -67 [-100, +0] | 8 | noise |
| Weitere geprüfte Ideen | Hybrid: Richter darf zu Prüfen eskalieren (Turbo, 7B) | caveat | 48 | -0.02 [-0.05, +0.00] | +9 [+0, +25] | +0 [+0, +0] | -4 [-12, +0] | +0 [+0, +0] | 2 | noise |
| Scorer: Qwen 7B → Kev-4B (gleiche Fragen) | Qwen 7B → Kev-4B (allgemeine, gesetzesbasierte Fragen) | exact | 48 | +0.07 [-0.12, +0.22] | +5 [-27, +35] | +19 [+0, +41] | -4 [-22, +11] | -17 [-50, +0] | 22 | noise |
| Scorer: Qwen 7B → Kev-4B (gleiche Fragen) | Qwen 7B → Kev-4B (abgestimmte Fragen) | exact | 48 | -0.01 [-0.21, +0.14] | -14 [-35, +0] | +15 [-6, +41] | -10 [-36, +9] | -67 [-100, +0] | 15 | noise |
| Fragen: abgestimmt → allgemein, gesetzesbasiert (gleicher Scorer) | abgestimmt → allgemein (Qwen 7B) | exact | 48 | -0.14 [-0.30, +0.01] | **+50 [+17, +80]** | -8 [-25, +0] | **-25 [-45, -7]** | -33 [-100, +0] | 22 | loss |
| Fragen: abgestimmt → allgemein, gesetzesbasiert (gleicher Scorer) | abgestimmt → allgemein (Kev-4B) | exact | 48 | -0.07 [-0.26, +0.15] | **+68 [+44, +89]** | -4 [-32, +23] | -19 [-39, +5] | +17 [+0, +50] | 28 | loss |
| Kev: ASR und Transkript-Obergrenze | Kev allgemein: large-v3 → ORACLE | confounded | 48 | +0.10 [-0.04, +0.25] | -23 [-64, +25] | -19 [-45, +5] | +12 [-12, +39] | +17 [-50, +100] | 24 | noise |

### Takeaway per factor

- **Prüfungsdesign: freier Richter + G-Eval (v1) → Fakten**: 2× belegter Gewinn, 1× Abwägung (Gewinn und Verlust). Leitvergleich: v1 → nur Fakten (Turbo, 7B): Flag-AUC 0.68 → 0.84 (+0.16 [+0.05, +0.28]) belegt; Fehlalarme 86% → 18%, verpasst 15% → 27%; 29 von 48 Entscheiden ändern sich → **belegter Gewinn** (Fehlalarmquote -68 Pkt., Exakter Status +35 Pkt. belegt).
- **ASR: Turbo → large-v3 (MIT)**: 3× Rauschen (KI enthält 0), 1× verzerrt (nicht gezählt). Leitvergleich: Champion-Prüfungen: Turbo (ohne Prompt) → large-v3: Flag-AUC 0.85 → 0.87 (+0.02 [-0.02, +0.05]); Fehlalarme 14% → 14%, verpasst 23% → 15%; 13 von 48 Entscheiden ändern sich → **im Rauschen**.
- **Transkript-Obergrenze: ASR → ORACLE-Referenzskript**: 2× verzerrt (nicht gezählt). Leitvergleich: 7B Fakten: large-v3 → ORACLE: Flag-AUC 0.89 → 0.76 (-0.13 [-0.27, -0.02]) belegt; Fehlalarme 14% → 18%, verpasst 15% → 46%; 16 von 48 Entscheiden ändern sich → **belegter Verlust** (Verpasst +31 Pkt. belegt) · verzerrt: the reference scripts are Swiss German DIALECT text with reference speakers, the ASR view is Standard German with diarized roles: transcript quality AND language change together. ORACLE is never a submission candidate.
- **LLM-Grösse: 7B → 8B → 14B (Fakten)**: 2× Rauschen (KI enthält 0), 2× verzerrt (nicht gezählt). Leitvergleich: 7B → 14B (large-v3, nur Fakten): Flag-AUC 0.89 → 0.85 (-0.04 [-0.09, +0.00]); Fehlalarme 14% → 18%, verpasst 15% → 23%; 9 von 48 Entscheiden ändern sich → **im Rauschen**.
- **Fragen-Formulierung / Dev-Anpassung**: 5× belegter Verlust, 4× Rauschen (KI enthält 0). Leitvergleich: abgestimmt → Paraphrase 1 (7B): Flag-AUC 0.87 → 0.72 (-0.15 [-0.31, -0.02]) belegt; Fehlalarme 14% → 23%, verpasst 15% → 38%; 15 von 48 Entscheiden ändern sich → **belegter Verlust** (Verpasst +23 Pkt. belegt).
- **Sprache: Deutsch → Englisch**: 1× belegter Gewinn, 1× Rauschen (KI enthält 0). Leitvergleich: Fakt-Fragen Deutsch → Englisch (Champion): Flag-AUC 0.73 → 0.87 (+0.13 [+0.01, +0.29]) belegt; Fehlalarme 14% → 14%, verpasst 42% → 15%; 13 von 48 Entscheiden ändern sich → **belegter Gewinn** (Verpasst -27 Pkt. belegt).
- **Rollen Berater/Kunde sichtbar**: 1× belegter Gewinn. Leitvergleich: Rollen verborgen → sichtbar (Champion): Flag-AUC 0.81 → 0.87 (+0.06 [+0.00, +0.15]); Fehlalarme 18% → 14%, verpasst 27% → 15%; 10 von 48 Entscheiden ändern sich → **belegter Gewinn** (Exakter Status +12 Pkt. belegt).
- **Stichwörter/Muster mit leichtem Gewicht**: 1× belegter Gewinn, 1× belegter Verlust, 1× Rauschen (KI enthält 0). Leitvergleich: nur Fakten → + leichte Stichwörter/Muster (Champion): Flag-AUC 0.89 → 0.87 (-0.02 [-0.06, +0.00]); Fehlalarme 14% → 14%, verpasst 15% → 15%; 0 von 48 Entscheiden ändern sich → **im Rauschen**.
- **Fusion: Schwelle, Prüfband, Eskalation**: 6× Rauschen (KI enthält 0). Leitvergleich: Stichwörter enthalten sich ohne Treffer (v1): Flag-AUC 0.68 → 0.65 (-0.03 [-0.12, +0.04]); Fehlalarme 45% → 68%, verpasst 31% → 15%; 16 von 48 Entscheiden ändern sich → **im Rauschen**.
- **Policy-Tabelle v1 → v2 / v3**: 4× Rauschen (KI enthält 0). Leitvergleich: Tabelle v1 → v3 (neu aufgenommenes Audio): Flag-AUC 0.83 → 0.88 (+0.05 [+0.00, +0.18]); Fehlalarme 14% → 14%, verpasst 23% → 15%; 2 von 48 Entscheiden ändern sich → **im Rauschen**.
- **Robustheit: Dev → andere Bedingungen**: 2× Rauschen (KI enthält 0), 1× nicht gepaart. Leitvergleich: Dev-Audio → neu aufgenommen (Tempo 0.96, -3 dB): Flag-AUC 0.87 → 0.83 (-0.04 [-0.11, +0.01]); Fehlalarme 14% → 14%, verpasst 15% → 23%; 12 von 48 Entscheiden ändern sich → **im Rauschen**.
- **Weitere geprüfte Ideen**: 5× Rauschen (KI enthält 0). Leitvergleich: S3 'keine stille Entlastung' (Champion): Flag-AUC 0.87 → 0.89 (+0.02 [-0.03, +0.10]); Fehlalarme 14% → 50%, verpasst 15% → 8%; 10 von 48 Entscheiden ändern sich → **im Rauschen**.
- **Scorer: Qwen 7B → Kev-4B (gleiche Fragen)**: 2× Rauschen (KI enthält 0). Leitvergleich: Qwen 7B → Kev-4B (allgemeine, gesetzesbasierte Fragen): Flag-AUC 0.72 → 0.79 (+0.07 [-0.12, +0.22]); Fehlalarme 64% → 68%, verpasst 8% → 27%; 22 von 48 Entscheiden ändern sich → **im Rauschen**.
- **Fragen: abgestimmt → allgemein, gesetzesbasiert (gleicher Scorer)**: 2× belegter Verlust, 2× Daten fehlen. Leitvergleich: abgestimmt → allgemein (Qwen 7B): Flag-AUC 0.87 → 0.72 (-0.14 [-0.30, +0.01]); Fehlalarme 14% → 64%, verpasst 15% → 8%; 22 von 48 Entscheiden ändern sich → **belegter Verlust** (Fehlalarmquote +50 Pkt., Exakter Status -25 Pkt. belegt).
- **Kev: ASR und Transkript-Obergrenze**: 1× Daten fehlen, 1× verzerrt (nicht gezählt). Leitvergleich: Kev allgemein: large-v3 → ORACLE: Flag-AUC 0.79 → 0.89 (+0.10 [-0.04, +0.25]); Fehlalarme 68% → 45%, verpasst 27% → 8%; 24 von 48 Entscheiden ändern sich → **im Rauschen** · verzerrt: dialect reference text vs Standard German ASR.

### Confounded / caveat comparisons (what else differs)

- `llm_models/qwen25_7b` → `llm_models/qwen25_7b__facts_only` (caveat): check set: keywords 0.35 + patterns 0.2 + llm_judge + geval -> facts alone B is a re-fusion of an EARLIER run of the same llm-sweep config (stale-source warning). The facts probes are deterministic (log-probs, T=0, no facts code change between commits f012763 and 1fd19e7); v1's judge samples at T=0.7, so A itself varies run to run (see the rerun row).
- `llm_models/qwen25_7b` → `llm_models/qwen25_7b__kwpat_facts` (caveat): llm_judge + geval replaced by facts; keywords/patterns kept at the v1 weights same stale-source caveat as above
- `llm_models/qwen25_7b__facts_only` → `llm_models/qwen25_7b_facts_l3` (caveat): ASR model (turbo int8 with the default keyword prompt -> large-v3) A is a stale re-fusion of an earlier run (commit f012763 vs 1fd19e7; no facts code change in between)
- `asr_models/turbo_gsw_int8` → `asr_models/large_v3_gsw` (confounded): v1's free judge re-samples at T=0.7 in every run: judge sampling noise is mixed into the ASR effect
- `llm_models/qwen25_7b_facts_l3` → `llm_models/qwen25_7b_facts_oracle` (confounded): the reference scripts are Swiss German DIALECT text with reference speakers, the ASR view is Standard German with diarized roles: transcript quality AND language change together. ORACLE is never a submission candidate.
- `llm_models/qwen25_14b_facts_l3` → `llm_models/qwen25_14b_facts_oracle` (confounded): dialect reference text vs Standard German ASR (quality and language change together)
- `llm_models/qwen25_7b__facts_only` → `llm_models/qwen25_14b_facts` (caveat): check LLM A is a stale re-fusion of an earlier 7B run (commit f012763 vs 5d9264d)
- `llm_models/qwen25_7b__facts_only` → `llm_models/qwen3_8b__facts_only` (confounded): model family/generation changes too (Qwen3, thinking off), not only the size
- `champion/champion` → `champion14/champion14` (confounded): the 14B is the `default` LLM in recommended-14b, so it also assigns the advisor/customer roles (7B in A); facts parallel 2 vs 5
- `llm_models/qwen25_14b_facts_l3` → `llm_models/qwen25_14b_para_l3` (caveat): fact question wording separate runs (commit 1fd19e7 vs f0b67b0); facts are deterministic
- `llm_models/qwen25_7b__facts_only` → `llm_models/qwen25_7b_facts_en` (caveat): the facts check reads the LLM's English translation of the Standard German view A is a stale re-fusion of an earlier run (commit f012763 vs 1fd19e7)
- `llm_models/qwen25_7b__facts_only` → `llm_models/qwen25_7b__facts_kwlight` (caveat): keywords 0.15 + patterns 0.1 + abstain_on_empty both are re-fusions of different (stale) source runs of qwen25_7b; facts deterministic
- `champion/champion` → `champion/fs_tuned` (caveat): contrast few-shot examples in the fact probes fs_tuned merges 4 fold runs built by scripts/research/s2_fewshot.py
- `llm_models/qwen25_7b__facts_only` → `llm_models/qwen25_7b__hybrid` (caveat): fusion.type hybrid with llm_judge as second opinion both re-fusions of the same stale qwen25_7b source
- `kev_vs_facts/kev_general` → `kev_vs_facts/kev_general_oracle` (confounded): dialect reference text vs Standard German ASR

## Path: v1 → Fakten → large-v3 → leichte Stichwörter → Tabelle v3

| step | A → B | flag AUC A → B | Δ AUC | Δ FAR (pp) | Δ miss (pp) | Δ acc (pp) | verdict |
|---|---|---|---|---|---|---|---|
| Fakten statt freier Richter | `llm_models/qwen25_7b` → `llm_models/qwen25_7b__facts_only` | 0.68 → 0.84 | **+0.16 [+0.05, +0.28]** | **-68 [-92, -38]** | +12 [-6, +31] | **+35 [+12, +57]** | gain |
| large-v3 statt Turbo | `llm_models/qwen25_7b__facts_only` → `llm_models/qwen25_7b_facts_l3` | 0.84 → 0.89 | +0.05 [+0.00, +0.11] | -5 [-14, +0] | -12 [-25, +0] | +6 [-5, +20] | noise |
| + leichte Stichwörter/Muster | `champion/facts_only` → `champion/champion` | 0.89 → 0.87 | -0.02 [-0.06, +0.00] | +0 [+0, +0] | +0 [+0, +0] | +0 [+0, +0] | noise |
| Tabelle v3 | `champion/champion` → `champion/table_v3` | 0.87 → 0.92 | +0.05 [+0.00, +0.17] | +0 [+0, +0] | -8 [-25, +0] | +4 [+0, +14] | noise |

Link check `llm_models/qwen25_7b_facts_l3` = `champion/facts_only`: identical decisions and scores.

## Generalisation (same system, other conditions)

| track | condition | variant | n | flag AUC [95% CI] | FAR | miss | 3-class acc | vs first row |
|---|---|---|---|---|---|---|---|---|
| Champion (7B, Tabelle v1) | Dev, abgestimmte Fragen | `champion/champion` | 48 | 0.87 [0.72, 0.99] | 14% | 15% | 79% | base |
| Champion (7B, Tabelle v1) | Paraphrase 1 | `champion/para` | 48 | 0.72 [0.52, 0.88] | 23% | 38% | 67% | Δ AUC **-0.15 [-0.31, -0.02]**, 15 flips |
| Champion (7B, Tabelle v1) | Paraphrase 2 | `champion/para2` | 48 | 0.74 [0.54, 0.90] | 23% | 31% | 71% | Δ AUC **-0.13 [-0.29, -0.01]**, 13 flips |
| Champion (7B, Tabelle v1) | Neu aufgenommenes Audio | `perturbed/perturbed` | 48 | 0.83 [0.67, 0.96] | 14% | 23% | 73% | Δ AUC -0.04 [-0.11, +0.01], 12 flips |
| Champion (7B, Tabelle v1) | Synthetisch, out-of-sample (nur Fakten, Referenztext) | `synth_stress/facts7b_v1` | 74 | 0.80 [0.71, 0.89] | 7% | 43% | 57% | unpaired (other calls) |
| Champion (7B, Tabelle v1) | Synthetisch, Paraphrase 1 | `synth_stress/facts7b_para` | 74 | 0.70 [0.59, 0.80] | 21% | 54% | 46% | unpaired (other calls) |
| Nur Fakten (7B, large-v3) | Dev, abgestimmte Tabelle | `llm_models/qwen25_7b_facts_l3` | 48 | 0.89 [0.77, 0.99] | 14% | 15% | 79% | base |
| Nur Fakten (7B, large-v3) | Blinde Tabelle | `llm_models/qwen25_7b_facts_l3__blind_only` | 48 | 0.79 [0.63, 0.93] | 18% | 42% | 58% | Δ AUC -0.10 [-0.24, +0.00], 15 flips |
| Tabelle v3 (7B) | Dev | `champion/table_v3` | 48 | 0.92 [0.80, 1.00] | 14% | 8% | 83% | base |
| Tabelle v3 (7B) | Neu aufgenommenes Audio | `perturbed/table_v3` | 48 | 0.88 [0.76, 0.98] | 14% | 15% | 73% | Δ AUC -0.04 [-0.10, +0.00], 14 flips |
| Tabelle v3 (7B) | Synthetisch (nur Fakten, Referenztext) | `synth_stress/facts7b_v3` | 74 | 0.83 [0.74, 0.91] | 7% | 37% | 57% | unpaired (other calls) |
| 14B (large-v3, nur Fakten) | Dev, abgestimmte Tabelle | `llm_models/qwen25_14b_facts_l3` | 48 | 0.85 [0.73, 0.96] | 18% | 23% | 65% | base |
| 14B (large-v3, nur Fakten) | Paraphrase 1 | `llm_models/qwen25_14b_para_l3` | 48 | 0.88 [0.76, 0.98] | 9% | 27% | 77% | Δ AUC +0.03 [-0.04, +0.09], 9 flips |
| 14B (large-v3, nur Fakten) | Blinde Tabelle | `llm_models/qwen25_14b_facts_l3__blind_only` | 48 | 0.85 [0.72, 0.96] | 27% | 12% | 58% | Δ AUC +0.00 [-0.08, +0.07], 12 flips |
| Kev-4B (allgemeine Fragen) | Dev | `kev_vs_facts/kev_general` | 48 | 0.79 [0.62, 0.93] | 68% | 27% | 50% | base |
| Kev-4B (allgemeine Fragen) | Paraphrase | `kev_vs_facts/kev_para` | – | pending | | | | |
| Kev-4B (allgemeine Fragen) | Blinde Tabelle | `kev_vs_facts/kev_blind` | – | pending | | | | |

## Reference rows (baselines)

| system | flag AUC | flag F1 | FAR | miss | 3-class acc |
|---|---|---|---|---|---|
| champion/champion | 0.87 | 0.86 | 14% | 15% | 79% |
| flag everything (alarm) | 0.50 | 0.70 | 100% | 0% | 42% |
| flag nothing (no_alert) | 0.50 | 0.00 | 0% | 100% | 46% |
| keyword_only: checks_ablation/keywords | 0.55 | 0.47 | 32% | 62% | 50% |
| v1: llm_models/qwen25_7b | 0.68 | 0.66 | 86% | 15% | 38% |

## Metric guide

| metric | use for decisions? | why | our number |
|---|---|---|---|
| Flag-AUC | ja (Hauptmass) | Schwellenfrei: rangiert der Score markierungswürdige Anrufe über harmlose? Unabhängig von Schwelle und Prävalenz; 0.5 = Zufall. | champion/champion: 0.87 [0.72, 0.99]; nur Stichwörter: 0.55 |
| CV@FAR20 (Recall bei ≤ 20% Fehlalarmen) | ja (Betriebspunkt) | Schwelle auf den anderen Dev-Folds gewählt (out-of-fold), so dass höchstens 20% harmlose Anrufe markiert werden: so würde das System betrieben. | champion/champion: Recall 81% bei 14% Fehlalarmen |
| Fehlalarmquote und Verpasst (CV-Schwelle) | ja (immer zusammen) | Die zwei Fehlerarten, die Officer und Bank spüren: Fehlalarme kosten Zeit, Verpasste sind das Compliance-Risiko. Einzeln lässt sich jede auf 0 drücken. | champion/champion: Fehlalarme 14% [0%, 35%], verpasst 15% [0%, 36%] |
| Exakter Status (3 Klassen) | ja (Zweitmass) | Alarm / Prüfen / Kein Alarm genau richtig: zählt, ob offene Fälle als Prüfen erkannt werden. | champion/champion: 79% [63%, 95%]; immer 'Kein Alarm': 46% |
| Prüf-Recall | mit Vorsicht | Anteil der Soll-'Prüfen'-Fälle, die als Prüfen kommen. Sehr wenige Fälle: breite Intervalle. | champion/champion: 67% [0%, 100%] |
| FAR-Boden | ja (Ausschlusskriterium) | Fehlalarmquote bei Schwelle 1.0: Anrufe, die die Prüf-Regeln von sich aus markieren. Liegt er über 20%, kann keine Schwelle die Vorgabe erfüllen. | champion/champion: 14%; v1: 41% |
| Flag-F1 allein | nein | Etwa die Hälfte der Dev-Anrufe ist markierungswürdig: 'alles markieren' erreicht schon einen hohen F1 bei 100% Fehlalarmen. | alles markieren: F1 0.70 (Prävalenz 54%, Fehlalarme 100%); champion/champion: F1 0.86 |
| Holdout-Zahlen | nein (nur Plausibilität) | Sehr wenige Dialoge und mehrfach angeschaut: jede Zahl kippt mit einem Anruf. Der echte Test ist das versteckte Set am Sonntag. | 12 Anrufe / 6 Dialoge, 3 Blicke |
| Einzellauf-Unterschiede innerhalb der Intervalle | nein | Überlappen sich die 95%-Intervalle bzw. enthält das gepaarte Intervall 0, ist kein Unterschied belegt. v1 (freier Richter, T=0.7) ist zudem von Lauf zu Lauf nicht reproduzierbar. | 32 von 50 gepaarten Vergleichen sind Rauschen; v1 zweimal gerechnet: Fehlalarme 45% vs 86%, 25 von 48 Entscheiden anders |

## Per family (% exact label) and cost

| system | trade | access | disclosure | documentation | splitting | numbers | flag AUC | s/call | LLM calls/call |
|---|---|---|---|---|---|---|---|---|---|
| v1 (freier Richter, Turbo, 7B) | 29% (14) | 50% (10) | 38% (8) | 33% (6) | 100% (4) | 0% (6) | 0.68 | 82.6 | 53.4 |
| Nur Stichwörter | 57% (14) | 30% (10) | 25% (8) | 67% (6) | 50% (4) | 83% (6) | 0.55 | 0.0 | 0.0 |
| Fakten (Turbo, 7B) | 86% (14) | 70% (10) | 50% (8) | 67% (6) | 50% (4) | 100% (6) | 0.84 | 12.2 | 11.8 |
| Fakten (Turbo, 14B) | 100% (14) | 50% (10) | 62% (8) | 67% (6) | 50% (4) | 100% (6) | 0.87 | 79.1 | 46.7 |
| Champion (large-v3, 7B) | 100% (14) | 80% (10) | 62% (8) | 50% (6) | 50% (4) | 100% (6) | 0.87 | 4.1 | 1.6 |
| Champion Tabelle v3 | 100% (14) | 80% (10) | 62% (8) | 50% (6) | 100% (4) | 100% (6) | 0.92 | 4.9 | 10.0 |
| Champion Paraphrase 1 | 93% (14) | 40% (10) | 50% (8) | 67% (6) | 50% (4) | 83% (6) | 0.72 | 5.8 | 21.4 |
| Champion 14B | 79% (14) | 50% (10) | 50% (8) | 50% (6) | 50% (4) | 100% (6) | 0.82 | 4.0 | 1.3 |
| Champion Turbo (Einzel-Durchlauf) | 93% (14) | 60% (10) | 50% (8) | 67% (6) | 50% (4) | 100% (6) | 0.85 | 4.8 | 21.8 |
| ORACLE 14B (nur Experiment) | 100% (14) | 80% (10) | 100% (8) | 67% (6) | 50% (4) | 100% (6) | 0.90 | 83.1 | 46.7 |
| Kev-4B allgemein | 79% (14) | 50% (10) | 25% (8) | 33% (6) | 50% (4) | 33% (6) | 0.79 | 2.4 | 7.8 |
| Kev-4B abgestimmt | 100% (14) | 50% (10) | 75% (8) | 33% (6) | 0% (4) | 100% (6) | 0.86 | 15.7 | 20.0 |
| Qwen 7B allgemein | 57% (14) | 60% (10) | 38% (8) | 67% (6) | 50% (4) | 50% (6) | 0.72 | 3.0 | 15.0 |

## Pending / missing comparisons (light up when the data appears)

- kev_questions: `kev_vs_facts/kev_facts` → `kev_vs_facts/kev_blind` (pending: kev_vs_facts/kev_blind)
- kev_questions: `kev_vs_facts/kev_facts` → `kev_vs_facts/kev_para` (pending: kev_vs_facts/kev_para)
- kev_transcript: `kev_vs_facts/kev_general_turbo` → `kev_vs_facts/kev_general` (pending: kev_vs_facts/kev_general_turbo)
