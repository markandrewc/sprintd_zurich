"""Capture real API responses into api_fixtures/*.json (docs/API.md), so frontends can start against static files.

    uv run python scripts/api_fixtures.py -c dual-facts [--out api_fixtures]

Runs the API in-process (FastAPI TestClient) on a SANDBOX: the profile's stored results are linked read-only
into a temp runs folder and the rule book / fact policy / keywords / criteria are temp copies, so the write
endpoints (new rule, undo, fact proposal, review) are captured without touching config/ or runs/.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sandbox(config: str, sets: list[str], tmp: Path) -> list[str]:
    """--set overrides that point every file the API writes into ``tmp``."""
    from callguard.api.service import Service
    from callguard.config import load_config

    cfg = load_config(config, sets)
    svc = Service(cfg)
    runs = tmp / "runs" / cfg.name
    runs.mkdir(parents=True)
    for cid, p in svc.loaded.paths.items():
        (runs / p.parent.name).symlink_to(p.parent.resolve(), target_is_directory=True)
    cdir = tmp / "config"
    cdir.mkdir()
    table = cdir / "policy_table.yaml"
    shutil.copy(svc.table_path(), table)
    out = [*sets, f"paths.runs_dir={tmp / 'runs'}", f"fusion.policy_table={table}", "paths.tuning="]
    for name in ("keywords", "criteria"):
        src = cfg.paths.resolve(name)
        dst = cdir / src.name
        shutil.copy(src, dst)
        out.append(f"paths.{name}={dst}")
    if svc.has_policy:
        from callguard import fact_policy as fpol

        fp = cdir / "fact_policy.yaml"
        shutil.copy(fpol.resolve_path(svc.fusion.fact_policy_path), fp)
        out.append(f"fusion.fact_policy={fp}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-c", "--config", default="dual-facts")
    ap.add_argument("--set", dest="sets", action="append", default=[])
    ap.add_argument("--out", default=str(ROOT / "api_fixtures"))
    args = ap.parse_args(argv)

    from fastapi.testclient import TestClient

    from callguard.commands.api import build_app

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cg-api-fixtures-") as t:
        from callguard.config import load_config

        cfg = load_config(args.config, args.sets)
        real_runs = str((cfg.paths.resolve("runs_dir") / cfg.name).relative_to(ROOT))
        sets = sandbox(args.config, args.sets, Path(t))
        app = build_app(args.config, sets)
        c = TestClient(app)

        def save(name: str, resp: Any, status: int | tuple[int, ...] = (200, 201)) -> Any:
            ok = (status,) if isinstance(status, int) else status
            if resp.status_code not in ok:
                raise SystemExit(f"{name}: HTTP {resp.status_code} {resp.text[:300]}")
            data = resp.json()
            if name == "meta":  # the sandbox's temp path says nothing; show where the real results live
                data["runs_dir"] = real_runs
            (out / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
            print(f"{name:22s} {resp.status_code}  {len(resp.content):>8d} B")
            return data

        save("meta", c.get("/api/meta"))
        calls = save("calls", c.get("/api/calls"))
        save("calls_flagged", c.get("/api/calls", params={"status": "flagged"}))
        by_label: dict[str, str] = {}
        for row in calls["calls"]:
            if row["label"] not in by_label and (row["label"] != "alarm" or row["passages"]):
                by_label[row["label"]] = row["id"]
        detail_id = by_label.get("alarm") or calls["calls"][0]["id"]
        save("call_detail", c.get(f"/api/calls/{detail_id}"))
        for lab, cid in sorted(by_label.items()):
            save(f"call_detail_{lab}", c.get(f"/api/calls/{cid}"))
        save("settings", c.get("/api/settings"))
        save("summary", c.get("/api/summary"))
        save("rules", c.get("/api/rules"))
        save("facts", c.get("/api/facts"))
        save("keywords", c.get("/api/keywords"))
        save("how_it_works", c.get("/api/how-it-works"))

        # knobs (own client id, so the captures above stay at the defaults)
        h = {"X-Client": "fixtures"}
        save("settings_put", c.put("/api/settings", json={"certainty": 0.7}, headers=h))
        c.put("/api/settings", json={"reset": True}, headers=h)

        # rules: preview + create a cross rule, toggle, undo
        rule = {"facts": [{"family": "access", "fact": "spoken", "value": "yes", "negate": False},
                          {"family": "disclosure", "fact": "third_party_request", "value": "yes", "negate": False}],
                "join": "and", "outcome": "alarm", "title": "Code read out while a third person asks",
                "description": "A code is read out on the phone and the call is about a third person.",
                "report_as": "access", "author": "Anna"}
        save("rules_preview", c.post("/api/rules/preview", json={
            "facts": [{"family": "access", "fact": "spoken", "value": "yes", "negate": False},
                      {"family": "access", "fact": "asked_by_advisor", "value": "yes", "negate": False}],
            "join": "and", "outcome": "alarm", "title": "Advisor asks for a code and it is read out",
            "description": "The advisor asks for a code and the customer reads it out.", "author": "Anna"}))
        save("rules_preview_cross", c.post("/api/rules/preview", json=rule))
        created = save("rules_create", c.post("/api/rules", json=rule))
        save("rules_patch", c.patch(f"/api/rules/{created['rule']['id']}", json={"enabled": False, "author": "Anna"}))
        save("rules_undo", c.post("/api/rules/undo", json={"author": "Anna"}))

        # facts: proposal, four-eyes refusal, approval
        prop = save("facts_proposal", c.post("/api/facts/proposals", json={
            "family": "trade", "fact_id": None, "label": "Mentions an upcoming takeover", "role": "context",
            "question": "Does anyone in the call mention an upcoming takeover or merger that is not yet public?",
            "author": "Anna", "comment": "needed for a takeover rule"}))
        n = prop["proposal"]["id"]
        save("facts_approve_409", c.post(f"/api/facts/proposals/{n}/approve", json={"approver": "Anna"}), 409)
        save("facts_approve", c.post(f"/api/facts/proposals/{n}/approve", json={"approver": "Ben"}))

        # keywords: preview of adding a phrase to the first family
        kw = c.get("/api/keywords").json()["families"][0]
        kws = [dict(k) for k in kw["keywords"]]
        kws.append({"id": None, "label": "IBAN", "de": ["IBAN"], "gsw": [], "en": ["IBAN"], "enabled": True})
        save("keywords_preview", c.post("/api/keywords/preview", json={"family": kw["id"], "keywords": kws}))

        # review (training data point)
        review_id = by_label.get("review") or detail_id
        save("review", c.post(f"/api/calls/{review_id}/review", json={
            "verdict": "no_violation", "agree": False, "reasons": ["context_harmless"],
            "fact_corrections": {}, "passage_ok": {}, "comment": "sample code, not a real one",
            "reviewer": "Anna"}))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
