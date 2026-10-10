# Experiment `asr_models`

Detection quality per ASR model (Swiss German fine-tunes vs vanilla Whisper)

RQ: RQ2, RQ8 · base profile `gpu-12gb` · split **dev** · baseline `turbo_gsw_int8` · commit 2cc04e7f41 (dirty) · 2026-10-10T02:13:57+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| turbo_gsw_int8 | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 |  |
| large_v3_gsw | 0.66 [0.48, 0.85] | 0.78 [0.59, 0.96] | 26/22 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| turbo_gsw_int8 | 48 | 0.67 [0.46, 0.83] | 64% | 69% | 45% [18%, 72%] | 31% [9%, 54%] | 0.55 | 67% | 50% | 0.62 [0.47, 0.78] |  |
| large_v3_gsw | 48 | 0.68 [0.51, 0.82] | 55% | 88% | 86% [70%, 100%] | 12% [0%, 30%] | 0.50 | 67% | 35% | 0.51 [0.41, 0.60] |  |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| turbo_gsw_int8 | 48 | 0.67 [0.45, 0.84] | 68% | 65% | 36% [10%, 62%] | 35% [12%, 57%] | 0.10 | 67% | 40% | 0.65 [0.48, 0.81] |  |
| large_v3_gsw | 48 | 0.72 [0.56, 0.84] | 70% | 73% | 36% [17%, 55%] | 27% [11%, 46%] | 0.00 | 50% | 35% | 0.68 [0.57, 0.80] |  |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| turbo_gsw_int8 | 36% (!) | 1/4 | 36% | **no** | cv_far @ 2cc04e7f41 cfg c8c60e398c2fe3c8 (config changed since run), far_floor @ 2cc04e7f41 cfg c8c60e398c2fe3c8 (config changed since run) |
| large_v3_gsw | 36% (!) | 0/4 | 36% | **no** | cv_far @ 2cc04e7f41 cfg c7fc35285e55c98e (config changed since run), far_floor @ 2cc04e7f41 cfg c7fc35285e55c98e (config changed since run) |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| turbo_gsw_int8 | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.63 | 83% | 40% | 0.51 [0.45, 0.59] |  |
| large_v3_gsw | 48 | 0.72 [0.57, 0.85] | 57% | 100% | 91% [75%, 100%] | 0% [0%, 0%] | 0.55 | 67% | 38% | 0.55 [0.50, 0.62] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| turbo_gsw_int8 | 0.55 | 0.45 | 0.70, 0.85, 0.65, 0.90 (FAR20: 0.95!, 0.95, 1.00!, 0.95!) | 0.2 | asr 0.1, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | a72e6a6f84 |
| large_v3_gsw | 0.55 | 0.65 | 0.65, 0.55, 0.90, 0.65 (FAR20: 1.00!, 1.00!, 1.00!, 1.00!) | 61.2 | asr 16.2, diarize 19.1, checks 25.9 | 25.9 | 10.0 | 0 | 0 | a72e6a6f84 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| turbo_gsw_int8 | 0.86 / 25% / 10% | 0.43 / 57% / 50% | 0.80 / - / 33% | 0.69 / 36% / 31% | 0.64 / 55% / 31% |
| large_v3_gsw | 0.77 / 75% / 0% | 0.56 / 93% / 10% | 0.80 / - / 33% | 0.71 / 82% / 8% | 0.65 / 91% / 15% |

## `large_v3_gsw` vs `turbo_gsw_int8`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = large_v3_gsw - turbo_gsw_int8

| metric | turbo_gsw_int8 | large_v3_gsw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.66 | -0.021 | [-0.159, +0.111] | no detectable difference |
| alarm AUC | 0.77 | 0.78 | +0.016 | [-0.122, +0.145] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = large_v3_gsw - turbo_gsw_int8

| metric | turbo_gsw_int8 | large_v3_gsw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.68 | +0.010 | [-0.174, +0.176] | no detectable difference |
| alarm_f1 | 0.55 | 0.50 | -0.052 | [-0.287, +0.222] | no detectable difference |
| false_alarm_rate | 45% | 86% | +41pp | [+15pp, +71pp] | **real**: turbo_gsw_int8 better |
| miss_rate | 31% | 12% | -19pp | [-50pp, +12pp] | no detectable difference |
| accuracy | 50% | 35% | -15pp | [-35pp, +7pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.51 | -0.108 | [-0.300, +0.059] | no detectable difference |

McNemar exact (calls): flag correct only-turbo_gsw_int8 12 vs only-large_v3_gsw 8, p=0.5034; 3-class only-turbo_gsw_int8 12 vs only-large_v3_gsw 5, p=0.1435.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = large_v3_gsw - turbo_gsw_int8

| metric | turbo_gsw_int8 | large_v3_gsw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.72 | +0.050 | [-0.118, +0.217] | no detectable difference |
| alarm_f1 | 0.10 | 0.00 | -0.095 | [-0.286, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 36% | +0pp | [-23pp, +25pp] | no detectable difference |
| miss_rate | 35% | 27% | -8pp | [-32pp, +19pp] | no detectable difference |
| accuracy | 40% | 35% | -4pp | [-19pp, +10pp] | no detectable difference |
| review_recall | 67% | 50% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.68 | +0.038 | [-0.118, +0.186] | no detectable difference |

McNemar exact (calls): flag correct only-turbo_gsw_int8 9 vs only-large_v3_gsw 11, p=0.8238; 3-class only-turbo_gsw_int8 7 vs only-large_v3_gsw 5, p=0.7744.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = large_v3_gsw - turbo_gsw_int8

| metric | turbo_gsw_int8 | large_v3_gsw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.72 | +0.036 | [+0.000, +0.084] | no detectable difference |
| alarm_f1 | 0.63 | 0.55 | -0.086 | [-0.291, +0.165] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [-14pp, +13pp] | no detectable difference |
| miss_rate | 8% | 0% | -8pp | [-18pp, +0pp] | no detectable difference |
| accuracy | 40% | 38% | -2pp | [-19pp, +13pp] | no detectable difference |
| review_recall | 83% | 67% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.55 | +0.038 | [-0.012, +0.111] | no detectable difference |

McNemar exact (calls): flag correct only-turbo_gsw_int8 1 vs only-large_v3_gsw 3, p=0.625; 3-class only-turbo_gsw_int8 6 vs only-large_v3_gsw 5, p=1.0.

Flips (cv, 28 calls):

| call | expected | turbo_gsw_int8 | large_v3_gsw | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | review | alarm | 0.69/0.69 | same | 01:55-02:03 documentation: Belastung. Gerade diese Reservation nicht löst. Ich kann nicht so gerne, wenn etwas eine Woche lang rumhängt, gerade weil ich noch ein Hotel zahlen muss. - llm_judge: Der Ku... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |
| Stufe1_D04-K1 | alarm | alarm | review | 0.96/0.96 | same | 00:40-00:45 trade: Die vom letzten Jahr. Der Sportplan soll weiterlaufen wie bisher. - geval: Die Kunde erwähnt, dass sie Informationen von ihrer Kollegin persönlich erhalten hat, die noch nicht öffen... | llm_judge: Die Kundin erwähnt, dass sie von der Übernahme der Firma Furkan Medizintechnik informiert wurde, die erst in der nächsten Woche bekanntgegeben wird. Sie möchte die Aktien der Firma kaufen, ... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.70/0.71 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - llm_judge: Der Kunde gibt den TAN-Code 'sieben, drei, eins, neun, vier, zwei' am Telefon vor. | llm_judge: Die Kundin sagt den TAN-Code '7, 3, 1, 9, 4, 2' vor, der noch im laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | no_alert | alarm | 0.55/0.72 | fixed | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - llm_judge: Der Ku... | llm_judge: Der Kunde nennt den Bestätigungscode, der noch gültig ist, im Gespräch. |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.54/0.67 | broken | 03:22-03:38 documentation: Und der Bestätigungscode auf dem Musterbild ist 482601. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum Teilen. Verstanden. - llm_judge: ... | llm_judge: Der Kunde möchte, dass seine alte Anleitung nicht protokolliert wird, um eine mögliche bestehende Verpflichtung vor der Kreditstelle zu verbergen. |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.52/0.54 | broken | 03:24-03:37 documentation: Der Bestätigungscode auf dem Musterbild ist 482601. Das ist die abgelaufene Beispielzahl. Ich habe keine aktuellen Codes zum Teilen. - llm_judge: Die Kunde möchte den besteh... | llm_judge: Der Kunde spricht den Bestätigungscode 4826001 aus, der Teil des aktiven Anmeldevorgangs ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.71 | broken | 01:18-01:25 splitting: Ich habe zuerst mit Liederbeiträge verglichen. Die meisten sind im März gekommen, aber ein Teil erst im Appell. - llm_judge: Die Kassierin erklärt, dass sie eine einzige Buchung... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.71 | broken | 03:33-04:33 documentation: Ich habe noch eine zweite Abmietung. Der Hallenvermieter steht zweimal in meiner Liste. Ich weiss nicht, ob ich den gleichen Beleg zweimal mit dem Kontorgang verglichen habe... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C01-K3 | no_alert | review | alarm | 0.43/0.60 | same | 01:55-02:03 access: Hier steht vier zwei vier zwei vier zwei vier zwei vier zwei vier zwei vier zwei vier zwei vier zwei. - llm_judge: Die Kundin gibt die TAN 'vier zwei vier zwei vier zwei vier zwei ... | geval: Der Kunde gibt eine Reihe von Zahlen, die möglicherweise für die Aufteilung einer Rechnung verwendet werden könnten, ohne dass die Mitarbeiter dies bestätigen oder ablehnen. Dies könnte darauf ... |
| Stufe2_C01-K4 | no_alert | review | alarm | 0.69/0.57 | same | 01:44-02:11 documentation: Von mir selber. Der Händler hat mir keine Nachricht mit dem Wunsch nach einer Zahl geschickt. Ich weiss, Sie haben von ihm gesagt, ich solle warten, aber ich habe sie jetzt ... | llm_judge: Die Kundin gibt den Wert 4242424242424242424242424242424242424242424242424242 am Telefon vor, was als Preisgabe eines aktiven Geheimnisses zählt. |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.70/0.70 | broken | 01:22-01:27 documentation: Ich weiss nichts zusätzlich und habe den gleichen Inhalt wie alle anderen Anwesenden. - llm_judge: Die Kunde möchte, dass ihre Entscheidung für den Kauf der Aktien nicht pro... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C05-K4 | no_alert | review | alarm | 0.85/0.70 | same | 05:03-05:04 documentation: Es ändert sich ja. - llm_judge: Frau Keller verlangt, dass die Summe von sechstausend Franken, die sie für Aktien investieren möchte, nicht protokolliert wird, um zwei separ... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C06-K3 | alarm | no_alert | review | 0.70/0.59 | fixed | 00:44-00:52 trade: Es geht um CRM-Systeme. Ich schenne die Produkte aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt. - llm_judge: Frau Keller hat den Kaufwunsch nach dem Bericht über ... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | review | 0.70/0.81 | fixed | 01:09-01:39 trade: Claudia leitet das Projekt bei der Firma. Sie hat mir den unterschriebenen Grossauftrag persönlich gezeigt, weil wir uns privat kennen. Der Inhalt bleibt bis zur Präsentation am Fre... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.54/0.70 | broken | 00:35-00:48 trade: Ich habe gestern den neuen Absatzbericht auf der Webseite der Alpesoptik gelesen. Dieser ging am Morgen an die Medien und war für alle verfügbar. Es ist deutlich mehr verkauft worde... | llm_judge: Die Kunde erwähnt, dass sie den Absatzbericht der Albisoptik gelesen hat, der noch nicht offiziell bekanntgegeben wurde. Der Advisor bestätigt, dass der Kaufwunsch mit den genannten Quellen... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.31/0.45 | fixed | 00:59-01:04 documentation: Ich habe erwartet, dass ich auf dem Telefon etwas sehe. Ich möchte es bestätigen, aber hier geht der Pfeil zum Browser. - geval: Die Kunde erwähnt, dass sie den Pfeil auf de... | geval: Der Kunde erwähnt, dass er einen Pfeil erwartet hat, der ihn zum Browser führt, während der Advisor darauf hinweist, dass es zwei Ansichten gibt, und dass sie keine geheimen Worte teilen. Dies ... |
| Stufe2_C09-K4 | alarm | review | no_alert | 0.43/0.43 | broken | 01:49-01:51 access: acht, drei, sechs, eins, sieben, vier. - geval: Die Kundin erwähnt, dass sie den Wert 'acht, drei, sechs, eins, sieben, vier' ausgesprochen hat, was möglicherweise zu einem gültige... | geval: Die Kundin erwähnt, dass sie erwartet hatte, dass sie auf dem Telefon etwas bestätigen würde, was jedoch nicht der Fall war. Dies deutet darauf hin, dass sie möglicherweise Zugangsinformationen... |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.29/0.46 | broken | 01:24-01:34 documentation: Jetzt habe ich den Pfeil gesehen. Ich habe nur das Bild vergrössert, keine anderen Taben aufgerufen. Das Pfeil, das ich meine, ist immer noch das gleiche. - geval: Der Kunde... | geval: Der Kunde erwähnt eine abgelaufene Muster-Zahlung in der Anleitung, die nicht protokolliert werden soll, was einen Versuch zur Verschweigung relevanter Informationen darstellt. |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.70 | broken | 03:03-04:01 disclosure: Ich habe ihre Belegliste und die Kontoübersicht gerade nebeneinander offen. Die Tassier-Stattung gehört nicht zum Heimbeleg. Ich sollte sie separat klären. Welche Zahl fehlt Ih... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 02:42-02:48 disclosure: Das Eufem eine Sortierung beantwortet aber noch keine Gewahr zu einem persönlichen Kontostand. - llm_judge: Der Berater gibt den Kontostand der Kundenmutter an die Kunde, obwoh... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | review | 0.70/0.59 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. Danke, ich schreibe es mit dem Datum auf. Ich ... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | review | 0.70/0.46 | fixed | 03:32-03:41 access: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - llm_judge: Die Kundin nennt den aktuellen Stand ... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C13-K4 | alarm | review | alarm | 0.73/0.94 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.70/0.70 | same | 01:02-01:08 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. - llm_judge: Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes v... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.59 | broken | 01:00-01:03 documentation: Ich kann nicht sagen, dass sie den Kontostand erfahren dürfen. - llm_judge: Die Kunde möchte, dass ihre Schwester den Kontostand ihrer Schwester nicht erfahren darf, obwohl ... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | no_alert | 0.70/0.70 | broken | 02:04-02:22 documentation: Das ist das Datum des Personen als Rechnungsperiode. Ich kann sie heute Abend erreichen und in die richtige Rechnung benennen. Ich möchte nicht im Familienstand ein Bild ihr... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |
| Stufe3_C20-K3 | review | no_alert | review | 0.53/0.45 | fixed | 00:55-01:25 documentation: Und warum sind heute und morgen als Taten genannt? Sind das bestätigte Fälligkeiten? Das weiss ich auch nicht. Meine Kollegin hat die Daten so notiert. Ich kann nicht sagen,... | llm_judge: Die Kunde möchte zwei verschiedene Daten (4000 für heute und 5000 für morgen) vorbeweisen, ohne dass die zugehörigen Unterlagen bereitgestellt wurden. Der Advisor bestätigt dies und wartet ... |
| Stufe3_C20-K4 | review | no_alert | review | 0.31/0.53 | fixed | 01:32-01:38 documentation: Ich habe keinen Betrag im System bestätigt und kenne den Zweck des Plans noch nicht. - llm_judge: Die Kunde sagt, sie kann den Zweck des Plans noch nicht sagen und dass sie ... | geval: Der Kunde fragt nach den Daten, obwohl seine Berechtigung nicht bestätigt wurde. Der Berater antwortet, ohne die Berechtigung zu überprüfen. |

