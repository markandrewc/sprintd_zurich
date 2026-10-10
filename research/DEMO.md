# Jury demo, Sunday 2026-10-11 09:00 (5 min live + 3 min questions)

Profile: `config/recommended.yaml` (large-v3 MIT ASR, Qwen2.5-7B facts + light keywords/patterns, threshold 0.55).
All 60 case calls are already processed into `runs/recommended/<call>/result.json` with audio snippets. Everything
shown below comes from that cache. The UI only re-fuses scores and re-runs the keyword check, so it needs **no GPU and
no vLLM**.
Every number below was checked on 2026-10-10 against the real UI: Streamlit AppTest on runs/recommended, plus
interactive steps on a copy of it.

```bash
export PATH=$HOME/.local/bin:$PATH
cp -a runs/recommended /tmp/recommended.bak && cp config/keywords.json /tmp/keywords.bak.json   # undo point
uv run callguard ui -c recommended            # http://localhost:8501 ; open the deep links below in tabs beforehand
```

Pre-open these tabs:
- Inbox: `http://localhost:8501/`
- `http://localhost:8501/?call=Stufe1_D02-K1&t=86`: alarm, opens at the snippet
- `http://localhost:8501/?call=Stufe1_D03-K1`: harmless call with keywords
- `http://localhost:8501/?call=Stufe3_C17-K3`: review
- The **Qualität** page

## The 4 demo items mapped to calls

All calls below are DEV dialogues. Holdout dialogues are D07, C03, C04, C15, C16 and C19. Show them only if you say they are holdout.

| # | jury item | call | what is on screen |
|---|---|---|---|
| 1 | audio to alert with snippets | **Stufe1_D02-K1** (trade, expected alarm) | Alarm, score 0.99. Snippet 2 at **01:26.5–01:35.4**, 13 s clip: *"Gerade darum möchte ich diese Aktie jetzt kaufen, vor der Meldung. Wenn alle am Freitag die Quartalszahlen sehen, ist der Preis doch schon oben."* Reason: *"Handelswunsch mit nicht öffentlicher Information aus interner Quelle. Regel: trade.alarm_1. Fakten: Eigener Handelswunsch geäussert = ja (1.00); Begründet mit nicht öffentlicher Insider-Information = ja (1.00); Information bereits öffentlich = nein (1.00)"*. Snippet 1 at 00:36.6–01:07.9: the sister in the finance department, figures "noch nicht publiziert", "vertraulich behandeln". |
| 1b | backup alarm (access) | Stufe1_D05-K1 (expected alarm) | Alarm 0.91. Snippet **01:16.9–01:22.1**, 9 s: *"Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei."* Facts: code read out = ja (1.00), belongs to the running login = ja (0.89), rule access.alarm_1. The negated "Sie müssen mir kein PIN und kein Passwort sagen" at 00:22 is marked as negated (score 0.10). |
| 2 | threshold or keyword change, visible effect on hit count | the Inbox (60 calls) | See the recipe below: threshold 0.55 → 0.50 gives Alarm 17 → 28. Keyword K10 off gives keyword hits 82 → 68. |
| 3 | harmless call that contains keywords | **Stufe1_D03-K1** (expected no_alert) | Kein Alarm, score 0.04. The "Warum kein Alarm? (Insiderhandel)" panel is open. |
| 3b | the system hands over when unsure | **Stufe3_C17-K3** (expected review) | Prüfen, score 0.50, causes listed. |
| 4 | detection quality on the test set | **Qualität** page + holdout table | Dev and holdout numbers, see below. |

### What "Warum kein Alarm?" shows on Stufe1_D03-K1

- **Summary:** "Stichwörter wie «Finanzabteilung», «Quartalszahlen», «vor der Meldung» kommen vor, aber «facts» bewertet
  «Insiderhandel» nur mit 0.00: Kein Handelswunsch auf Basis nicht öffentlicher Information."
- **Keyword hits (6):**
  - Finanzabteilung 01:10
  - Quartalszahlen 02:00 and 02:12
  - vor der Meldung 03:05, *verneint*
  - nicht publiziert 03:08, *verneint*
  - vertraulich 04:20
- **Stärkstes Gegenargument:** «facts», score 0.00, certainty 100%, verdict "nicht vorhanden". Fact values:
  - Eigener Handelswunsch geäussert = **nein (0.99)**
  - Begründet mit nicht öffentlicher Insider-Information = **nein (1.00)**
  - Information bereits öffentlich = **ja (1.00)**
- **Entlastungsregel:** "Kein Handelswunsch auf Basis nicht öffentlicher Information." The fact check names this rule.
  The panel also shows the keyword list's "harmlos, wenn …" notes, for example "Öffentliche Unternehmensmeldungen werden sachlich erläutert."
- **Check table:**
  - keywords: weight 0.15, score 0.78, above the threshold on its own
  - facts: weight 1.0, score 0.00
  - Total 0.04, review from 0.40, alarm from 0.55.
- In the transcript: the customer says at 03:02–03:09 "Ich will nicht vor der Meldung handeln und habe auch keine
  Informationen, die noch nicht publiziert wären". At 01:40 she says the report has been public "seit gestern Morgen".

### What the review banner shows on Stufe3_C17-K3

"Prüfen: Unsicher → an Menschen übergeben." The banner lists three causes:
1. Knapp unter der Schwelle (0.50 in 0.40–0.55).
2. Prüfungen sind sich selbst unsicher (facts 30%).
3. Sachverhalt offen: *"Ein Wert wurde vorgelesen, aber unklar ist, zu welchem Vorgang er gehört oder ob er gültig ist.
   Regel: access.review_1. Fakten: Code/Wert am Telefon vorgelesen = ja (0.92); Im Gespräch offen, ob der Wert gültig ist =
   ja (1.00); Wert abgelaufen oder Muster = nein (0.90)"*.

Two passages:
- 01:23.5–01:26.5: "Ich weiss nicht, ob der Wert oben oder unten dazugehört."
- 01:39.0–01:47.5: "2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen."

This matches the expected assessment ("Herkunft und Gültigkeit nicht geklärt → review"). There are no keywords in this call, so a keyword filter would not see it at all.

## Item 2 recipe: what to click and what the Inbox shows

Profile default: **Alarm 17 · Prüfen 11 · Kein Alarm 32 · Mensch nötig 28** (60 calls).

**A. Threshold.** This is the main item. It needs no file writes and is instant.
1. In the sidebar, set **Alarmschwelle** from 0.55 to **0.50**. The Inbox shows **Alarm 28 (+11) · Prüfen 0 (−11) · Kein Alarm 32**.
   - The 11 "open fact" calls have a score of exactly 0.50. At 0.50 they become automatic alarms instead of going to a human.
   - Say: "A lower threshold means more automatic alarms. Our default keeps the unclear cases with a human."
2. Set it to **0.95**. The Inbox shows **Alarm 7 (−10) · Prüfen 20 (+9) · Kein Alarm 33 (+1)**.
   - The softer alarms (D05, D07, D09, D10, C07-K4, C12-K4) move to review.
   - D10-K2 (score 0.80) falls out completely. That is a miss, the price of a high threshold.
3. Click **Zurücksetzen**. The counts return to 17/11/32.
4. Optional: set **Max. Unsicherheit** from 0.35 to 0.20. The Inbox shows Alarm 10 (−7), Prüfen 18 (+7). Uncertain alarms go to a human.

Note: anywhere between 0.55 and 0.70 nothing changes (17/11/32). The facts scores are near-discrete, which gives a
robust plateau. Do not demo with small slider moves.

**B. Keyword list.** This shows configuration without code. It writes `config/keywords.json` and rewrites the result.json files (about 1 s, CPU only).
1. Open **Stichwörter & Kriterien**, tab **Zugangsinformation preisgegeben**. Untick **An** for **K10** ("Zugangswörter":
   PIN, Passwort, TAN, Bestätigungscode). Click **Stichwörter speichern**.
2. Scroll down and click **Stichwörter jetzt auf alle Anrufe anwenden**. The result shows **Stichwort-Treffer 68 (−14)**, Alarm 17 (+0),
   Prüfen 11 (+0), Kein Alarm 32 (+0).
3. Open Stufe1_D05-K1. **Verdächtige Passagen** goes from 3 to 1. It is still an alarm at 0.94, because the fact check heard
   the 6-digit TAN read out.
4. Say: "Keywords are evidence, not the verdict. Removing a keyword removes its marks, but the context check still
   catches the disclosure." (Do not claim more: with keywords only, facts weight 0, D05 is downgraded to review.)
5. **Undo:** tick K10 again, save, and apply. The result shows Stichwort-Treffer 82 (+14).
   If anything looks off: `cp /tmp/keywords.bak.json config/keywords.json && rm -rf runs/recommended && cp -a /tmp/recommended.bak runs/recommended`, then click **Neu laden** in the sidebar.

Alternative B': add a keyword instead of removing one.
- In tab **Insiderhandel**, use the empty last row: Bezeichnung "Familie als Quelle", Hochdeutsch "Schwester, Bruder". Save, then apply.
- Result: **Stichwort-Treffer 102 (+20)**, labels +0. Stufe1_D02-K1 gets a 3rd passage.

**C. "Pure keyword filter" contrast.** This is the strongest storytelling, about 30 s. It is sidebar-only and writes no files.
1. In **Gewichte der Prüfungen**, set **facts** to 0. Only keywords and patterns are left.
2. The Inbox shows **Alarm 8 (−9) · Prüfen 2 (−9) · Kein Alarm 50 (+18)**.
   - **Stufe1_D03-K1/K2 become alarms (false alarms).**
   - The context-only cases C06, C07, C12, C17 and C18 drop out (misses).
   - The holdout alarm D07 also drops out.
3. Click **Zurücksetzen**.
4. Say: "This is the keyword filter the brief warns about: blind to context. The fact check fixes both directions."

## 5-minute script

| time | say | click / show |
|---|---|---|
| 0:00–0:30 | "Every call, not samples. Swiss German audio → Standard German transcript (self-hosted Whisper large-v3 Swiss German, MIT) → atomic fact questions to a self-hosted 7B LLM → an officer-editable rule table decides alarm / review / no alarm. Keywords stay visible as evidence." | Inbox: 60 calls, 17 / 11 / 32, score strip |
| 0:30–1:45 | **Item 1.** "Stufe1_D02-K1: from audio to alarm." | Open the D02-K1 tab (opens at 01:26). Play snippet 2 (13 s). Show the reason line with the facts and rule trade.alarm_1, the timeline markers, snippet 1 (sister in the finance department, not yet published), and the transcript tab with advisor/customer roles. |
| 1:45–2:45 | **Item 3.** "The trap call: same words, harmless." | D03-K1: Kein Alarm 0.04. The "Warum kein Alarm?" panel is open: 6 keyword hits, 2 of them negated, but facts says no trade wish (0.99), the information is public (1.00), rule trade.no_alert. Then 15 s on C17-K3: "When the facts are open, we hand over to a human", with the three causes. |
| 2:45–3:45 | **Item 2.** "The officer tunes without code." | Sidebar threshold 0.55 → 0.50: Alarm 17 → 28, Prüfen 11 → 0. Then 0.95: Alarm 7, Prüfen 20. Reset. If time allows, set facts weight 0 to show the keyword filter: D03 becomes a false alarm. Reset. (Keyword edit, recipe B, only if time allows. It is safer in Q&A.) |
| 3:45–4:45 | **Item 4.** Honest numbers. | Qualität page (dev, 48 calls, 95% CIs), then the holdout table at the bottom of the same page. Use the wording below. |
| 4:45–5:00 | "Self-hosted, fits one 12 GB GPU, every alert has a passage, a snippet, a rule and facts; unclear cases are escalated." | Back to the Inbox |

### Item 4: the honest test-set numbers (say exactly this)

**Dev split, Qualität page:** 48 calls / 24 dialogues, threshold 0.55, "markiert" = alarm or review.

| measure | value | 95% CI |
|---|---|---|
| precision | 88% | 75–100 |
| recall | 85% | 64–100 |
| flag F1 | 86% | 74–97 |
| false-alarm rate | **14%** | 0–33 |
| missed | 15% | 0–36 |
| exact 3-class status | 79% | 63–95 |

Cross-validated (journal 04:09): flag AUC 0.87 [0.72, 0.99], alarm F1 0.86, review recall 67%. For comparison, v1
(free LLM judge) had AUC 0.68, false alarms 86% and 3-class accuracy 38%.

**Holdout:** held back all night, evaluated once on the frozen config. 12 calls / 6 dialogues, logged in
`runs/holdout_log.jsonl` (3 logged looks in total: champion, v1 reference, 14B candidate -> a sanity check, not a test). The table is shown at the bottom of the Qualität page.

| system | false alarms | alarm F1 | flag recall | 3-class acc |
|---|---|---|---|---|
| **champion (recommended)** | **0%** (6/6 harmless correct) | **0.67** | 50% | **67%** |
| v1 baseline, same holdout | 100% (everything → review) | 0.00 | 100% | 17% |

- Caught: the disclosure alarm D07, both versions.
- Missed: the splitting alarm C16 (K3 no_alert, K4 only review) and the open documentation case C19 (→ no_alert).
- Say: "6 dialogues: a sanity check, not a measurement; the confidence intervals are huge. Weak spots are the same as on
  dev: open review cases and the splitting family." (Dev flag F1 0.86 vs holdout 0.67 also reflects that.)

Q&A caveat, if asked about overfitting: the fact wording was written against dev transcripts.
- Paraphrasing the questions drops dev AUC 0.87 → 0.72.
- A table written blind from the criteria scores 0.73–0.85.
- A realistic unseen-call AUC is about 0.75–0.80 (estimate, not measured). See research/MORNING_REPORT.md.

## Fallback plan

1. **GPU or vLLM down: nothing changes for the demo.**
   - The UI reads the stored results, re-fuses on CPU and re-runs keywords on CPU.
   - LLM results come from `.cache`, keyed by the last known model id. This was checked with the LLM URL pointing to a dead port: same 17/11/32, and keyword apply in 1 s.
   - Do **not** click **Anruf verarbeiten**: it needs ASR + LLM on the GPU.
   - "Audio to alert" is shown from the stored run. Provenance (ASR model, LLM, config hash) is in the call page's "Herkunft & Audit" expander.
2. **Laptop instead of the GPU host:** copy `runs/recommended/`, the audio (`data_upstream/inventx-case-study/data/Audio`)
   and ideally `.cache/`.
   - Without `.cache`, keyword apply still works. The facts results are kept and marked "nicht neu gelaufen", and the labels stay the same.
   - Snippets live in `runs/recommended/<call>/snippets/`, so they play even without the full recordings.
3. **UI won't start:** show `runs/recommended/Stufe1_D02-K1/snippets/01_trade_86s.wav` and the decision from the JSON:
   `python3 -c "import json;d=json.load(open('runs/recommended/Stufe1_D02-K1/result.json'))['decision'];print(d['label'],d['reasons'])"`.
4. **Last resort:** `uv run callguard ui -c demo-offline`. Say it is the offline demo profile: reference scripts and a fake LLM, not
   the real system.
5. After any rehearsal with recipe B, restore the keywords and runs from the backups listed above.

## Extra step (20 s): the officer answers the open fact on Stufe3_C17-K3 (S6, "Offene Fakten")

Use it right after the review banner of C17-K3. No GPU, no LLM: only the policy table is re-read.

1. Open the call page for **Stufe3_C17-K3** (`/call?call=Stufe3_C17-K3`). It shows **Prüfen**, rule `access.review_1`.
2. Scroll to the open panel **Offene Fakten**. It shows: *"Offen: Wert gehört zum laufenden, gültigen Vorgang"*, the
   question, and "Modell: unklar (ja 0.00 · nein 0.00 · unklar 1.00)".
3. Click **Ja (gültig)**. Red box: **Alarm**, rule `access.alarm_1` ("Ein gültiger Zugangswert wurde am Telefon
   ausgesprochen"). Below it: **Anruf gesamt: Alarm**, score 0.97 at threshold 0.55 (before: Prüfen, 0.50).
4. Click **Nein (abgelaufen / ungültig)**. Green box: **Kein Alarm**, rule `access.no_alert`, call score 0.00.
   (`config/open_facts.yaml`: once the officer has answered whether the value is valid, "im Gespräch offen, ob gültig"
   no longer counts as open.) **Weiss nicht** keeps it at Prüfen.
5. Click **Zurücksetzen**. The model's values come back.

Say: "The system does not dump the review on you. It asks the one question it could not answer. Your answer is applied
to the same rule table, and the call is decided in a second. Every answer goes into the audit log with the fact, the
answer and the table hash."
- Proof: the **Herkunft & Audit** panel lists `fact_answer` entries (user `officer`, `fact=current, answer=yes, label=alarm`).
- The answer changes only the view in memory. The stored `result.json` is not changed.
- Writes: each click appends one line to `runs/recommended/audit.jsonl` (kinds `fact_answer` / `fact_answer_reset`).
