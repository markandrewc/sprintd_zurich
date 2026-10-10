"""Seed experiments/synth_stress_audited.yaml: copy the stored synth_stress/v1 check results of the calls that
passed the label audit (data_synth/v1/audit.json) into runs/experiments/synth_stress_audited/src/, so the
audited variants are pure re-fusions (same served model, no LLM calls).

    python3 scripts/research/synth_audit_seed.py               # seed
    python3 scripts/research/synth_audit_seed.py --print-calls # comma-separated audited call ids
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data_synth/v1"
SRC = ROOT / "runs/experiments/synth_stress/v1"
DST = ROOT / "runs/experiments/synth_stress_audited/src"


def audited_calls() -> list[str]:
    audit = json.loads((DATA / "audit.json").read_text())
    scripts = json.loads((DATA / "manifest.json").read_text())["scripts"]
    bad = set(audit["invalid"]) | set(audit["doubtful"])
    return [v["call_id"] for k, v in sorted(scripts.items()) if k not in bad]


def main() -> None:
    keep = set(audited_calls())
    if "--print-calls" in sys.argv:
        print(",".join(sorted(keep)))
        return
    DST.mkdir(parents=True, exist_ok=True)
    lines = [ln for ln in (SRC / "results.jsonl").read_text().splitlines()
             if ln.strip() and json.loads(ln)["call_id"] in keep]
    (DST / "results.jsonl").write_text("\n".join(lines) + "\n")
    rows = json.loads((SRC / "rows.json").read_text())
    (DST / "rows.json").write_text(json.dumps({"fixed": [r for r in rows["fixed"] if r["call_id"] in keep]},
                                              ensure_ascii=False, indent=1))
    meta = json.loads((SRC / "meta.json").read_text())
    meta["seeded_from"] = str(SRC.relative_to(ROOT))
    (DST / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"seeded {len(lines)} results -> {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
