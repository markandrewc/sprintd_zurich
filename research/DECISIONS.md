# Decision records

One record per decision. Status: proposed | accepted | superseded. Evidence links point to
`research/findings/`. Keep dissent: if a teammate disagrees, write their argument down.

## D1 ASR model and transcript view
- Status: proposed (default until RQ1/RQ2 answer it: Swiss German Whisper turbo int8, view `de`)
- Context / options / evidence / decision / consequences / dissent: <fill from RQ1, RQ2, RQ3>

## D2 Check set
- Status: proposed (keywords + patterns + llm_judge + geval)
- Evidence: RQ4, RQ5, RQ7

## D3 LLM
- Status: proposed (Qwen2.5-7B-Instruct-AWQ on 12 GB; bigger on event GPUs)
- Evidence: RQ6

## D4 Fusion and uncertainty policy
- Status: proposed (weighted fusion, threshold 0.55, review band 0.15, uncertainty escalation)
- Evidence: RQ9

## D5 Threshold for Sunday
- Status: proposed (CV-chosen on dev folds; one holdout check)
- Evidence: RQ9, leaderboard
