"""Text normalization shared by the ASR evaluation (WER/CER) and the script <-> transcript alignment.

Pure string functions: no file access, no labels. ``callguard.eval_asr`` re-exports :func:`normalize_text`.
"""

from __future__ import annotations

import re

from callguard.checks.textnorm import fold

_NUMBERS: dict[str, int] = {
    # Standard German (folded: ü -> u, ß -> ss)
    "null": 0, "eins": 1, "zwei": 2, "zwo": 2, "drei": 3, "vier": 4, "funf": 5, "sechs": 6, "sieben": 7,
    "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwolf": 12, "dreizehn": 13, "vierzehn": 14,
    "funfzehn": 15, "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19, "zwanzig": 20,
    "dreissig": 30, "vierzig": 40, "funfzig": 50, "sechzig": 60, "siebzig": 70, "achtzig": 80,
    "neunzig": 90, "hundert": 100, "tausend": 1000,
    # Swiss German spellings. Left out on purpose: "eis"/"ein" (article), "nün" -> "nun" (= now),
    # "zäh" (= tough): mapping them would create more errors than it removes.
    "zwoi": 2, "zwoo": 2, "dru": 3, "foif": 5, "fuf": 5, "fuuf": 5, "sachs": 6, "nuun": 9, "sibe": 7, "sibni": 7, "zwolfi": 12,
    "drizah": 13, "drizehn": 13, "vierzah": 14, "fufzah": 15, "sachzah": 16, "sibezah": 17,
    "achtzah": 18, "nunzah": 19, "zwanzg": 20, "drissg": 30, "drissig": 30, "vierzg": 40, "fufzg": 50,
    "sachzg": 60, "sibezg": 70, "achtzg": 80, "nunzg": 90, "tusig": 1000, "tuusig": 1000,
}
_UNITS = {"ein": 1, "eis": 1, "zwei": 2, "zwoi": 2, "drei": 3, "dru": 3, "vier": 4, "funf": 5, "foif": 5,
          "fuf": 5, "fuuf": 5, "nuun": 9, "sechs": 6, "sachs": 6, "sieben": 7, "sibe": 7, "acht": 8, "neun": 9, "nun": 9}
_TENS = {k: v for k, v in _NUMBERS.items() if v in (20, 30, 40, 50, 60, 70, 80, 90)}
# "einundzwanzig", Swiss "einezwänzg" / "drüezwänzg"
_COMPOUND_RE = re.compile(rf"^({'|'.join(_UNITS)})(?:und|e)({'|'.join(_TENS)})$")
_THOUSANDS_RE = re.compile(r"(?<=\d)['’.  ](?=\d{3}\b)")
_APOSTROPHE_RE = re.compile(r"['’`´]")
_WORD_RE = re.compile(r"[^\W_]+")


def _number(tok: str) -> str:
    if tok in _NUMBERS:
        return str(_NUMBERS[tok])
    m = _COMPOUND_RE.match(tok)
    if m:
        return str(_UNITS[m.group(1)] + _TENS[m.group(2)])
    return tok


def normalize_text(text: str) -> str:
    """WER form: lowercase, umlauts folded (ä -> a, ß -> ss), punctuation dropped, whitespace collapsed,
    number words 0-20 + tens (German and Swiss spellings) as digits, "1'000" -> "1000", "%" -> prozent."""
    text = text.replace("%", " prozent ")
    text = _THOUSANDS_RE.sub("", text)
    text = _APOSTROPHE_RE.sub("", fold(text).lower())  # "geht's" -> "gehts" on both sides
    return " ".join(_number(t) for t in _WORD_RE.findall(text))
