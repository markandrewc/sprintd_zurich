# Team-Optionen: alle Kandidaten mit denselben Zahlen

Generiert 2026-10-10T13:36:17+0200 von `callguard candidates` (Spezifikation `experiments/contrib/candidates.yaml`, 2000 Bootstrap-Stichproben, Seed 13). Nicht von Hand bearbeiten: Texte in `experiments/contrib/decisions.yaml` / `comparison_zurich.yaml` ändern und neu erzeugen.

Lesehilfe: Dev-Split (48 Anrufe / 24 Dialoge), 95%-Bootstrap-KI über Zwillingsgruppen/Dialoge. AUC = Flag-AUC aus den Scores (schwellenfrei); Fehlalarme / Verpasst / Prüf-Recall / Exakt an der out-of-fold CV-Schwelle. **Fett** = bester Wert der Spalte unter den Kandidaten; „belegt“ nur, wenn das gepaarte KI gegen den Champion 0 ausschliesst, sonst „≈ Champion“. Δ = gepaarte Differenz zum eigenen abgestimmten Lauf (gleiche Anrufe). „ausstehend“ / „läuft noch“ füllt sich beim nächsten Lauf von `callguard candidates` automatisch. Der Holdout ist verbraucht und kommt hier nicht vor.

## Kandidaten-Matrix

| Kandidat | Flag-AUC [KI] | Fehlalarme (CV) | Verpasst (CV) | Prüf-Recall | Exakt 3 Klassen | gepaart vs. Champion | AUC umformuliert | Δ umf. | AUC blinde Tabelle | Δ blind | AUC neu aufgenommen | Δ neu aufg. | Beleg hit@1 | Passagen | s/Anruf | Hardware | Lizenz | E2E getestet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Champion: Qwen2.5-7B Fakten, Tabelle v1 | 0.87 [0.72, 0.99] | 14% [0, 35] | 15% [0, 36] | 67% [0, 100] | 79% [63, 95] | Referenz | 0.73 [0.53, 0.89] (Ø 2) | -0.14 [-0.30, -0.02] belegt | 0.73 [0.53, 0.90] | -0.14 [-0.32, -0.01] belegt | 0.83 [0.67, 0.96] | -0.04 [-0.11, +0.01] ≈ | 73% [45, 91], Zufall 24% | ja | 4.1 | 12 GB 4070 gestaffelt (ASR, dann vLLM); 24 GB: alles zusammen | LLM Apache-2.0, ASR MIT | ja (gestaffelt, neue Dateien, Journal 04:50) |
| Champion mit Tabelle v3 | 0.92 [0.80, 1.00] | 14% [0, 35] | **8% [0, 25]** (≈ Champion) | **100% [100, 100]** (≈ Champion) | **83% [68, 100]** (≈ Champion) | ≈ Champion | n/a | n/a | n/a | n/a | **0.88 [0.76, 0.98]** (≈ Champion) | -0.037 [-0.102, +0.002] ≈ | – | ja | 4.9 | wie Champion | LLM Apache-2.0, ASR MIT | teilweise (gleiche Kette, Profil recommended-v3; auf neuen Dateien nicht separat gelaufen) |
| Kev-4B Fakten, Tabelle v1 | 0.86 [0.67, 0.98] | **0% [0, 0]** (≈ Champion) | 31% [9, 56] | 0% [0, 0] | 69% [48, 86] | ▲ AUC umformuliert +0.17 [+0.04, +0.31] | **0.90 [0.73, 1.00] (Ø 2)** belegt | +0.04 [-0.01, +0.11] ≈ | **0.85 [0.68, 1.00]** (≈ Champion) | -0.00 [-0.09, +0.11] ≈ | 0.81 [0.60, 0.96] | -0.05 [-0.15, +0.01] ≈ | 43% [12, 75], Zufall 17%, 8/14 ohne Passage | nein (nur Stichwort-/Muster-Treffer) | 15.7 | 12 GB gestaffelt: ASR, vLLM 7B für Rollen, dann Kev (~8 GB); 24 GB zusammen | Kev Apache-2.0 (LoRA auf Qwen3.5-4B), ASR MIT | nein (nur Experimente auf gecachten Transkripten + Rollen) |
| Kev-4B Fakten, Tabelle v3 | 0.83 [0.65, 0.96] | 5% [0, 15] | 31% [9, 56] | 0% [0, 0] | 67% [47, 83] | ≈ Champion | n/a | n/a | n/a | n/a | 0.79 [0.58, 0.95] | -0.04 [-0.15, +0.03] ≈ | 47% [13, 80], Zufall 18%, 8/15 ohne Passage | nein (nur Stichwort-/Muster-Treffer) | 6.3 | wie Kev v1 | Kev Apache-2.0, ASR MIT | nein |
| Qwen3.8-27B 3-bit Fakten, Tabelle v1 | 0.85 [0.64, 1.00] | **0% [0, 0]** (≈ Champion) | 31% [8, 58] | 0% [0, 0] | 77% [60, 92] | ≈ Champion | 0.87 [0.66, 1.00] | +0.017 [+0.000, +0.069] ≈ | 0.83 [0.63, 0.97] | -0.02 [-0.14, +0.06] ≈ | n/a | n/a | 50% [22, 78], Zufall 18%, 8/18 ohne Passage | nein (evidence aus; nur Stichwort-/Muster-Treffer) | 26.3 | 12 GB 4070 allein (10.9 GB GGUF); ASR + Rollen (vLLM 7B) vorher in eigenen Stufen | Qwen3.8: Lizenz nicht geprüft (Modellkarte), ASR MIT | nein (Experimente; Rollen aus dem Cache) |
| Qwen3.8-27B 3-bit Fakten, Tabelle v3 | 0.85 [0.64, 1.00] | **0% [0, 0]** (≈ Champion) | 31% [8, 58] | 0% [0, 0] | 77% [60, 92] | ≈ Champion | n/a | n/a | n/a | n/a | n/a | n/a | 50% [22, 78], Zufall 18%, 8/18 ohne Passage | nein (nur Stichwort-/Muster-Treffer) | 11.9 | wie Q3.8 3-bit | Qwen3.8: nicht geprüft, ASR MIT | nein |
| Qwen3.8-27B 6-bit Fakten, Tabelle v1 | 0.85 [0.65, 1.00] | **0% [0, 0]** (≈ Champion) | 27% [7, 50] | 0% [0, 0] | 79% [62, 93] | ≈ Champion | 0.86 [0.66, 1.00] | +0.012 [+0.000, +0.044] ≈ | läuft noch | läuft noch | ausstehend | ausstehend | 47% [19, 75], Zufall 18%, 9/19 ohne Passage | nein (evidence aus; nur Stichwort-/Muster-Treffer) | 135.6 | 24 GB A5000 (22 GB GGUF füllt die Karte); ASR + Rollen in eigenen Stufen | Qwen3.8: nicht geprüft, ASR MIT | nein (Experimente auf dem A5000; Rollen aus dem Cache) |
| Qwen3.8-27B 6-bit Fakten, Tabelle v3 | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | n/a | n/a | n/a | n/a | ausstehend | ausstehend | – | nein (nur Stichwort-/Muster-Treffer) | ausstehend | wie Q3.8 6-bit | Qwen3.8: nicht geprüft, ASR MIT | nein |
| Allgemeine Fragen auf Qwen2.5-7B | 0.72 [0.55, 0.88] | 64% [38, 88] | **8% [0, 25]** (≈ Champion) | 33% [0, 100] | 54% [39, 71] | ▼ Fehlalarme (CV) +50 Pkt. [+17, +80]; ▼ Exakt 3 Klassen -25 Pkt. [-45, -7] | 0.71 [0.50, 0.89] | -0.01 [-0.15, +0.09] ≈ | n/a | n/a | 0.76 [0.58, 0.91] | +0.04 [-0.05, +0.11] ≈ | 57% [23, 88], Zufall 18%, 5/14 ohne Passage | nein (nur Stichwort-/Muster-Treffer) | 3.0 | wie Champion | LLM Apache-2.0, ASR MIT | nein |
| Allgemeine Fragen auf Kev-4B (Teamkollege) | 0.79 [0.62, 0.93] | 68% [44, 89] | 27% [7, 50] | 17% [0, 50] | 50% [35, 64] | ▼ Fehlalarme (CV) +55 Pkt. [+30, +75]; ▼ Exakt 3 Klassen -29 Pkt. [-50, -10]; ▲ AUC umformuliert +0.157 [+0.003, +0.387] | 0.88 [0.74, 1.00] | +0.09 [-0.03, +0.28] ≈ | n/a | n/a | 0.76 [0.56, 0.92] | -0.03 [-0.12, +0.05] ≈ | **87% [60, 100], Zufall 55%** (ungepaart, Zufall beachten) | ja (Fenster ~40 Wörter, lang) | **2.4** | wie Kev v1 | Kev Apache-2.0, ASR MIT | nein bei uns (im Prototyp des Teamkollegen ja, andere ASR) |
| Allgemeine Fragen auf Qwen3.8 3-bit | 0.83 [0.65, 0.96] | 32% [6, 64] | 27% [6, 50] | 0% [0, 0] | 62% [43, 80] | ▼ Exakt 3 Klassen -17 Pkt. [-37, -2] | 0.83 [0.67, 0.96] | +0.00 [-0.12, +0.11] ≈ | n/a | n/a | n/a | n/a | 50% [22, 78], Zufall 18%, 8/18 ohne Passage | nein (nur Stichwort-/Muster-Treffer) | 20.4 | wie Q3.8 3-bit | Qwen3.8: nicht geprüft, ASR MIT | nein |
| Allgemeine Fragen auf Qwen3.8 6-bit | 0.86 [0.69, 0.99] | 32% [10, 58] | 15% [0, 33] | 17% [0, 50] | 71% [55, 85] | ≈ Champion | ausstehend | ausstehend | n/a | n/a | ausstehend | ausstehend | 47% [18, 79], Zufall 18%, 9/19 ohne Passage | nein (nur Stichwort-/Muster-Treffer) | 102.6 | wie Q3.8 6-bit | Qwen3.8: nicht geprüft, ASR MIT | nein |
| Zwei Leser R1 (Qwen 7B + Kev, Label-Einigkeit) | **0.93 [0.82, 1.00]** (≈ Champion) | 14% [0, 35] | 12% [0, 29] | 50% [0, 100] | 65% [45, 83] | ▼ Exakt 3 Klassen -15 Pkt. [-32, -2]; ▲ AUC umformuliert +0.13 [+0.04, +0.23]; ▲ AUC blinde Tabelle +0.12 [+0.03, +0.25] | 0.86 [0.69, 0.98] (Ø 2) | -0.071 [-0.194, +0.000] ≈ | 0.84 [0.71, 0.96] | -0.08 [-0.21, +0.03] ≈ | 0.86 [0.72, 0.98] | -0.069 [-0.165, -0.004] belegt | 70% [45, 91], Zufall 24%, 1/23 ohne Passage | ja (aus Qwen) | 19.7 | 24 GB zusammen (nie getestet) oder 12 GB gestaffelt + `agreement merge` | Apache-2.0 (beide), ASR MIT | nein (nur Re-Fusion gespeicherter Läufe) |
| v1 (Stichwörter + freier LLM-Richter, Turbo-ASR) | 0.68 [0.53, 0.84] | 86% [64, 100] | 15% [0, 35] | 83% [50, 100] | 38% [23, 55] | ▼ Flag-AUC -0.19 [-0.33, -0.05]; ▼ Fehlalarme (CV) +73 Pkt. [+46, +94]; ▼ Exakt 3 Klassen -42 Pkt. [-65, -18] | n/a | n/a | n/a | n/a | n/a | n/a | – | ja | 82.6 | 12 GB | Apache-2.0 / ASR CC-BY-NC-Herkunft (Turbo) | ja (Ausgangssystem) |
| Nur Stichwörter | 0.55 [0.38, 0.73] | 32% [7, 61] | 62% [33, 87] | 0% [0, 0] | 50% [35, 65] | ▼ Flag-AUC -0.32 [-0.51, -0.15]; ▼ Verpasst (CV) +46 Pkt. [+19, +73]; ▼ Exakt 3 Klassen -29 Pkt. [-50, -11] | n/a | n/a | n/a | n/a | n/a | n/a | – | ja | 0.0 | CPU (+ ASR) | – | ja |
| Alles markieren (Alarm) | 0.50 [0.50, 0.50] | 100% [100, 100] | 0% [0, 0] | 0% [0, 0] | 42% [25, 58] | Untergrenze | n/a | n/a | n/a | n/a | n/a | n/a | – | – | 0.0 | – | – | – |

Prüfen-Fälle (CV, vorhergesagt, davon richtig; Soll 6 von 48): Champion v1 10 (4 richtig); Champion v3 12 (6 richtig); Kev v1 6 (0 richtig); Kev v3 6 (0 richtig); Q3.8 3-bit v1 1 (0 richtig); Q3.8 3-bit v3 1 (0 richtig); Q3.8 6-bit v1 1 (0 richtig); Allg. Qwen 7B 7 (2 richtig); Allg. Kev 11 (1 richtig); Allg. Q3.8 3-bit 4 (0 richtig); Allg. Q3.8 6-bit 6 (1 richtig); Zwei Leser R1 16 (3 richtig); v1 20 (5 richtig); Stichwörter 1 (0 richtig); Alles markieren 0 (0 richtig).

Beleg hit@1 = Anteil der richtig markierten Anrufe, deren erste angezeigte Passage eine annotierte Beleg-Zeile trifft (`callguard evidence-eval`-Methode, Dev). „Zufall“ = was eine gleich lange Passage an zufälliger Stelle träfe: lange Passagen (Kev allgemein, ~48 s) treffen schon zufällig oft. Anrufe ohne Passage zählen als Fehltreffer.

## test50 (extern, FHNW-TTS, 8 Dialekte)

> **Externer Testsatz: nie zum Tunen verwendet; Zahlen nicht mit Dev vergleichbar gepoolt. Eigener Datensatz (100 Anrufe, 50 Dialoge sauber/verrauscht, 8 Dialekt-Stimmen), eigene Ergebnisse (runs/test50), vorregistriert (research/findings/test50_prereg.md).**

Eigene Spaltengruppe, eigene Anrufe: fixe Schwelle = die auf Dev eingefrorene Konfiguration jeder Variante; CV in test50 = Schwelle out-of-fold innerhalb von test50 (Zwillingsgruppen zusammen), nur zum Vergleich. Gepaart gegen den Champion auf denselben test50-Anrufen (KI über A/B-Paare). „Dev → test50“ ist eine ungepaarte Differenz zweier getrennt gebooteter AUCs (verschiedene Anrufe), kein gepoolter Wert.

| Kandidat | Flag-AUC [KI] | Fehlalarme (fix) | Verpasst (fix) | Exakt 3 Klassen (fix) | Prüf-Recall (fix) | CV in test50: Fehlalarme / Verpasst / Exakt | gepaart vs. Champion (test50) | Dev → test50 AUC (ungepaart) |
|---|---|---|---|---|---|---|---|---|
| Champion: Qwen2.5-7B Fakten, Tabelle v1 | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend |
| Champion mit Tabelle v3 | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend |
| Kev-4B Fakten, Tabelle v1 | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend |
| Kev-4B Fakten, Tabelle v3 | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant |
| Qwen3.8-27B 3-bit Fakten, Tabelle v1 | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant |
| Qwen3.8-27B 3-bit Fakten, Tabelle v3 | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant |
| Qwen3.8-27B 6-bit Fakten, Tabelle v1 | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend |
| Qwen3.8-27B 6-bit Fakten, Tabelle v3 | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant |
| Allgemeine Fragen auf Qwen2.5-7B | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend |
| Allgemeine Fragen auf Kev-4B (Teamkollege) | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend |
| Allgemeine Fragen auf Qwen3.8 3-bit | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant |
| Allgemeine Fragen auf Qwen3.8 6-bit | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend |
| Zwei Leser R1 (Qwen 7B + Kev, Label-Einigkeit) | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant |
| v1 (Stichwörter + freier LLM-Richter, Turbo-ASR) | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant |
| Nur Stichwörter | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant | nicht geplant |
| Alles markieren (Alarm) | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend | ausstehend |

### Anmerkungen je Kandidat

- **Champion: Qwen2.5-7B Fakten, Tabelle v1**: Eingefroren, einziger Kandidat mit Holdout-Lauf (3 Blicke, nur Plausibilität).
- **Champion mit Tabelle v3**: v3 wurde in Kenntnis eines Holdout-Fehlers (Aufteilen) entworfen; kein Holdout-Lauf.
- **Kev-4B Fakten, Tabelle v1**: Kev kennt kein „unklar“: offene Fakten werden ja/nein, die Prüfen-Regeln der Tabelle feuern kaum.
- **Qwen3.8-27B 3-bit Fakten, Tabelle v1**: Nur eine Paraphrase gerechnet (para2 nicht geplant).
- **Qwen3.8-27B 6-bit Fakten, Tabelle v1**: Kosten auf dem A5000 gemessen (llama.cpp, 4 Slots): ~135 s Prüfzeit pro Anruf.
- **Zwei Leser R1 (Qwen 7B + Kev, Label-Einigkeit)**: Vorregistriert, nicht bestanden: 3-Klassen-Genauigkeit belegt schlechter, Prüf-Recall 3/6.
- **v1 (Stichwörter + freier LLM-Richter, Turbo-ASR)**: Freier Richter mit T=0.7: von Lauf zu Lauf nicht reproduzierbar.
- **Nur Stichwörter**: Turbo-Transkripte (gpu-12gb), gleiche Anrufe.

### Zuordnung zu gespeicherten Varianten

| Kandidat | abgestimmt | umformuliert | blinde Tabelle | neu aufgenommen | test50 (extern) |
|---|---|---|---|---|---|
| Champion: Qwen2.5-7B Fakten, Tabelle v1 | `champion/champion` (da) | `kev_vs_facts/qwen_facts_para` (da), `kev_vs_facts/qwen_facts_para2` (da) | `kev_vs_facts/qwen_facts_blind` (da) | `perturbed:perturbed/perturbed` (da) | `test50:test50/champion` (ausstehend) |
| Champion mit Tabelle v3 | `champion/table_v3` (da) | n/a | n/a | `perturbed:perturbed/table_v3` (da) | `test50:test50/champion_v3` (ausstehend) |
| Kev-4B Fakten, Tabelle v1 | `kev_vs_facts/kev_facts` (da) | `kev_vs_facts/kev_facts_para` (da), `kev_vs_facts/kev_facts_para2` (da) | `kev_vs_facts/kev_facts_blind` (da) | `perturbed:kev_perturbed/kev_facts` (da) | `test50:test50/kev_facts` (ausstehend) |
| Kev-4B Fakten, Tabelle v3 | `kev_vs_facts/kev_facts_v3` (da) | n/a | n/a | `perturbed:kev_perturbed/kev_facts_v3` (da) | nicht geplant |
| Qwen3.8-27B 3-bit Fakten, Tabelle v1 | `qwen38/q38_facts` (da) | `qwen38/q38_facts_para` (da) | `qwen38/q38_facts_blind` (da) | n/a | nicht geplant |
| Qwen3.8-27B 3-bit Fakten, Tabelle v3 | `qwen38/q38_facts_v3` (da) | n/a | n/a | n/a | nicht geplant |
| Qwen3.8-27B 6-bit Fakten, Tabelle v1 | `qwen38_q6/q38q6_facts` (da) | `qwen38_q6/q38q6_facts_para` (da) | `qwen38_q6/q38q6_facts_blind` (läuft noch) | `perturbed:qwen38_q6_perturbed/q38q6_facts` (ausstehend) | `test50:test50/q38q6_facts` (ausstehend) |
| Qwen3.8-27B 6-bit Fakten, Tabelle v3 | `qwen38_q6/q38q6_facts_v3` (ausstehend) | n/a | n/a | `perturbed:qwen38_q6_perturbed/q38q6_facts_v3` (ausstehend) | nicht geplant |
| Allgemeine Fragen auf Qwen2.5-7B | `kev_vs_facts/qwen_general` (da) | `kev_vs_facts/qwen_general_para` (da) | n/a | `perturbed:kev_perturbed/qwen_general` (da) | `test50:test50/qwen_general` (ausstehend) |
| Allgemeine Fragen auf Kev-4B (Teamkollege) | `kev_vs_facts/kev_general` (da) | `kev_vs_facts/kev_general_para` (da) | n/a | `perturbed:kev_perturbed/kev_general` (da) | `test50:test50/kev_general` (ausstehend) |
| Allgemeine Fragen auf Qwen3.8 3-bit | `qwen38/q38_general` (da) | `qwen38/q38_general_para` (da) | n/a | n/a | nicht geplant |
| Allgemeine Fragen auf Qwen3.8 6-bit | `qwen38_q6/q38q6_general` (da) | `qwen38_q6/q38q6_general_para` (ausstehend) | n/a | `perturbed:qwen38_q6_perturbed/q38q6_general` (ausstehend) | `test50:test50/q38q6_general` (ausstehend) |
| Zwei Leser R1 (Qwen 7B + Kev, Label-Einigkeit) | `two_readers/r1` (da) | `two_readers/r1_para` (da), `two_readers/r1_para2` (da) | `two_readers/r1_blind` (da) | `perturbed:two_readers_perturbed/r1` (da) | nicht geplant |
| v1 (Stichwörter + freier LLM-Richter, Turbo-ASR) | `llm_models/qwen25_7b` (da) | n/a | n/a | n/a | nicht geplant |
| Nur Stichwörter | `checks_ablation/keywords` (da) | n/a | n/a | n/a | nicht geplant |
| Alles markieren (Alarm) | `trivial/flag_all` (da) | n/a | n/a | n/a | `test50:test50/champion` (ausstehend) |

### Ausstehend / läuft noch

- Champion: Qwen2.5-7B Fakten, Tabelle v1: test50 (extern) `test50:test50/champion` (ausstehend)
- Champion mit Tabelle v3: test50 (extern) `test50:test50/champion_v3` (ausstehend)
- Kev-4B Fakten, Tabelle v1: test50 (extern) `test50:test50/kev_facts` (ausstehend)
- Qwen3.8-27B 6-bit Fakten, Tabelle v1: blinde Tabelle `qwen38_q6/q38q6_facts_blind` (läuft noch)
- Qwen3.8-27B 6-bit Fakten, Tabelle v1: neu aufgenommen `perturbed:qwen38_q6_perturbed/q38q6_facts` (ausstehend)
- Qwen3.8-27B 6-bit Fakten, Tabelle v1: test50 (extern) `test50:test50/q38q6_facts` (ausstehend)
- Qwen3.8-27B 6-bit Fakten, Tabelle v3: abgestimmt (Dev) `qwen38_q6/q38q6_facts_v3` (ausstehend)
- Qwen3.8-27B 6-bit Fakten, Tabelle v3: neu aufgenommen `perturbed:qwen38_q6_perturbed/q38q6_facts_v3` (ausstehend)
- Allgemeine Fragen auf Qwen2.5-7B: test50 (extern) `test50:test50/qwen_general` (ausstehend)
- Allgemeine Fragen auf Kev-4B (Teamkollege): test50 (extern) `test50:test50/kev_general` (ausstehend)
- Allgemeine Fragen auf Qwen3.8 6-bit: umformuliert `qwen38_q6/q38q6_general_para` (ausstehend)
- Allgemeine Fragen auf Qwen3.8 6-bit: neu aufgenommen `perturbed:qwen38_q6_perturbed/q38q6_general` (ausstehend)
- Allgemeine Fragen auf Qwen3.8 6-bit: test50 (extern) `test50:test50/q38q6_general` (ausstehend)
- Alles markieren (Alarm): test50 (extern) `test50:test50/champion` (ausstehend)

## Offene Team-Entscheidungen

Alle Zahlen: Dev-Split (48 Anrufe, 24 Dialoge), 95%-KI. Bei 48 Anrufen sind Unterschiede von 1-2 Anrufen Rauschen; „belegt“ heisst: das gepaarte Intervall gegen den Champion schliesst 0 aus. Der Holdout ist verbraucht.

### 1. Policy-Tabelle für Sonntag: v1 oder v3?

**Frage:** Welche Regel-Tabelle entscheidet aus den Fakten Alarm / Prüfen / Kein Alarm?

v3 ergänzt v1 um aus den Kriterien abgeleitete Regeln „entscheidender Fakt offen → Prüfen“ und Nachfragen beim Aufteilen (research/DECISIONS.md D2b). Umschalten = Profil `recommended-v3`, kein Code.

- **Option v1 (eingefroren)**: Flag-AUC 0.87 [0.72, 0.99], Fehlalarme 14% [0, 35], verpasst 15% [0, 36], Prüf-Recall 67% [0, 100].
  - pro: Einzige Tabelle mit Holdout-Lauf (12 Anrufe, 0 Fehlalarme, Alarm-F1 0.67; 3 Blicke, nur Plausibilität).
  - pro: Weniger LLM-Aufrufe: 4.1 s Prüfzeit pro Anruf.
  - contra: Verpasst mehr: 15% [0, 36] gegen 8% [0, 25] (v3).
  - contra: Neu aufgenommenes Audio: AUC 0.83 [0.67, 0.96] gegen 0.88 [0.76, 0.98] (v3).
  - Aufwand: keiner (Stand heute)
- **Option v3**: Flag-AUC 0.92 [0.80, 1.00], Fehlalarme 14% [0, 35], verpasst 8% [0, 25], Prüf-Recall 100% [100, 100].
  - pro: Drei unabhängige Dev-Tests zeigen in dieselbe Richtung: Dev verpasst -8 Pkt. [-25, +0] ≈, neu aufgenommen AUC +0.054 [+0.000, +0.177] ≈, synthetisch Prüf-Recall 38% → 48% (D2b).
  - pro: Fehlalarme unverändert (+0 Pkt. [+0, +0] ≈).
  - pro: Mehr „Prüfen“ statt stillem „Kein Alarm“, passt zur Antwort der Organisatoren (Konfigurierbarkeit).
  - contra: Jede einzelne Differenz liegt im Rauschen (gepaart: AUC +0.052 [+0.000, +0.172] ≈, exakt +4 Pkt. [+0, +14] ≈).
  - contra: In Kenntnis eines Holdout-Fehlers (Aufteilen) entworfen; kein Holdout-Lauf möglich.
  - contra: Keine Paraphrasen-Probe für v3; mehr LLM-Aufrufe (4.9 s pro Anruf).
  - contra: Auf Kev / Qwen3.8: Kev v3 0.83 [0.65, 0.96], Q3.8 3-bit v3 0.85 [0.64, 1.00], Q3.8 6-bit v3 ausstehend.
  - Aufwand: `-c recommended-v3` bzw. `scripts/run_staged.sh recommended-v3`; 5 min Doctor + Smoke-Test.

**Unsere Empfehlung:** v3 übernehmen (Stand D2b): weniger Verpasste bei gleichen Fehlalarmen in drei unabhängigen Tests; ehrlich kommunizieren, dass keine Einzeldifferenz belegt ist.

**Was die Empfehlung ändern würde:**
- v3 erhöht auf Kev oder Qwen3.8 die Fehlalarme deutlich (Zeilen Kev v3 / Q3.8 v3, sobald gerechnet).
- Die Organisatoren werten „Prüfen“ als Fehler (dann zählt exakte 3-Klassen-Genauigkeit, nicht Verpasste).
- Ein Smoke-Test von recommended-v3 auf neuen Dateien schlägt fehl.
- Der externe Testsatz test50 (eigener Datensatz, nie gepoolt) zeigt v3 belegt schlechter: Champion v1 AUC ausstehend, v3 ausstehend, gepaart ausstehend; verpasst ausstehend gegen ausstehend.

Quellen: `research/DECISIONS.md`, `research/findings/RQ10.md`, `config/recommended-v3.yaml`

**Entscheid des Teams:** offen

### 2. Standard-Entscheider für das versteckte Set und die Demo

**Frage:** Welches Modell liest die Fakten im Standardprofil? (Champion 7B / Qwen3.8 6-bit / Kev / zwei Leser)

Antwort der Organisatoren (Sa ~13:00, docs/CASE.md): exakte Werte zählen weniger als dass das Verhalten konfigurierbar ist. Alle Kandidaten unten sind Profile derselben Pipeline; der Standard sollte der sein, der auf neuen Dateien sicher durchläuft, die anderen bleiben umschaltbar.

- **Option Champion Qwen2.5-7B**: AUC 0.87 [0.72, 0.99], exakt 79% [63, 95], Beleg hit@1 73% [45, 91], Zufall 24%.
  - pro: Einziger Kandidat, der auf neuen Dateien end-to-end getestet ist (gestaffelt, ~30 s pro Anruf).
  - pro: Liefert Passagen mit Begründung; Prüf-Recall 67% [0, 100].
  - contra: Hängt an der Formulierung: umformuliert 0.73 [0.53, 0.89] (Ø 2) (-0.14 [-0.30, -0.02] belegt), blinde Tabelle 0.73 [0.53, 0.90].
  - Aufwand: keiner
- **Option Qwen3.8-27B 6-bit**: AUC 0.85 [0.65, 1.00] (gepaart -0.01 [-0.20, +0.12] ≈), Fehlalarme 0% [0, 0], verpasst 27% [7, 50], exakt 79% [62, 93].
  - pro: Allgemeine Fragen ohne Regelschicht: nur auf 6-bit ist kein Mass belegt schlechter als der Champion (Fehlalarme 32% [10, 58], gepaart +18 Pkt. [-14, +47] ≈; exakt -8 Pkt. [-28, +6] ≈).
  - pro: Die 3-bit-Variante ist formulierungsrobust (umformuliert 0.87 [0.66, 1.00], +0.017 [+0.000, +0.069] ≈); 6-bit: 0.86 [0.66, 1.00].
  - contra: Braucht den 24 GB A5000 (Verfügbarkeit Sonntag offen); ~135.6 s Prüfzeit pro Anruf.
  - contra: Keine Prüfen-Fälle (Prüf-Recall 0% [0, 0]), keine Fakten-Passagen (evidence aus).
  - contra: Nie end-to-end auf neuen Dateien gelaufen.
  - Aufwand: llama-server + Profil qwen38-q6 auf dem A5000; Rollen brauchen vorher vLLM 7B.
- **Option Kev-4B Fakten**: AUC 0.86 [0.67, 0.98], Fehlalarme 0% [0, 0], verpasst 31% [9, 56], exakt 69% [48, 86].
  - pro: Formulierungsrobust: umformuliert 0.90 [0.73, 1.00] (Ø 2), gepaart gegen Champion +0.17 [+0.04, +0.31] belegt.
  - pro: Klein (~8 GB), läuft auf dem 4070 (gestaffelt).
  - contra: Kein „unklar“: 6× Prüfen vorhergesagt, 0 von 6 Soll-Prüfen getroffen; verpasst 31% [9, 56].
  - contra: Keine Fakten-Passagen: Beleg hit@1 43% [12, 75], Zufall 17%, 8/14 ohne Passage.
  - contra: Drei Stufen auf 12 GB (ASR, vLLM für Rollen, Kev); nie end-to-end getestet.
  - Aufwand: serve_kev.py + Profil kev; Runbook docs/KEV.md.
- **Option Zwei Leser R1**: AUC 0.93 [0.82, 1.00] (gepaart +0.060 [-0.002, +0.160] ≈), exakt 65% [45, 83] (gepaart -15 Pkt. [-32, -2] belegt).
  - pro: Bester Rang (AUC) und robuster bei Umformulierung: 0.86 [0.69, 0.98] (Ø 2) (gepaart +0.13 [+0.04, +0.23] belegt).
  - pro: „Uneinig → Prüfen“ ist eine einleuchtende Officer-Einstellung.
  - contra: Vorregistriert nicht bestanden: exakte 3-Klassen-Genauigkeit belegt schlechter, Prüf-Recall 50% [0, 100].
  - contra: Live nur auf 24 GB (nie getestet), sonst gestaffelt + Zusammenführen.
  - Aufwand: Profil two-readers; auf dem 4070 nur gestaffelt.

**Unsere Empfehlung:** Champion 7B als Standard für das versteckte Set (einziger end-to-end getesteter Weg, liefert Passagen). In der Demo die anderen als umschaltbare Profile mit ihren gemessenen Zahlen zeigen (Konfigurierbarkeit ist laut Organisatoren wichtiger als der exakte Wert).

**Was die Empfehlung ändern würde:**
- Qwen3.8 6-bit schlägt den Champion auf umformulierten Fragen oder neu aufgenommenem Audio belegt (Zellen oben, sobald gerechnet) UND der A5000 ist Sonntag sicher verfügbar.
- Die Organisatoren bewerten nur Alarm ja/nein (dann zählen Fehlalarme/Verpasste mehr als Prüfen).
- test50 (extern, 8 Dialekt-Stimmen, eigener Datensatz): ein Kandidat schlägt den Champion dort belegt (gepaart über A/B-Paare): Kev ausstehend, Qwen3.8 6-bit ausstehend; Champion ausstehend, Dev → test50 ausstehend.

Quellen: `docs/CASE.md`, `research/findings/two_readers.md`, `experiments/kev_vs_facts.yaml`, `experiments/qwen38_q6.yaml`

**Entscheid des Teams:** offen

### 3. Demo-Hardware: A5000 (24 GB) oder deben 4070 (12 GB)?

**Frage:** Auf welcher Maschine läuft die Live-Demo am Sonntag?

- **Option A5000 24 GB VM**: Alle Modelle gleichzeitig; Verfügbarkeit Sonntag unbestätigt.
  - pro: Live: Champion, Kev, zwei Leser (Qwen 7B + Kev + large-v3 zusammen), Qwen3.8 6-bit (allein).
  - pro: Kein Umschalten zwischen ASR und LLM nötig.
  - contra: Zwei-Leser-Profil auf 24 GB nie getestet; Qwen3.8 6-bit füllt die Karte allein (~135.6 s pro Anruf).
  - contra: Verfügbarkeit Sonntag offen.
  - Aufwand: Setup + Doctor auf der VM (~30 min), wenn verfügbar.
- **Option deben RTX 4070 12 GB**: Bewährt; Modelle gestaffelt.
  - pro: Champion end-to-end getestet (`scripts/run_staged.sh recommended`, ~30 s pro Anruf; Fallback `recommended-turbo` in einem Durchgang).
  - pro: Qwen3.8 3-bit läuft allein; Kev läuft allein.
  - contra: Kev und Qwen nicht gleichzeitig: zwei Leser nur gestaffelt; Qwen3.8 6-bit gar nicht.
  - Aufwand: keiner
- **Option Laptop ohne GPU (nur gespeicherte Ergebnisse)**: UI mit gespeicherten Ergebnissen, Schwelle/Prüfband/Stichwörter live (Re-Fusion ohne Modell).
  - pro: Kein Ausfallrisiko
  - contra: Keine neuen Anrufe live
  - Aufwand: keiner

**Unsere Empfehlung:** Demo-Basis: gespeicherte Ergebnisse (Laptop/4070, kein Risiko) plus ein neuer Anruf live auf dem 4070 mit dem Champion. A5000 nur als Bonus (zwei Leser / Qwen3.8 live), wenn er Sonntag früh bestätigt ist.

**Was die Empfehlung ändern würde:**
- A5000 Sonntag bestätigt und ein Smoke-Test von two-readers dort grün.

Quellen: `docs/KEV.md`, `config/two-readers.yaml`, `config/qwen38-q6.yaml`, `docs/SUNDAY_RUNBOOK.md`

**Entscheid des Teams:** offen

### 4. GitHub: Integrations-Branch wohin pushen?

**Frage:** Wie kommt der heutige Stand (Integrations-Branch) zum Team und in die Abgabe?

- **Option als eigener Branch + PR auf main**
  - pro: Team kann reviewen; main bleibt bis zum Merge unverändert
  - pro: PR zeigt alle Änderungen auf einen Blick
  - contra: Ein Merge-Schritt mehr vor der Abgabe
  - Aufwand: push + PR (~5 min), Review durch das Team
- **Option nach overnight**
  - pro: Passt zur Regel „Forschungsergebnisse → overnight“ (CLAUDE.md)
  - contra: Code (UI, Plugins), den das Team braucht, liegt dann nicht auf main
  - Aufwand: push
- **Option direkt auf main**
  - pro: Sofort für alle und für die Abgabe verfügbar
  - contra: Kein Review; main muss bis Sonntag 08:30 grün bleiben
  - Aufwand: push (Tests vorher grün)

**Unsere Empfehlung:** Eigener Branch + PR auf main, nach grüner Offline-Testsuite; Merge nach kurzem Team-Review, spätestens Samstagabend (main = Abgabe).

**Was die Empfehlung ändern würde:**
- Teammitglieder brauchen den Code sofort auf dem GPU-Rechner → direkt main (Tests grün).

Quellen: `CLAUDE.md`

**Entscheid des Teams:** offen

### 5. Abstimmung mit dem Teamkollegen (Kev / allgemeine Fragen)

**Frage:** Wie führen wir unsere Pipeline und den Prototyp sprintd_zurich zusammen?

Messungen auf unseren Transkripten: Kev ist formulierungsrobust (umformuliert 0.90 [0.73, 1.00] (Ø 2) gegen Champion 0.73 [0.53, 0.89] (Ø 2), gepaart +0.17 [+0.04, +0.31] belegt), kennt aber kein „unklar“ (6× Prüfen vorhergesagt, 0 von 6 Soll-Prüfen getroffen) und liefert mit den Fakten keine Passagen. Die allgemeinen Fragen markieren ohne Regelschicht zu viel: Fehlalarme Kev 68% [44, 89] (gepaart +55 Pkt. [+30, +75] belegt), Qwen 7B 64% [38, 88] (+50 Pkt. [+17, +80] belegt); Qwen3.8 3-bit 32% [6, 64] (+18 Pkt. [-15, +55] ≈, exakt -17 Pkt. [-37, -2] belegt). Ausnahme Qwen3.8 6-bit: Fehlalarme 32% [10, 58] (+18 Pkt. [-14, +47] ≈), exakt -8 Pkt. [-28, +6] ≈, also nichts belegt schlechter als der Champion.

- **Option kombinieren**: Unsere Pipeline als Standard, Kev als umschaltbarer Leser, ihre Stärken übernehmen.
  - pro: Ein Produkt; Kev-Robustheit als Option sichtbar
  - pro: Übernehmen: Rechtsgrundlage je Prüfpunkt, Feedback je Fund + Label-Export, Fragen-Versionierung
  - contra: Integrationsaufwand am Samstagnachmittag
  - Aufwand: ~2-3 h (Felder in policy table/UI, Export-Format)
- **Option getrennt lassen**
  - pro: Kein Integrationsrisiko
  - contra: Zwei Demos, keine gemeinsame Zahl; Jury sieht zwei halbe Lösungen
  - Aufwand: keiner
- **Option ihr Design übernehmen**
  - pro: Einfacher (eine Frage-Liste, eine Schwelle)
  - contra: Allgemeine Fragen auf Kev: Fehlalarme 68% [44, 89], exakt 50% [35, 64] (gepaart -29 Pkt. [-50, -10] belegt)
  - contra: Keine Prüfen-Klasse, keine Stichwortliste (Jury-Anforderung)
  - Aufwand: Umbau

**Unsere Empfehlung:** Kombinieren: unsere Pipeline (ASR, Rollen, Fakten + Tabelle, Stichwörter, UI) als Standard, Kev als optionaler, formulierungsrobuster Leser; Rechtsgrundlage, Feedback-Export und Fragen-Versionierung aus sprintd_zurich übernehmen. Details: Abschnitt „Unser Ansatz vs. sprintd_zurich“.

**Was die Empfehlung ändern würde:**
- Kev mit einer „unklar“-Antwort, die Prüfen-Fälle erzeugt, oder Kev-Passagen mit gutem hit@1.
- Auf test50 (ihr Testsatz, extern): allgemeine Fragen auf Kev ausstehend, Fehlalarme ausstehend, gegen Champion ausstehend.
- Qwen3.8 6-bit allgemein bleibt auf umformulierten Fragen und neuem Audio gleich gut (ausstehend, ausstehend).

Quellen: `experiments/kev_vs_facts.yaml`, `research/findings/two_readers.md`, `experiments/contrib/comparison_zurich.yaml`

**Entscheid des Teams:** offen

### 6. Fragen an die Organisatoren am Sonntag

**Frage:** Was müssen wir vor 08:30 wissen?

- **Option Ablauf**
  - pro: Wer verarbeitet das versteckte Set: wir auf ihren Dateien oder sie mit unserem Code?
  - pro: Zeitlimit und Anzahl Anrufe? (Champion gestaffelt ~30 s pro Anruf auf dem 4070)
  - pro: Hardware vor Ort (GPU, VRAM, Internet für Modell-Downloads)?
- **Option Format**
  - pro: Eingabe: nur .wav, Dateinamen, gleiche TTS-Stimmen und Stufenstruktur?
  - pro: Ausgabe: result.json pro Anruf, CSV mit call_id,expected, oder Trigger-API?
  - pro: Wird „Prüfen“ als Treffer, eigene Klasse oder ignoriert gewertet? (Antwort Sa: Konfigurierbarkeit zählt mehr)
- **Option Regeln**
  - pro: Fine-Tuning auf den gegebenen Anrufen erlaubt?
  - pro: Dürfen wir unsere Schwelle / unseren Prüfmodus vorab fest wählen und begründen?

**Unsere Empfehlung:** Fragen 1-3 Sonntag früh vor dem Lauf klären; Antworten in docs/CASE.md festhalten.

Quellen: `docs/CASE.md`, `docs/SUNDAY_RUNBOOK.md`

**Entscheid des Teams:** offen

## Unser Ansatz vs. sprintd_zurich (Teamkollege)

Geschrieben gegen Commit `47c4ffd` von `github.com/markandrewc/sprintd_zurich`.
**Achtung:** das Repo steht jetzt auf `954446c`; der Vergleich muss aktualisiert werden.

Gemessen wurde auf unseren Dev-Daten (48 Anrufe, large-v3-Transkripte, unsere Rollen), nicht in ihrer Umgebung. Ihre README nennt keine Kennzahlen. Wo keine Messung steht, ist die Zeile eine Beschreibung.

| Thema | Unser Ansatz (callguard) | sprintd_zurich (Teamkollege) | Messung / Beleg | Wirkung | Empfehlung |
|---|---|---|---|---|---|
| ASR-Modell | gcoli/whisper-large-v3-swiss-german-mit (MIT), Ausgabe Hochdeutsch, Keyword-Prompt | Flix-AI/flix-swissgerman-full (Whisper large, Volltraining, Apache-2.0), HF-Pipeline bf16, language=de | RQ2 (Dev, Keyword-Stellen-Recall): gcoli 83.7% [77.5, 93.2] vs Flix 76.1%; Intervalle überlappen. | Transkript-Qualität begrenzt alle Prüfungen; Unterschied nicht belegt. | **behalten**: höherer gemessener Recall, MIT-Lizenz; Flix bleibt Alternative |
| Segmentierung / Sprecher | sherpa-onnx-Diarisierung (CPU) + LLM weist Berater/Kunde zu; Rollen gehen in die Fakt-Fragen | nvidia/Nemotron-3-Diarization, Sprecher-Chunks ≤ 20 s (Lücke ≤ 1 s), max. 2 Sprecher, keine Rollen | Fall-Audio ist eine TTS-Stimme (ihre README: nur „Sprecher 1“). Rollen verbergen: AUC −0.06 [−0.15, +0.00] (RQ6, grenzwertig). | Rollen helfen den Fakten knapp; akustische Diarisierung trennt auf dem Fall-Audio kaum. | **behalten**: Rollen per LLM funktionieren auch bei einer Stimme |
| Entscheider-Modell | Qwen2.5-7B-AWQ (vLLM, Log-Probs, Champion); Optionen Qwen3.8-27B 3/6-bit, Kev-4B, zwei Leser | Kev-4B (jaredpalmer/kev-4b, LoRA auf Qwen3.5-4B, bf16 ~8 GB, in-process) | Gleiche Fakten-Tabelle: Champion 0.87 [0.72, 0.99], Kev 0.86 [0.67, 0.98] (gepaart -0.01 [-0.21, +0.14] ≈); umformuliert Champion 0.73 [0.53, 0.89] (Ø 2), Kev 0.90 [0.73, 1.00] (Ø 2) (gepaart +0.17 [+0.04, +0.31] belegt). | Kev ist formulierungsrobust, kennt aber kein „unklar“ (6× Prüfen vorhergesagt, 0 von 6 Soll-Prüfen getroffen). | **kombinieren**: Kev als umschaltbarer Leser, Champion als Standard |
| Fragen | abgestimmte atomare Fakt-Fragen (Englisch) + Policy-Tabelle; Paraphrasen- und Blind-Tabellen als Robustheitsprobe | 15 allgemeine, gesetzesbasierte Ja/Nein-Fragen (Englisch, 10 gesetzlich + 5 intern), ohne Testdaten geschrieben | Auf Kev: allgemein 0.79 [0.62, 0.93], Fakten 0.86 [0.67, 0.98]. Allgemein umformuliert 0.88 [0.74, 1.00]. Fakten-Fragen auf Deutsch statt Englisch: AUC −0.13 [−0.29, −0.01] (RQ6). | Allgemeine Fragen sind weniger an Dev angepasst, markieren ohne Regelschicht aber zu viel (Fehlalarme 68% [44, 89]). | **kombinieren**: ihre Gesetzesbezüge als Kategorien unserer Fakten; Tabelle behalten |
| Entscheidungsregel | Policy-Tabelle → Alarm / Prüfen / Kein Alarm, gewichtete Fusion, Schwelle 0.55 (CV gewählt), Prüfband | max p(ja) über alle Fragen ≥ 0.7 → Alarm, sonst kein Alarm (binär, keine Prüfen-Klasse) | Ihre Regel auf unseren Transkripten (Kev allgemein): Fehlalarme 68% [44, 89], exakt 50% [35, 64] (gepaart -29 Pkt. [-50, -10] belegt); Champion Fehlalarme 14% [0, 35]. | Ohne Prüfen-Klasse kein „unsicher → Mensch“; die Organisatoren wollen das Verhalten konfigurierbar. | **behalten**: 3 Klassen + konfigurierbarer Prüfmodus |
| Lokalisierung der Belege | Belege = Segment-IDs aus den Fakt-Antworten; Passagen + Audio-Snippets (±2 s) mit Zeitstempel | Okklusion: bestes 40-Wort-Fenster (Überlappung 20), darin 25-Wort-Spanne mit grösstem p-Abfall; Snippet ±10 s | Beleg hit@1: Champion 73% [45, 91], Zufall 24%; ihr Fensterverfahren (bei uns nachgebaut, Kev allgemein) 87% [60, 100], Zufall 55%. | Lange Fenster treffen schon zufällig oft; kurze Passagen sparen dem Officer Zeit. | **behalten**: präziser bei kürzeren Passagen; Okklusion als Ersatz, wo ein Modell keine Belege liefert (Kev, Qwen3.8) |
| Stichwörter | editierbare Stichwortliste (config/keywords.json, UI-Seite), leichtes Gewicht in der Fusion | keine | Nur Stichwörter: AUC 0.55 [0.38, 0.73]; die Liste ist eine Anforderung des Falls. | Allein schwach, aber erklärbar und vom Officer anpassbar. | **behalten** |
| Rechtsgrundlage | keine Gesetzesartikel an den Prüfungen (nur Kriterien-Text) | jede Frage mit `basis` (z.B. FinfraG Art. 142 / 154, StGB Art. 305bis, GwG Art. 6 / 9), im Fund angezeigt | beschreibend | Für Compliance-Officer und Jury glaubwürdiger. | **übernehmen**: Feld `basis` je Familie/Fakt, im Anruf anzeigen |
| Schwelle | Schwelle per Out-of-fold-CV gewählt (0.55), Regler + Prüfband in der Seitenleiste, Re-Fusion ohne Modell | fest 0.7 in questions.json, Regler in „Einstellungen“ mit Vorschau „N von M Anrufen“, nicht kalibriert | beschreibend | Beide live einstellbar; ihre Vorschau der Fallzahl ist officer-freundlich. | **kombinieren**: Vorschau der Arbeitslast beim Verstellen |
| Evaluation | Dev/Holdout-Split, Zwillinge im selben Fold, Out-of-fold-CV-Schwellen, Bootstrap-KI, AUC, 3 Klassen | alle 30 Dialoge auf Referenzskripten (optional ASR), binär, TP/FP/FN/TN, Präzision/Recall/F1, kein KI, kein Split | Ihre Einstellung (Kev allgemein auf Dialekt-Referenzskripten, ORACLE): AUC 0.89 [0.69, 0.99]; auf unserer ASR: 0.79 [0.62, 0.93]. | Referenzskripte überschätzen die Leistung auf Audio; ohne KI ist kein Unterschied belegbar. | **behalten** |
| Officer-Feedback / Labels | Rückmeldung je Anruf → Schwellen-Vorschlag (Feedback & Tuning), offene Fakten beantworten, Audit-Log | Urteil je Anruf + richtig/falsch je Fund + übersehene Kategorien; Export labels.jsonl für Fine-Tuning | beschreibend | Ihr Export macht Feedback zu Trainingsdaten. | **übernehmen**: Feedback je Fund + Label-Export |
| Fragen-Versionierung | Tabellen/Kriterien als YAML in Git; Cache-Schlüssel enthalten den Inhalt | PUT /questions erhöht `version`, archiviert questions_v{N}.json, jede Analyse speichert ihre Version | beschreibend | Nachvollziehbar, welche Fragen ein Urteil erzeugt haben. | **übernehmen**: Version der Tabelle in result.json schreiben |
| GPU-Handhabung | gestaffelte Läufe (ASR, dann LLM) + inhaltsadressierter Cache; Server getrennt (vLLM, llama.cpp, Kev) | ModelSlot: Laden bei Bedarf, Entladen nach 120 s Leerlauf; erst alle ASR, dann Analyse | Champion gestaffelt ~30 s pro Anruf (Journal 04:50). | Ihr Ansatz braucht keine Server-Neustarts. | **offen** |
| UI | Streamlit, mehrseitige Officer-UI (Eingang, Anruf, Stichwörter, Qualität, Experimente, ...) | Gradio, 4 Tabs (Anrufe, Neue Anrufe, Prüfpunkte, Einstellungen), SQLite, Auto-Refresh | beschreibend | – | **behalten** |
| Synthetische Daten | Text-Skripte aus neuen Szenarien (Qwen3-8B), 74 Anrufe, Referenztext ohne ASR | SwissDial-TTS (VITS, 8 Dialekte) für Audio; keine Daten im Repo | beschreibend | Ihre TTS könnte Audio mit anderen Stimmen/Dialekten für einen ASR-Robustheitstest liefern. | **kombinieren**: unsere Skripte mit ihrer TTS vertonen |

