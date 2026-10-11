"""Pattern check: spoken digit sequences (card numbers, one-time codes, PINs, references).

Customers read numbers aloud as digits ("4242 4242"), digit by digit ("vier, zwei, vier, zwei") or
in Swiss German ("sibe, drü, eis, nüün"). This check finds such runs, counts the digits and
classifies the object by length and by nearby words, e.g. a 6-digit run near "TAN" is probably a
one-time code. Amounts, dates and years are skipped. Every signal is weak and explainable on
purpose: whether the code was still valid or only a sample from a manual is for the LLM checks.

Only the families ``access`` and ``numbers`` are scored, and only if they are configured.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from callguard.checks.textnorm import Token, acronym_like, fold, is_acronym, segment_tokens, token_times, tokenize
from callguard.plugins import Check
from callguard.types import CheckResult, Family, FamilyScore, Finding, Segment, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.patterns")

ACCESS, NUMBERS = "access", "numbers"

# kind -> (family, score); scores stay low: digits alone never prove misconduct
SCORES: dict[str, tuple[str, float]] = {
    "card": (NUMBERS, 0.5),
    "iban": (NUMBERS, 0.15),
    "long_number": (NUMBERS, 0.15),
    "access_code": (ACCESS, 0.5),
    "access_code_customer": (ACCESS, 0.6),
    "pin": (ACCESS, 0.4),
    "pin_customer": (ACCESS, 0.5),
    "code_like": (NUMBERS, 0.2),
    "short_number": (NUMBERS, 0.1),
}

ACCESS_CUES = ("PIN", "TAN", "Code", "Bestätigungscode", "Passwort", "Kennwort", "Anmeldecode",
               "SMS-Code", "Zugangscode", "Sicherheitscode", "Freigabecode", "Geheimzahl",
               # English transcript views (translations, Whisper task=translate)
               "password", "passcode")
PIN_CUES = frozenset({"pin", "pincode", "geheimzahl"})  # a 4-5 digit run is only a secret near these
# "...code" compounds that are not secrets (QR-bill, BIC, ...)
NOT_SECRET_CODES = frozenset({"barcode", "qrcode", "landercode", "postcode", "zipcode", "swiftcode",
                              "bankcode", "farbcode", "dresscode", "quellcode", "rabattcode", "gutscheincode"})
MASKED_CUES = frozenset({"letzten", "letzte", "letschte", "letschti", "endziffern", "endziffer", "endstellen",
                         "endnummer", "endet", "schluss", "maskiert", "verdeckt", "last", "ending", "ends", "masked"})
SAMPLE_STEMS = ("beispiel", "muster", "abgelaufen", "abglaufe", "ungultig", "ungueltig",
                "example", "sample", "expired", "invalid")
UNIT_WORDS = frozenset({
    "franken", "franke", "fr", "chf", "rappen", "rp", "euro", "eur", "dollar", "usd", "prozent",
    "prozentpunkte", "uhr", "minute", "minuten", "minute", "sekunde", "sekunden", "stunde", "stunden",
    "stund", "tag", "tage", "tagen", "tag", "woche", "wochen", "wuche", "monat", "monate", "monaten",
    "jahr", "jahre", "jahren", "johr", "mal", "stuck", "kilo", "kg", "meter", "km", "grad", "mio", "mrd",
    # English views
    "francs", "franc", "cents", "dollars", "percent", "minutes", "seconds", "hours", "hour", "days", "day",
    "weeks", "week", "months", "month", "years", "year", "times", "million", "billion",
})
MONTHS = frozenset({"januar", "janner", "februar", "marz", "maerz", "merz", "april", "mai", "juni",
                    "juli", "august", "september", "oktober", "november", "dezember",
                    "january", "february", "march", "june", "july", "october", "december"})
CURRENCY_BEFORE = frozenset({"chf", "fr", "eur", "usd", "franken"})
CONNECTORS = frozenset({"und", "and"})
MAX_RUN_GAP = 1.5  # seconds: a digit run may continue into the next ASR segment of the same speaker

_UNITS = {
    "null": "0", "eins": "1", "eis": "1", "zwei": "2", "zwo": "2", "zwoi": "2", "zwöi": "2", "drei": "3",
    "drü": "3", "drüü": "3", "vier": "4", "fünf": "5", "füf": "5", "füüf": "5", "foif": "5", "föif": "5",
    "sechs": "6", "sächs": "6", "sieben": "7", "siebe": "7", "sibe": "7", "acht": "8", "neun": "9",
    "nün": "9", "nüün": "9", "zehn": "10", "zäh": "10", "elf": "11", "zwölf": "12",
    # English (translated views): units and teens only. "twenty four" would read as 20 + 4 = "204",
    # so tens are left out; digit-by-digit dictation ("four two four two") is the case that matters.
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
}
_UNIT_STEMS = {"ein": "1", "eine": "1", "eis": "1", **{k: v for k, v in _UNITS.items() if len(v) == 1}}
_TEEN_STEMS = {"drei": "3", "dri": "3", "drü": "3", "vier": "4", "fünf": "5", "füf": "5", "föif": "5",
               "foif": "5", "sech": "6", "säch": "6", "sieb": "7", "sib": "7", "sibe": "7", "siebe": "7",
               "acht": "8", "neun": "9", "nün": "9", "nüün": "9"}
_TENS = {"zwanzig": "2", "zwänzg": "2", "zwanzg": "2", "dreissig": "3", "drissg": "3", "driissg": "3",
         "vierzig": "4", "vierzg": "4", "fünfzig": "5", "füfzg": "5", "foifzg": "5", "föifzg": "5",
         "sechzig": "6", "sächzg": "6", "sechzg": "6", "siebzig": "7", "sibezg": "7", "siebezg": "7",
         "siebzg": "7", "achtzig": "8", "achtzg": "8", "neunzig": "9", "nünzg": "9", "nüünzg": "9"}


def _alt(words: Any) -> str:
    return "|".join(sorted(map(re.escape, words), key=len, reverse=True))


_TEEN_RE = re.compile(rf"^({_alt(_TEEN_STEMS)})(zehn|zäh)$")
_TENS_RE = re.compile(rf"^(?:({_alt(_UNIT_STEMS)})(?:und|e|ä)?)?({_alt(_TENS)})$")
_AMOUNT_RE = re.compile(r"hundert|tausend|tuusig|tusig|million|milliard|hundred|thousand|billion")
_IBAN_PREFIX_RE = re.compile(r"^[a-z]{2}\d{2}$")
# char spans that look like digits but are amounts/dates: 12,50 / 8'000 / 30.09.2026 / 12/27
_NOT_A_CODE_RE = re.compile(
    r"(?<![\d.,'’])\d+[.,]\d{1,2}(?![.,]?\d)"
    r"|\d{1,3}(?:['’]\d{3})+(?:[.,]\d+)?"
    r"|\b\d{1,2}\.\s?\d{1,2}\.(?:\s?\d{2,4})?"
    r"|\b\d{1,2}\s?/\s?\d{2,4}\b")
_AMOUNT = "amount"


def _ascii_variants(word: str) -> set[str]:
    """ASR output without umlauts: 'fuenf', 'funf' (but never 'nun' for nün: that is 'now')."""
    out = {word, word.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")}
    folded = fold(word)
    if folded not in {"nun", "sachs", "zah"}:
        out.add(folded)
    return out


_NUMBER_WORDS = {v: d for w, d in _UNITS.items() for v in _ascii_variants(w)}


def number_value(raw: str) -> str | None:
    """Digit string of a spoken German / Swiss German number word 0-99 ('zweiundvierzig' -> '42'),
    ``"amount"`` for hundreds/thousands (an amount, not a digit sequence), else None."""
    w = unicodedata.normalize("NFC", raw).lower().replace("ß", "ss")
    if w in _NUMBER_WORDS:
        return _NUMBER_WORDS[w]
    if m := _TEEN_RE.match(w):
        return "1" + _TEEN_STEMS[m.group(1)]
    if m := _TENS_RE.match(w):
        return _TENS[m.group(2)] + (_UNIT_STEMS[m.group(1)] if m.group(1) else "0")
    if _AMOUNT_RE.search(w):
        return _AMOUNT
    return None


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


@dataclass
class _Seg:
    seg: Segment
    text: str
    toks: list[Token]
    excluded: list[tuple[int, int]]


@dataclass
class _Run:
    items: list[tuple[int, int, str]] = field(default_factory=list)  # (segment idx, token idx, digits)

    @property
    def digits(self) -> str:
        return "".join(d for _, _, d in self.items)

    @property
    def seg_idxs(self) -> list[int]:
        return list(dict.fromkeys(s for s, _, _ in self.items))


class PatternCheck(Check):
    plugin_kind = "check"
    plugin_type = "patterns"

    def __init__(self, ctx: "Context", *, access_cue_window: int = 2, confidence: float = 0.35,
                 absent_confidence: float = 0.2, sample_factor: float = 0.5,
                 access_cues: list[str] | None = None, name: str | None = None, weight: float = 1.0,
                 enabled: bool = True):
        if int(access_cue_window) < 0:
            raise ValueError(f"access_cue_window must be >= 0, got {access_cue_window}")
        for key, v in (("confidence", confidence), ("absent_confidence", absent_confidence),
                       ("sample_factor", sample_factor)):
            if not 0 <= float(v) <= 1:
                raise ValueError(f"{key} must be in 0..1, got {v}")
        super().__init__(ctx, name=name, weight=weight, enabled=enabled, access_cue_window=access_cue_window,
                         confidence=confidence, absent_confidence=absent_confidence,
                         sample_factor=sample_factor, access_cues=access_cues)
        self.access_cue_window = int(access_cue_window)
        self.confidence = float(confidence)
        self.absent_confidence = float(absent_confidence)
        self.sample_factor = float(sample_factor)
        self.cues = [tuple(tokenize(c)) for c in (ACCESS_CUES if access_cues is None else access_cues)]
        self.cues = [c for c in self.cues if c]

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        """Keyword edits must not rerun this check: only which of its families are enabled matters."""
        return {"params": self.cache_params(),
                "families": sorted(f.id for f in families if f.enabled and f.id in (ACCESS, NUMBERS))}

    # -- cues -------------------------------------------------------------------------------------

    def cue_at(self, toks: list[Token], i: int) -> int:
        """Length in tokens of an access cue starting at ``toks[i]`` (0 = none)."""
        for cue in self.cues:
            n = len(cue)
            window = toks[i:i + n]
            if len(window) == n and all(
                    t.text == c.text and (not is_acronym(c.raw) or acronym_like(t)) for t, c in zip(window, cue)):
                if n == 1 and cue[0].text == "code" and i > 0 and toks[i - 1].text == "qr":
                    continue
                return n
            if (n == 1 and not is_acronym(cue[0].raw) and len(cue[0].text) >= 4
                    and toks[i].text.endswith(cue[0].text) and toks[i].text not in NOT_SECRET_CODES):
                return 1  # compounds: Einmalcode, Aktivierungscode, Bankpasswort
        return 0

    def segment_cues(self, s: _Seg) -> list[str]:
        cues, i = [], 0
        while i < len(s.toks):
            n = self.cue_at(s.toks, i)
            if n:
                cues.append(s.text[s.toks[i].start:s.toks[i + n - 1].end])
                i += n
            else:
                i += 1
        return cues

    # -- runs -------------------------------------------------------------------------------------

    @staticmethod
    def _excluded(s: _Seg, t: Token) -> bool:
        return any(a < t.end and t.start < b for a, b in s.excluded)

    def find_runs(self, segs: list[_Seg]) -> list[_Run]:
        """Maximal sequences of digit tokens / number words, joined by spaces, commas, hyphens or 'und'."""
        runs: list[_Run] = []
        cur: _Run | None = None
        connector = False
        for si, s in enumerate(segs):
            for ti, t in enumerate(s.toks):
                digits = t.raw if t.is_digits else number_value(t.raw)
                if digits and digits != _AMOUNT and not self._excluded(s, t):
                    if cur and not self._continues(segs, cur.items[-1], (si, ti)):
                        runs.append(cur)
                        cur = None
                    cur = cur or _Run()
                    cur.items.append((si, ti, digits))
                    connector = False
                elif cur and not connector and t.text in CONNECTORS and cur.items[-1][0] == si:
                    connector = True
                else:
                    if cur:
                        runs.append(cur)
                    cur, connector = None, False
        if cur:
            runs.append(cur)
        return runs

    @staticmethod
    def _continues(segs: list[_Seg], a: tuple[int, int, str], b: tuple[int, int]) -> bool:
        (sa, ta, _), (sb, tb) = a, b
        A, B = segs[sa], segs[sb]
        ta_tok, tb_tok = A.toks[ta], B.toks[tb]
        if sa == sb:
            sep = A.text[ta_tok.end:tb_tok.start]
        else:
            if (A.seg.speaker, A.seg.role) != (B.seg.speaker, B.seg.role) or B.seg.start - A.seg.end > MAX_RUN_GAP:
                return False
            if sb != sa + 1 or ta != len(A.toks) - 1 or tb != 0:
                return False
            sep = A.text[ta_tok.end:] + " " + tb_tok.sep
        if any(c in ":;!?" for c in sep):
            return False  # "die letzten vier: vier, zwei, vier, zwei"
        # a full stop ends a sentence, except between digit groups ASR wrote as "4242. 4242."
        return "." not in sep or (ta_tok.is_digits and tb_tok.is_digits)

    def is_amount_or_date(self, segs: list[_Seg], run: _Run) -> bool:
        s0, t0, _ = run.items[0]
        s1, t1, _ = run.items[-1]
        first, last = segs[s0], segs[s1]
        nxt = last.toks[t1 + 1] if t1 + 1 < len(last.toks) else None
        prv = first.toks[t0 - 1] if t0 > 0 else None
        after = last.text[last.toks[t1].end:nxt.start if nxt else len(last.text)]
        before = first.toks[t0].sep
        if nxt and (nxt.text in UNIT_WORDS or nxt.text in MONTHS or number_value(nxt.raw) == _AMOUNT):
            return True
        if prv and (prv.text in CURRENCY_BEFORE or prv.text in MONTHS):
            return True
        if any(c in after for c in "%€$£") or any(c in before for c in "€$£"):
            return True
        tok = first.toks[t0]
        return len(run.items) == 1 and tok.is_digits and len(tok.raw) == 4 and 1900 <= int(tok.raw) <= 2099

    # -- classification ---------------------------------------------------------------------------

    def classify(self, segs: list[_Seg], run: _Run, cues: dict[int, list[str]]) -> tuple[str, dict[str, Any]] | None:
        digits = run.digits
        n = len(digits)
        idxs = run.seg_idxs
        s0, t0, _ = run.items[0]
        customer = any(segs[i].seg.role == "customer" for i in idxs)
        near = [i for i in range(idxs[0] - self.access_cue_window, idxs[-1] + self.access_cue_window + 1)
                if cues.get(i)]
        near.sort(key=lambda i: (abs(i - s0), i > s0))  # nearest, preferring the cue before the digits
        cue = cues[near[0]][0] if near else None
        pin_cue = next((c for i in near for c in cues[i] if fold(c).lower() in PIN_CUES), None)
        context = [t for i in range(max(0, idxs[0] - 1), idxs[-1] + 1) for t in segs[i].toks]
        masked = next((t.raw for t in context if t.text in MASKED_CUES), None)
        prv = segs[s0].toks[t0 - 1] if t0 > 0 else None
        iban = (prv is not None and bool(_IBAN_PREFIX_RE.match(prv.text))) or any(
            t.text == "iban" for t in segs[s0].toks)
        detail: dict[str, Any] = {"digits": digits, "n_digits": n, "cue": None, "role": segs[s0].seg.role}

        if n >= 9 and iban:
            kind = "iban"
        elif n >= 13:
            kind = "card"
            detail["luhn"] = luhn_ok(digits)
        elif n >= 9:
            kind = "long_number"
        elif n >= 6:
            kind = ("access_code_customer" if customer else "access_code") if cue else "code_like"
            detail["cue"] = cue
        elif n >= 4:
            if pin_cue and not masked:
                kind = "pin_customer" if customer else "pin"
                detail["cue"] = pin_cue
            else:
                kind = "short_number"
                detail["masked_cue"] = masked
        else:
            return None
        if SCORES[kind][0] == ACCESS:
            near_toks = [t for i in range(max(0, idxs[0] - 1), min(len(segs), idxs[-1] + 2)) for t in segs[i].toks]
            detail["sample_cue"] = next((t.raw for t in near_toks if any(st in t.text for st in SAMPLE_STEMS)), None)
        detail["kind"] = kind
        return kind, detail

    @staticmethod
    def reason(kind: str, d: dict[str, Any]) -> str:
        n = d["n_digits"]
        text = {
            "card": f"Mögliche vollständige Kartennummer ({n} Ziffern) vorgelesen",
            "iban": f"Mögliche IBAN/Kontonummer ({n} Ziffern) vorgelesen",
            "long_number": f"Längere Ziffernfolge ({n} Ziffern): Konto-, Telefon- oder Referenznummer?",
            "access_code": f"Möglicher Zugangscode ({n} Ziffern) vorgelesen, Stichwort «{d['cue']}»",
            "access_code_customer": f"Kundschaft liest möglichen Zugangscode ({n} Ziffern) vor, Stichwort «{d['cue']}»",
            "pin": f"Mögliche PIN ({n} Ziffern) vorgelesen, Stichwort «{d['cue']}»",
            "pin_customer": f"Kundschaft liest mögliche PIN ({n} Ziffern) vor, Stichwort «{d['cue']}»",
            "code_like": f"Ziffernfolge ({n} Ziffern) ohne Zugangs-Stichwort: Code oder Referenz?",
            "short_number": f"Kurze Ziffernfolge ({n} Ziffern): Kartenendziffern oder Referenz",
        }[kind]
        if d.get("luhn"):
            text += " (Luhn-Prüfziffer gültig)"
        if d.get("masked_cue"):
            text += f" – «{d['masked_cue']}» deutet auf maskierte Endziffern"
        if d.get("sample_cue"):
            text += f" – Hinweis auf Muster/abgelaufenen Wert («{d['sample_cue']}»)"
        return text

    # -- check ------------------------------------------------------------------------------------

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        fam_ids = {f.id for f in families if f.enabled} & {ACCESS, NUMBERS}
        result = CheckResult(check=self.name, type=self.plugin_type, meta={})
        if not fam_ids:
            result.meta["note"] = "neither 'access' nor 'numbers' family configured"
            return result
        errors: list[str] = []
        segs: list[_Seg] = []
        for seg in transcript.segments:
            try:
                text, toks = segment_tokens(seg)
                excluded = [m.span() for m in _NOT_A_CODE_RE.finditer(text)]
                segs.append(_Seg(seg, text, toks, excluded))
            except Exception as e:  # one odd segment must not cost the whole call its number evidence
                log.warning("patterns: segment %s skipped: %r", seg.id, e)
                errors.append(f"segment {seg.id}: {e!r}")
        cues = {i: c for i, s in enumerate(segs) if (c := self.segment_cues(s))}

        findings: list[Finding] = []
        skipped: Counter[str] = Counter()
        for run in self.find_runs(segs):
            try:
                if self.is_amount_or_date(segs, run):
                    skipped["amount_or_date"] += 1
                    continue
                classified = self.classify(segs, run, cues)
                if classified is None:
                    continue
                kind, detail = classified
                family, score = SCORES[kind]
                if family not in fam_ids:
                    skipped[f"family_{family}_not_configured"] += 1
                    continue
                if detail.get("sample_cue"):
                    score *= self.sample_factor
                findings.append(self.finding(segs, run, family, score, kind, detail))
            except Exception as e:
                log.warning("patterns: run %s skipped: %r", run.digits, e)
                errors.append(f"run {run.digits}: {e!r}")

        result.findings = findings
        for fid in sorted(fam_ids):
            result.family_scores[fid] = self.family_score([f for f in findings if f.family == fid])
        result.meta["access_cues"] = {segs[i].seg.id: c for i, c in cues.items()}
        if skipped:
            result.meta["skipped_runs"] = dict(skipped)
        if errors:
            result.meta["errors"] = errors
        return result

    def finding(self, segs: list[_Seg], run: _Run, family: str, score: float, kind: str,
                detail: dict[str, Any]) -> Finding:
        (s0, t0, _), (s1, t1, _) = run.items[0], run.items[-1]
        first, last = segs[s0], segs[s1]
        start = token_times(first.seg, first.toks, t0, t0)[0]
        end = token_times(last.seg, last.toks, t1, t1)[1]
        if s0 == s1:
            matched = first.text[first.toks[t0].start:first.toks[t1].end]
        else:
            matched = first.text[first.toks[t0].start:] + " " + last.text[:last.toks[t1].end]
        detail["matched_text"] = matched.strip()
        return Finding(check=self.name, family=family, score=round(score, 4),
                       segment_ids=[segs[i].seg.id for i in run.seg_idxs], start=start, end=end,
                       reason=self.reason(kind, detail), detail=detail)

    def family_score(self, findings: list[Finding]) -> FamilyScore:
        if not findings:
            return FamilyScore(score=0.0, confidence=self.absent_confidence,
                               reason="Keine auffälligen Ziffernfolgen gefunden")
        top = max(findings, key=lambda f: f.score)
        reason = top.reason + (f" (+{len(findings) - 1} weitere)" if len(findings) > 1 else "")
        return FamilyScore(
            score=top.score, confidence=self.confidence, reason=reason,
            segment_ids=list(dict.fromkeys(s for f in findings for s in f.segment_ids)),
            detail={"runs": len(findings), "kinds": dict(Counter(f.detail["kind"] for f in findings))},
        )
