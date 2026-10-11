"""Text normalization and tokenization shared by the rule checks.

Swiss German scripts, Standard German ASR output and an officer's keyword list never agree on
umlauts, quotes or hyphenation ("Prüefig" / "Prüfung", «Muster» / "Muster", "Kreditkarten-Nummer").
Matching therefore happens on folded tokens, while every token remembers where it came from (word
index with timestamps, or char offsets) so a hit can be cut out of the audio precisely.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace

from callguard.types import Segment, Word

# a token is a run of letters/digits; combining marks are kept so NFD input ("ä") stays one token
_TOKEN_RE = re.compile(r"[^\W_](?:[^\W_]|[̀-ͯ])*")
SENTENCE_END = frozenset(".!?;")


def fold(text: str) -> str:
    """ß -> ss and strip diacritics (ä -> a, é -> e). Keeps case."""
    text = text.replace("ß", "ss").replace("ẞ", "SS")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize(text: str, *, case_sensitive: bool = False) -> str:
    """Matching form of a text: folded tokens joined by single spaces, punctuation and quotes dropped."""
    return " ".join(t.cased if case_sensitive else t.text for t in tokenize(text))


@dataclass(frozen=True, slots=True)
class Token:
    text: str  # matching form: lowercased + folded
    cased: str  # folded, case kept (case-sensitive keywords)
    raw: str  # surface form exactly as in the source text
    start: int  # char offsets into the tokenized source text
    end: int
    sep: str  # source text between the previous token (or text start) and this token
    boundary: bool  # a sentence starts here: first token, or . ! ? ; since the previous token
    word_first: int | None = None  # Segment.words indices covered, when tokenized from words
    word_last: int | None = None

    @property
    def is_digits(self) -> bool:
        return self.raw.isascii() and self.raw.isdigit()


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    prev_end = 0
    for m in _TOKEN_RE.finditer(text):
        raw, sep = m.group(0), text[prev_end:m.start()]
        cased = fold(raw)
        tokens.append(Token(text=cased.lower(), cased=cased, raw=raw, start=m.start(), end=m.end(),
                            sep=sep, boundary=not tokens or any(c in SENTENCE_END for c in sep)))
        prev_end = m.end()
    return tokens


def tokenize_words(words: list[Word]) -> tuple[str, list[Token]]:
    """Tokenize the joined word texts and map every token back to the words it spans.

    Our ASR backends emit words without leading space (join with " "). Raw Whisper words carry
    their own leading space and continuation pieces have none (" Quartals" + "zahlen"): if any word
    brings a leading space the texts are concatenated as they are, so pieces form one token, timed
    from the first to the last piece.
    """
    parts: list[str] = []
    owner: list[int] = []
    raw_style = any(w.text[:1].isspace() for w in words)
    for i, w in enumerate(words):
        if parts and not raw_style and not parts[-1][-1:].isspace() and not w.text[:1].isspace():
            parts.append(" ")
            owner.append(i)
        parts.append(w.text)
        owner.extend([i] * len(w.text))
    text = "".join(parts)
    return text, [replace(t, word_first=owner[t.start], word_last=owner[t.end - 1]) for t in tokenize(text)]


def segment_tokens(seg: Segment) -> tuple[str, list[Token]]:
    """Tokens of one segment, from word timestamps when the ASR delivered them, else from the text.

    Returns the tokenized source text as well, so callers can slice matched text and separators.
    """
    if seg.words:
        return tokenize_words(seg.words)
    return seg.text, tokenize(seg.text)


def token_times(seg: Segment, tokens: list[Token], first: int, last: int) -> tuple[float, float]:
    """Audio span of ``tokens[first..last]`` (inclusive): word timestamps if known, else the segment."""
    a, b = tokens[first], tokens[last]
    if seg.words and a.word_first is not None and b.word_last is not None:
        return seg.words[a.word_first].start, seg.words[b.word_last].end
    return seg.start, seg.end


def is_acronym(phrase_token: str) -> bool:
    """Short all-caps list entries such as PIN, TAN, BIN, WIR: matched case-aware, see :func:`acronym_like`."""
    letters = [c for c in phrase_token if c.isalpha()]
    return bool(letters) and len(phrase_token) <= 4 and all(c.isupper() for c in letters)


def acronym_like(tok: Token) -> bool:
    """Could this token be the spoken acronym rather than an ordinary word?

    All caps always counts. A capitalized token counts only mid-sentence: German capitalizes nouns,
    so "die Pin" is the noun, while "Wir"/"Bin" at a sentence start are just the pronoun/verb
    (the reason short acronyms cannot be matched case-insensitively).
    """
    letters = [c for c in tok.cased if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return True
    return tok.cased[:1].isupper() and not tok.boundary
