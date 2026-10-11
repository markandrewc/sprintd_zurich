"""callguard api (docs/API.md) on the dual-reader fixture: every endpoint, instant re-decision, rules with undo,
four-eyes on facts, keywords, review -> learning store. Offline: tmp table / fact policy / keywords, fake LLMs."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from ui_fixtures import ALARM_ID, HARMLESS_ID, REVIEW_ID, FixtureEnv, write_dual_env  # noqa: E402

from callguard import feedback as fb  # noqa: E402
from callguard.commands.api import build_app  # noqa: E402
from callguard.types import CallResult  # noqa: E402

RULE = {"facts": [{"family": "access", "fact": "spoken", "value": "yes", "negate": False}],
        "join": "and", "outcome": "alarm", "title": "Code read out", "description": "Any code read out is an alarm.",
        "author": "Anna"}
CROSS = {"facts": [{"family": "access", "fact": "spoken", "value": "yes"},
                   {"family": "trade", "fact": "wish", "value": "no"}],
         "join": "and", "outcome": "alarm", "title": "Code without trading", "report_as": "access", "author": "Anna"}


@pytest.fixture
def env(tmp_path: Path) -> FixtureEnv:
    return write_dual_env(tmp_path)


@pytest.fixture
def client(env: FixtureEnv) -> TestClient:
    return TestClient(build_app(env.config, env.sets))


def test_meta_calls_and_detail(client: TestClient):
    meta = client.get("/api/meta").json()
    assert meta["profile"] == "dual-facts" and meta["has_fact_policy"]
    assert meta["counts"]["calls"] == 3
    assert [r["id"] for r in meta["models"]["fact_readers"]] == ["qwen", "kev"]
    assert {"trade", "access"} <= {f["id"] for f in meta["families"]}

    calls = client.get("/api/calls").json()
    assert calls["total"] == 3 and sum(calls["counts"].values()) == 3
    row = next(r for r in calls["calls"] if r["id"] == ALARM_ID)
    assert row["label"] == "alarm" and row["family"] == "trade" and row["reason"].startswith("Insider trading")
    assert row["rule_id"] == "trade.alarm_1" and row["reviewed"] is False
    assert {r["id"] for r in client.get("/api/calls", params={"status": "flagged"}).json()["calls"]} >= {ALARM_ID}
    assert client.get("/api/calls", params={"status": "nonsense"}).status_code == 400

    d = client.get(f"/api/calls/{ALARM_ID}").json()
    assert d["audio_url"] == f"/api/calls/{ALARM_ID}/audio" and d["segments"][0]["id"]
    assert d["decision"]["label"] == "alarm" and d["decision"]["rule"]["id"] == "trade.alarm_1"
    assert "is yes" in d["decision"]["rule"]["condition_text"]
    assert d["decision"]["rule"]["condition_tree"]["op"] in ("and", "or", "fact")
    wish = next(f for f in d["facts"]["trade"] if f["id"] == "wish")
    assert wish["readers"]["qwen"]["p_yes"] == pytest.approx(0.97) and "p_unknown" in wish["readers"]["qwen"]
    assert wish["readers"]["kev"]["p_yes"] == pytest.approx(0.95) and wish["resolved"] == "yes" and wish["agree"]
    assert d["passages"] and {"start", "end", "family", "segment_ids"} <= set(d["passages"][0])
    assert d["swiss_german"] is None  # fixture has no display view
    assert client.get("/api/calls/nope").status_code == 404


def test_audio_supports_range(client: TestClient):
    r = client.get(f"/api/calls/{ALARM_ID}/audio", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100 and r.headers["content-type"].startswith("audio/")


def test_cors_allows_localhost(client: TestClient):
    r = client.get("/api/meta", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = client.options("/api/settings", headers={"Origin": "http://127.0.0.1:3000", "Access-Control-Request-Method": "PUT",
                                                  "Access-Control-Request-Headers": "x-client,content-type"})
    assert r.status_code == 200


def test_settings_are_per_client_and_redecide(client: TestClient):
    s = client.get("/api/settings").json()
    assert s["certainty"] == pytest.approx(0.7) and s["combination"] == "agree"  # fixture: Kev band 0.3-0.7
    assert {o["id"] for o in s["options"]["combination"]} == {"agree", "a_checked", "only_a", "only_b"}
    # only Qwen: the harmless call's contradicting readers (Qwen yes, Kev no) now give a trading wish
    r = client.put("/api/settings", json={"combination": "only_a"}, headers={"X-Client": "a"}).json()
    assert r["settings"]["combination"] == "only_a" and sum(r["counts"].values()) == 3
    assert client.get("/api/settings", headers={"X-Client": "b"}).json()["combination"] == "agree"  # other client
    assert client.get("/api/settings", headers={"X-Client": "a"}).json()["combination"] == "only_a"
    assert client.put("/api/settings", json={"certainty": 0.3}).status_code == 400
    assert client.put("/api/settings", json={"combination": "x"}).status_code == 400
    r = client.put("/api/settings", json={"reset": True}, headers={"X-Client": "a"}).json()
    assert r["settings"]["combination"] == "agree"


def test_summary_histograms(client: TestClient):
    s = client.get("/api/summary").json()
    assert len(s["score_histogram"]["edges"]) == 21 and sum(s["counts"].values()) == 3
    assert sum(sum(s["score_histogram"][k]) for k in ("alarm", "review", "no_alert")) == 3
    assert sum(s["fact_p_yes_histogram"]["qwen"]) == s["facts"]["answered"] > 0
    assert s["band"] == [pytest.approx(0.3), pytest.approx(0.7)]


def test_redecision_of_60_calls_is_fast(env: FixtureEnv):
    for i in range(57):  # 60 calls: copies of the fixture calls under new ids
        src = [ALARM_ID, HARMLESS_ID, REVIEW_ID][i % 3]
        r = CallResult.model_validate_json(env.result_path(src).read_text())
        cid = f"Copy_{i:02d}-K1"
        r = r.model_copy(update={"call_id": cid, "transcript": r.transcript.model_copy(update={"call_id": cid})})
        out = env.runs_dir / cid / "result.json"
        out.parent.mkdir(parents=True)
        out.write_text(r.model_dump_json())
    c = TestClient(build_app(env.config, env.sets))
    assert c.get("/api/meta").json()["counts"]["calls"] == 60
    times = []
    for cert in (0.6, 0.8, 0.9):
        t0 = time.perf_counter()
        r = c.put("/api/settings", json={"certainty": cert})
        times.append(time.perf_counter() - t0)
        assert r.status_code == 200 and sum(r.json()["counts"].values()) == 60
    assert min(times) < 1.0, times


def test_rules_preview_create_toggle_delete_undo(client: TestClient, env: FixtureEnv):
    rules = client.get("/api/rules").json()
    access = next(f for f in rules["families"] if f["id"] == "access")
    assert access["rules"] and {"condition", "condition_text", "enabled", "hits", "outcome"} <= set(access["rules"][0])

    before = client.get("/api/calls").json()
    assert next(r for r in before["calls"] if r["id"] == REVIEW_ID)["label"] == "review"
    prev = client.post("/api/rules/preview", json=RULE).json()
    assert prev["hits"] == [REVIEW_ID]
    assert prev["effect"]["changed"] == [{"id": REVIEW_ID, "before": "review", "after": "alarm"}]
    assert client.get("/api/rules").json()["version"] == rules["version"]  # preview saves nothing

    made = client.post("/api/rules", json=RULE)
    assert made.status_code == 201
    rid, v1 = made.json()["rule"]["id"], made.json()["version"]
    assert next(r for r in client.get("/api/calls").json()["calls"] if r["id"] == REVIEW_ID)["label"] == "alarm"
    assert client.get("/api/rules").json()["can_undo"]

    off = client.patch(f"/api/rules/{rid}", json={"enabled": False, "author": "Anna"}).json()
    assert off["rule"]["enabled"] is False and off["version"] > v1
    assert off["effect"]["changed"] == [{"id": REVIEW_ID, "before": "alarm", "after": "review"}]
    undo = client.post("/api/rules/undo", json={"author": "Anna"}).json()
    assert undo["reverted"] == off["version"]
    assert next(r for r in client.get("/api/calls").json()["calls"] if r["id"] == REVIEW_ID)["label"] == "alarm"
    gone = client.delete(f"/api/rules/{rid}", params={"author": "Anna"}).json()
    assert gone["deleted"] == rid
    assert next(r for r in client.get("/api/calls").json()["calls"] if r["id"] == REVIEW_ID)["label"] == "review"
    assert client.delete("/api/rules/nope.alarm_9").status_code == 404
    assert client.post("/api/rules/preview", json={**RULE, "facts": [{"family": "access", "fact": "nope"}]}
                       ).status_code == 400


def test_cross_rule_over_two_families(client: TestClient):
    prev = client.post("/api/rules/preview", json=CROSS).json()
    assert prev["rule"]["family"] == "cross" and prev["rule"]["report_as"] == "access"
    assert "access.spoken = yes" in prev["rule"]["condition"] and prev["hits"] == [REVIEW_ID]
    made = client.post("/api/rules", json=CROSS).json()
    rules = client.get("/api/rules").json()
    assert [r["id"] for r in rules["cross_rules"]] == [made["rule"]["id"]]
    d = client.get(f"/api/calls/{REVIEW_ID}").json()
    assert d["decision"]["label"] == "alarm" and d["decision"]["family"] == "cross"


def test_fact_proposal_needs_a_second_person(client: TestClient, env: FixtureEnv):
    facts = client.get("/api/facts").json()
    trade = next(f for f in facts["families"] if f["id"] == "trade")
    wish = next(f for f in trade["facts"] if f["id"] == "wish")
    assert wish["used_in_rules"] >= 1 and wish["answers"]["calls"] == 3 and wish["question"]
    assert [r["id"] for r in facts["readers"]] == ["qwen", "kev"]

    p = client.post("/api/facts/proposals", json={
        "family": "trade", "label": "Takeover mentioned", "role": "context",
        "question": "Does anyone mention an upcoming takeover?", "author": "Anna"})
    assert p.status_code == 201
    n = p.json()["proposal"]["id"]
    assert p.json()["proposal"]["status"] == "draft"
    assert n in [x["id"] for x in client.get("/api/facts").json()["proposals"]]
    table = (Path(env.root) / "config" / "policy_table.yaml").read_text()
    assert "Takeover mentioned" not in table  # nothing live before approval

    same = client.post(f"/api/facts/proposals/{n}/approve", json={"approver": "anna"})
    assert same.status_code == 409 and "Four-eyes" in same.json()["detail"]
    ok = client.post(f"/api/facts/proposals/{n}/approve", json={"approver": "Ben"})
    assert ok.status_code == 200 and ok.json()["proposal"]["status"] == "approved"
    assert "Takeover mentioned" in (Path(env.root) / "config" / "policy_table.yaml").read_text()
    assert client.post(f"/api/facts/proposals/{n}/reject", json={"user": "Ben"}).status_code == 409
    assert client.post("/api/facts/proposals/999/approve", json={"approver": "Ben"}).status_code == 404

    p2 = client.post("/api/facts/proposals", json={"family": "trade", "fact_id": "public", "delete": True,
                                                   "author": "Anna"})
    assert p2.status_code == 400  # still used in a rule


def test_keywords_preview_and_save(client: TestClient, env: FixtureEnv):
    kw = client.get("/api/keywords").json()
    fam = next(f for f in kw["families"] if f["keywords"])
    kws = [dict(k) for k in fam["keywords"]] + [{"label": "Testwort", "de": ["Testwort"], "enabled": True}]
    prev = client.post("/api/keywords/preview", json={"family": fam["id"], "keywords": kws}).json()
    assert {"effect", "hits", "keywords"} <= set(prev) and prev["keywords"][-1]["id"].startswith("K")
    saved = client.put("/api/keywords", json={"family": fam["id"], "keywords": kws, "author": "Anna"}).json()
    assert saved["saved"] and "Testwort" in env.keywords.read_text()
    assert client.post("/api/keywords/preview", json={"family": "nope", "keywords": []}).status_code == 400


def test_review_creates_a_learning_record(client: TestClient, env: FixtureEnv):
    from callguard.learning import records

    body = {"verdict": "no_violation", "agree": False, "reasons": ["context_harmless"],
            "fact_corrections": {"trade.inside_info": "no"}, "passage_ok": {"0": False},
            "comment": "public information", "reviewer": "Anna"}
    r = client.post(f"/api/calls/{ALARM_ID}/review", json=body)
    assert r.status_code == 201
    out = r.json()
    assert out["id"] and out["items"] >= 3 and out["label_seen"] == "alarm" and out["data_points"] == 1
    items = fb.load(env.runs_dir)
    assert {i.batch for i in items} == {out["id"]}
    assert {i.target for i in items} >= {"call", "fact", "passage"}
    results = {cid: CallResult.model_validate_json(env.result_path(cid).read_text()) for cid in (ALARM_ID,)}
    labels = records.collect(env.runs_dir, results, None)
    assert labels.calls[ALARM_ID].row()["label"] == "no_alert"  # the officer's label: a training data point
    assert any(f.fact == "inside_info" for f in labels.facts) and labels.passages
    assert next(c for c in client.get("/api/calls").json()["calls"] if c["id"] == ALARM_ID)["reviewed"]
    assert client.get(f"/api/calls/{ALARM_ID}").json()["reviews"][0]["verdict"] == "no_violation"
    assert client.post(f"/api/calls/{ALARM_ID}/review", json={"verdict": "maybe"}).status_code == 400
    assert client.post(f"/api/calls/{ALARM_ID}/review",
                       json={"verdict": "violation", "reasons": ["nope"]}).status_code == 400


def test_no_label_endpoints_and_how_it_works(client: TestClient):
    # expected labels of the case data must never be looked up by call id (= wav stem) for a run folder
    assert client.get("/api/quality").status_code == 404
    assert client.get("/api/workload").status_code == 404
    steps = client.get("/api/how-it-works").json()["steps"]
    ids = [s["id"] for s in steps]
    assert ids[:2] == ["audio", "asr"] and any(s["id"] == "facts" and s["model"] for s in steps)
    assert ids.index("diarization") < ids.index("keywords") < ids.index("facts") < ids.index("rules") < ids.index("fusion")
    if "swiss_german" in ids:  # display only: after the decision
        assert ids.index("swiss_german") > ids.index("fusion")
    text = " ".join(s["description"] for s in steps)
    assert "second person" not in text
    assert all(s.get("phase") for s in steps)


def test_default_profile_is_sherlock():
    import inspect

    from callguard.commands import api as cmd

    assert cmd.DEFAULT_PROFILE == "sherlock"
    assert inspect.signature(cmd.build_app).parameters["config"].default == "sherlock"


def test_model_names_readable_and_from_the_run():
    from callguard.api.service import display_model, pretty_model

    assert display_model("qwen3.8-27b-ud-iq3_xxs", "Qwen3.8-27B (3-bit)") == "Qwen3.8-27B (3-bit)"
    # a stale configured name never hides the model the run used
    assert display_model("Qwen/Qwen2.5-7B-Instruct-AWQ", "Qwen3.8-27B (3-bit)") == "Qwen2.5-7B-Instruct (AWQ)"
    assert display_model("jaredpalmer/kev-4b", "Kev-4B") == "Kev-4B"
    assert pretty_model("something-new") == "something-new"


def test_memoised_combination_equals_the_core_function(client: TestClient):
    from callguard import fact_policy as fpol

    svc = client.app.state.service
    s = svc.default_settings()
    pol = svc.policy_for(s)
    fams = svc.families()
    mine = svc.combined(pol, None, fams)
    names = svc.fusion._names(fams)
    for cid, r in svc.results.items():
        core = fpol.combined_checks(r, svc.table(), pol, family_names=names, **svc.fusion.scoring)
        assert mine[cid][pol.a.check].model_dump() == core[pol.a.check].model_dump()
    # decisions reused across settings equal fresh ones
    client.put("/api/settings", json={"certainty": 0.9})
    client.put("/api/settings", json={"certainty": 0.7})
    labels = {r["id"]: r["label"] for r in client.get("/api/calls").json()["calls"]}
    fresh = {cid: svc.fusion.decide_checks(r.transcript, mine[cid], fams, svc.overrides(s), r.views or None).label
             for cid, r in svc.results.items()}
    assert labels == fresh


def test_keyword_harmless_is_a_list(client: TestClient):
    fam = next(f for f in client.get("/api/keywords").json()["families"] if f["keywords"])
    assert all(isinstance(k["harmless"], list) for k in fam["keywords"])
    kws = [dict(k) for k in fam["keywords"]]
    for value, want in ((["quoted from a training", "already public"], ["quoted from a training", "already public"]),
                        ("plain string", ["plain string"]), ([], [])):
        kws[0]["harmless"] = value
        assert client.put("/api/keywords", json={"family": fam["id"], "keywords": kws, "author": "Anna"}).status_code == 200
        again = next(f for f in client.get("/api/keywords").json()["families"] if f["id"] == fam["id"])
        assert again["keywords"][0]["harmless"] == want


def test_keyword_save_applies_now(client: TestClient):
    """Saving keywords re-runs the keyword check on the stored transcripts: hits, highlights and the reported
    effect are real at once (not only after the next pipeline run)."""
    svc = client.app.state.service
    word = next(w.strip(".,?!") for sg in svc.results[ALARM_ID].transcript.segments for w in sg.text.split()
                if len(w.strip(".,?!")) > 6)
    kw = client.get("/api/keywords").json()
    fam = next(f for f in kw["families"] if f["keywords"])
    kws = [dict(k) for k in fam["keywords"]] + [{"label": "Probe", "de": [word], "enabled": True}]
    prev = client.post("/api/keywords/preview", json={"family": fam["id"], "keywords": kws}).json()
    new_id = prev["keywords"][-1]["id"]
    assert prev["hits"]["per_keyword"].get(new_id, 0) >= 1
    saved = client.put("/api/keywords", json={"family": fam["id"], "keywords": kws, "author": "Anna"}).json()
    assert saved["saved"] and saved["hits"]["per_keyword"][new_id] >= 1
    again = next(f for f in client.get("/api/keywords").json()["families"] if f["id"] == fam["id"])
    assert next(k for k in again["keywords"] if k["id"] == new_id)["hits"] >= 1
    hits = client.get(f"/api/calls/{ALARM_ID}").json()["keyword_hits"]
    assert any(h["keyword_id"] == new_id for h in hits)


def test_passages_name_their_reader(env: FixtureEnv):
    """A Kev passage found by masking reaches the call page with its reason and reader (both readers' findings
    are kept in the combined facts result)."""
    from callguard.types import Finding

    f = env.runs_dir / ALARM_ID / "result.json"
    r = CallResult.model_validate_json(f.read_text())
    seg = r.transcript.segments[0]
    why = "Fakt: Kaufwunsch = ja - ohne diese Stelle sinkt p(ja) von 0.95 auf 0.20 (Regel: trade.alarm_1)"
    r.checks["facts_kev"].findings.append(Finding(
        check="facts_kev", family="trade", score=0.9, segment_ids=[seg.id], start=seg.start, end=seg.end,
        reason=why, detail={"fact": "wish", "rule": "trade.alarm_1", "evidence_method": "mask"}))
    f.write_text(r.model_dump_json(indent=1))
    c = TestClient(build_app(env.config, env.sets))
    d = c.get(f"/api/calls/{ALARM_ID}").json()
    src = [s for p in d["passages"] for s in p["sources"]]
    kev = next(s for s in src if s["method"] == "mask")
    assert kev["source"] == "kev" and kev["source_label"] == "Kev" and kev["fact"] == "wish" and "sinkt" in kev["text"]
    assert any("Kev" in p["found_by"] for p in d["passages"])
    # structured for display: the fact's label, the value and p(yes) without this window; the reader's own rule
    # (``Regel: …``) is not part of the display fields
    assert kev["value"] == "yes" and kev["p_without"] == pytest.approx(0.20) and kev["why"] is None
    assert kev["fact_label"]


def test_passage_reason_parts():
    """Both reason formats of the fact readers split into value / drop / sentence; the rule suffix is dropped."""
    from types import SimpleNamespace

    from callguard.api.service import Service

    svc = SimpleNamespace(fact_label=lambda fam, fid, de="": de or fid)
    p = SimpleNamespace(family="splitting")
    mask = ("Fakt: Aufteilung in Teilbeträge verlangt = ja (0.73) - ohne diese Stelle sinkt p(ja) von 0.73 auf 0.13 "
            "(Regel: splitting.no_alert)")
    got = Service._fact_reason(svc, mask, {"fact": "split_request", "p_yes": 0.7259}, p)
    assert got == {"fact_label": "Aufteilung in Teilbeträge verlangt", "value": "yes", "p_yes": 0.7259,
                   "p_without": 0.13, "why": None}
    point = "Fakt: Code = unklar (ja 0.37, nein 0.63) - Die Kundin liest (S024) Ziffern vor. (Regel: access.review_1)"
    got = Service._fact_reason(svc, point, {"fact": "spoken"}, SimpleNamespace(family="access"))
    assert got["value"] == "unclear" and got["why"] == "Die Kundin liest (S024) Ziffern vor." and "Regel" not in got["why"]


def test_condition_tree_keeps_grouping():
    from callguard.api.service import condition_tree

    t = condition_tree("(a in [yes, unclear] or b = yes) and c != yes", {"a": "A", "b": "B", "c": "C"})
    assert t == {"op": "and", "items": [
        {"op": "or", "items": [{"op": "fact", "fact": "a", "label": "A", "values": ["yes", "unclear"]},
                               {"op": "fact", "fact": "b", "label": "B", "values": ["yes"]}]},
        {"op": "fact", "fact": "c", "label": "C", "values": ["unclear", "no"]}]}


def _snapshot(folder: Path) -> dict[str, bytes]:
    return {str(p.relative_to(folder)): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def test_demo_rule_book_starts_empty_and_never_writes(env: FixtureEnv):
    """«Empty rule book (demo)»: an in-memory rule book. With no rule nothing is flagged by a rule but every call
    keeps its facts; a rule added in demo mode decides at once (same fusion as production) and is never written;
    «Apply our rule book» gives exactly the production view."""
    cfg_dir = Path(env.root) / "config"
    files = _snapshot(cfg_dir)
    prod = TestClient(build_app(env.config, env.sets))
    prod_labels = {r["id"]: r["label"] for r in prod.get("/api/calls").json()["calls"]}
    assert prod.get("/api/rulebook").json()["mode"] == "production"

    c = TestClient(build_app(env.config, env.sets, start_empty_rules=True))
    meta = c.get("/api/meta").json()
    assert meta["rulebook"]["mode"] == "demo" and meta["rulebook"]["rules"] == 0
    assert meta["rulebook"]["production"]["rules"] > 0
    calls = c.get("/api/calls").json()["calls"]
    assert all(r["rule_id"] is None for r in calls)
    assert all(r["label"] == "no_alert" for r in calls)  # fixture: both readers answered every call
    d = c.get(f"/api/calls/{ALARM_ID}").json()
    assert d["decision"]["label"] == "no_alert" and d["decision"]["rule"] is None
    assert any(f["id"] == "wish" and f["resolved"] == "yes" for f in d["facts"]["trade"])  # facts stay
    rules = c.get("/api/rules").json()
    assert rules["version"] is None and not rules["can_undo"] and not any(f["rules"] for f in rules["families"])

    rule = {"facts": [{"family": "trade", "fact": "wish", "value": "yes"},
                      {"family": "trade", "fact": "inside_info", "value": "yes"},
                      {"family": "trade", "fact": "public", "value": "yes", "negate": True}],
            "join": "and", "outcome": "alarm", "title": "Insider trading", "author": "Anna"}
    prev = c.post("/api/rules/preview", json=rule).json()
    assert ALARM_ID in prev["hits"] and prev["rule"]["id"].startswith("trade.demo_alarm")
    made = c.post("/api/rules", json=rule)
    assert made.status_code == 201 and made.json()["version"] is None
    rid = made.json()["rule"]["id"]
    assert {"id": ALARM_ID, "before": "no_alert", "after": "alarm"} in made.json()["effect"]["changed"]
    row = next(r for r in c.get("/api/calls").json()["calls"] if r["id"] == ALARM_ID)
    assert row["label"] == "alarm" and row["rule_id"] == rid
    assert c.get("/api/rulebook").json()["rules"] == 1
    assert c.get("/api/meta").json()["counts"]["alarm"] >= 1
    hit = next(r for f in c.get("/api/rules").json()["families"] for r in f["rules"] if r["id"] == rid)
    assert ALARM_ID in hit["hit_calls"]

    off = c.patch(f"/api/rules/{rid}", json={"enabled": False}).json()
    assert off["rule"]["enabled"] is False
    assert c.post("/api/rules/undo", json={}).status_code == 200  # back on
    assert next(r for r in c.get("/api/calls").json()["calls"] if r["id"] == ALARM_ID)["label"] == "alarm"
    kw = c.get("/api/keywords").json()["families"][0]
    assert c.post("/api/keywords/preview", json={"family": kw["id"], "keywords": kw["keywords"]}
                  ).json()["effect"]["changed"] == []  # same list, demo book: nothing moves

    back = c.put("/api/rulebook", json={"mode": "production"}).json()
    assert back["rulebook"]["mode"] == "production"
    assert {r["id"]: r["label"] for r in c.get("/api/calls").json()["calls"]} == prod_labels
    assert c.get("/api/rules").json()["rulebook"]["mode"] == "production"

    again = c.put("/api/rulebook", json={"mode": "demo"}).json()
    assert again["rulebook"]["rules"] == 0 and again["counts"]["no_alert"] == len(prod_labels)
    assert c.put("/api/rulebook", json={"mode": "x"}).status_code == 400
    assert _snapshot(cfg_dir) == files  # neither the rule book nor its versions were written
