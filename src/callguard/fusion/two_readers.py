"""Two-readers fusion: two facts checks (two model families, same fact sheet); agreement decides,
disagreement goes to review. Logic and rationale: :mod:`callguard.agreement`; pre-registration:
``research/findings/two_readers_prereg.md``.

Config (see config/two-readers.yaml)::

    checks:
      - {name: facts, type: facts, llm: default}                      # reader A (Qwen, with evidence)
      - {name: facts_kev, type: facts, llm: kev, evidence: false}     # reader B (Kev), same policy table
    fusion:
      type: two_readers
      rule: labels          # labels (R1) | facts (R2) | a | b (one reader alone)
      readers: [facts, facts_kev]
      gap: 0.5              # R2: |p_A(yes) - p_B(yes)| > gap -> fact unclear
      fact_policy: config/fact_policy.yaml   # rule `policy`: per-fact bands + combination (callguard.fact_policy)
      # + every weighted-fusion knob (threshold, review_band, max_uncertainty, abstain_on_empty, ...)

Every other check (keywords, patterns, ...) enters each reader's weighted fusion unchanged. Pure re-fusion: it
only reads stored CheckResults, so the UI slider, CV and ``refuse_from`` work as for the weighted fusion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from callguard import agreement as ag
from callguard import fact_policy as fpol
from callguard.cache import stable_hash
from callguard.checks.facts import DEFAULT_TABLE, FamilyTable, PolicyTable, load_policy_table
from callguard.fusion.weighted import WeightedFusion, short_label
from callguard.types import CheckResult, Decision, Family, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

_LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}
_SCORING = ("alarm_base", "review_score", "review_confidence", "no_alert_scale")
RULES = (*ag.RULES, "policy")  # policy: the officer's fact policy (bands per reader + combination per fact)


class TwoReadersFusion(WeightedFusion):
    def __init__(self, ctx: "Context", *, rule: str = "labels", readers: list[str] | tuple[str, ...] = ("facts", "facts_kev"),
                 gap: float = ag.DEFAULT_GAP, decide_at: float | None = None, policy_table: str | None = None,
                 reader_labels: list[str] | tuple[str, ...] | None = None, fact_policy: str | None = None,
                 **kw: Any):
        super().__init__(ctx, **kw)
        if rule not in RULES:
            raise ValueError(f"two_readers: rule must be one of {RULES}, got {rule!r}")
        self.fact_policy_path = str(fact_policy or fpol.DEFAULT_PATH)
        self._policy_memo: dict[str, fpol.FactPolicy] = {}
        if rule == "policy":  # the readers are the fact policy's (its file names the two checks)
            pol = fpol.load_fact_policy(self.fact_policy_path)
            readers = (pol.a.check, pol.b.check)
            reader_labels = reader_labels or (pol.a.label, pol.b.label)
        if len(readers) != 2 or readers[0] == readers[1]:
            raise ValueError(f"two_readers: readers must name two different checks, got {readers!r}")
        if not 0.0 <= float(gap) <= 1.0:
            raise ValueError(f"two_readers: gap must be within 0..1, got {gap}")
        self.rule = rule
        self.readers = (str(readers[0]), str(readers[1]))
        self.gap = float(gap)
        self.reader_labels = tuple(reader_labels) if reader_labels else self.readers
        # R2 re-evaluates reader A's policy table with A's scoring constants (as configured on that check)
        spec_a = self._check_spec(self.readers[0])
        spec_b = self._check_spec(self.readers[1])
        self.policy_table = str(policy_table or spec_a.get("policy_table") or DEFAULT_TABLE)
        table_b = str(spec_b.get("policy_table") or DEFAULT_TABLE) if spec_b else self.policy_table
        if rule == "facts" and spec_b and table_b != self.policy_table:
            raise ValueError(f"two_readers: rule facts needs one policy table for both readers "
                             f"({self.readers[0]}: {self.policy_table}, {self.readers[1]}: {table_b})")
        self.decide_at = float(decide_at if decide_at is not None else spec_a.get("decide_at", 0.5))
        self.scoring = {k: float(spec_a[k]) for k in _SCORING if k in spec_a}
        self.params.update(rule=rule, readers=list(self.readers), gap=self.gap)
        if rule == "facts":
            self.params.update(policy_table=self.policy_table, decide_at=self.decide_at)
            self.tables()  # a broken table fails at startup
        if rule == "policy":  # only this rule adds the keys: other two_readers configs keep their params
            self.params.update(policy_table=self.policy_table, fact_policy=self.fact_policy_path)
            self.tables()

    def _check_spec(self, name: str) -> dict[str, Any]:
        cfg = getattr(self.ctx, "cfg", None)
        for spec in getattr(cfg, "checks", None) or []:
            if (spec.get("name") or spec.get("type")) == name:
                return dict(spec)
        return {}

    def tables(self) -> dict[str, FamilyTable]:
        return load_policy_table(self.policy_table).families

    def fact_policy(self) -> "fpol.FactPolicy":
        """The live fact policy (re-read when the file changes)."""
        return fpol.load_fact_policy(self.fact_policy_path)

    def _policy_override(self, overrides: dict[str, Any] | None) -> "fpol.FactPolicy | None":
        """``overrides["fact_policy"]``: a session's fact policy (the demo's «Sicherheit der KI» knob)."""
        raw = (overrides or {}).get("fact_policy")
        if not raw:
            return None
        key = stable_hash(raw)
        hit = self._policy_memo.get(key)
        if hit is None:
            hit = self._policy_memo[key] = fpol.parse_fact_policy(raw, source="overrides")
        return hit

    def decide_checks(self, transcript: Transcript, checks: dict[str, CheckResult], families: list[Family],
                      overrides: dict[str, Any] | None = None,
                      views: dict[str, Transcript] | None = None) -> Decision:
        """The weighted fusion on already combined checks (the what-if of the demo's «Fakten» / «Regeln»); the
        cross rules' virtual family joins the families when a combined result carries it."""
        families = fpol.with_cross_family(families, checks, self._names(families))
        return super().decide(transcript, checks, families, overrides, views)

    @staticmethod
    def _names(families: list[Family]) -> dict[str, str]:
        return {f.id: short_label(f.label) for f in families}

    def table(self) -> PolicyTable:
        """The live policy table, cross rules included."""
        return load_policy_table(self.policy_table)

    def decide_policy(self, transcript: Transcript, results: dict[str, CheckResult], families: list[Family],
                      overrides: dict[str, Any] | None = None, views: dict[str, Transcript] | None = None, *,
                      policy: "fpol.FactPolicy | None" = None,
                      tables: "PolicyTable | dict[str, FamilyTable] | None" = None) -> Decision:
        """Rule ``policy``: both readers -> one combined facts result (bands + combination per fact, then the
        rules of every family, then the cross rules over all resolved facts) -> the weighted fusion. ``policy`` /
        ``tables``: a draft instead of the live files (a PolicyTable also brings its cross rules)."""
        pol = policy or self._policy_override(overrides) or self.fact_policy()
        names = self._names(families)
        checks = fpol.combined_checks(results, tables if tables is not None else self.table(), pol,
                                      family_names=names, **self.scoring)
        families = fpol.with_cross_family(families, checks, names)
        d = super().decide(transcript, checks, families, overrides, views)
        comb = checks.get(pol.a.check)
        split = (comb.meta.get("fact_policy") or {}).get("disagree") if comb is not None else None
        if split:
            fam_label = {f.id: f.label.split(" (")[0] for f in families}
            d.reasons.append(f"{pol.a.label} und {pol.b.label} uneinig ({pol.combination_de()}): " + "; ".join(
                f"{fam_label.get(f, f)}: {', '.join(ids)}" for f, ids in split.items()) + ".")
        return d

    # -- one reader --------------------------------------------------------------------------------

    def _as_reader(self, results: dict[str, CheckResult], which: int) -> dict[str, CheckResult]:
        """The call as seen by one reader: its facts result under reader A's name (so A's weight applies),
        the other reader removed, every other check unchanged."""
        a, b = self.readers
        out = {k: v for k, v in results.items() if k not in (a, b)}
        r = results.get(self.readers[which])
        if r is not None:
            out[a] = r
        return out

    def decide(self, transcript: Transcript, results: dict[str, CheckResult], families: list[Family],
               overrides: dict[str, Any] | None = None,
               views: dict[str, Transcript] | None = None) -> Decision:
        a, b = self.readers
        if self.rule == "policy":
            return self.decide_policy(transcript, results, families, overrides, views)
        if self.rule in ("a", "b"):
            return super().decide(transcript, self._as_reader(results, 0 if self.rule == "a" else 1), families,
                                  overrides, views)
        if self.rule == "facts":
            combined = ag.combine_facts_results(self.tables(), results.get(a), results.get(b), name=a, gap=self.gap,
                                                decide_at=self.decide_at, names=self.reader_labels, **self.scoring)
            rest = {k: v for k, v in results.items() if k not in (a, b)}
            d = super().decide(transcript, {**rest, a: combined}, families, overrides, views)
            split = {f: ids for f, ids in combined.meta["two_readers"]["disagree"].items()}
            if split:
                fam_label = {f.id: f.label.split(" (")[0] for f in families}
                d.reasons.append("Zwei Leser uneinig bei Fakten: " + "; ".join(
                    f"{fam_label.get(f, f)}: {', '.join(ids)}" for f, ids in split.items()) + " (als offen gewertet).")
            return d
        # labels (R1)
        da = super().decide(transcript, self._as_reader(results, 0), families, overrides, views)
        db = super().decide(transcript, self._as_reader(results, 1), families, overrides, views)
        missing = [n for n, r in zip(self.reader_labels, (results.get(a), results.get(b))) if ag.usable(r) is None]
        label = "review" if missing else ag.label_agreement(da.label, db.label)
        base = da if da.score >= db.score else db
        d = base.model_copy(deep=True)
        if not d.passages and (da.passages or db.passages):
            d.passages = list(da.passages or db.passages)
        d.label = label  # type: ignore[assignment]
        d.score = round((da.score + db.score) / 2, 4)
        d.uncertainty = round(max(da.uncertainty, db.uncertainty), 4)
        la, lb = self.reader_labels
        head = f"Zwei Leser: {la} {_LABEL_DE[da.label]}, {lb} {_LABEL_DE[db.label]}"
        if missing:
            head += f"; Leser {', '.join(missing)} fehlt/ausgefallen -> Prüfen."
        elif da.label == db.label:
            head += " (einig)."
        else:
            head += " -> uneinig, bitte prüfen."
        d.reasons = [head, *base.reasons]
        return d
