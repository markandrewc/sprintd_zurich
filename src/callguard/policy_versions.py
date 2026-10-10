"""Versions and four-eyes approval of the policy table (UI page "Regelwerk").

Storage, next to the active table (``config/policy_table.yaml`` -> ``config/policy_versions/``)::

    policy_table_v<N>.yaml        the full table of version N (what would become active)
    policy_table_v<N>.meta.json   {version, status, author, created, comment, parent, approver, approved_at, ...}

Status: ``draft`` (Entwurf) -> ``approved`` (Freigegeben, by a second person: the approver must differ from
the author) or ``rejected`` (Verworfen). The ACTIVE file is only ever written by :meth:`VersionStore.approve`,
so the live pipeline (which reads ``config/policy_table.yaml``) only runs approved versions. "Zurücksetzen
auf Version N" creates a new draft with N's content, which needs approval like any other change.

Version 1 is a snapshot of the active file the first time the store is opened (``kind: initial``); if the
active file was edited by hand afterwards, the next open snapshots it as ``kind: external`` (it is live
already, so it is recorded as approved, marked as not approved in the UI). Every save / approval /
rejection is an audit event (``policy_draft``, ``policy_approved``, ``policy_rejected``) with the plain
German diff.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from callguard import audit
from callguard import policy_edit as pe
from callguard.checks.facts import PolicyTableError

VERSIONS_DIRNAME = "policy_versions"
_FILE = re.compile(r"^policy_table_v(\d+)\.yaml$")
STATUS_DE = {"draft": "Entwurf", "approved": "Freigegeben", "rejected": "Verworfen"}


class FourEyesError(ValueError):
    """Approval refused: no approver, or the approver is the author."""


def same_person(a: str | None, b: str | None) -> bool:
    norm = lambda s: " ".join(str(s or "").split()).casefold()  # noqa: E731
    return bool(norm(a)) and norm(a) == norm(b)


@dataclass
class Version:
    n: int
    path: Path
    meta: dict[str, Any]

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


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class VersionStore:
    def __init__(self, active_path: str | Path, versions_dir: str | Path | None = None,
                 audit_dir: str | Path | None = None):
        self.active_path = Path(active_path)
        self.dir = Path(versions_dir) if versions_dir else self.active_path.parent / VERSIONS_DIRNAME
        self.audit_dir = Path(audit_dir) if audit_dir else None

    # -- reading ---------------------------------------------------------------------------------

    def _meta_path(self, n: int) -> Path:
        return self.dir / f"policy_table_v{n}.meta.json"

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
            out.append(Version(n, p, meta))
        return sorted(out, key=lambda v: v.n)

    def get(self, n: int) -> Version:
        v = next((v for v in self.versions() if v.n == n), None)
        if v is None:
            raise KeyError(f"Version {n} gibt es nicht")
        return v

    def active(self) -> Version | None:
        """The approved version whose content is in the active file (the latest approval)."""
        approved = [v for v in self.versions() if v.status == "approved"]
        return max(approved, key=lambda v: (str(v.meta.get("approved_at") or ""), v.n)) if approved else None

    def drafts(self) -> list[Version]:
        return [v for v in self.versions() if v.status == "draft"]

    def next_n(self) -> int:
        vs = self.versions()
        return (vs[-1].n + 1) if vs else 1

    # -- writing ---------------------------------------------------------------------------------

    def _write(self, n: int, text: str, meta: dict[str, Any]) -> Version:
        path = self.dir / f"policy_table_v{n}.yaml"
        _atomic_write(path, text)
        meta = {"version": n, **meta, "file_hash": audit.file_hash(path)}
        _atomic_write(self._meta_path(n), json.dumps(meta, ensure_ascii=False, indent=1))
        return Version(n, path, meta)

    def _log(self, kind: str, user: str, **data: Any) -> None:
        if self.audit_dir is not None:
            audit.log_event(self.audit_dir, kind, user=user, policy_table=str(self.active_path), **data)

    def ensure_initial(self) -> Version:
        """Snapshot the active file as version 1 (first use) or as an ``external`` version (hand edit)."""
        act = self.active()
        current = self.active_path.read_text(encoding="utf-8")
        pe.validate(pe.load_doc(self.active_path))  # a broken active file is reported, not versioned
        if act is not None and act.text() == current:
            return act
        kind = "initial" if act is None else "external"
        n = self.next_n()
        v = self._write(n, current, {
            "status": "approved", "kind": kind, "author": "Datei" if kind == "external" else "Ausgangsversion",
            "approver": None, "created": audit.now_iso(), "approved_at": audit.now_iso(),
            "comment": ("Ausgangsversion (Datei beim ersten Öffnen des Regelwerks)" if kind == "initial"
                        else "Aktive Datei wurde ausserhalb der Oberfläche geändert"),
            "parent": act.n if act else None})
        self._log("policy_snapshot", "system", version=n, snapshot=kind)
        return v

    def save_draft(self, doc: dict[str, Any], author: str, comment: str = "", parent: int | None = None,
                   family_names: dict[str, str] | None = None) -> Version:
        if not str(author or "").strip():
            raise FourEyesError("Bitte Ihren Namen angeben (Autor des Entwurfs).")
        pe.validate(doc)
        base = self.get(parent) if parent else self.active()
        n = self.next_n()
        header = pe.header_of(self.active_path.read_text(encoding="utf-8"))
        header = "\n".join(line for line in header.splitlines() if not line.startswith("# Regelwerk-Version"))
        header = (header + "\n" if header else "") + f"# Regelwerk-Version {n} · verfasst von {author.strip()}"
        diff = pe.diff_docs(base.doc(), doc, family_names) if base else []
        v = self._write(n, pe.dump_doc(doc, header), {
            "status": "draft", "kind": "edit", "author": author.strip(), "created": audit.now_iso(),
            "comment": comment.strip(), "parent": base.n if base else None, "approver": None, "diff": diff})
        self._log("policy_draft", author.strip(), version=n, parent=v.meta["parent"], comment=comment.strip(),
                  diff=diff)
        return v

    def approve(self, n: int, approver: str, note: str = "") -> Version:
        """Four eyes: the approver must be named and must not be the author. Writes the active file."""
        v = self.get(n)
        if v.status != "draft":
            raise FourEyesError(f"Version {n} ist {STATUS_DE.get(v.status, v.status)}, nicht Entwurf.")
        if not str(approver or "").strip():
            raise FourEyesError("Freigabe braucht den Namen der freigebenden Person.")
        if same_person(approver, v.author):
            raise FourEyesError(f"Vier-Augen-Prinzip: {v.author} hat Version {n} verfasst und kann sie nicht "
                                "selbst freigeben. Eine zweite Person muss freigeben.")
        try:
            pe.validate(v.doc())
        except PolicyTableError as e:
            raise FourEyesError(f"Version {n} ist ungültig: {e}") from None
        before = self.active()
        _atomic_write(self.active_path, v.text())
        meta = {**v.meta, "status": "approved", "approver": approver.strip(), "approved_at": audit.now_iso(),
                "approval_note": note.strip()}
        meta.pop("file_hash", None)
        out = self._write(n, v.text(), meta)
        self._log("policy_approved", approver.strip(), version=n, author=v.author,
                  previous=before.n if before else None, note=note.strip(), diff=v.meta.get("diff") or [],
                  active_hash=audit.file_hash(self.active_path))
        return out

    def reject(self, n: int, user: str, note: str = "") -> Version:
        v = self.get(n)
        if v.status != "draft":
            raise FourEyesError(f"Version {n} ist kein Entwurf.")
        meta = {**v.meta, "status": "rejected", "rejected_by": user.strip() or "?", "rejected_at": audit.now_iso(),
                "approval_note": note.strip()}
        meta.pop("file_hash", None)
        out = self._write(n, v.text(), meta)
        self._log("policy_rejected", user.strip() or "?", version=n, author=v.author, note=note.strip())
        return out

    def rollback(self, n: int, author: str, family_names: dict[str, str] | None = None) -> Version:
        """A new DRAFT with the content of version ``n`` (needs approval like any change)."""
        return self.save_draft(self.get(n).doc(), author, comment=f"Zurücksetzen auf Version {n}",
                               family_names=family_names)
