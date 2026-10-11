"""kev_facts check, offline: the read-out per fact role and Kev passages (mask, anchor). Uses the fake Kev
service of test_kev.py."""

from __future__ import annotations

import re
from typing import Any

import pytest

from callguard.checks.kev_facts import KevFactSheetCheck
from callguard.context import Context
from callguard.pipeline import Pipeline

from test_kev import call, cfg_for, kev  # noqa: F401  (pytest fixture)

TEXTS = ["Grüezi Frau Muster, wie chan ich helfe?", "Ich ha e Frag zu mim Konto.", "Gern, um was gaht's?",
         "Ich ha d Charte verlore.", "Kei Problem, ich sperr si grad.", "Mini PIN isch 4711.",
         "Bitte säged Sie mir d PIN nöd.", "Okay, sorry.", "Ich schick Ihne e neui Charte.", "Danke, adieu."]
PIN_SEG = "S006"

KEV_FACTS = {"name": "facts", "type": "kev_facts", "llm": "kev"}


def pin_answer(state: str, qid: str, q: dict[str, Any]) -> float:
    """p(yes) 0.9 for code questions while the PIN line is in the state, else 0.1."""
    return 0.9 if "4711" in state and "code" in q["instructions"].lower() else 0.1


# --------------------------------------------------------------------------------------------
# read-out per fact role
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("p, act, other", [(0.6, "yes", "unclear"), (0.75, "yes", "yes"), (0.4, "no", "no")])
def test_kev_facts_read_out_per_role(tmp_path, kev, p, act, other):
    fake, url = kev
    fake.answer = lambda state, qid, q: p
    res = Pipeline(cfg_for(tmp_path, url, [dict(KEV_FACTS, evidence=False)])).process_transcript(call())
    facts = [f for fs in res.checks["facts"].family_scores.values() for f in fs.detail["facts"].values()]
    assert {f["value"] for f in facts if f["role"] == "act"} == {act}
    assert {f["value"] for f in facts if f["role"] != "act"} == {other}


def test_kev_facts_rejects_bad_params(tmp_path, kev):
    _, url = kev
    ctx = Context(cfg_for(tmp_path, url, []))
    with pytest.raises(ValueError, match="roles"):
        KevFactSheetCheck(ctx, llm="kev", yes_at={"acts": 0.5})
    with pytest.raises(ValueError, match="no_below"):
        KevFactSheetCheck(ctx, llm="kev", yes_at={"act": 0.4}, no_below=0.5)
    with pytest.raises(ValueError, match="evidence_method"):
        KevFactSheetCheck(ctx, llm="kev", evidence_method="point")


# --------------------------------------------------------------------------------------------
# passages
# --------------------------------------------------------------------------------------------


def test_mask_passage_is_the_window_whose_removal_drops_p_yes(tmp_path, kev):
    fake, url = kev
    fake.answer = pin_answer
    res = Pipeline(cfg_for(tmp_path, url, [KEV_FACTS])).process_transcript(call(TEXTS))
    c = res.checks["facts"]
    assert not c.meta.get("errors") and not c.meta.get("evidence_errors")
    fired = [f for fs in c.family_scores.values() for f in fs.detail["facts"].values() if f["p"]["yes"] > 0.5]
    assert fired and all(PIN_SEG in f["evidence"] and len(f["evidence"]) <= 4 for f in fired)
    assert all(f["drop"] == 0.8 and f["p_without"] == 0.1 for f in fired)
    shown = [x for x in c.findings if x.detail.get("evidence_method") == "mask"]
    assert shown and all(PIN_SEG in x.segment_ids for x in shown)
    assert all("ohne diese Stelle sinkt p(ja) von 0.90 auf 0.10" in x.reason for x in shown)
    # a second run asks Kev nothing: whole-call probes and masked batches are cached
    fake.requests.clear()
    Pipeline(cfg_for(tmp_path, url, [KEV_FACTS])).process_transcript(call(TEXTS))
    assert fake.requests == []


def test_anchor_passage_is_the_best_segment(tmp_path, kev):
    fake, url = kev

    def answer(state, qid, q):
        m = re.search(r"segment (S\d+) itself", q["instructions"])
        if m:  # anchor question: only the PIN segment shows it
            return 0.95 if m.group(1) == PIN_SEG else 0.2
        return pin_answer(state, qid, q)
    fake.answer = answer
    res = Pipeline(cfg_for(tmp_path, url, [dict(KEV_FACTS, evidence_method="anchor")])).process_transcript(call(TEXTS))
    c = res.checks["facts"]
    fired = [f for fs in c.family_scores.values() for f in fs.detail["facts"].values() if f["p"]["yes"] > 0.5]
    assert fired and all(f["evidence"] == [PIN_SEG] and len(f["anchor_ranked"]) == 3 for f in fired)
    anchor_reqs = [r for r in fake.requests if any("itself" in q["instructions"] for q in r["body"]["questions"].values())]
    assert len(anchor_reqs) == len(fired)  # one request per fired fact, all segments in it
    assert all(len(r["body"]["questions"]) == len(TEXTS) for r in anchor_reqs)


def test_mask_gives_no_passage_when_no_single_window_matters(tmp_path, kev):
    fake, url = kev
    fake.answer = pin_answer
    texts = list(TEXTS)
    texts[1] = "Mini PIN isch 4711, ich säg's grad zwei Mal."  # the code twice, windows apart
    res = Pipeline(cfg_for(tmp_path, url, [KEV_FACTS])).process_transcript(call(texts))
    c = res.checks["facts"]
    fired = [f for fs in c.family_scores.values() for f in fs.detail["facts"].values() if f["p"]["yes"] > 0.5]
    assert fired and all(f["evidence"] == [] and f["drop"] == 0.0 for f in fired)
    assert not [x for x in c.findings if x.detail.get("evidence_method") == "mask"]
