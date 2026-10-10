# «Sicherheit der KI» (certainty c): dev only

Dev calls: 48 (dev folds, holdout excluded), fixed threshold 0.55, combination Einigkeit. Per fact and reader: ja if p(ja) >= c, nein if p(ja) <= 1 - c, else unklar. 95% CIs over twin groups in the JSON.

Criterion: max 3-class accuracy (dev, fixed threshold); ties -> lower false-alarm rate -> lower miss rate -> both readers on the band before Kev only -> lower c.

| setting | flagged / alarm / review | 3-class acc | FAR | miss | review recall | flag AUC |
|---|---|---|---|---|---|---|
| default (Qwen three-way, Kev 0.3-0.7) | 26 / 11 / 15 | 75% | 14% | 12% | 100% | 0.92 |
| both readers c=0.60 **(chosen)** | 27 / 12 / 15 | 77% | 14% | 8% | 100% | 0.93 |
| Kev only c=0.60 | 27 / 12 / 15 | 77% | 14% | 8% | 100% | 0.93 |
| both readers c=0.65 | 26 / 11 / 15 | 75% | 14% | 12% | 100% | 0.93 |
| Kev only c=0.65 | 27 / 12 / 15 | 77% | 14% | 8% | 100% | 0.93 |
| both readers c=0.70 | 27 / 11 / 16 | 73% | 18% | 12% | 100% | 0.91 |
| Kev only c=0.70 | 26 / 11 / 15 | 75% | 14% | 12% | 100% | 0.92 |
| both readers c=0.75 | 27 / 11 / 16 | 73% | 18% | 12% | 100% | 0.91 |
| Kev only c=0.75 | 26 / 11 / 15 | 75% | 14% | 12% | 100% | 0.92 |
| both readers c=0.80 | 27 / 11 / 16 | 73% | 18% | 12% | 100% | 0.91 |
| Kev only c=0.80 | 26 / 11 / 15 | 75% | 14% | 12% | 100% | 0.92 |
