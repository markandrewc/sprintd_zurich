"""Dialect script turns <-> ASR segments: a monotonic alignment that gives every script turn a time span.

Pure: text and times in, spans out. It never reads files, labels or results (no ``Skript_mit_Sollbewertung``,
no expected labels); callers pass the turns. Used by the evidence hit-rate evaluation (``callguard evidence-eval``)
and, display only, by the demo's Swiss German transcript view (``callguard.demo.original_script``).

Alignment (dialect script turn -> ASR segments of Standard German; no word timings for the script):
a monotonic dynamic-programming alignment that assigns every ASR segment to exactly one script turn,
turns in script order (turns may be skipped, e.g. a short "Ja." merged into a neighbour segment). Score of
segment i on turn j =

    W_SIM  * token overlap(i, j)     fuzzy (rapidfuzz ratio >= 80) match of the segment's content tokens
                                     (>= 4 letters or digits, stopwords dropped, umlauts folded, number
                                     words -> digits incl. Swiss spellings) against the turn's tokens,
                                     IDF-weighted over turns, so names / amounts / keywords dominate
  - W_POS  * |relative position of the segment in the call - relative position of the turn in the
             script| (turn position by cumulative characters; the case audio is synthetic speech at a
             near-constant rate, so this is a strong prior)
  + W_ROLE * (+1 speaker role matches, -1 mismatch, 0 unknown) (diarization roles can be wrong: small)
  - W_SKIP per skipped turn.

A turn's time span = [first start, last end] of its segments; a turn with no segment gets the gap
between its neighbours (``aligned=False``). The weights were set once by reasoning, not fitted.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
from rapidfuzz import fuzz
from rapidfuzz.process import cdist

from callguard.data import Turn
from callguard.normalize import normalize_text
from callguard.types import Segment

W_SIM, W_POS, W_ROLE, W_SKIP = 1.0, 2.0, 0.15, 0.3
MATCH_RATIO = 80.0

# function words (folded, lowercase) of Standard German and the script's Swiss German, >= 4 letters
_STOP = set("""
aber alle allem allen aller alles also auch bitte dann darum dass dein deine dem den denn der des dessen
dich dies diese diesem diesen dieser dieses doch dort durch eine einem einen einer eines etwa euch eure
gibt habe haben hast hat hatte hier ihnen ihre ihrem ihren ihrer jetzt kann kein keine konnen konnte machen
mein meine mich mir nach nicht noch nur oder ohne schon sehr sein seine sich sie sind soll sollen ueber uber
unser unsere viel vom von vor wann warum was weil welche wenn werden wieder wird wie wir wird wo zum zur
genau gerne guten grueezi gruezi ganz jetzt eben einfach mal mussen muss
au aber isch hesch hend hand hani hets het gseit gsi gsii sii sind nod nid nöd ned scho denn emal mol
mache mached mues muesed chan chond chonnt cha chunt gaht gahts gits gits halt eifach ebe sicher grad
dass das wo wott wett wetted mini mis dini dis ihri ires ihres ihne ihnen eusi euse oder und
""".split())


# --------------------------------------------------------------------------------------------
# tokens + similarity
# --------------------------------------------------------------------------------------------


def content_tokens(text: str) -> list[str]:
    """Normalized tokens that carry content: digits, or >= 4 letters and not a function word."""
    return [t for t in normalize_text(text).split() if t.isdigit() or (len(t) >= 4 and t not in _STOP)]


def similarity(seg_texts: Sequence[str], turn_texts: Sequence[str]) -> np.ndarray:
    """(n_segments, n_turns) IDF-weighted share of a segment's content tokens found (fuzzy) in a turn."""
    seg_toks = [content_tokens(t) for t in seg_texts]
    turn_toks = [content_tokens(t) for t in turn_texts]
    n, m = len(seg_toks), len(turn_toks)
    out = np.zeros((n, m))
    vocab = sorted({t for ts in seg_toks for t in ts})
    tvocab = sorted({t for ts in turn_toks for t in ts})
    if not vocab or not tvocab or not m:
        return out
    ratio = cdist(vocab, tvocab, scorer=fuzz.ratio, dtype=np.float32)  # (V, T)
    hit_tok = ratio >= MATCH_RATIO
    # token -> turns it occurs in (fuzzy)
    col = {t: k for k, t in enumerate(tvocab)}
    in_turn = np.zeros((len(vocab), m), dtype=bool)
    for j, ts in enumerate(turn_toks):
        if ts:
            cols = [col[t] for t in set(ts)]
            in_turn[:, j] = hit_tok[:, cols].any(axis=1)
    df = in_turn.sum(axis=1)
    idf = np.log((m + 1) / (df + 0.5))
    row = {t: k for k, t in enumerate(vocab)}
    for i, ts in enumerate(seg_toks):
        if not ts:
            continue
        idx = [row[t] for t in ts]
        w = idf[idx]
        if w.sum() <= 0:
            continue
        out[i] = (w[:, None] * in_turn[idx]).sum(axis=0) / w.sum()
    return out


def _turn_positions(turns: Sequence[Turn]) -> np.ndarray:
    lens = np.array([max(len(t.text), 1) for t in turns], dtype=float)
    ends = np.cumsum(lens)
    return (ends - lens / 2) / ends[-1]


def _segment_positions(segments: Sequence[Segment]) -> np.ndarray:
    t0 = min(s.start for s in segments)
    t1 = max(s.end for s in segments)
    span = max(t1 - t0, 1e-6)
    return np.array([((s.start + s.end) / 2 - t0) / span for s in segments])


# --------------------------------------------------------------------------------------------
# alignment
# --------------------------------------------------------------------------------------------


@dataclass
class TurnSpan:
    turn: str
    start: float
    end: float
    segment_ids: list[str] = field(default_factory=list)
    aligned: bool = True


@dataclass
class Alignment:
    assignment: list[int]  # segment index -> turn index
    spans: dict[str, TurnSpan]  # turn id -> time span
    turns: list[Turn]
    segments: list[Segment]

    def turn_of(self, seg_id: str) -> str | None:
        for s, j in zip(self.segments, self.assignment):
            if s.id == seg_id:
                return self.turns[j].id
        return None


def align(turns: Sequence[Turn], segments: Sequence[Segment]) -> Alignment:
    """Monotonic segment -> turn assignment maximizing token overlap + position prior + role agreement."""
    turns, segs = list(turns), [s for s in segments if s.end >= s.start]
    if not turns or not segs:
        return Alignment([], {}, turns, segs)
    n, m = len(segs), len(turns)
    sim = similarity([s.text for s in segs], [t.text for t in turns])
    pos = np.abs(_segment_positions(segs)[:, None] - _turn_positions(turns)[None, :])
    role = np.zeros((n, m))
    for i, s in enumerate(segs):
        if s.role == "unknown":
            continue
        for j, t in enumerate(turns):
            if t.role != "unknown":
                role[i, j] = 1.0 if s.role == t.role else -1.0
    score = W_SIM * sim - W_POS * pos + W_ROLE * role
    jj = np.arange(m)
    skip = W_SKIP * np.maximum(0, jj[:, None] - jj[None, :] - 1)  # skip[j, j'] for j' <= j
    allowed = jj[None, :] <= jj[:, None]
    dp = np.full((n, m), -np.inf)
    back = np.zeros((n, m), dtype=int)
    dp[0] = score[0] - W_SKIP * jj
    for i in range(1, n):
        cand = np.where(allowed, dp[i - 1][None, :] - skip, -np.inf)  # (j, j')
        back[i] = cand.argmax(axis=1)
        dp[i] = score[i] + cand.max(axis=1)
    j = int(np.argmax(dp[-1] - W_SKIP * (m - 1 - jj)))
    assignment = [0] * n
    for i in range(n - 1, -1, -1):
        assignment[i] = j
        j = int(back[i, j])
    spans: dict[str, TurnSpan] = {}
    for i, j in enumerate(assignment):
        t = turns[j].id
        sp = spans.get(t)
        if sp is None:
            spans[t] = TurnSpan(t, segs[i].start, segs[i].end, [segs[i].id])
        else:
            sp.start, sp.end = min(sp.start, segs[i].start), max(sp.end, segs[i].end)
            sp.segment_ids.append(segs[i].id)
    # turns without a segment: the gap between their aligned neighbours
    for k, t in enumerate(turns):
        if t.id in spans:
            continue
        prev = next((spans[turns[q].id].end for q in range(k - 1, -1, -1) if turns[q].id in spans), segs[0].start)
        nxt = next((spans[turns[q].id].start for q in range(k + 1, m) if turns[q].id in spans), segs[-1].end)
        spans[t.id] = TurnSpan(t.id, min(prev, nxt), max(prev, nxt), [], aligned=False)
    return Alignment(assignment, spans, turns, segs)
