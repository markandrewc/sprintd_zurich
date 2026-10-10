# Fine-tuning from officer labels: the shadow-evaluation contract

Status: **roadmap, nothing here has been run.** Our assessment (`docs/research/finetuning_assessment.md`):
no fine-tune before the submission. With 48 dev calls (18 independent units) no gain would be measurable,
the Kev upstream needs about 1,000 records for a measurable +5 points, and the ORACLE run shows the ASR
is not the bottleneck. What exists today: the labels are captured with provenance, exported in the
trainers' formats with split hygiene enforced, and the threshold can be re-fitted with a four-eyes
approval (`docs/LEARNING.md`).

## Für den Pitch (Deutsch)

> Die Feedbacks der Prüferinnen werden zu Trainingsdaten — aber ein neues Modell geht erst live, wenn es
> auf ungesehenen, geprüften Anrufen nachweislich besser ist.

Jede Beurteilung (Urteil zum Anruf, Passage trifft zu / nicht zu, Fakt stimmt / stimmt nicht, übersehene
Kategorie) wird mit Herkunft gespeichert: welche Konfiguration, welches Regelwerk, welches Modell, welches
Transkript. Daraus entsteht ein Trainingsdatensatz für den Faktenleser. Ein nachtrainiertes Modell läuft
zuerst im Schatten mit: es bewertet Anrufe, die es nie gesehen hat, entscheidet aber nichts. Live geht es
nur, wenn es dort messbar besser ist (Konfidenzintervall der Differenz schliesst 0 aus), nicht mehr
Fehlalarme erzeugt und eine zweite Person die Umstellung freigibt. Der Weg zurück auf das alte Modell
bleibt offen und wird protokolliert.

## The contract (what must be true before a retrained model is activated)

1. **Data.** Training records come only from `callguard learn export` files named `*.train.jsonl`
   (`use: train`): real officer labels on *new* calls. Never case calls (dev and holdout are
   evaluation-only), never simulated demo feedback. The export re-checks this and refuses to write
   otherwise (`callguard.learning.hygiene`).
2. **Unseen test set.** The shadow test set is `*.shadow_test.jsonl` (`use: shadow_test`): about 20 % of the
   new conversations, chosen by a stable hash of the twin unit, so the clean / noisy recordings of one
   conversation are on the same side and a call never changes sides when more labels arrive. The
   candidate never sees these calls during training, prompt work or threshold choice.
3. **Minimum size.** At least ~1,000 trainable fact labels (Kev upstream evidence) and at least 30 shadow
   calls per family that the change targets; below that the run is not started (`Lernen` page readiness).
4. **Shadow run.** Current and candidate model score the same shadow calls with the same policy table,
   fusion and threshold (`callguard experiment` with two variants; the candidate is a profile that points
   `checks.facts.llm` at the adapter).
5. **Decision rule (pre-registered, write it into `research/` before the run):**
   * paired bootstrap over twin units (`callguard.stats.paired_bootstrap`, 2,000 replicates): the
     candidate's flag F1 (or fact accuracy against the officers' answers) is better and the 95 % CI of the
     difference **excludes 0**;
   * **no rise in false alarms**: the false-alarm-rate difference is <= 0 at the point estimate and its CI
     does not lie above 0;
   * no family gets worse with a CI that excludes 0;
   * case dev calls are reported as a second, informational benchmark (never a reason to activate).
6. **Activation** is a config change proposed by one person and approved by another (four-eyes, audit
   log, rollback to the previous model id), like threshold proposals (`callguard learn approve`).
7. **Provenance.** Every later result records the adapter id / hash (`provenance.models`), so labels
   given under the new model stay distinguishable from labels given under the old one.

## Skeleton scripts (not executed; GPU host only)

| script | trains | input |
|---|---|---|
| `kev_lora.sh` | Kev-4B LoRA (pointer head kept), `kev.train --init_from jaredpalmer/kev-4b` | `kev_noul.train.jsonl` (or `kev_choice`) |
| `qwen_lora.sh` | QLoRA on the facts model (Qwen2.5-7B-Instruct), chat SFT on the facts prompt | `qwen_sft.train.jsonl` |

Both scripts refuse to start when the export's manifest shows fewer trainable labels than the minimum,
and both end by printing the shadow-evaluation command instead of activating anything.

## Formats (written by `callguard learn export`)

* **Kev noul** (one line per call, all labelled facts of the call as questions):
  `{"state": "<transcript as the facts check renders it>", "questions": {"access.current": {"type": "noul",
  "instructions": "Topic: Zugangsinformation preisgegeben [access]\n<question>", "label": true}}, "meta": {...}}`.
  The instruction string is the one `callguard.llm.kev.KevLLM` sends at serving time, so train = serve.
  "unclear" answers are left out (noul has no third value).
* **Kev choice**: same, `"type": "choice", "criteria": {"yes": ..., "no": ..., "unknown": ...}, "label": "unknown"`.
  Kev's internal record (`kev/model.py: encode`) is `{"state", "questions": [{"instr", "options", "label": idx}]}`;
  `kev.train` builds it from the request form (`to_record`).
* **Qwen SFT**: `{"messages": [system, user, {"role": "assistant", "content": "yes|no|unknown"}], "meta": {...}}`,
  the exact `fact_prompts.fact_messages` prompt of the facts check (prompt version in `meta`).
