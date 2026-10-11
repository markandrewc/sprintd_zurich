# Sherlock Phones · Swiss

Officer UI in the International Typographic Style: one 12-column grid, Inter, black on white, one signal red.
SvelteKit (Svelte 5) and hand-written CSS, no component library.

## Run

1. API, from the **repo root** (stored audio paths are relative to it), against the run folder of the calls:

   ```bash
   uv run callguard api -c sherlock --set paths.runs_dir=<run folder> --port 8600
   # e.g. --set paths.runs_dir=runs/testset-NAME   -> reads runs/testset-NAME/sherlock/*/result.json
   ```

   `-c sherlock` is the default profile. `-c sherlock-qwen` (Qwen-only fallback) works too: there is no
   certainty cutoff, and the Rules / Facts pages say they are not available for that profile.

2. Frontend:

   ```bash
   cd frontends/swiss
   npm ci
   npm run dev -- --port 8605                     # http://localhost:8605
   # or a production build:
   npm run build && npm run preview -- --port 8605
   ```

The app talks to the API on `localhost:8600` (vite proxies `/api`, so audio range requests work);
`SHERLOCK_API=http://host:8600 npm run dev -- --port 8605` points the proxy elsewhere (also for `preview`).

- The header shows **Live · profile · run folder · N calls**, read from `/api/meta`, and which rule book decides
  (**Regelwerk: Sherlock (23 Regeln)** or **Demo: eigenes Regelwerk (N Regeln)**): check it before presenting.
- If the API is not reachable or fails, a full-width red **API nicht erreichbar** banner appears and nothing is
  faked: no sample data, no pretend saves. The app retries every 10 s (or click **Retry now**).
- Sample data only on purpose: `VITE_USE_FIXTURES=1 npm run dev -- --port 8605` answers from `static/fixtures/`
  (captured responses of an older run, not results of your calls). A black **Sample data** banner is shown on
  every page and every save is refused.

## Demo: from facts to rules

Shows that the AI readers only answer facts and the rules decide. Nothing is written to the rule book file.

1. Start the API with an empty rule book (or click **Empty rule book (demo)** on the Rules page):
   `uv run callguard api -c sherlock --set paths.runs_dir=<run folder> --port 8600 --start-empty-rules`.
   The header says **Demo: eigenes Regelwerk (0 Regeln)**, a black demo bar is shown on every page, and every
   call is «No alert» from the rules; each call page still shows both readers' fact answers.
2. Rules → **+ New rule**, e.g. Insider trading: *Own trading wish* is yes, *Justified with non-public inside
   information* is yes, *Information already public* is not yes → Alarm. The live box counts the matches; **Apply
   rule**. The Calls page then shows the new counts and, in the «Eigenes Regelwerk» panel, which calls each demo
   rule flags (pure re-decision of the stored fact answers; no model runs).
3. **Apply our rule book** (demo bar, or Rules page) switches to the full rule book: the header says
   **Regelwerk: Sherlock (23 Regeln)** and the dashboard is the normal production view.

Same fusion as production: keyword / pattern cues stay light cues. A call can be flagged without any rule only
when its fact readers did not answer (keywords alone then decide, as in production); the demo panel lists such
calls separately. Rule ids added in demo mode carry `demo_` (`trade.demo_alarm_1`).

## Pages

| | |
|---|---|
| 01 Calls | the three counts, certainty cutoff with the readers' probability spread, the call list |
| Call | player, synced transcript (Standard German / Swiss German view, display only), passages with time, category, reason and the reader that found them (Qwen pointing / Kev masking), decision, facts, review |
| 02 Rules | rule list (switch off, reorder, delete), undo; **New rule** opens the step builder with live "matches N of all calls"; **Empty rule book (demo)** / **Apply our rule book** |
| 03 Facts | facts per category with answer spread; add a fact (single-user mode: proposed and approved in one step; stored calls answer it after the next run) |
| 04 Keywords | edit words per category, see the effect, save (the keyword check is re-run on all stored transcripts at once) |
| Advanced | score threshold and reader combination (linked from Rules) |
| 05 How it works | the pipeline as a phase diagram plus step details |

Keyboard on the call page: Space play/pause, ← → 5 s, N / P next / previous passage, click a line to play from it.
When the recording is not on this machine the transcript still plays on a timer.

`npm run check` type-checks everything.
