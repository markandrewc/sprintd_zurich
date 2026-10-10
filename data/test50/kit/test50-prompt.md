# Prompt: 50 new labelled test calls with FHNW Swiss German TTS – saved to my Mac

You are helping a hackathon team (sprintd Zurich 2026, case Inventx × Outcept). Our system checks Swiss German phone calls between a bank advisor and a customer for compliance issues and decides **alarm**, **review** or **no_alert**.

Build a **new, held-out test set of 50 calls**:
1. Write each dialogue in Standard German (DE), with its expected detection result.
2. Have the **FHNW STT4SG TTS API** translate every sentence into Swiss German (CH) and synthesise it as audio.
3. Assemble the sentences into full customer calls (a clean and a noisy version).
4. Save everything (DE text, CH text, call audio, labels) in **a folder on my Mac that I choose**.

**No local AI models.** All translation and speech come from the FHNW API. Local code only does plumbing: HTTP requests, files, and joining and mixing audio.

Work on your own and only stop when something blocks you or a step below says to ask me.

**Attached in `test50-kit.zip`** (unzip it and read everything first):
- `families-v3.json`: families, slot questions, rule table (facts → verdict), gold facts of Outcept's 30 scripts
- `check_rules.py`: rule logic and scorer
- `Stichwortliste.json`: Outcept's keyword list (K01–K11, de + gsw)
- `Stufe2_C05.txt`, `Stufe2_C06.txt` (a contrastive pair) and `Stufe3_C17.txt` (a review case) as format and style examples

The examples are Outcept's test data. Copy their **style and logic**, never their scenarios, names, companies, cue words or sentences.

---

## 0. Before anything else
1. **Ask me which folder on my Mac to use.**
   - If you can reach my computer (connected folders or a device shell), request access to that folder.
   - Otherwise ask for its full path; you will then give me a Terminal command that writes there.
2. **Show me the usage terms** and wait for my OK before the first bulk run:
   - The TTS demo says the model must not be used commercially.
   - The FHNW site says the demos are not for production and that entered data may be stored for research.
   - FHNW's STT demo forbids automated access, bulk extraction and model training. We therefore use **only** the TTS API, for a small non-commercial test set, slowly, and never to train a model.
   - All dialogue content is fictional.

## 1. The FHNW TTS API (Gradio, runs on CPU)
Base: `https://stt4sg.fhnw.ch/tts/`. Each call takes two requests: a POST returns an `event_id`, then a GET streams the result as server-sent events.

```
POST https://stt4sg.fhnw.ch/tts/call/translate_interface   body {"data": ["<Standard German text>", "<dialect>"]}  → {"event_id": "…"}
GET  https://stt4sg.fhnw.ch/tts/call/translate_interface/<event_id>   → "event: complete" + "data: [\"<Swiss German text>\"]"

POST https://stt4sg.fhnw.ch/tts/call/speech_interface      body {"data": ["<Swiss German text>", "<dialect>"]}  → {"event_id": "…"}
GET  https://stt4sg.fhnw.ch/tts/call/speech_interface/<event_id>      → "event: complete" + "data: [{…file with \"url\"/\"path\"…}, \"<markdown>\"]"
```

- Download the audio from the returned `url`. If there is none, use `https://stt4sg.fhnw.ch/tts/file=<path>`.
- On `event: error`, retry with exponential backoff.
- Allowed dialects, exactly these strings: `Aargau`, `Bern`, `Basel`, `Graubünden`, `Luzern`, `St. Gallen`, `Valais`, `Zürich`.
- There is no voice parameter, so the voice probably depends on the dialect.
- The API has no speech-to-text. The CH text from `translate_interface` *is* the transcript of the audio we generate from it.
- **Etiquette (hard rules for the script):**
  - one request at a time, with a 2 s pause between requests
  - cache every result by `sha1(endpoint + dialect + text)`, so a rerun never calls the API again
  - resume after interruption
  - stop after 5 consecutive failures

## 2. Test-set design (50 calls)
Each call has two speakers: `Beratung` (bank) and `Kundin` or `Kunde`. Names, firms, places and amounts in CHF are all fictional.

| Block | Calls | Expected |
|---|---|---|
| Per alarm family (trade, access, disclosure, documentation, splitting): 3 contrastive pairs | 30 | 15 alarm + 15 no_alert |
| Per alarm family: 1 review case (one needed fact stays open) | 5 | review |
| Per alarm family: 1 keyword trap (family keywords negated, quoted, refused or already public) | 5 | no_alert |
| numbers: 3 pairs (same digits read; an early field reference decides the class) | 6 | no_alert |
| Multi-topic: a harmless topic plus a real issue from another family, or two harmless topics with distractor keywords | 4 | worst family wins |

**Facts and rules:** use the slots and rule table in `families-v3.json` exactly. The verdict follows only from the facts:
- alarm if every alarm slot of a family is ja
- a needed slot unklar → review; any nein → no_alert
- disclosure: an open authorization → review even without disclosure
- numbers never alarm
- later refusals, warnings or cancellations never undo an act; execution is not required

**Pair rules:**
1. A and B are identical except **one early context turn** (T003–T006).
2. The act comes **at least 5 turns later**, is **word-for-word identical**, and refers back only indirectly ("deswegen", "die Zahl von vorhin", "die markierte Zeile").
3. The changed turn flips exactly one slot, and with it the verdict.
4. Vary the cues across pairs (source, validity, authorization, document line, motive). No recurring phrase may give the answer away.

**Keywords:**
- Relevant in some alarms, harmless in traps, as distractors from other families, and absent in at least half of the alarms.
- Label every occurrence (K-ID, turn, speaker, relevant / benign).

## 3. Writing the DE text (it goes to the translator)
- Call length: 10–18 turns, 150–450 words, about 1.5–4 minutes.
- Each turn has 1–3 sentences, and each sentence is at most 180 characters.
- Use plain spoken Standard German.
  - Write numbers as words ("sieben, drei, eins, neun").
  - No abbreviations, brackets or slashes; keep names short.
- Decisive turns (context + act) get one clear key sentence:
  - Put the key words mid-sentence and keep negations explicit ("kein", "nicht").
  - No irony or implication.

## 4. Dialects
- Each call gets two **different** dialects: one for Beratung, one for Kundin/Kunde.
- Each dialect appears in at least 10 role slots across the set. Pair members A and B use the same two dialects.
- **Voice check, first API step:**
  - Synthesise one short sentence per dialect into `voice_check/`.
  - Ask me to listen. If two dialects sound like the same voice, never put them in the same call.

## 5. Per sentence
1. DE → `translate_interface(de, dialect)` → `ch_auto`.
2. Compare `ch_auto` with DE using simple string rules:
   - **negations**: nicht / kein / nie / niemand ↔ nöd / nid / ned / ni / kei / keis / keini / nie / niemer / niemert
   - **numbers**: same digits, in the same order
   - **key terms of decisive facts**: abgelaufen, Webseite, Vollmacht, Kreditstelle, Rechnung, Freigabe…
   - **names**
   - Anything lost or changed → a row in `needs_review.csv`, and that sentence is **not** synthesised yet.
3. I or you fix it as a minimal edit → `ch_final` (with `edited: true`). Otherwise `ch_final = ch_auto`.
4. `ch_final` → `speech_interface(ch_final, dialect)` → snippet audio in `cache/`.
5. Plausibility check: 8–22 characters per second of audio. If not, split the sentence and regenerate.

## 6. Assembling the calls (Python standard library only)
- Use `urllib`, `json`, `wave`, `array`, `math`, `random`, `hashlib`, `csv` and `subprocess` only, so nothing needs installing.
- If a snippet isn't 16 kHz mono PCM16 WAV, convert it with macOS `afconvert -f WAVE -d LEI16@16000 -c 1`. Use `ffmpeg` if present, otherwise a built-in linear resampler.
- Trim silence (below −40 dBFS) and normalise each role to an RMS of about −20 dBFS.
- Gaps, seeded per call ID:
  - 120–300 ms between sentences
  - 300–900 ms between turns
  - no overlaps
- Every sentence is synthesised on its own, with **its speaker's dialect**. The speakers are only joined when the call is assembled.
- **Pairs:** build B from A's snippets and swap in only B's changed turn, so the act audio is byte-identical.
- Also write one **stem per speaker**: `<id>_Beratung.wav` and `<id>_Kunde.wav`, each as long as the call, with silence while the other person speaks. These are for checking speaker separation.
- Record exact **start/end per turn and sentence** from sample counts.
- `<id>_clean.wav`
- `<id>_noisy.wav`, built from the clean file:
  - telephone band 300–3400 Hz (two RBJ biquads in plain Python)
  - pink noise at an SNR of 15–25 dB
  - on a decisive turn, one synthetic **bell** (880 + 1320 Hz, 0.6 s decay) or **knock** (3–4 noise bursts, 80 ms apart)
    - level −12 to −6 dB relative to the speech
    - it overlaps the key sentence partly, never fully
  - one **word restart** on a decisive turn: the first word's audio cut at 35 %, then 150 ms of silence, then the full sentence
  - log every event with its time

## 7. What lands in my folder
```
<my folder>/
  README.md                 how it was built, distribution table, limits, how to rerun
  manifest.csv              id, family, type, expected, duration_s, dialects, n_turns, edited_sentences
  families-test50.json      copy of families-v3.json whose "gold" holds the 50 new calls
                            → python3 check_rules.py families-test50.json predictions.json scores us unchanged
  texts_test50.jsonl        one line per call: DE + CH texts and all labels
  make_calls.py             the script (stdlib only), plus run.command for a double-click start
  needs_review.csv          sentences whose translation check failed
  voice_check/              one sample per dialect
  calls/<id>/
    <id>_clean.wav          full call (both speakers in one file), 16 kHz mono
    <id>_noisy.wav
    <id>_Beratung.wav       stem: only the advisor, silence elsewhere
    <id>_Kunde.wav          stem: only the customer, silence elsewhere
    <id>_DE.txt             first line "Beratung: Zürich · Kundin: Bern", then turn by turn like the samples:
                            "T001 · Beratung (Zürich) [00:00.0–00:04.3]" + Standard German text on the next line
    <id>_CH.txt             the same layout with the Swiss German text (transcript of the audio)
    <id>.json               labels + timestamps (schema below)
    <id>_outcept.txt        Outcept script format (header like the examples + CH turns)
  cache/                    API responses and sentence snippets (needed for resuming)
  logs/progress.log
```

`<id>.json`:
```json
{"id": "T50-trade-02-A", "family": "trade", "type": "pair|review|trap|numbers_pair|multi",
 "pair_id": "T50-trade-02", "variant": "A", "families_involved": ["trade"],
 "dialects": {"Beratung": "Zürich", "Kundin": "Bern"}, "duration_s": 154.2,
 "turns": [{"id": "T001", "speaker": "Beratung", "dialect": "Zürich", "de": "…", "ch_auto": "…",
            "ch_final": "…", "edited": false, "start": 0.00, "end": 4.31,
            "sentences": [{"de": "…", "ch_final": "…", "start": 0.00, "end": 2.10}]}],
 "facts": {"trade": {"kaufwunsch": "ja", "info_nicht_oeffentlich": "ja", "wegen_info": "ja"},
           "access": {"wert_vorgelesen": "nein"}, "disclosure": {"drittinfo_erfragt": "nein"},
           "documentation": {"weglass_wunsch": "nein"}, "splitting": {"teilung_angefragt": "nein"}},
 "evidence": {"kaufwunsch": "T012", "info_nicht_oeffentlich": "T004", "wegen_info": "T012"},
 "expected": "alarm",
 "belege": [{"turn": "T004", "start": 18.4, "end": 25.9}, {"turn": "T012", "start": 96.0, "end": 101.2}],
 "begruendung": "1–2 Sätze, warum", "offen": null,
 "keyword_hits": [{"id": "K04", "phrase": "vor der Meldung", "turn": "T012", "speaker": "K", "label": "relevant"}],
 "noise_events": [{"type": "bell", "turn": "T012", "start": 97.1, "end": 97.7}]}
```
`facts` holds all slots of the target family (both families for multi-topic calls), plus the gate slot of every other family. For numbers: `{"numbers": {"zahlenobjekt": "…"}}`.

## 8. Order of work
1. Write all 50 dialogues (DE + labels), validate them (section 9, checks 1–3 and 6), and save `texts_test50.jsonl` and the `_DE.txt` files to my folder **straight away**, so I keep them even if the audio step fails.
2. Write `make_calls.py` and `run.command` into the folder.
3. **Test with one call:** `--only T50-trade-01-A`.
   - If you have a shell on my computer, check first whether it reaches the API (one request) and run it there.
   - If not, give me the exact Terminal command for macOS, e.g. `cd "<folder>" && caffeinate -i python3 make_calls.py --only T50-trade-01-A` (caffeinate keeps the Mac awake).
   - Check the outputs before going on.
4. **Voice check** (section 4), and wait for my listening result.
5. **Full run:** sequential, resumable, progress in `logs/progress.log`. If you run it on my computer, start it in the background and poll. Otherwise give me the full-run command.
6. Work through `needs_review.csv`: you propose minimal `ch_final` edits, I confirm, and the rerun only fills the gaps.
7. Run the final validation, then write `README.md` and a short summary for me:
   - counts per family × type × verdict
   - the dialect matrix, total duration and the number of edited sentences
   - anything that failed

## 9. Validation
1. facts → verdict with the logic of `check_rules.py` (worst family wins) equals `expected`; print the distribution table.
2. Pairs: exactly one differing turn (T003–T006), an identical act turn at least 5 turns later, and lengths within ±5 words.
3. Every evidence turn exists and contains the fact; Belege times lie inside their turns.
4. Translation checks (section 5) are resolved: `needs_review.csv` is empty or every row is decided.
5. Audio: no empty or clipped snippet, characters per second plausible, timestamps monotonic, noisy SNR within range, and the act audio byte-identical within each pair.
6. No sequence of more than 8 words copied from the example scripts; no name or firm used more than twice.
7. A Swiss German speaker on our team listens to 10 calls, especially the decisive turns. If a decisive word is not understandable, rephrase that DE sentence and regenerate.
