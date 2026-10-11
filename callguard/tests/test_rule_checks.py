"""Keyword and pattern checks: offline, fast, on ASR-like Standard German and the case's Swiss German scripts."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from callguard import registry
from callguard.checks.keywords import KeywordCheck
from callguard.checks.patterns import PatternCheck, luhn_ok, number_value
from callguard.checks.textnorm import normalize, segment_tokens, token_times, tokenize, tokenize_words
from callguard.config import ROOT
from callguard.data import parse_turns
from callguard.families import load_families
from callguard.types import Family, Keyword, Segment, Transcript, Word

DATA = ROOT / "data_upstream" / "inventx-case-study" / "data"
needs_data = pytest.mark.skipif(not (DATA / "Transkript").exists(), reason="case data not checked out")


def seg(text: str, sid: str = "S001", start: float = 0.0, end: float = 5.0, role: str = "unknown",
        speaker: str | None = None, words: list[Word] | None = None) -> Segment:
    return Segment(id=sid, start=start, end=end, text=text, role=role, speaker=speaker, words=words or [])


def transcript(*segments: Segment) -> Transcript:
    return Transcript(call_id="t", segments=list(segments))


def words_of(text: str, start: float = 10.0, step: float = 0.5) -> list[Word]:
    """Words as our ASR backends emit them: no leading space, punctuation attached."""
    return [Word(start=start + i * step, end=start + (i + 1) * step - 0.05, text=w)
            for i, w in enumerate(text.split())]


def fam(fid: str, *keywords: Keyword, can_alarm: bool = True) -> Family:
    return Family(id=fid, label=fid, keywords=list(keywords), can_alarm=can_alarm)


K04 = Keyword(id="K04", label="Handeln vor der Meldung", de=["vor der Meldung"], gsw=["vor de Meldig"])
K01 = Keyword(id="K01", label="Nicht öffentliche Information", de=["nicht öffentlich"], gsw=["nöd öffentlich"])
K03 = Keyword(id="K03", label="Marktrelevanter Inhalt", de=["Quartalszahlen", "Insider Trading"])
K10 = Keyword(id="K10", label="Zugangswörter", de=["PIN", "TAN", "Passwort"])
K09 = Keyword(id="K09", label="Zahlungsmittel", de=["Kreditkartennummer"])
TRADE = fam("trade", K01, K03, K04)
ACCESS = fam("access", K10)
NUMBERS = fam("numbers", K09, can_alarm=False)


def kw_run(text: str, families: list[Family] | None = None, **params) -> list:
    return KeywordCheck(None, **params).run(transcript(seg(text)), families or [TRADE, ACCESS]).findings


# --------------------------------------------------------------------------------------------
# textnorm
# --------------------------------------------------------------------------------------------


def test_normalize_folds_umlauts_quotes_and_punctuation():
    assert normalize("«Prüefig» umgah, Straße! „Übernahme“ – Ärger") == "pruefig umgah strasse ubernahme arger"
    assert normalize("Die  PIN.", case_sensitive=True) == "Die PIN"
    assert normalize("ähnlich") == "ahnlich"  # decomposed umlaut stays one token


def test_tokenize_keeps_offsets_and_sentence_boundaries():
    text = "Die PIN. Wir sind «da»"
    toks = tokenize(text)
    assert [t.text for t in toks] == ["die", "pin", "wir", "sind", "da"]
    assert [text[t.start:t.end] for t in toks] == ["Die", "PIN", "Wir", "sind", "da"]
    assert [t.boundary for t in toks] == [True, False, True, False, False]


def test_tokenize_words_inserts_spaces_between_clean_words():
    text, toks = tokenize_words(words_of("Der Code ist 7, 3, 1."))
    assert text == "Der Code ist 7, 3, 1."
    assert [t.text for t in toks] == ["der", "code", "ist", "7", "3", "1"]
    assert [(t.word_first, t.word_last) for t in toks] == [(i, i) for i in range(6)]


def test_tokenize_words_joins_subword_pieces_and_maps_times():
    words = [Word(start=1.0, end=1.4, text=" Die"), Word(start=1.5, end=1.9, text=" Quartals"),
             Word(start=1.9, end=2.4, text="zahlen.")]
    s = seg("Die Quartalszahlen.", words=words)
    _, toks = tokenize_words(words)
    assert [t.text for t in toks] == ["die", "quartalszahlen"]
    assert (toks[1].word_first, toks[1].word_last) == (1, 2)
    assert token_times(s, toks, 1, 1) == (1.5, 2.4)
    _, plain = segment_tokens(seg("Die Quartalszahlen.", start=3.0, end=4.0))
    assert token_times(seg("x", start=3.0, end=4.0), plain, 1, 1) == (3.0, 4.0)  # no words -> segment


# --------------------------------------------------------------------------------------------
# KeywordCheck
# --------------------------------------------------------------------------------------------


def test_negation_before_hit():
    (f,) = kw_run("Ich habe nicht vor, vor der Meldung zu kaufen.")
    assert f.detail["keyword_id"] == "K04" and f.detail["negated"] is True
    assert f.score == pytest.approx(0.1)
    assert f.reason.startswith("Stichwort K04 «vor der Meldung» (Handeln vor der Meldung) – verneint")
    assert f.detail["harmless"] == K04.harmless


def test_negation_scope_stops_at_sentence_end_and_respects_window():
    (f,) = kw_run("Das ist nicht gut. Vor der Meldung kaufe ich.")
    assert not f.detail["negated"]
    (f,) = kw_run("Nicht dass ich jetzt heute unbedingt vor der Meldung kaufe.", negation_window=4)
    assert not f.detail["negated"]  # "nicht" is 5 tokens before the hit
    (f,) = kw_run("Ich will nöd vor de Meldig handle.")
    assert f.detail["negated"] and f.detail["negation_cue"] == "nöd"


def test_negation_inside_keyword_phrase_is_not_a_negation():
    fs = kw_run("Die Zahlen sind noch nicht öffentlich, ich will vor der Meldung kaufen.")
    by_kw = {f.detail["keyword_id"]: f for f in fs}
    assert set(by_kw) == {"K01", "K04"}
    assert not by_kw["K01"].detail["negated"]
    assert not by_kw["K04"].detail["negated"]  # the "nicht" belongs to "nicht öffentlich"
    assert by_kw["K01"].score == pytest.approx(0.35)


def test_whole_words_only_no_partial_hits():
    assert kw_run("Ich habe die Notiz an die Pinnwand gehängt, meine Tante hilft. Das Tanzen ist super.") == []
    (f,) = kw_run("Sie hat mir die PIN gesagt.")
    assert f.detail["matched_text"] == "PIN"


def test_short_acronyms_need_acronym_casing():
    wir = Keyword(id="KW", label="WIR-Bank", de=["WIR"])
    fams = [fam("trade", wir)]
    assert kw_run("Wir kaufen heute. Dann haben wir Zeit.", fams) == []  # pronoun, not the bank
    assert len(kw_run("Das Konto bei der WIR läuft.", fams)) == 1
    (f,) = kw_run("Können Sie mir die Pin bestätigen?")  # capitalized noun mid-sentence
    assert f.detail["keyword_id"] == "K10"
    assert kw_run("Ich gebe ihm die pin nicht? tan") == []  # lowercase is not the acronym


def test_case_sensitive_keyword():
    k = Keyword(id="KC", label="Ort", de=["Bern"], case_sensitive=True)
    assert kw_run("ich bern das", [fam("trade", k)]) == []
    assert len(kw_run("Ich wohne in Bern.", [fam("trade", k)])) == 1


def test_fuzzy_near_miss_and_exact_only():
    (f,) = kw_run("Sie hat mir gesagt, die Quartalszahle sind besser.")
    assert f.detail["fuzzy_score"] == pytest.approx(96.3, abs=0.1)
    assert f.score == pytest.approx(0.35 * f.detail["fuzzy_score"] / 100, abs=1e-3)
    assert "ähnlich: «Quartalszahle»" in f.reason
    assert kw_run("Sie hat mir gesagt, die Quartalszahle sind besser.", fuzzy=100) == []


def test_fuzzy_multiword_tolerates_one_extra_token():
    k = Keyword(id="K08", label="Kontrollumgehung", de=["Prüfung umgehen"])
    (f,) = kw_run("Können wir so die Prüfung zu umgehen?", [fam("splitting", k)])
    assert f.detail["matched_text"] == "Prüfung zu umgehen"


def test_fuzzy_skips_short_phrases():
    k = Keyword(id="KS", label="kurz", de=["Konto"])
    assert kw_run("Die Kontos sind gesperrt.", [fam("trade", k)]) == []
    k = Keyword(id="K03", label="x", gsw=["Übernahm"])  # Swiss stem vs. the verb "übernäh" (take over)
    assert len(kw_run("Ich wett nöd alles übernäh.", [fam("trade", k)])) == 1
    assert kw_run("Ich wett nöd alles übernäh.", [fam("trade", k)], fuzzy_min_chars=9) == []


def test_disabled_family_is_skipped():
    off = TRADE.model_copy(update={"enabled": False})
    res = KeywordCheck(None).run(transcript(seg("Ich kaufe vor der Meldung.")), [off, ACCESS])
    assert res.findings == [] and set(res.family_scores) == {"access"}


def test_compound_spelling_variants_match_exactly():
    (f,) = kw_run("Lesen Sie mir die Kreditkarten-Nummer vor.", [NUMBERS])
    assert f.detail["fuzzy_score"] == 100 and f.detail["matched_text"] == "Kreditkarten-Nummer"
    (f,) = kw_run("Das wäre Insidertrading.", [TRADE], fuzzy=100)
    assert f.detail["phrase"] == "Insider Trading"


def test_family_score_noisy_or_per_keyword_and_cap():
    res = KeywordCheck(None).run(transcript(seg(
        "Quartalszahlen, Quartalszahlen und nochmals Quartalszahlen.")), [TRADE])
    assert len(res.findings) == 3
    assert res.family_scores["trade"].score == pytest.approx(0.35)  # repetition does not inflate
    res = KeywordCheck(None).run(transcript(seg(
        "Die Quartalszahlen sind nicht öffentlich, ich kaufe vor der Meldung.")), [TRADE])
    fs = res.family_scores["trade"]
    assert fs.score == pytest.approx(1 - 0.65 ** 3, abs=1e-3)
    assert fs.confidence == pytest.approx(0.4) and fs.verdict is None
    assert fs.segment_ids == ["S001"] and fs.detail["keywords"] == {"K03": 1, "K01": 1, "K04": 1}
    many = [Keyword(id=f"X{i}", label="x", de=[f"wort{i}"]) for i in range(10)]
    res = KeywordCheck(None).run(transcript(seg(" ".join(f"wort{i}" for i in range(10)))), [fam("trade", *many)])
    assert res.family_scores["trade"].score == pytest.approx(0.9)


def test_absent_and_families_without_keywords():
    res = KeywordCheck(None).run(transcript(seg("Guten Tag, wie kann ich helfen?")), [TRADE, fam("empty")])
    fs = res.family_scores["trade"]
    assert (fs.score, fs.confidence, fs.reason) == (0.0, 0.25, "Keine Stichwörter gefunden")
    assert "empty" not in res.family_scores and res.meta["families_without_keywords"] == ["empty"]


def test_disabled_keyword_is_ignored():
    off = K04.model_copy(update={"enabled": False})
    assert kw_run("Ich kaufe vor der Meldung.", [fam("trade", off)]) == []


def test_word_timestamps_pin_the_hit():
    text = "Ich will die Aktie vor der Meldung kaufen."
    s = seg(text, start=10.0, end=14.0, words=words_of(text))
    (f,) = KeywordCheck(None).run(transcript(s), [TRADE]).findings
    assert (f.start, f.end) == (pytest.approx(12.0), pytest.approx(13.45))
    assert f.segment_ids == ["S001"] and "char_span" not in f.detail


def test_without_words_the_segment_span_and_char_offsets_are_used():
    text = "Ich will die Aktie vor der Meldung kaufen."
    (f,) = KeywordCheck(None).run(transcript(seg(text, start=7.0, end=9.0)), [TRADE]).findings
    assert (f.start, f.end) == (7.0, 9.0)
    a, b = f.detail["char_span"]
    assert text[a:b] == "vor der Meldung"


def test_roles_restrict_and_fall_back_when_unknown():
    t = transcript(seg("Ich kaufe vor der Meldung.", "S1", role="customer"),
                   seg("Vor der Meldung kaufen ist verboten.", "S2", role="advisor"))
    res = KeywordCheck(None, roles=["customer"]).run(t, [TRADE])
    assert [f.segment_ids for f in res.findings] == [["S1"]]
    t_unknown = transcript(seg("Ich kaufe vor der Meldung.", "S1"), seg("Vor der Meldung.", "S2"))
    res = KeywordCheck(None, roles=["customer"]).run(t_unknown, [TRADE])
    assert len(res.findings) == 2 and "note" in res.meta


def test_bad_params_raise():
    with pytest.raises(ValueError):
        KeywordCheck(None, fuzzy=150)
    with pytest.raises(ValueError):
        KeywordCheck(None, roles=["boss"])
    with pytest.raises(TypeError):
        KeywordCheck(None, fuzy=90)
    with pytest.raises(ValueError):
        PatternCheck(None, confidence=2)


def test_registry_and_cache_params():
    chk = registry.create("check", {"type": "keywords", "name": "kw", "weight": 0.35, "fuzzy": 95}, ctx=None)
    assert isinstance(chk, KeywordCheck) and chk.name == "kw" and chk.weight == 0.35
    assert chk.cache_params()["fuzzy"] == 95 and "weight" not in chk.cache_params()
    pat = registry.create("check", {"type": "patterns", "name": "patterns"}, ctx=None)
    assert isinstance(pat, PatternCheck)
    # keyword edits must not invalidate the pattern check's cache
    assert pat.cache_key([TRADE, ACCESS]) == pat.cache_key([fam("access"), TRADE])


def test_broken_segment_degrades_gracefully(monkeypatch):
    chk = KeywordCheck(None)
    calls = {"n": 0}
    orig = chk.segment_hits

    def flaky(phrases, toks, *rest):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return orig(phrases, toks, *rest)

    monkeypatch.setattr(chk, "segment_hits", flaky)
    res = chk.run(transcript(seg("vor der Meldung", "S1"), seg("vor der Meldung", "S2")), [TRADE])
    assert [f.segment_ids for f in res.findings] == [["S2"]]
    assert "S1" in res.meta["errors"][0]


# --------------------------------------------------------------------------------------------
# PatternCheck
# --------------------------------------------------------------------------------------------


def pat_run(*segments: Segment, families: list[Family] | None = None, **params):
    return PatternCheck(None, **params).run(transcript(*segments), families or [ACCESS, NUMBERS])


@pytest.mark.parametrize("word,digits", [
    ("vier", "4"), ("Zwei", "2"), ("nüün", "9"), ("sibe", "7"), ("drü", "3"), ("eis", "1"), ("null", "0"),
    ("fuenf", "5"), ("zwölf", "12"), ("zweiundvierzig", "42"), ("sibeundzwänzg", "27"), ("einezwänzg", "21"),
    ("vierzehn", "14"), ("dreissig", "30"), ("dreißig", "30"),
    ("viertausendfünfhundert", "amount"), ("achttuusig", "amount"),
    ("nun", None), ("ein", None), ("zwölfti", None), ("vierte", None), ("Kreditkarte", None),
])
def test_number_words(word, digits):
    assert number_value(word) == digits


def test_luhn():
    assert luhn_ok("4242424242424242") and not luhn_ok("4242424242424241")


def test_last_four_digits_are_a_masked_suffix():
    r = pat_run(seg("Uf de Kreditkarte sind die letzten vier: vier, zwei, vier, zwei.", role="customer"))
    (f,) = r.findings
    assert f.family == "numbers" and f.detail["n_digits"] == 4 and f.detail["digits"] == "4242"
    assert f.score == pytest.approx(0.1) and f.detail["masked_cue"] == "letzten"
    assert r.family_scores["access"].score == 0.0


def test_code_after_access_cue_is_access():
    r = pat_run(seg("Bitte lesen Sie mir den Bestätigungscode nicht vor.", "S1", role="advisor"),
                seg("Okay.", "S2", role="customer"),
                seg("Der Code ist 4 8 1 5 2 3.", "S3", role="customer"))
    (f,) = r.findings
    assert f.family == "access" and f.detail["n_digits"] == 6 and f.detail["cue"] == "Code"
    assert f.score == pytest.approx(0.6) and f.segment_ids == ["S3"]
    assert r.family_scores["access"].score == pytest.approx(0.6)
    assert r.family_scores["access"].confidence == pytest.approx(0.35)


def test_cue_window_counts_segments():
    segs = [seg("Ich habe hier eine TAN bekommen.", "S1", role="customer"),
            seg("Ja.", "S2"), seg("Gut.", "S3"),
            seg("Sieben, drei, eins, neun, vier, zwei.", "S4", role="customer")]
    (f,) = pat_run(*segs).findings
    assert f.family == "numbers" and f.score == pytest.approx(0.2)  # cue 3 segments away
    (f,) = pat_run(*segs, access_cue_window=3).findings
    assert f.family == "access" and f.detail["cue"] == "TAN"


def test_advisor_reading_code_scores_lower_than_customer():
    (f,) = pat_run(seg("Die TAN lautet 731942.", role="advisor")).findings
    assert f.family == "access" and f.score == pytest.approx(0.5)


def test_six_digits_without_cue_are_weak_numbers():
    (f,) = pat_run(seg("Ich lese Ihnen die sechs Stellen vor: acht, drei, sechs, eins, sieben, vier.")).findings
    assert f.family == "numbers" and f.score == pytest.approx(0.2) and f.detail["n_digits"] == 6


def test_full_card_number_digits_and_words():
    (f,) = pat_run(seg("Die Nummer ist 4242 4242 4242 4242.")).findings
    assert f.family == "numbers" and f.detail["n_digits"] == 16 and f.detail["luhn"] is True
    assert f.score == pytest.approx(0.5)
    assert f.reason.startswith("Mögliche vollständige Kartennummer (16 Ziffern) vorgelesen")
    (f,) = pat_run(seg("Da steht: " + ", ".join(["vier", "zwei"] * 8) + ".")).findings
    assert f.detail["n_digits"] == 16
    (f,) = pat_run(seg("zweiundvierzig zweiundvierzig zweiundvierzig zweiundvierzig")).findings
    assert f.detail["n_digits"] == 8


def test_run_continues_into_next_segment_of_same_speaker_only():
    a = seg("Die Nummer ist 4242 4242", "S1", 0.0, 3.0, speaker="SPK1")
    b = seg("4242 4242.", "S2", 3.4, 5.0, speaker="SPK1")
    (f,) = pat_run(a, b).findings
    assert f.detail["n_digits"] == 16 and f.segment_ids == ["S1", "S2"]
    other = b.model_copy(update={"speaker": "SPK0"})
    assert sorted(x.detail["n_digits"] for x in pat_run(a, other).findings) == [8, 8]


def test_amounts_dates_and_years_are_ignored():
    texts = ["Das kostet 4500 Franken.", "Ich habe 12,50 CHF bezahlt.", "Am 30.09.2026 ist es fällig.",
             "Im Jahr 2026 kaufe ich.", "Es sind 8'000 auf dem Konto.", "Der Zins ist 3,5 % und 1250 €.",
             "Ich habe viertausendfünfhundert überwiesen.", "Noch siebenundzwanzig Sekunden.",
             "Gültig bis 12/27.", "Am vierten September, zwei Wochen später.", "Zwei Millionen dreihunderttausend.",
             "Die zwei drei Fragen."]
    for text in texts:
        assert pat_run(seg(text)).findings == [], text


def test_pin_cue_makes_four_digits_access():
    (f,) = pat_run(seg("Meine PIN ist 4 7 1 1.", role="customer")).findings
    assert f.family == "access" and f.score == pytest.approx(0.5) and f.detail["kind"] == "pin_customer"
    (f,) = pat_run(seg("Die PIN sage ich nicht, die letzten vier der Karte sind 4 2 4 2.")).findings
    assert f.family == "numbers"


def test_sample_cue_lowers_access_score():
    (f,) = pat_run(seg("Der Bestätigungscode auf dem Musterbild ist 4 8 2 6 0 1.", role="customer")).findings
    assert f.family == "access" and f.score == pytest.approx(0.3) and f.detail["sample_cue"] == "Musterbild"


def test_iban_is_not_a_card():
    (f,) = pat_run(seg("Meine IBAN ist CH93 0076 2011 6238 5295 7.")).findings
    assert f.detail["kind"] == "iban" and f.score == pytest.approx(0.15)


def test_qr_code_is_not_an_access_cue():
    (f,) = pat_run(seg("Auf dem QR-Code steht 123 456.")).findings
    assert f.family == "numbers" and f.detail["cue"] is None


def test_only_configured_families_are_scored():
    r = pat_run(seg("Die TAN ist 731942."), families=[NUMBERS])
    assert set(r.family_scores) == {"numbers"} and r.findings == []
    assert r.meta["skipped_runs"] == {"family_access_not_configured": 1}
    r = pat_run(seg("Die TAN ist 731942."), families=[TRADE])
    assert r.family_scores == {} and r.findings == []


def test_pattern_word_timestamps():
    text = "Die TAN ist sieben drei eins neun vier zwei."
    (f,) = pat_run(seg(text, start=10.0, end=14.0, words=words_of(text))).findings
    assert (f.start, f.end) == (pytest.approx(11.5), pytest.approx(14.45))
    assert f.detail["matched_text"] == "sieben drei eins neun vier zwei"


def test_absent_numbers():
    r = pat_run(seg("Guten Tag, ich habe zwei Fragen zum Konto."))
    assert r.findings == []
    fs = r.family_scores["access"]
    assert (fs.score, fs.confidence, fs.reason) == (0.0, 0.2, "Keine auffälligen Ziffernfolgen gefunden")


# --------------------------------------------------------------------------------------------
# Real keyword list on the case's Swiss German reference scripts
# --------------------------------------------------------------------------------------------


def script_transcript(name: str) -> Transcript:
    turns = parse_turns((DATA / "Transkript" / f"{name}.txt").read_text())
    return Transcript(call_id=name, segments=[
        Segment(id=t.id, start=i * 10.0, end=i * 10.0 + 9.0, text=t.text, role=t.role)
        for i, t in enumerate(turns)])


@pytest.fixture(scope="module")
def real_families() -> list[Family]:
    return load_families(ROOT / "config" / "keywords.json", ROOT / "config" / "criteria.yaml")


@needs_data
def test_swiss_german_forms_hit_in_reference_script(real_families):
    res = KeywordCheck(None).run(script_transcript("Stufe1_D02"), real_families)
    hits = {(f.detail["keyword_id"], f.segment_ids[0], normalize(f.detail["phrase"])) for f in res.findings}
    for expected in [("K01", "T004", "no nod publiziert"), ("K02", "T004", "finanzabteilig"),
                     ("K03", "T004", "quartalszahle"), ("K05", "T006", "under eus"),
                     ("K04", "T008", "vor de meldig")]:
        assert expected in hits
    assert res.family_scores["trade"].score > 0.8
    assert not any(f.detail["negated"] for f in res.findings)


@needs_data
def test_annotated_keyword_spots_are_all_found(real_families):
    """Every 'Keywordstellen' entry of the expected-assessment files is found at phrase level."""
    chk = KeywordCheck(None)
    total = 0
    for path in sorted((DATA / "Skript_mit_Sollbewertung").glob("*.txt")):
        m = re.search(r"^Keywordstellen: (.*)$", path.read_text(), re.M)
        spots = re.findall(r"(K\d\d) '([^']+)' (T\d{3})", m.group(1)) if m else []
        if not spots:
            continue
        res = chk.run(script_transcript(path.stem), real_families)
        found = {(f.detail["keyword_id"], f.segment_ids[0], normalize(f.detail["phrase"])) for f in res.findings}
        for kid, phrase, turn in spots:
            total += 1
            assert (kid, turn, normalize(phrase)) in found, (path.stem, kid, phrase, turn)
    assert total >= 40


@needs_data
def test_negated_access_words_and_tante_in_reference_scripts(real_families):
    res = KeywordCheck(None).run(script_transcript("Stufe1_D05"), real_families)
    t003 = [f for f in res.findings if f.segment_ids == ["T003"]]
    assert {f.detail["phrase"] for f in t003} == {"PIN", "Passwort"} and all(f.detail["negated"] for f in t003)
    res = KeywordCheck(None).run(script_transcript("Stufe1_D09"), real_families)  # "Darlehe vo minere Tante"
    assert not [f for f in res.findings if f.detail["keyword_id"] == "K10"]


@needs_data
def test_pattern_check_on_reference_scripts(real_families):
    chk = PatternCheck(None)
    (f,) = chk.run(script_transcript("Stufe1_D05"), real_families).findings  # TAN read out, alarm case
    assert f.family == "access" and f.score == pytest.approx(0.6) and f.detail["digits"] == "731942"
    (f,) = chk.run(script_transcript("Stufe1_D06"), real_families).findings  # expired sample, no_alert case
    assert f.family == "access" and f.detail["sample_cue"] and f.score < 0.6
    (f,) = chk.run(script_transcript("Stufe2_C01"), real_families).findings
    assert f.detail["kind"] == "card" and f.detail["n_digits"] == 16
    (f,) = chk.run(script_transcript("Stufe2_C03"), real_families).findings
    assert f.detail["kind"] == "short_number" and f.detail["masked_cue"]
    assert chk.run(script_transcript("Stufe2_C15"), real_families).findings == []  # amounts only


# --------------------------------------------------------------------------------------------
# Real ASR output (slow): Whisper's own word format and digit rendering
# --------------------------------------------------------------------------------------------


@pytest.mark.slow
def test_pattern_check_on_real_asr_excerpt(tmp_path: Path, real_families):
    """D05 at ~80 s: the customer reads out her TAN. Whisper writes "7, 3, 1, 9, 4, 2"."""
    pytest.importorskip("faster_whisper")
    from callguard.audio import cut
    from callguard.config import load_config
    from callguard.context import Context

    cfg = load_config("local")
    src, model = DATA / "Audio" / "Stufe1_D05-K1.wav", ROOT / cfg.asr["model"]
    if not src.exists() or not (model / "model.bin").exists():
        pytest.skip("local Whisper model or case audio missing")
    excerpt = cut(src, 70.0, 90.0, tmp_path / "excerpt.wav")
    t = registry.create("asr", cfg.asr, ctx=Context(cfg, use_cache=False)).transcribe(excerpt, "excerpt")
    assert any(s.words for s in t.segments)

    res = PatternCheck(None).run(t, real_families)
    runs = [f for f in res.findings if f.detail["n_digits"] == 6]
    assert runs, [s.text for s in t.segments]
    f = runs[0]
    assert 0.0 <= f.start < f.end <= 20.5 and "errors" not in res.meta
    seg_ = t.segment(f.segment_ids[0])
    assert f.end - f.start < seg_.end - seg_.start  # pinned to words, not the whole segment
    assert "errors" not in KeywordCheck(None).run(t, real_families).meta
