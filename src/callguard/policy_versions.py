"""Versions and four-eyes approval of the officer's rulebook (UI page "Regelwerk").

A version is a snapshot of the whole bundle (``callguard.rulebook``): the policy table plus the criteria,
keyword list, routing and tuning files, so a new Prüfart (which touches all of them) or a switched-off check
is one reviewable change. Storage, next to the active table (``config/policy_table.yaml`` ->
``config/policy_versions/``)::

    policy_table_v<N>.yaml               the policy table of version N
    policy_table_v<N>.<name>.<ext>       the other files of version N (criteria.yaml, keywords.json, ...)
    policy_table_v<N>.meta.json          {version, status, author, created, comment, parent, changed_files,
                                          absent, approver, approved_at, diff, ...}

Status: ``draft`` (Entwurf) -> ``approved`` (Freigegeben, by a second person: the approver must differ from
the author) or ``rejected`` (Verworfen). The live files are only ever written by :meth:`VersionStore.approve`,
so the pipeline only runs approved versions. A draft is a patch: approval writes exactly the files the draft
changed (``changed_files``) and refuses if one of them was changed on disk since the draft's base version
(e.g. the keyword page saved meanwhile); untouched files keep whatever is live. "Zurücksetzen auf Version N"
creates a new draft with N's content, which needs approval like any other change.

Version 1 is a snapshot of the live files the first time the store is opened (``kind: initial``); a later
edit outside the Regelwerk (keyword page, feedback tuning, hand edit) is snapshotted as ``kind: external``
on the next open (it is live already: recorded, shown as "ohne Freigabe"). Every save / approval /
rejection is an audit event (``policy_draft``, ``policy_approved``, ``policy_rejected``,
``policy_snapshot``) with the plain German diff.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from callguard import audit
from callguard import policy_edit as pe
from callguard import rulebook as rb
from callguard.checks.facts import PolicyTableError

VERSIONS_DIRNAME = "policy_versions"
_FILE = re.compile(r"^policy_table_v(\d+)\.yaml$")
STATUS_DE = {"draft": "Entwurf", "approved": "Freigegeben", "rejected": "Verworfen"}


class FourEyesError(ValueError):
    """Approval refused: no approver, the approver is the author, or a conflict with the live files."""


def same_person(a: str | None, b: str | None) -> bool:
    norm = lambda s: " ".join(str(s or "").split()).casefold()  # noqa: E731
    return bool(norm(a)) and norm(a) == norm(b)


@dataclass
class Version:
    n: int
    path: Path
    meta: dict[str, Any]
    extra_paths: dict[str, Path] = field(default_factory=dict)  # name -> stored copy in the versions dir

    @property
    def status(self) -> str:
        return str(self.meta.get("status") or "draft")

    @property
    def author(self) -> str:
        return str(self.meta.get("author") or "?")

    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def doc(self) -> dict[str, Any]:
        return pe.load_doc(self.path)

    def stored(self, name: str) -> bool:
        return name == "policy_table" or name in self.extra_paths or name in (self.meta.get("absent") or [])

    def text_of(self, name: str) -> str | None:
        """Stored text of one file (None: the file did not exist in this version)."""
        if name == "policy_table":
            return self.text()
        p = self.extra_paths.get(name)
        return p.read_text(encoding="utf-8") if p is not None and p.is_file() else None

    def bundle(self) -> dict[str, dict[str, Any]]:
        return {n: rb.parse_text(n, self.text_of(n)) for n in rb.NAMES if self.stored(n)}


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _read(p: Path) -> str | None:
    return p.read_text(encoding="utf-8") if p.is_file() else None


class VersionStore:
    def __init__(self, active_path: str | Path, versions_dir: str | Path | None = None,
                 audit_dir: str | Path | None = None, extras: dict[str, str | Path] | None = None):
        self.active_path = Path(active_path)
        self.dir = Path(versions_dir) if versions_dir else self.active_path.parent / VERSIONS_DIRNAME
        self.audit_dir = Path(audit_dir) if audit_dir else None
        self.extras = {str(k): Path(v) for k, v in (extras or {}).items() if k in rb.EXTRA_NAMES}
        self.paths = {"policy_table": self.active_path, **self.extras}

    # -- reading ---------------------------------------------------------------------------------

    def _meta_path(self, n: int) -> Path:
        return self.dir / f"policy_table_v{n}.meta.json"

    def _extra_path(self, n: int, name: str) -> Path:
        suffix = self.extras[name].suffix if name in self.extras else ".yaml"
        return self.dir / f"policy_table_v{n}.{name}{suffix}"

    def versions(self) -> list[Version]:
        out = []
        for p in sorted(self.dir.glob("policy_table_v*.yaml")) if self.dir.is_dir() else []:
            m = _FILE.match(p.name)
            if not m:
                continue
            n = int(m.group(1))
            try:
                meta = json.loads(self._meta_path(n).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {"version": n, "status": "draft", "author": "?"}
            extra = {name: q for name in rb.EXTRA_NAMES
                     for q in self.dir.glob(f"policy_table_v{n}.{name}.*") if not q.name.endswith(".tmp")}
            out.append(Version(n, p, meta, extra))
        return sorted(out, key=lambda v: v.n)

    def get(self, n: int) -> Version:
        v = next((v for v in self.versions() if v.n == n), None)
        if v is None:
            raise KeyError(f"Version {n} gibt es nicht")
        return v

    def active(self) -> Version | None:
        """The approved version whose content is live (the latest approval or snapshot)."""
        approved = [v for v in self.versions() if v.status == "approved"]
        return max(approved, key=lambda v: (str(v.meta.get("approved_at") or ""), v.n)) if approved else None

    def drafts(self) -> list[Version]:
        return [v for v in self.versions() if v.status == "draft"]

    def next_n(self) -> int:
        vs = self.versions()
        return (vs[-1].n + 1) if vs else 1

    def live_texts(self) -> dict[str, str | None]:
        return {name: _read(p) for name, p in self.paths.items()}

    def live_bundle(self) -> dict[str, dict[str, Any]]:
        return {name: rb.parse_text(name, t) for name, t in self.live_texts().items()}

    # -- writing ---------------------------------------------------------------------------------

    def _write(self, n: int, texts: dict[str, str | None], meta: dict[str, Any]) -> Version:
        path = self.dir / f"policy_table_v{n}.yaml"
        absent = []
        for name, text in texts.items():
            if name == "policy_table":
                _atomic_write(path, text or "")
            elif text is None:
                absent.append(name)
                self._extra_path(n, name).unlink(missing_ok=True)
            else:
                _atomic_write(self._extra_path(n, name), text)
        meta = {"version": n, **meta, "absent": absent, "file_hash": audit.file_hash(path)}
        _atomic_write(self._meta_path(n), json.dumps(meta, ensure_ascii=False, indent=1))
        return self.get(n)

    def _log(self, kind: str, user: str, **data: Any) -> None:
        if self.audit_dir is not None:
            audit.log_event(self.audit_dir, kind, user=user, policy_table=str(self.active_path), **data)

    def _validate(self, bundle: dict[str, dict[str, Any]]) -> None:
        from callguard.families import families_from_raw
        from callguard.routing import RoutingConfig

        pe.validate(bundle["policy_table"])
        try:
            if "keywords" in bundle or "criteria" in bundle:
                families_from_raw(bundle.get("keywords") or {}, (bundle.get("criteria") or {}).get("families") or {})
            if bundle.get("routing"):
                RoutingConfig.from_dict(bundle["routing"])
            if bundle.get("fact_policy"):
                from callguard import fact_policy as fpol

                fpol.parse_fact_policy(bundle["fact_policy"])
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise PolicyTableError(f"Konfiguration ungültig: {e}") from None

    def ensure_initial(self) -> Version:
        """Snapshot the live files as version 1 (first use) or as an ``external`` version (edited elsewhere)."""
        act = self.active()
        live = self.live_texts()
        pe.validate(pe.load_doc(self.active_path))  # a broken live table is reported, not versioned
        if act is not None and all(act.stored(n) and act.text_of(n) == t for n, t in live.items()):
            return act
        kind = "initial" if act is None else "external"
        changed = [n for n, t in live.items() if act is None or not act.stored(n) or act.text_of(n) != t]
        n = self.next_n()
        v = self._write(n, live, {
            "status": "approved", "kind": kind, "author": "Datei" if kind == "external" else "Ausgangsversion",
            "approver": None, "created": audit.now_iso(), "approved_at": audit.now_iso(), "changed_files": changed,
            "comment": ("Ausgangsversion (Dateien beim ersten Öffnen des Regelwerks)" if kind == "initial"
                        else "Ausserhalb des Regelwerks geändert: " + ", ".join(rb.FILE_DE[c] for c in changed)),
            "parent": act.n if act else None})
        self._log("policy_snapshot", "system", version=n, snapshot=kind, files=changed)
        return v

    def save_draft(self, bundle: dict[str, Any], author: str, comment: str = "", parent: int | None = None,
                   family_names: dict[str, str] | None = None, profile: str = "",
                   check_kinds: dict[str, str] | None = None) -> Version:
        """``bundle``: name -> parsed file (``policy_table`` required); a bare policy table is accepted too."""
        if "families" in bundle and "policy_table" not in bundle:
            bundle = {"policy_table": bundle}
        if not str(author or "").strip():
            raise FourEyesError("Bitte Ihren Namen angeben (Autor des Entwurfs).")
        base = self.get(parent) if parent else self.active()
        base_texts = {n: (base.text_of(n) if base is not None and base.stored(n) else t)
                      for n, t in self.live_texts().items()}
        base_bundle = {n: rb.parse_text(n, t) for n, t in base_texts.items()}
        full = {**base_bundle, **{n: d for n, d in bundle.items() if n in self.paths}}
        self._validate(full)
        texts: dict[str, str | None] = {}
        changed = []
        for name in self.paths:
            if full[name] == base_bundle[name]:
                texts[name] = base_texts[name]
            else:
                texts[name] = rb.dump_text(name, full[name], base_texts[name] or _read(self.paths[name]))
                changed.append(name)
        n = self.next_n()
        header = pe.header_of(texts["policy_table"] or "")
        header = "\n".join(line for line in header.splitlines() if not line.startswith("# Regelwerk-Version"))
        header = (header + "\n" if header else "") + f"# Regelwerk-Version {n} · verfasst von {author.strip()}"
        if "policy_table" in changed or not base:
            texts["policy_table"] = pe.dump_doc(full["policy_table"], header)
        diff = rb.diff_bundle(base_bundle, full, family_names, profile, check_kinds) if base else []
        v = self._write(n, texts, {
            "status": "draft", "kind": "edit", "author": author.strip(), "created": audit.now_iso(),
            "comment": comment.strip(), "parent": base.n if base else None, "approver": None, "diff": diff,
            "changed_files": changed})
        self._log("policy_draft", author.strip(), version=n, parent=v.meta["parent"], comment=comment.strip(),
                  diff=diff, files=changed)
        return v

    def approve(self, n: int, approver: str, note: str = "") -> Version:
        """Four eyes: the approver must be named and must not be the author. Writes the changed live files."""
        v = self.get(n)
        if v.status != "draft":
            raise FourEyesError(f"Version {n} ist {STATUS_DE.get(v.status, v.status)}, nicht Entwurf.")
        if not str(approver or "").strip():
            raise FourEyesError("Freigabe braucht den Namen der freigebenden Person.")
        if same_person(approver, v.author):
            raise FourEyesError(f"Vier-Augen-Prinzip: {v.author} hat Version {n} verfasst und kann sie nicht "
                                "selbst freigeben. Eine zweite Person muss freigeben.")
        try:
            self._validate({**self.live_bundle(), **v.bundle()})
        except PolicyTableError as e:
            raise FourEyesError(f"Version {n} ist ungültig: {e}") from None
        changed = [c for c in (v.meta.get("changed_files") or ["policy_table"]) if c in self.paths]
        base = self.get(v.meta["parent"]) if v.meta.get("parent") else None
        live = self.live_texts()
        conflicts = [c for c in changed if base is not None and base.stored(c) and base.text_of(c) != live[c]]
        merged_text: str | None = None
        if "policy_table" in conflicts and base is not None:
            # rules applied instantly meanwhile (Regeln tab) + a facts draft: merge per family and part
            merged = merge_tables(base.doc(), pe.load_doc(self.active_path), v.doc())
            if merged is not None:
                conflicts.remove("policy_table")
                merged_text = pe.dump_doc(merged, pe.header_of(v.text()))
        if conflicts:
            raise FourEyesError("Seit dem Entwurf wurde ausserhalb geändert: " + ", ".join(rb.FILE_DE[c] for c in conflicts)
                                + f". Bitte Version {n} verwerfen und den Entwurf auf der aktuellen Version neu erstellen.")
        before = self.active()
        texts = {name: (v.text_of(name) if name in changed else live[name]) for name in self.paths}
        if merged_text is not None:
            texts["policy_table"] = merged_text
        for name in changed:
            if texts[name] is None:
                self.paths[name].unlink(missing_ok=True)
            else:
                _atomic_write(self.paths[name], texts[name])
        meta = {**v.meta, "status": "approved", "approver": approver.strip(), "approved_at": audit.now_iso(),
                "approval_note": note.strip()}
        for k in ("file_hash", "absent", "version"):
            meta.pop(k, None)
        out = self._write(n, texts, meta)  # the version now equals the live files
        self._log("policy_approved", approver.strip(), version=n, author=v.author,
                  previous=before.n if before else None, note=note.strip(), diff=v.meta.get("diff") or [],
                  files=changed, active_hash=audit.file_hash(self.active_path))
        return out

    def reject(self, n: int, user: str, note: str = "") -> Version:
        v = self.get(n)
        if v.status != "draft":
            raise FourEyesError(f"Version {n} ist kein Entwurf.")
        meta = {**v.meta, "status": "rejected", "rejected_by": user.strip() or "?", "rejected_at": audit.now_iso(),
                "approval_note": note.strip()}
        _atomic_write(self._meta_path(n), json.dumps(meta, ensure_ascii=False, indent=1))
        self._log("policy_rejected", user.strip() or "?", version=n, author=v.author, note=note.strip())
        return self.get(n)

    def rollback(self, n: int, author: str, family_names: dict[str, str] | None = None,
                 profile: str = "") -> Version:
        """A new DRAFT with the content of version ``n`` (needs approval like any change)."""
        draft = self.save_draft(self.get(n).bundle(), author, comment=f"Zurücksetzen auf Version {n}",
                                family_names=family_names, profile=profile)
        return draft

    # -- rules: instant (no approval), audit-logged, versioned, one-click undo ----------------------------

    def apply_rules(self, doc: dict[str, Any], user: str, comment: str = "",
                    family_names: dict[str, str] | None = None, kind: str = "rules") -> Version:
        """Apply a RULES-only change to the live table at once (demo tab «Regeln»): no second person needed,
        but a version (status approved, ``instant: true``) and an audit event (``policy_rules_applied``) are
        written, so :meth:`undo_rules` can revert it. Any change to facts (questions, new or removed facts,
        Prüfarten) is refused: facts go through :meth:`save_draft` + :meth:`approve` (four eyes)."""
        from callguard import fact_policy as fpol

        if not str(user or "").strip():
            raise FourEyesError("Bitte Ihren Namen angeben (wird im Audit-Log protokolliert).")
        self.ensure_initial()
        live_doc = pe.load_doc(self.active_path)
        if not fpol.only_rules_changed(live_doc, doc):
            raise FourEyesError("Fakten ändern: Freigabe durch zweite Person nötig. Diese Änderung betrifft nicht "
                                "nur Regeln (Fragen, Fakten oder Prüfarten); bitte als Entwurf im Tab «Fakten» speichern.")
        pe.validate(doc)
        if fpol.rules_part(live_doc) == fpol.rules_part(doc):
            raise FourEyesError("Keine Änderung an den Regeln.")
        before = self.active()
        old_text = self.active_path.read_text(encoding="utf-8")
        header = "\n".join(line for line in pe.header_of(old_text).splitlines()
                           if not line.startswith("# Regelwerk-Version"))
        n = self.next_n()
        header = (header + "\n" if header else "") + f"# Regelwerk-Version {n} · Regeln geändert von {user.strip()}"
        text = pe.dump_doc(doc, header)
        diff = pe.diff_docs(live_doc, doc, family_names)
        _atomic_write(self.active_path, text)
        texts = {**self.live_texts(), "policy_table": text}
        now = audit.now_iso()
        v = self._write(n, texts, {
            "status": "approved", "kind": kind, "instant": True, "author": user.strip(), "approver": None,
            "created": now, "approved_at": now, "comment": comment.strip() or "Regeln geändert (sofort wirksam)",
            "parent": before.n if before else None, "diff": diff, "changed_files": ["policy_table"]})
        self._log("policy_rules_applied", user.strip(), version=n, previous=before.n if before else None,
                  change=kind, comment=comment.strip(), diff=diff, active_hash=audit.file_hash(self.active_path))
        return v

    def last_rule_change(self) -> Version | None:
        """The active version if it is an instant rule change (what «Rückgängig» reverts), else None."""
        act = self.active()
        return act if act is not None and act.meta.get("instant") and act.meta.get("parent") else None

    def undo_rules(self, user: str, family_names: dict[str, str] | None = None) -> Version:
        """One-click undo of the last instant rule change: the rules of its parent version, facts as live."""
        from callguard import fact_policy as fpol

        last = self.last_rule_change()
        if last is None:
            raise FourEyesError("Keine sofort wirksame Regeländerung zum Rückgängigmachen.")
        parent = self.get(int(last.meta["parent"]))
        live_doc = pe.load_doc(self.active_path)
        target = fpol.with_rules(live_doc, fpol.rules_part(parent.doc()))
        return self.apply_rules(target, user, comment=f"Rückgängig: Version {last.n} (Regeln wie Version {parent.n})",
                                family_names=family_names, kind="rules_undo")


def merge_tables(base: dict[str, Any], live: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any] | None:
    """Three-way merge of a policy table per family and part (facts / rules / other keys): a part changed on
    one side only takes that side; changed on both sides (differently) = conflict (None). Used when a facts
    draft is approved after rules were applied instantly. The result must validate, else None."""
    bf, lf, df = (dict((d or {}).get("families") or {}) for d in (base, live, draft))
    if set(bf) != set(lf):  # a Prüfart added / removed outside this draft
        return None
    out = {k: v for k, v in draft.items() if k != "families"}
    fams: dict[str, Any] = {}
    for fid, dfam in df.items():
        if fid not in bf:
            fams[fid] = dfam
            continue
        b, lv = bf[fid] or {}, lf[fid] or {}
        merged: dict[str, Any] = {}
        for key in dict.fromkeys([*dfam, *lv, *b]):
            bv, lvv, dv = b.get(key), lv.get(key), dfam.get(key)
            if lvv == bv:
                val = dv
            elif dv in (bv, lvv):
                val = lvv
            else:
                return None
            if val is not None:
                merged[key] = val
        fams[fid] = merged
    out["families"] = fams
    try:
        pe.validate(out)
    except PolicyTableError:
        return None
    return out
