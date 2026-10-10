"""R3 paraphrase robustness: build config/policy_table_para.yaml from config/policy_table.yaml.

Same families, fact ids, labels, roles and rules; only the `en` and `de` questions are replaced by paraphrases
(same meaning, different words). The paraphrases were written from the original questions only, without
looking at any transcript.

    uv run python scripts/research/make_para_table.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

SRC = Path("config/policy_table.yaml")
DST = Path("config/policy_table_para.yaml")

PARA: dict[tuple[str, str], dict[str, str]] = {
    ("trade", "wish"): {
        "en": "Does anyone on the call (typically the client) state that they personally want to purchase, sell "
              "or trade a particular security, regardless of whether the advisor later declines or the order is "
              "never carried out?",
        "de": "Bringt jemand im Gespräch (in der Regel die Kundin/der Kunde) zum Ausdruck, selbst ein bestimmtes "
              "Wertpapier kaufen, verkaufen oder handeln zu wollen, egal ob die Beratung das danach ablehnt oder "
              "der Auftrag nie ausgeführt wird?",
    },
    ("trade", "inside_info"): {
        "en": "Is the reason this person gives for wanting to trade something they personally learned from an "
              "insider or confidential channel (for example a relative, their employer, the finance team, "
              "something told \"just between us\", or numbers or papers seen ahead of time), where that "
              "information has not been made public yet (for example earnings figures, an acquisition or a big "
              "contract before it is announced)?",
        "de": "Stützt diese Person ihren Wunsch zu handeln auf etwas, das sie persönlich über einen internen oder "
              "vertraulichen Kanal erfahren hat (etwa Verwandte, die eigene Firma, die Finanzabteilung, etwas "
              "\"unter vier Augen\" Gesagtes oder vorzeitig gesehene Zahlen oder Unterlagen), und das noch nicht "
              "bekannt gemacht wurde (etwa Quartalsergebnisse, eine Übernahme oder ein grosser Auftrag vor der "
              "offiziellen Mitteilung)?",
    },
    ("trade", "public"): {
        "en": "Is it stated during the call that the information behind the wish to trade has already been made "
              "public (for example in a press release, a published report or freely available figures)?",
        "de": "Wird im Gespräch erwähnt, dass die Information hinter dem Handelswunsch schon veröffentlicht wurde "
              "(etwa per Medienmitteilung, in einem publizierten Bericht oder als frei zugängliche Zahlen)?",
    },
    ("access", "spoken"): {
        "en": "Does anyone (typically the client) say aloud over the phone the digits or characters of something "
              "that could be a PIN, TAN, password, or a code for confirming, approving or logging in, even when "
              "it is not clear whether that value is still valid and even when the advisor interrupts them "
              "afterwards? (Merely the final four digits, a reference number or a sum of money is not enough.)",
        "de": "Spricht jemand (in der Regel die Kundin/der Kunde) am Telefon die Ziffern oder Zeichen von etwas "
              "aus, das eine PIN, eine TAN, ein Passwort oder ein Code zum Bestätigen, Freigeben oder Einloggen "
              "sein könnte, auch wenn nicht klar ist, ob der Wert noch gilt, und auch wenn die Beratung die "
              "Person danach unterbricht? (Bloss die letzten vier Ziffern, eine Referenznummer oder ein "
              "Geldbetrag reichen nicht.)",
    },
    ("access", "current"): {
        "en": "Is the value that was spoken part of an ongoing login or approval procedure that is still valid? "
              "Reply \"unknown\" if the call leaves open which procedure it is for or whether it is still valid.",
        "de": "Ist der genannte Wert Teil eines gerade laufenden Login- oder Freigabeprozesses, der noch gültig "
              "ist? Antworte \"unknown\", wenn das Gespräch offen lässt, zu welchem Prozess er gehört oder ob er "
              "noch gilt.",
    },
    ("access", "validity_open"): {
        "en": "Does anyone on the call state that nobody knows, or it is not clear, whether the value that was "
              "read aloud is still valid or which procedure it is for?",
        "de": "Erwähnt jemand im Gespräch, dass niemand weiss oder nicht klar ist, ob der vorgelesene Wert noch "
              "gilt oder zu welchem Prozess er gehört?",
    },
    ("access", "expired_or_sample"): {
        "en": "Does the call describe the spoken value as no longer valid, expired, unusable, or as a "
              "demonstration or example value (for instance taken from a manual or a help page)?",
        "de": "Wird der genannte Wert im Gespräch als nicht mehr gültig, abgelaufen, unbrauchbar oder als "
              "Beispiel- bzw. Musterwert (etwa aus einem Handbuch oder einer Hilfeseite) beschrieben?",
    },
    ("access", "asked_by_advisor"): {
        "en": "Does the advisor request that the client say or read aloud a PIN, TAN, password or code?",
        "de": "Verlangt die Beraterin/der Berater von der Kundin/dem Kunden, eine PIN, eine TAN, ein Passwort "
              "oder einen Code zu sagen oder vorzulesen?",
    },
    ("disclosure", "data_given"): {
        "en": "Does the advisor give the caller specific numbers or details taken from an account, loan or client "
              "record belonging to a person other than the caller (for example a balance, the size of a loan, "
              "an interest due date, or payments)?",
        "de": "Teilt die Beraterin/der Berater der anrufenden Person konkrete Zahlen oder Details aus einem "
              "Konto, Kredit oder Kundendossier mit, das nicht der anrufenden Person, sondern jemand anderem "
              "gehört (etwa einen Saldo, die Kredithöhe, einen Zinstermin oder Zahlungen)?",
    },
    ("disclosure", "third_party_request"): {
        "en": "Does the caller request that the advisor share details the bank has on the accounts, loans or "
              "banking dealings of some other person (rather than the caller's own)?",
        "de": "Verlangt die anrufende Person von der Beratung Auskünfte, die die Bank zu Konten, Krediten oder "
              "Bankgeschäften einer anderen Person (und nicht zu den eigenen) hat?",
    },
    ("disclosure", "authorized"): {
        "en": "Does the advisor state during the call that the caller holds a power of attorney or an information "
              "right on file that covers precisely the information in question?",
        "de": "Hält die Beratung im Gespräch fest, dass für die anrufende Person eine hinterlegte Vollmacht oder "
              "ein Auskunftsrecht besteht, das genau diese Auskunft umfasst?",
    },
    ("disclosure", "not_authorized"): {
        "en": "Does the advisor state during the call that the caller lacks a power of attorney, an information "
              "right or any permission for the information in question?",
        "de": "Hält die Beratung im Gespräch fest, dass der anrufenden Person für diese Auskunft eine Vollmacht, "
              "ein Auskunftsrecht oder eine Berechtigung fehlt?",
    },
    ("disclosure", "beyond_scope"): {
        "en": "Does the information that was disclosed exceed what the confirmed power of attorney covers?",
        "de": "Reicht die erteilte Auskunft weiter, als es der bestätigte Umfang einer Vollmacht erlaubt?",
    },
    ("documentation", "omit_request"): {
        "en": "Does anyone request or insist that some fact be left out of the record or the notes, or be kept "
              "from an internal department (for example the credit review or the financing team)?",
        "de": "Fordert oder wünscht jemand, dass eine Tatsache nicht festgehalten, nicht in die Notizen "
              "geschrieben oder einer internen Abteilung (etwa der Kreditprüfung oder der Finanzierungsstelle) "
              "vorenthalten wird?",
    },
    ("documentation", "relevant"): {
        "en": "Does the fact that is supposed to be kept out of the record or hidden matter for the process, for "
              "example an outstanding debt or obligation that must be repaid, in a credit review?",
        "de": "Spielt die Tatsache, die nicht festgehalten oder verborgen werden soll, für den Vorgang eine Rolle, "
              "etwa eine offene, zurückzuzahlende Schuld oder Verpflichtung bei einer Kreditprüfung?",
    },
    ("documentation", "correction_or_private"): {
        "en": "Is the point merely to fix or delete an incorrect or unrelated earlier entry, or to omit personal "
              "details that do not matter for the process, with everything that matters remaining visible?",
        "de": "Soll lediglich ein falscher oder nicht dazugehörender früherer Eintrag berichtigt oder gelöscht "
              "werden, oder sollen persönliche, für den Vorgang belanglose Details weggelassen werden, während "
              "alles Wesentliche sichtbar bleibt?",
    },
    ("splitting", "split_request"): {
        "en": "Does anyone request that one payment or invoice be broken up into multiple smaller amounts or "
              "instalments?",
        "de": "Wünscht jemand, dass eine Zahlung oder Rechnung in mehrere kleinere Beträge oder Raten zerlegt "
              "wird?",
    },
    ("splitting", "avoid_control"): {
        "en": "Is the purpose of the split, whether said outright or plainly evident, to bypass an internal check, "
              "sign-off, limit or area of responsibility?",
        "de": "Ist der Zweck der Aufteilung, ob ausdrücklich gesagt oder offensichtlich, eine interne Prüfung, "
              "Genehmigung, Limite oder Zuständigkeit zu umgehen?",
    },
    ("splitting", "single_invoice"): {
        "en": "Are the smaller amounts all part of one and the same invoice or payment?",
        "de": "Sind die kleineren Beträge alle Teil ein und derselben Rechnung oder Zahlung?",
    },
    ("splitting", "harmless"): {
        "en": "Is this about multiple separate, real invoices that are each paid when due, or is bypassing a check "
              "only rejected or mentioned as an example for training?",
        "de": "Geht es um mehrere voneinander unabhängige, echte Rechnungen, die jeweils bei Fälligkeit bezahlt "
              "werden, oder wird das Umgehen einer Kontrolle nur zurückgewiesen oder als Beispiel für eine "
              "Schulung erwähnt?",
    },
}


def main() -> None:
    table = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    seen = set()
    for fam_id, fam in table["families"].items():
        for fact in fam["facts"]:
            key = (fam_id, fact["id"])
            p = PARA[key]
            assert p["en"] != fact["en"] and p["de"] != fact["de"]
            fact["en"], fact["de"] = p["en"], p["de"]
            seen.add(key)
    assert seen == set(PARA), set(PARA) ^ seen
    header = ("# R3 paraphrase robustness (research only, not a candidate): config/policy_table.yaml with every\n"
              "# fact question (en and de) reworded with the same meaning, written without reading transcripts.\n"
              "# Ids, labels, roles and rules are identical. Generated by scripts/research/make_para_table.py.\n")
    DST.write_text(header + yaml.safe_dump(table, allow_unicode=True, sort_keys=False, width=110),
                   encoding="utf-8")
    print(f"wrote {DST}: {len(seen)} facts")


if __name__ == "__main__":
    main()
