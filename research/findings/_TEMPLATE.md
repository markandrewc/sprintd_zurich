# RQ<n>: <question>

**Answer in one sentence:** <...> (confidence: high / medium / low)

## Setup
- commit `<sha>`, config `<profile + overrides>`, experiment `experiments/<id>.yaml`
- split: dev folds <...> (n = <dialogues> dialogues / <calls> calls), holdout untouched
- models: ASR `<id>`, LLM `<served model id>`, views `<...>`

## Result
| option | flag F1 [95% CI] | FAR | miss rate | alarm F1 | review recall | s / call-min |
|---|---|---|---|---|---|---|

Difference best vs runner-up: <ΔF1> [95% CI <a, b>], McNemar p = <p>. <"real" or "no detectable difference at n=30">

## Calls that flip
| call | expected | <A> | <B> | decisive passage | why |
|---|---|---|---|---|---|

## Examples
<2-3 short passages with each option's reason>

## Recommendation
<...>

## Strongest counter-argument
<when would the other option be the better choice? what did we not test?>

## What would change our mind
<...>
