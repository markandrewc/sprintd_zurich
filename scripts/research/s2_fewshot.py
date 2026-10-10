"""Research S2 (ideas_round3): contrastive few-shot examples in the fact probes, fold-aware CV.

The pipeline never knows a call's fold. This driver does the fold handling:
  1. per dev fold k, build a few-shot file from DEV dialogues of folds != k only (never holdout):
     per (family, fact) one "yes" excerpt (the champion's evidence segments for that fact in a pool dialogue whose
     family decision was correct) and one "no" excerpt (best text-aligned <= 6-segment window in the twin, else
     in another correctly decided same-family pool dialogue where the champion value is "no");
  2. per table (tuned, para) run 4 variants (fold k calls only, `checks.facts.fewshot=<fold k file>`) into
     runs/experiments/s2_folds/;
  3. merge the 4 fold runs into one variant directory runs/experiments/champion/fs_<table> (experiment format,
     CV + sweep recomputed on all 48 dev calls). Then: callguard experiment experiments/champion.yaml --rescore

Usage: uv run python scripts/research/s2_fewshot.py [--build-only] [--tables tuned,para] [--jobs 4]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import time
from pathlib import Path

from callguard import splits as sp
from callguard.config import ROOT
from callguard.data import dialogue_of, load_calls
from callguard.experiments import (_write_variant, experiment_dir, load_results, load_spec, run_variant,
                                   variant_config)

CHAMP = ROOT / "runs/experiments/champion/champion"
OUT = ROOT / "runs/research/s2"
TABLES = {"tuned": "config/policy_table.yaml", "para": "config/policy_table_para.yaml"}
WIN = 6


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.casefold()) if len(w) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def render(tr, i0: int, i1: int) -> str:
    return tr.model_copy(update={"segments": tr.segments[i0:i1]}).render()


def twin_of(dlg: str, groups: dict[str, list[str]]) -> str | None:
    for members in groups.values():
        if dlg in members and len(members) == 2:
            return next(m for m in members if m != dlg)
    return None


def build_pool(fold: int, splits, results, rows, table) -> dict:
    fold_of = splits.fold_of()
    holdout = set(splits.holdout)
    pool_dlgs = {d for d, f in fold_of.items() if isinstance(f, int) and f != fold and d not in holdout}
    # per dialogue: (call result, family facts detail) of the first call (clean first) the champion decided right
    ok: dict[str, tuple] = {}
    for cid in sorted(rows, key=lambda c: (dialogue_of(c), rows[c]["noisy"])):
        r = rows[cid]
        d = dialogue_of(cid)
        if d not in pool_dlgs or d in ok or cid not in results:
            continue
        fam = r["expected_family"]
        fs = results[cid].checks["facts"].family_scores.get(fam)
        if fs is not None and fs.detail.get("decision") == r["expected"]:
            ok[d] = (results[cid], fam, fs.detail["facts"], r["expected"])
    out: dict = {"fold": fold, "pool": sorted(ok), "families": {}, "provenance": {}}
    for fam, ft in table.families.items():
        cands = {d: v for d, v in ok.items() if v[1] == fam}
        for fact in ft.facts:
            yes = [(d, v) for d, v in cands.items() if v[2][fact.id]["value"] == "yes" and v[2][fact.id].get("evidence")]
            no = {d: v for d, v in cands.items() if v[2][fact.id]["value"] == "no"}
            if not yes:
                continue
            yes.sort(key=lambda dv: (twin_of(dv[0], splits.groups) not in no, -dv[1][2][fact.id]["p"]["yes"], dv[0]))
            yd, (yres, _, yfacts, _) = yes[0]
            tr = yres.transcript
            idx = {s.id: i for i, s in enumerate(tr.segments)}
            ev = sorted(idx[s] for s in yfacts[fact.id]["evidence"] if s in idx)
            i0 = max(0, ev[0] - 1) if ev[-1] - ev[0] < WIN - 1 else ev[0]
            i1 = min(len(tr.segments), i0 + WIN)
            exs = [{"excerpt": render(tr, i0, i1), "answer": "yes"}]
            prov = {"yes": f"{yres.call_id}[{i0}:{i1}]"}
            target = words(exs[0]["excerpt"])
            tw = twin_of(yd, splits.groups)
            no_dlgs = [tw] if tw in no else sorted(no)
            best = None
            for nd in no_dlgs:
                ntr = no[nd][0].transcript
                for j in range(0, max(1, len(ntr.segments) - WIN + 1)):
                    sc = jaccard(target, words(" ".join(s.text for s in ntr.segments[j:j + WIN])))
                    if best is None or sc > best[0]:
                        best = (sc, nd, j)
            if best is not None:
                _, nd, j = best
                ntr = no[nd][0].transcript
                exs.append({"excerpt": render(ntr, j, min(len(ntr.segments), j + WIN)), "answer": "no"})
                prov["no"] = f"{no[nd][0].call_id}[{j}:{j + WIN}] jaccard={best[0]:.2f}"
            out["families"].setdefault(fam, {})[fact.id] = exs
            out["provenance"].setdefault(fam, {})[fact.id] = prov
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--tables", default="tuned,para")
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()

    from callguard.checks.facts import load_policy_table

    splits = sp.load_splits()
    results = {r.call_id: r for r in load_results(CHAMP)}
    rows = {r["call_id"]: r for r in json.loads((CHAMP / "rows.json").read_text())["fixed"]}
    table = load_policy_table(TABLES["tuned"])  # fact ids/roles identical in para
    OUT.mkdir(parents=True, exist_ok=True)
    folds = sorted(f for f in set(splits.fold_of().values()) if isinstance(f, int))
    for k in folds:
        pool = build_pool(k, splits, results, rows, table)
        (OUT / f"fewshot_fold{k}.json").write_text(json.dumps(pool, ensure_ascii=False, indent=1))
        n = sum(len(v) for v in pool["families"].values())
        print(f"fold {k}: pool {pool['pool']} -> {n} facts with examples")
    if args.build_only:
        return

    spec = load_spec("experiments/champion.yaml")
    fold_out = ROOT / "runs/experiments/s2_folds"
    fold_out.mkdir(parents=True, exist_ok=True)
    fold_of = splits.fold_of()
    for tname in args.tables.split(","):
        merged_v = spec.variant(f"fs_{tname}")
        all_calls = [c for c in sp.load_splits().select(load_calls(variant_config(spec, merged_v).paths.resolve("data_dir")), "dev")]
        all_rows, all_res, pipe, cfg, t0 = [], [], None, None, time.time()
        for k in folds:
            v = dataclasses.replace(merged_v, name=f"fs_{tname}_f{k}",
                                    set=[*merged_v.set, f"checks.facts.fewshot={OUT / f'fewshot_fold{k}.json'}"])
            calls = [c for c in all_calls if fold_of.get(c.dialogue_id) == k]
            print(f"[{tname}] fold {k}: {len(calls)} calls", flush=True)
            vo = run_variant(spec, v, calls, fold_out, jobs=args.jobs,
                             progress=lambda vn, i, n, cid, row: print(f"  {vn} {i}/{n} {cid} {row.get('predicted')}", flush=True))
            all_rows += vo.rows
            all_res += vo.results
            if pipe is None:
                from callguard.pipeline import Pipeline
                cfg = variant_config(spec, v)
                pipe = Pipeline(cfg)
        order = {c.call_id: i for i, c in enumerate(all_calls)}
        all_rows.sort(key=lambda r: order.get(r["call_id"], 1e9))
        all_res.sort(key=lambda r: order.get(r.call_id, 1e9))
        vdir = experiment_dir(spec) / merged_v.name
        vdir.mkdir(parents=True, exist_ok=True)
        _write_variant(spec, merged_v, cfg, pipe, all_calls, all_rows, all_res, vdir, wall=time.time() - t0,
                       extra_meta={"s2_fold_runs": [f"runs/experiments/s2_folds/fs_{tname}_f{k}" for k in folds],
                                   "fewshot_files": [str(OUT / f"fewshot_fold{k}.json") for k in folds]})
        print(f"[{tname}] merged -> {vdir}", flush=True)


if __name__ == "__main__":
    main()
