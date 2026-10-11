# Sherlock Phones HTTP API (contract v1)

One backend for every frontend. Start it:

```bash
uv sync                                               # fastapi + uvicorn are default dependencies
# from the repo root (stored audio paths are relative to it); -c sherlock is the default profile
uv run callguard api -c sherlock --set paths.runs_dir=runs/testset-NAME --port 8600   # reads runs/testset-NAME/sherlock/*/result.json
uv run callguard api -c sherlock-qwen --set paths.runs_dir=runs/testset-NAME          # Qwen-only fallback (no fact policy)
uv run callguard api -c sherlock --set paths.runs_dir=runs/testset-NAME --start-empty-rules   # demo: start with an empty, in-memory rule book
```

No model is ever loaded or called: every decision is re-computed from the stored per-call results
(`<runs_dir>/<profile>/<call_id>/result.json`), well under a second for all calls.

The API only serves what the pipeline produced from the .wav files in the run folder: it never reads expected
labels, reference scripts or stored research numbers (there is no quality / workload endpoint; accuracy is measured
offline after a run). Static copies of responses of an older run (dual-facts) are in [`api_fixtures/`](../api_fixtures/):
sample data for building a frontend without a server, never to be shown as results. Interactive schema: `http://localhost:8600/docs` (OpenAPI at `/openapi.json`).

## Conventions

| Thing | Rule |
|---|---|
| Base URL | `http://localhost:8600`, every path starts with `/api` |
| CORS | any `http://localhost:*` / `http://127.0.0.1:*` origin (extra origins: env `CALLGUARD_API_CORS`, comma-separated) |
| Format | JSON in and out, UTF-8; times in seconds (float) from the start of the recording |
| Call label | `alarm` \| `review` \| `no_alert` (`review` = a human should listen) |
| Fact value | `yes` \| `no` \| `unclear` |
| Who am I | body field `author` / `reviewer` / `approver` where the endpoint names one, else header `X-User`, else `"api"` |
| Per-client settings | header `X-Client: <any id>` (e.g. a random id per browser tab). Settings (`/api/settings`) are kept per client id in the API process; no header = the shared client `"default"`. Every read endpoint decides with the settings of its client. |
| Errors | `{"detail": "<English message>"}` with 400 (bad input, or the profile lacks the feature, e.g. /api/rules and /api/facts without a fact policy), 404 (unknown id or endpoint), 409 (four-eyes or state conflict), 422 (schema) |
| Clients and errors | A frontend must not fall back to sample data when the API is unreachable or answers 5xx: show an error (the swiss frontend shows a full-width "API nicht erreichbar" banner and never fakes a save). Sample data only when explicitly forced (swiss: `VITE_USE_FIXTURES=1`), clearly marked. |
| Language | Field names English. Officer strings the API builds are English (`reason`, `label`, `condition_text`, rule `text`, fact `label` / `question`, error `detail`), from the display-only map `config/display/labels_en.yaml`; a fact or rule missing there (e.g. created later) shows its rule-book text. Fields ending in `_de`, the fusion's `decision.reasons`, `families[].reason`, `passages[].reasons` and proposal `changes` are German (pipeline / rule-book wording): show them as detail, not as headline. |

Family ids: `numbers`, `trade`, `access`, `disclosure`, `documentation`, `splitting`, plus the virtual family
`cross` when a cross-family rule ("own rule over several categories") decided.

---

## GET /api/meta

What is loaded. Cheap; call once at start.

```json
{
  "app": "Sherlock Phones",
  "api_version": "1",
  "profile": "sherlock",
  "runs_dir": "runs/testset-NAME/sherlock",
  "code_version": "fd6e7b2",
  "models": {
    "asr": "whisper-large-v3-gsw-ct2",
    "asr_label": "Whisper large-v3, Swiss German fine-tune",
    "fact_readers": [
      {"id": "qwen", "label": "Qwen", "check": "facts", "model": "Qwen3.8-27B (3-bit)",
       "model_id": "qwen3.8-27b-ud-iq3_xxs", "type": "facts", "evidence": true, "evidence_method": "pointing"},
      {"id": "kev", "label": "Kev", "check": "facts_kev", "model": "Kev-4B", "model_id": "jaredpalmer/kev-4b",
       "type": "kev_facts", "evidence": true, "evidence_method": "mask", "mask_segments": 4}
    ],
    "swiss_german_view": "ctc_dialect:wav2vec2-gsw-swissdial-onnx",
    "swiss_german_view_label": "wav2vec2 XLS-R Swiss German dialect model (SwissDial)"
  },
  "counts": {"calls": 60, "alarm": 21, "review": 8, "no_alert": 31, "reviewed": 0},
  "families": [
    {"id": "trade", "label": "Insider trading", "label_de": "Insiderhandel (Information und Kaufwunsch)",
     "can_alarm": true, "legal_basis": "FinfraG Art. 142 ..."}
  ],
  "has_fact_policy": true,
  "load_errors": [],
  "rulebook": {"mode": "production", "name": "Sherlock", "rules": 23, "enabled": 23,
               "production": {"rules": 23, "enabled": 23}, "editable": true}
}
```

`rulebook`: which rule book decides right now, as `GET /api/rulebook` (see [Rule book: production or demo](#rule-book-production-or-demo)).

Reader models come from the stored results (whatever the run used, `model_id`), never hardcoded. `model` is the
readable name: the `model:` of `config/fact_policy.yaml` when it names the same model, else a readable form of
`model_id` (a stale display name never hides the model the run used). `evidence_method`: `pointing` (the reader
cites segments), `mask` / `anchor` (Kev finds passages itself), `null` (no passages). Without a fact policy
(`sherlock-qwen`) `has_fact_policy` is `false` and only the readers the profile runs are listed.

## GET /api/calls?status=&q=&family=&reviewed=

Inbox, riskiest first. All query params optional:
`status` = `alarm` | `review` | `no_alert` | `flagged` (alarm + review); `q` = case-insensitive substring of
id, reason or transcript; `family` = family id of the top family; `reviewed` = `true` | `false`.

```json
{
  "calls": [
    {
      "id": "Stufe1_D04-K1",
      "label": "alarm",
      "score": 0.83,
      "uncertainty": 0.12,
      "family": "access",
      "family_label": "Access credentials disclosed",
      "reason": "Valid access value spoken on the phone. Rule: access.alarm_1.",
      "rule_id": "access.alarm_1",
      "legal_basis": "Bankgeheimnis Art. 47 BankG ...",
      "passages": 2,
      "duration": 142.3,
      "reviewed": false,
      "stored_label": "alarm"
    }
  ],
  "counts": {"alarm": 21, "review": 8, "no_alert": 31},
  "total": 60
}
```

`stored_label` = the label the pipeline wrote; `label` = the label under the client's current settings.

## GET /api/calls/{id}

Everything the call page needs.

```json
{
  "id": "Stufe1_D04-K1",
  "duration": 142.3,
  "audio_url": "/api/calls/Stufe1_D04-K1/audio",
  "has_audio": true,
  "segments": [
    {"id": "S001", "start": 0.11, "end": 6.07, "speaker": "SPK0", "role": "advisor",
     "text": "Grüezi, hier ist ...", "confidence": 0.80}
  ],
  "swiss_german": {
    "description": "Swiss German, re-transcribed from the recording per segment (display only)",
    "model": "ctc_dialect:wav2vec2-gsw-swissdial-onnx",
    "segments": [{"id": "S001", "start": 0.11, "end": 6.07, "speaker": "SPK0", "role": "advisor", "text": "Grüezi ..."}]
  },
  "decision": {
    "label": "alarm", "score": 0.83, "uncertainty": 0.12, "threshold": 0.55, "review_floor": 0.4,
    "family": "access", "family_label": "Access credentials disclosed", "legal_basis": "...",
    "reason": "Valid access value spoken on the phone. Rule: access.alarm_1.",
    "reasons": ["...all fusion reasons..."],
    "rule": {
      "id": "access.alarm_1", "family": "access", "outcome": "alarm",
      "title": "...", "text": "Gültiger Zugangswert am Telefon ausgesprochen.",
      "condition": "spoken = yes and valid = yes",
      "condition_text": "\"Code/value spoken on the phone\" is yes AND \"Value is valid\" is yes",
      "condition_tree": {"op": "and", "items": [
        {"op": "fact", "fact": "spoken", "label": "Code/value spoken on the phone", "values": ["yes"]},
        {"op": "fact", "fact": "valid", "label": "Value is valid", "values": ["yes"]}]}
    },
    "stored_label": "alarm"
  },
  "families": [
    {"id": "access", "label": "Access credentials disclosed", "score": 0.83, "uncertainty": 0.12,
     "outcome": "alarm", "rule_id": "access.alarm_1", "rule_text": "A valid access value was spoken on the phone.",
     "reason": "(German fusion reason)"}
  ],
  "passages": [
    {"index": 0, "start": 31.2, "end": 44.8, "family": "access", "family_label": "Access credentials disclosed",
     "score": 0.83, "segment_ids": ["S008", "S009"], "reasons": ["facts: Fakt: ... (Regel: access.alarm_1)"],
     "text": "transcript of the passage",
     "found_by": ["Qwen", "Kev"],
     "sources": [
       {"source": "qwen", "source_label": "Qwen", "method": "pointing", "fact": "spoken", "rule": "access.alarm_1",
        "text": "Fakt: Code/Wert am Telefon vorgelesen = ja (0.97) - (German reason) (Regel: access.alarm_1)",
        "fact_label": "Code/value read out on the phone", "value": "yes", "p_yes": 0.97, "p_without": null,
        "why": "(German reason)"},
       {"source": "kev", "source_label": "Kev", "method": "mask", "fact": "spoken", "rule": "access.no_alert",
        "text": "Fakt: ... - ohne diese Stelle sinkt p(ja) von 0.91 auf 0.42 (Regel: access.no_alert)",
        "fact_label": "Code/value read out on the phone", "value": "yes", "p_yes": 0.91, "p_without": 0.42,
        "why": null},
       {"source": "keyword", "source_label": "Keyword", "method": null, "fact": null, "rule": null, "text": "...",
        "phrase": "Finanzabteilung", "keyword_id": "K02"}
     ]}
  ],
  "facts": {
    "access": [
      {
        "id": "spoken", "label": "Code/value read out on the phone", "label_de": "Code/Wert am Telefon vorgelesen",
        "role": "act",
        "question": "Does the advisor ... (English question)",
        "resolved": "yes", "agree": true, "combination": "agree",
        "readers": {
          "qwen": {"p_yes": 0.91, "p_no": 0.05, "p_unknown": 0.04, "value": "yes"},
          "kev": {"p_yes": 0.88, "value": "yes"}
        },
        "evidence_segment_ids": ["S008"],
        "evidence_reason": "(German, reader A's one-line justification; optional)"
      }
    ]
  },
  "keyword_hits": [
    {"kind": "keyword", "family": "numbers", "keyword_id": "K09", "phrase": "Kreditkartennummer",
     "matched_text": "Kreditkartennummer", "negated": false, "segment_ids": ["S012"], "start": 40.1, "end": 44.0,
     "score": 0.5, "reason": "(German)"}
  ],
  "reviews": []
}
```

* `swiss_german` is `null` when the run has no Swiss German display view. Its segment ids and times are those
  of `segments`, so both play in sync with the audio.
* `facts` holds every family the readers answered; `p_unknown` is Qwen's p(unclear). Kev only gives p(yes).
  A reader that did not answer is `null`. `resolved` is what the rules saw under the client's settings.
* `keyword_hits` has `kind` `keyword` (keyword list) or `pattern` (digit sequences, codes; `keyword_id` null).
  `negated: true` = the phrase was negated ("not my card number") and does not count.
* `reviews` = the stored officer reviews of this call (oldest first):
  `[{"id", "ts", "reviewer", "verdict", "agree", "comment", "reasons": [codes], "label_seen", "items"}]`.
* `decision.rule` is `null` when no rule decided the top family (e.g. only keywords scored).
* `passages[].sources`: one entry per reason (same order as `reasons`, German text without the `check:` prefix):
  who found the passage (`source` = reader id, `keyword`, `pattern`, or `note` for fusion notes such as a
  shortened passage) and how (`method`: `pointing` = the reader cited the segments, `mask` = Kev: the window whose
  removal drops p(yes) most, `anchor`). `found_by` = the distinct `source_label`s. Both readers' passages are kept.
  Display fields: fact readers add `fact_label` (English), `value` and `p_yes` (what THIS reader answered), and
  either `p_without` (`mask`: p(yes) with this window removed) or `why` (`pointing`: the reader's own sentence,
  German); keywords add `phrase` / `keyword_id`, patterns `phrase` (e.g. "6-digit number"). `rule` is the rule
  that this one reader's answers matched when it searched for evidence, NOT the rule that decided the call
  (that is `decision.rule`): on a flagged call it is often the category's `no_alert` rule, so do not show it as
  the reason of a passage.
* `decision.rule.condition_tree` (also on every rule of `/api/rules`): the condition as a tree, so a UI can show
  its grouping: `{"op": "and"|"or", "items": [...]}`, `{"op": "not", "item": ...}`, `{"op": "true"}` or a fact
  test `{"op": "fact", "fact", "label", "values"}` (holds when the fact's value is one of `values`; `!=` and
  `in [...]` are folded into `values`). `null` if the condition does not parse.
* `keyword_hits` and the keyword findings the decision uses come from the CURRENT keyword list (see Keywords).

## GET /api/calls/{id}/audio

The recording (`audio/wav`, or whatever format is stored). Supports HTTP Range requests (206), so
`<audio src>` seeking works. 404 if the file is not on this machine.

## GET /api/settings · PUT /api/settings

The three officer knobs. Per client (`X-Client`).

```json
{
  "certainty": 0.6,
  "combination": "agree",
  "on_split": "rules",
  "threshold": 0.55,
  "review_band": 0.15,
  "defaults": {"certainty": 0.6, "combination": "agree", "threshold": 0.55, "on_split": "rules"},
  "options": {
    "certainty": {"min": 0.5, "max": 1.0, "step": 0.01,
                  "help": "A reader's answer counts as yes if p(yes) >= c, as no if p(yes) <= 1 - c, else unclear."},
    "combination": [
      {"id": "agree", "label": "Agreement", "help": "Both yes -> yes, both no -> no, otherwise unclear."},
      {"id": "a_checked", "label": "Qwen, Kev as check", "help": "..."},
      {"id": "only_a", "label": "Qwen only", "help": "..."},
      {"id": "only_b", "label": "Kev only", "help": "..."}
    ],
    "on_split": [
      {"id": "rules", "label": "Rule book decides", "help": "The combined facts go through the rules as usual (default)."},
      {"id": "review", "label": "Review", "help": "If Qwen alone and Kev alone would reach different verdicts, ..."},
      {"id": "alarm", "label": "Alarm", "help": "..."}
    ],
    "threshold": {"min": 0.05, "max": 0.95, "step": 0.01}
  }
}
```

PUT body: any subset of `{"certainty": 0.7, "combination": "a_checked", "on_split": "review", "threshold": 0.5}`,
or `{"reset": true}`. `on_split` ("When Qwen and Kev disagree" on the Advanced page): each reader's own fact values
go through the same rules; if the two verdicts differ, the family becomes at least Prüfen (`review`) or Alarm
(`alarm`); `rules` (the default, `config/fact_policy.yaml`) adds nothing. Re-decides every call immediately and returns:

```json
{
  "settings": {"certainty": 0.7, "combination": "agree", "threshold": 0.55, "...": "as GET"},
  "counts": {"alarm": 18, "review": 14, "no_alert": 28},
  "changed": [{"id": "Stufe1_D07-K2", "before": "alarm", "after": "review"}],
  "elapsed_ms": 140
}
```

`changed` is relative to the client's previous settings.

Without a fact policy (profile `sherlock-qwen`, one reader): `certainty`, `combination` and `on_split` (and their
defaults) are `null`, `options.combination` and `options.on_split` are empty, and PUT of either is a 400; only `threshold` can be moved. `/api/summary`
then has `certainty` and `band` `null`.

## GET /api/summary

For the dashboard charts (client's settings).

```json
{
  "total": 60,
  "counts": {"alarm": 21, "review": 8, "no_alert": 31},
  "score_histogram": {"edges": [0.0, 0.05, "...", 1.0], "alarm": [0, "..."], "review": ["..."], "no_alert": ["..."]},
  "fact_p_yes_histogram": {"edges": [0.0, 0.05, "...", 1.0], "qwen": [120, "..."], "kev": [98, "..."]},
  "certainty": 0.6,
  "band": [0.4, 0.6],
  "facts": {"answered": 1680, "agree": 1500, "unclear": 120},
  "by_family": {"access": {"alarm": 5, "review": 2}}
}
```

Histograms: 20 equal bins on [0, 1] (`edges` has 21 numbers). `fact_p_yes_histogram` counts every stored
(call, fact) answer of each reader; draw the certainty band `[1 - c, c]` over it.

---

## Rules (instant, with undo)

Rules are pure logic over the fact values. A change is live at once (a new rule-book version is written and
audit-logged); `POST /api/rules/undo` reverts the last instant change. Facts themselves need four-eyes approval
(see Facts).

### GET /api/rules

```json
{
  "version": 7,
  "can_undo": true,
  "rulebook": {"mode": "production", "name": "Sherlock", "rules": 23, "enabled": 23, "...": "as GET /api/rulebook"},
  "families": [
    {
      "id": "access", "label": "Access credentials disclosed", "label_de": "Zugangsinformation preisgegeben",
      "legal_basis": "...",
      "facts": [{"id": "spoken", "label": "Code/Wert am Telefon vorgelesen"}],
      "rules": [
        {"id": "access.alarm_1", "family": "access", "outcome": "alarm", "title": "", "text": "...",
         "condition": "spoken = yes and valid = yes", "condition_text": "...", "enabled": true,
         "position": 0, "hits": 5, "hit_calls": ["Stufe1_D04-K1"]}
      ]
    }
  ],
  "cross_rules": [
    {"id": "eigene.alarm_1", "family": "cross", "outcome": "alarm", "title": "Code + third party",
     "text": "...", "condition": "access.spoken = yes and disclosure.third_party = yes",
     "condition_text": "...", "report_as": "access", "enabled": true, "position": 0, "hits": 1, "hit_calls": ["..."]}
  ]
}
```

First enabled matching rule decides a family; `hits` = calls where this rule decided its family under the
client's settings.

### POST /api/rules · POST /api/rules/preview

Same body. Facts from one family make a family rule; facts from several families make a cross rule.

```json
{
  "facts": [
    {"family": "access", "fact": "spoken", "value": "yes", "negate": false},
    {"family": "disclosure", "fact": "third_party", "value": "yes", "negate": false}
  ],
  "join": "and",
  "outcome": "alarm",
  "title": "Code given to a third party",
  "description": "Raise an alarm when a code is spoken and the caller is not the customer.",
  "report_as": "access",
  "author": "Anna"
}
```

`join`: `and` | `or`. `outcome`: `alarm` | `review` | `no_alert`. `negate: true` means "is not".
`report_as` only for cross rules (family id the alarm is reported under; optional).

Preview (nothing saved) returns:

```json
{
  "rule": {"id": "eigene.alarm_1", "family": "cross", "outcome": "alarm", "condition": "...", "condition_text": "..."},
  "hits": ["Stufe1_D04-K1"],
  "effect": {"changed": [{"id": "Stufe1_D04-K1", "before": "review", "after": "alarm"}],
             "net": {"alarm": 1, "review": -1, "no_alert": 0}, "summary": "changes 1 of 60 calls: +1 alarm, -1 review"}
}
```

POST returns 201 with the same plus `"version": 8`.

### PATCH /api/rules/{rule_id}

`{"enabled": false, "author": "Anna"}` or `{"move": -1}` (up one place) / `{"move": 1}` (down). Returns
`{"rule": {...}, "version": 9, "effect": {...}}`.

### DELETE /api/rules/{rule_id}?author=Anna

Returns `{"deleted": "access.alarm_1", "version": 10, "effect": {...}}`.

### POST /api/rules/undo

Body `{"author": "Anna"}`. Returns `{"version": 11, "reverted": 10, "effect": {...}}`; 409 if the last change
was not an instant rule change.

### Rule book: production or demo

For a live demo the API can decide with an EMPTY rule book that is kept in the API process only: every call is
re-decided from its stored fact answers with no rule (the readers' facts stay on every call page), a rule added
on the Rules page decides at once, and switching back gives exactly the production view. The rule book file
(`config/policy_table.yaml`) and its versions are never written in demo mode; there is no audit entry for demo
rules. The demo book is one per API process (shared by all clients); facts, questions and legal bases are always
the live ones (an approved fact is in the demo book too). Decisions use exactly the production fusion (fact
policy, rules, keywords and patterns as light cues, review band): with no rule, every category scores 0 from the
facts, and keyword / pattern cues alone cannot reach the review band while the readers answered (weights 0.15 /
0.1 against the facts' 1.0). A call whose fact readers both failed is decided by keywords / patterns alone (as in
production) and can still be flagged: such a row has `rule_id: null`.

`GET /api/rulebook`:

```json
{"mode": "demo", "name": "Sherlock", "rules": 1, "enabled": 1, "can_undo": true,
 "production": {"rules": 23, "enabled": 23}, "editable": true}
```

`PUT /api/rulebook` with `{"mode": "demo"}` starts an EMPTY demo book (always empty, also when one was active);
`{"mode": "production"}` goes back to the full rule book (the demo book is dropped). 400 for another mode or a
profile without a fact policy. Returns `{"rulebook": {...as GET...}, "counts": {...}, "effect": {...}}` (labels
before vs after the switch at the client's settings). Start the API in demo mode with
`callguard api ... --start-empty-rules`; the default is production.

In demo mode `/api/rules`, `/api/rules/preview`, `POST /api/rules`, `PATCH`, `DELETE` and `/api/rules/undo` work on
the demo book with the same bodies and answers, except: `version` is `null`, new rule ids carry `demo_`
(`trade.demo_alarm_1`, `eigene.demo_alarm_1`), and undo steps back through the demo changes (409 when there is
none). `/api/rules` also carries `rulebook`. Every read endpoint (calls, call detail, summary, meta, facts'
`used_in_rules`, keyword preview / effect) decides with the active book.

---

## Facts (four-eyes)

### GET /api/facts

```json
{
  "families": [
    {
      "id": "trade", "label": "Insider trading", "label_de": "...",
      "facts": [
        {"id": "wish", "label": "Eigener Handelswunsch geäussert", "role": "act",
         "question": "Does a person in the call ... (English)", "question_de": "Äussert eine Person ...",
         "used_in_rules": 3,
         "answers": {"calls": 60, "yes": 12, "no": 44, "unclear": 4, "agree": 55}}
      ]
    }
  ],
  "readers": [
    {"id": "qwen", "label": "Qwen", "model": "Qwen3.8-27B (3-bit)", "mode": "band", "band": [0.4, 0.6]},
    {"id": "kev", "label": "Kev", "model": "jaredpalmer/kev-4b", "mode": "band", "band": [0.4, 0.6]}
  ],
  "combination": "agree",
  "active_version": 7,
  "proposals": [
    {"id": 8, "status": "draft", "author": "Anna", "created": "2026-10-10T20:01:00+02:00",
     "comment": "New fact: ...", "changes": ["..."]}
  ]
}
```

`answers` = how the stored answers resolve under the client's settings. `roles`: `act` (the misconduct),
`context` (makes it incriminating), `exculpatory` (makes it harmless), `authorization`.

### POST /api/facts/proposals

New or changed fact (or removal) as a draft for a second person to approve:

```json
{"family": "trade", "fact_id": null, "label": "Mentions a takeover", "role": "context",
 "question": "Does anyone mention an upcoming takeover?", "question_de": "",
 "author": "Anna", "comment": "needed for a new rule", "delete": false}
```

`fact_id: null` = new fact (id derived from the label). With `delete: true` only `family`, `fact_id`, `author`
matter. Returns 201 `{"proposal": {...as in GET...}}`.

### POST /api/facts/proposals/{id}/approve

`{"approver": "Ben", "note": ""}`. **409** if the approver is the author (four-eyes) or the draft is no longer
open. Returns `{"proposal": {...,"status": "approved","approver": "Ben"}, "active_version": 8}`. A new or
changed question only takes effect for calls once the AI readers answer it again (next pipeline run); stored
calls keep their stored answers.

### POST /api/facts/proposals/{id}/reject

`{"user": "Ben", "note": "duplicate"}`. Returns `{"proposal": {...,"status": "rejected"}}`.

---

## Keywords

### GET /api/keywords

```json
{
  "families": [
    {"id": "numbers", "label": "Card and reference numbers", "keywords": [
      {"id": "K09", "label": "Kreditkartennummer", "enabled": true, "case_sensitive": false,
       "de": ["Kreditkartennummer"], "gsw": ["Kreditchartenummere"], "en": ["credit card number"],
       "harmless": ["Notes when a hit is NOT suspicious (German, free text)"], "hits": 7}
    ]}
  ]
}
```

### POST /api/keywords/preview · PUT /api/keywords

Body: `{"family": "numbers", "keywords": [ ...full list of that family, same shape as GET... ], "author": "Anna"}`.
`harmless` is a list of free-text notes (empty list = none); PUT / preview also accept a plain string.
A keyword without `id` is new (gets the next free `Kxx`); a keyword without any `de` / `gsw` phrase is dropped.
The keyword check re-runs in memory on every stored transcript (milliseconds). Preview returns, without saving:

```json
{"effect": {"changed": [{"id": "...", "before": "no_alert", "after": "review"}], "net": {"alarm": 0, "review": 1, "no_alert": -1},
            "summary": "changes 1 of 60 calls: +1 review, -1 no alert"},
 "hits": {"before": 4, "after": 6, "per_keyword": {"K09": 7, "K10": 2}},
 "keywords": [ "...the family's list as it would be saved (ids assigned)..." ]}
```

`hits.before` / `hits.after` = keyword hits of this family over all calls; `hits.per_keyword` = hits per keyword id
with the edited list (what the Hits column would show). PUT saves (backup + audit log) and applies at once: the API
re-runs the keyword check on every stored transcript whenever the keyword file changes, so `/api/keywords` hits,
`keyword_hits`, passages and labels change immediately. PUT returns the real `effect` (labels before vs after the
save, at the client's settings), `hits` with `per_keyword` after the save, the saved `keywords`, `"saved": true`
and `"applied"`.

---

## Review (training data)

### POST /api/calls/{id}/review

```json
{
  "verdict": "violation",
  "agree": true,
  "reasons": ["context_harmless"],
  "fact_corrections": {"access.valid": "no"},
  "passage_ok": {"0": true, "1": false},
  "comment": "code was an expired example",
  "reviewer": "Anna"
}
```

`verdict`: `violation` | `no_violation` | `unclear`. `agree`: does the officer agree with the label shown.
`reasons`: any of `context_harmless`, `transcript_error`, `rule_too_strict`, `rule_too_lax`, `missing_info`,
`other_family` (fact and passage reasons are derived from `fact_corrections` / `passage_ok`).
`fact_corrections`: `"family.fact" -> yes|no|unclear` (the officer's value). `passage_ok`: passage index ->
true (applies) / false (does not apply).

Returns 201:

```json
{"id": "c1b1b814cd14", "items": 3, "label_seen": "alarm", "data_points": 12,
 "counts": {"call": 12, "fact": 4, "passage": 5}}
```

`id` = the stored data point (one form submission = one batch); `items` = labels it produced (call + one per
fact correction / passage judgement); `data_points` / `counts` = the whole learning store.

Stored in the learning store (`<runs_dir>/feedback.jsonl`, schema 2, with provenance), audit-logged. The call
then shows `reviewed: true`.

---

## Explanation

There is no `/api/quality` or `/api/workload` (404): they looked up expected labels of the case data by call id
(= wav file name), which must never happen for an arbitrary run folder. Accuracy is scored offline after a run.

### GET /api/how-it-works

Pipeline steps for a diagram, in run order, built from the profile's config and the models in the stored results.
`phase`: `Listen` | `Read` | `Decide` | `Display` (after the decision, display only) | `Person`. Steps that the
profile does not have are left out (no `combine` without a fact policy, no `swiss_german` without the view).

```json
{"steps": [
  {"id": "audio", "phase": "Listen", "title": "Recording", "model": null, "description": "..."},
  {"id": "asr", "phase": "Listen", "title": "Speech to text", "model": "Whisper large-v3, Swiss German fine-tune", "description": "..."},
  {"id": "diarization", "phase": "Listen", "title": "Who speaks", "model": "sherpa-onnx speaker separation, CPU + Qwen3.8-27B (3-bit)", "description": "... roles by Qwen3.8-27B ..."},
  {"id": "keywords", "phase": "Read", "title": "Keywords and patterns", "model": null, "description": "..."},
  {"id": "facts", "phase": "Read", "title": "Two AI readers answer yes/no facts", "model": "Qwen3.8-27B (3-bit) + Kev-4B", "description": "... Qwen points to the segments ...; Kev ... finds the passages itself by masking ..."},
  {"id": "combine", "phase": "Decide", "title": "Combine the readers", "model": null, "description": "..."},
  {"id": "rules", "phase": "Decide", "title": "Rules decide", "model": null, "description": "..."},
  {"id": "fusion", "phase": "Decide", "title": "Score and label", "model": null, "description": "..."},
  {"id": "swiss_german", "phase": "Display", "title": "Swiss German view (display only)", "model": "wav2vec2 XLS-R Swiss German dialect model (SwissDial)", "description": "..."},
  {"id": "review", "phase": "Person", "title": "Officer review", "model": null, "description": "..."}
]}
```

## Fixtures

`api_fixtures/` holds responses captured from an older dual-facts run: sample data only (regenerate with
`uv run python scripts/api_fixtures.py -c <profile>`; it runs on a sandbox copy, so the write examples never touch
`config/` or `runs/`):

| File | Request |
|---|---|
| `meta.json` | GET /api/meta |
| `calls.json`, `calls_flagged.json` | GET /api/calls, `?status=flagged` |
| `call_detail.json` (= `call_detail_alarm.json`), `call_detail_review.json`, `call_detail_no_alert.json` | GET /api/calls/{id} |
| `settings.json`, `settings_put.json` | GET /api/settings, PUT `{"certainty": 0.7}` |
| `summary.json` | GET /api/summary |
| `rules.json` | GET /api/rules |
| `rules_preview.json`, `rules_preview_cross.json` | POST /api/rules/preview (one family; several families) |
| `rules_create.json`, `rules_patch.json`, `rules_undo.json` | POST /api/rules, PATCH `{"enabled": false}`, POST /api/rules/undo |
| (none) | GET / PUT /api/rulebook: not captured (the fixtures predate it; the swiss frontend reads `rulebook` from meta when present) |
| `facts.json` | GET /api/facts |
| `facts_proposal.json`, `facts_approve_409.json`, `facts_approve.json` | POST proposal, approve by the author (409), approve by a second person |
| `keywords.json`, `keywords_preview.json` | GET /api/keywords, POST /api/keywords/preview |
| `review.json` | POST /api/calls/{id}/review |
| `how_it_works.json` | GET /api/how-it-works |

The audio is not in the fixtures; any short wav works as a stand-in.
