# The case (condensed): "Every bank call checked, not just samples"

Inventx AG + Outcept, sprintd Innovation Sprint Zurich, 9-11 Oct 2026. Full brief:
`data_upstream/inventx-case-study/README.md` (upstream: github.com/Outcept/inventx-case-study).

## Problem
Bank advisor <-> customer calls are all recorded, only samples are reviewed. Misconduct (insider trading,
sharing access secrets, disclosure to third parties, ...) on both sides of the line goes undetected.
The calls are Swiss German, where off-the-shelf speech tools fail.

## Required for a valid submission
1. Transcription of the Swiss German call.
2. Several kinds of AI-based fraud checks.
3. Suspicious passages as audio snippets, each with timestamp and reason.
4. An adjustable threshold.
5. A metric for false alarms and missed cases, reported on the test set.
The prototype runs without manual steps per call.

## Jury (weights)
| criterion | weight | what they reward |
|---|---|---|
| Creativity & innovation | 20 | fresh, surprising, workable approach |
| Feasibility | 10 | realistic architecture for a bank's secured environment, self-hostable models |
| Design & usability | 25 | officer understands each alert + reason; adjusts threshold AND keyword list without code |
| Impact & relevance | 20 | solves the actual problem |
| Detection quality & traceability | 25 | few false alarms + few misses on the **hidden test set**; every hit has passage + criterion; shows when unsure and escalates |

"Tuning" = one threshold trading false alarms vs misses. "Configuration" = what is looked for (keyword
families, kinds of checks). Both changeable by an officer without code. "A pure keyword filter is easy
to configure but blind to context. A language model understands context but is hard to steer. The
interesting solutions sit in between."

## Demo (Sunday 09:00-11:00, 5 min live + 3 min questions; submission 08:30)
1. One call from audio to alert, with the suspicious audio snippets.
2. One change to the threshold or the keyword list with a visible effect on the number of hits.
3. One borderline case: a harmless call that still contains a keyword (e.g. Stufe1_D03).
4. Detection quality on the test set.

## Data (`data_upstream/inventx-case-study/data`)
- 60 WAV (16 kHz mono, synthetic voices, ~4 h 40) = 30 dialogues x {clean K1/K3, noisy K2/K4}.
- `Transkript/` scripts (Swiss German dialect, turn by turn `T001 · Beratung`), `Skript_mit_Sollbewertung/`
  same + header: Testziel (family), Ereignis (present/absent/undetermined/not_applicable),
  Bearbeitung (alarm/no_alert/review), Begründung, Offen, Belege (evidence turns), Keywordstellen.
- Levels: Stufe1 = direct keyword calls (10 dialogues), Stufe2 = context pairs where only context
  decides (16, mostly no keywords at all), Stufe3 = open cases, expected "review" (4).
- Labels over the 60 calls: alarm 24, no_alert 28, review 8. Families: trade, access, disclosure,
  documentation, splitting, numbers (numbers never alarms by itself).
- Hidden test set: ~30% of the material held back by Inventx/Outcept, run on Sunday.
- Rule: do not feed file names, scripts or expected assessments into the audio pipeline as hints.

## Allowed tech
Anything self-hostable: Whisper / Swiss German variants, open LLMs, any model on our GPUs. Not allowed
in the core pipeline: cloud-only services (Deepgram, AssemblyAI, ElevenLabs, OpenAI credits).

## Stretch goals (none required)
Speaker separation; notifying the right person; feedback (mark false alarms -> better thresholds);
patterns across calls (advisor who stands out repeatedly); operating concept for a secured environment;
Outcept trigger API (`server.py` in the case repo: POST /triggers {url, title, description}).

## Open questions for the organizers (ask on site; record answers here)
- Is `review` scored as a hit, a separate class, or ignored? Precision/recall on alarm or on alarm+review?
- The brief mentions 8 calls recorded by two people - are they available?
- Sunday: do they run our code or do we run on their files? Time limit, output format?
- Same TTS voices / level structure in the hidden set? Is fine-tuning on the given calls allowed?
- Are passages scored against the "Belege" turns, or only the call label?
- Event GPUs: which, when, VRAM, internet access?
