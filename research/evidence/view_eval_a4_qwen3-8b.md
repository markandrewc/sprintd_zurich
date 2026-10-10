# View eval a4_qwen3-8b

profile `gpu-views` llms.default.extra_body={chat_template_kwargs: {enable_thinking: false}} views.de_fused.translator.concurrency=1
WER/CER vs the Swiss German scripts (dialect spelling: inflated, compare views only). Brackets: 95% dialogue bootstrap CI.

| view | calls | kw recall | kw spots | false hits/call | CER gsw | WER gsw |
|---|---|---|---|---|---|---|
| de | 4 | 47.4% [21.7-80.0] | 9/19 | 0.25 | 34.1% | 66.1% |
| de_large | 4 | 73.7% [61.5-89.5] | 14/19 | 0.00 | 27.9% | 63.0% |
| de_vanilla | 4 | 68.4% [50.0-80.0] | 13/19 | 0.00 | 24.0% | 58.9% |
| de_fused | 4 | 79.0% [61.5-92.9] | 15/19 | 0.00 | 27.3% | 61.5% |

| call | de | de_large | de_vanilla | de_fused |
|---|---|---|---|---|
| Stufe1_D02-K2 | 1/7 (missed K01,K02,K03,K04,K05) false K09 | 5/7 (missed K04,K05) | 5/7 (missed K04,K05) | 5/7 (missed K04,K05) |
| Stufe1_D04-K2 | 4/6 (missed K02,K04) | 4/6 (missed K02,K03) | 5/6 (missed K02) | 5/6 (missed K02) |
| Stufe1_D05-K2 | 2/4 (missed K10) | 4/4 | 2/4 (missed K10) | 4/4 |
| Stufe1_D09-K2 | 2/2 | 1/2 (missed K06) | 1/2 (missed K06) | 1/2 (missed K06) |
