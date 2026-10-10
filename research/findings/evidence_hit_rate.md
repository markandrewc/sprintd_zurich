# Evidence hit rate + «möglicherweise verhört» (traceability, measured)

**Answer in one sentence:** on the dev split the champion's top passage lands on an annotated evidence turn
(`Belege`) in 16 of 22 correctly flagged calls (73%, 95% CI 45–91%; 24% would be luck), and one of the first
three passages does in 21 of 22 (95%, CI 86–100%). The «möglicherweise verhört» flag does not separate wrong
from right decisions for the champion, but 5 of the 7 passages it flags really do contain recognition errors.
(confidence: medium, small n)

## Setup
- code: `src/callguard/eval_evidence.py`, CLI `uv run callguard evidence-eval [--variant exp/variant ...]
  [--show-alignments N]`, output `runs/evidence_eval/evidence.{md,json}` (copy:
  `research/evidence/evidence_eval.md`). Evaluation only: the module reads the labels; the pipeline never
  imports it (`tests/test_eval_evidence.py::test_pipeline_code_never_imports_the_label_reading_evaluation`).
- data: stored results of `runs/experiments/kev_vs_facts/{champion,kev_facts,kev_general}`, dev split only
  (24 dialogues / 48 calls, clean + noisy), ASR whisper-large-v3-gsw-ct2 (the same transcripts for all three).
  Holdout dialogues get dropped if they are present (none were).
- population: **true flags** = predicted alarm|review and expected alarm|review. A true flag without any
  passage counts as a miss.
- hit = the passage's [start, end] overlaps the time span of at least one `Belege` turn. @1 = first passage
  in the order the officer sees them, @3 = any of the first three. `±2 s` = the snippet as played (2 s of
  context on each side). `chance@1` = probability that a passage of the same length, placed at a random
  point in the call, overlaps an evidence turn (the luck baseline; long passages hit by luck).
- CIs: percentile bootstrap (2000 replicates) over twin groups / dialogues, the same unit as `stats.py`.

## Alignment method (script turn -> ASR time)
The labelled scripts are Swiss German turns without timings. The ASR is Standard German with segment
times. A monotonic DP assigns every ASR segment to exactly one script turn, keeping script order and
allowing skipped turns. Score = fuzzy token overlap (rapidfuzz ratio >= 80 on content tokens: umlauts
folded, number words to digits including Swiss spellings, function words dropped, IDF-weighted so
names, amounts and keywords dominate) − 2 × |relative position in call − relative position in script|
+ 0.15 × speaker-role agreement − 0.3 per skipped turn. Weights were set once by reasoning and never fitted.
A turn's span runs from the first start to the last end of its segments.

**Automatic check:** each keyword finding whose keyword id appears in exactly one annotated turn
(`Keywordstellen`) is an anchor. 39 of 39 anchors were aligned to the annotated turn (champion
transcripts). This check is optimistic, because keywords are exactly the distinctive tokens the
similarity uses.

**Hand spot check (11 evidence turns; print any of them with `--show-alignments N`):** D02-K2 T004, D04-K1
T008, D05-K2 T006, D09-K1 T012, D10-K2 T003, C06-K4 T032, C13-K3 T006, C12-K4 T005, C18-K3 T016, C17-K4 T010
and C20-K4 T010. That covers clean and noisy recordings and all three levels, including 8-minute calls.
- 11 of 11 turns were assigned to the right ASR segments. The ASR text is clearly the same sentence in
  Standard German, and the neighbouring turns are also right.
- Boundary spill in 3 of 11: an ASR segment runs across the speaker change, so a turn picks up one word or
  a short phrase of its neighbour. In D02-K2, T005 ends with "Ja," from T006. In C20-K4, T010 ends with "Ich"
  from T011. In D05-K2, T006 starts with a misheard tail of T005. The time error is 1 s or less.
- The ASR text can be badly wrong without hurting the alignment. C13-K3 T006 contains a whisper
  hallucination ("Der Satz sagt ..." repeated), but it was still aligned correctly through the position
  prior and the other tokens.
- Estimated alignment error: well under 1 turn in 11 of 11 hand checks plus 39 of 39 anchors. Residual
  risk is about ±1 s at turn edges. That can turn a "touching" passage into a near miss, which is one
  reason the ±2 s column exists. 95% upper bound of the turn-level error rate (rule of three): about 6%
  counting all 50 checks, about 27% for the 11 hand checks alone.

## Result: evidence hit rate (dev, true flags)

| variant | true flags | no passage | hit@1 | hit@1 ±2 s | hit@3 | hit@all | chance@1 | median top passage | median miss @1 |
|---|---|---|---|---|---|---|---|---|---|
| **champion** (kev_vs_facts/champion) | 22 | 0 | **73% [45–91]** (16/22) | 77% [50–100] | **95% [86–100]** (21/22) | 100% | 24% | 12.4 s | 14.4 s (n=6) |
| kev_facts | 14 | **8** | 43% [12–75] (6/14) | 43% | 43% | 43% | 17% | 1.5 s | – |
| kev_general | 15 | 0 | 87% [60–100] (13/15) | 87% | 100% | 100% | **55%** | **48 s** | 111 s (n=2) |

Per family (champion): access 2/4 @1, 4/4 @3. disclosure 4/4. documentation 2/4 @1, 4/4 @3. splitting 2/2.
trade 6/8 @1, 7/8 @3. With n = 2–8 per family, the per-family CIs cover most of [0, 1]. Do not rank families.

How to read it:
- **champion**: 3× the luck baseline at @1 with short, listenable passages (median 12 s). The 6 misses
  @1 are not wrong places:
  - in 5 of them the evidence is passage 2 or 3, and the top passage is a related turn the annotation
    didn't list. In D04-K1 it is "das bleibe unter uns", in C17-K3/K4 "ob der Wert dazugehört", in C13-K3
    the turn just before T032 (1.7 s away, a hit with the ±2 s snippet context).
  - D04-K2 is the only real miss @3: the three passages are the confidentiality remark, the buy order and
    a later turn, not T008/T012 (16 s away).
  - Passages with equal scores are ordered by time, so a context turn can come before the act turn.
- **kev_facts** (Kev as facts backend) flags 8 correct calls **with nothing to listen to**. The Kev facts
  check returns no evidence segment ids, so fusion has no passage to cut. That is a traceability failure
  regardless of its accuracy. It needs evidence ids before it can be a submission candidate.
- **kev_general** hits more often, but its passages are 48 s long (8 segments), so luck alone gives 55%.
  Its hit rate is inflated by length, and it is not more precise.

## Result: «möglicherweise verhört» (dev)
Threshold 0.60 = bottom decile of all 2860 dev segment confidences, chosen without labels (p10 = 0.597).
Low-confidence segments: clean 8.2%, noisy 11.9%. The flag is off for backends without confidences;
the reference ASR reports 1.0 and is never flagged.

Champion, 25 flagged calls with passages: 7 of 59 shown passages are flagged, including 2 of 25 top
passages. Wrong decision = 3-class label differs from the expected one:

| top passage | low confidence | not low | share low |
|---|---|---|---|
| wrong decision | 0 | 6 | 0% |
| right decision | 2 | 17 | 11% |

Fisher p = 1.0. Using the top 3 passages: wrong 1/6 vs right 5/19, p = 1.0. False flags only: 0/3 vs 2/22.
**No association: wrong decisions are not more often based on low-confidence passages.** With 6 wrong
decisions, any effect smaller than very large is undetectable.

kev_general (17 flagged calls): wrong 5/6 vs right 4/11 low-confidence top passages, Fisher p = 0.13.
This is suggestive but not significant, and confounded: its 48 s passages hold 8 segments, so "lowest
segment below p10" is much more likely there (16 of 45 passages are flagged).

What the flag catches (champion, all 7 flagged passages, compared with the script by hand). 5 of 7
contain real recognition errors:
- D02-K2: "Ich möchte sie jetzt kaufen, **wurde gemeldet**" (0.30). The script says "vor der Meldung", so
  the incriminating phrase was misheard.
- D05-K2: "den TAN-**Card**" (0.58), script "die TAN grad".
- D09-K2: "**Zukunft**" (0.43), script "Herkunft". Also "Tante nicht aus dem Buch zu klären" (0.03), which
  is garbled.
- C12-K4: "allein **lernt da nichts**" (0.48), script "längt da nöd" ("is not enough").
- The other 2 are correct text: C06-K4 "was Sie wollen." (short fragment) and C14-K3.

So the flag is useful to the officer as "listen, don't read" rather than as a predictor of wrong
decisions. In D02-K2 the passage's reason quotes a misheard buy wish, and the badge tells the officer to
check the audio.

## Pitch line
"Our snippets are measured, not just shown. In 73% of correctly flagged calls the first passage we play
lands on the turn the case annotators marked as evidence (3× chance), and one of the first three does
95% of the time. Where speech recognition was unsure, we say 'möglicherweise verhört — bitte anhören'
instead of quoting a wrong transcript."

## Strongest counter-argument
- n = 22 true flags (24 dialogues). The 95% CI of hit@1 is 45–91%.
- `Belege` lists only 2–3 turns per dialogue. A passage on an equally relevant unlisted turn counts as a
  miss, so the rate is a lower bound on "useful".
- The alignment was checked on 50 points, not all of them.
- The champion's passages are short, which helps the chance baseline comparison. A variant with longer
  passages would score higher hit rates for the wrong reason, which is why chance@1 is reported.

## What would change our mind
- A larger labelled set (synthetic scripts with Belege, `data_synth/`), with audio, showing hit@1 below
  about 50%.
- A hand audit that finds top passages officers judge useless even though they overlap the evidence turn
  (possible with long multi-segment passages).
