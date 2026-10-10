"""R6 paraphrase ensemble: build config/policy_table_para2.yaml from config/policy_table.yaml.

A SECOND independent paraphrase set (the first is config/policy_table_para.yaml, R3). Same families, fact
ids, labels, roles and rules; only the `en` and `de` questions are reworded, in a deliberately different
style from the first set (call-anchored "In this call ..." phrasing, different verbs and examples order).
Written from the tuned questions and config/criteria.yaml only, without reading any transcript or result.

    uv run python scripts/research/make_para2_table.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

SRC = Path("config/policy_table.yaml")
DST = Path("config/policy_table_para2.yaml")

PARA2: dict[tuple[str, str], dict[str, str]] = {
    ("trade", "wish"): {
        "en": "In this call, does someone (most often the customer) say they themselves want a specific security "
              "bought, sold or traded for them? Count it even if the advisor refuses or the order is never placed.",
        "de": "Sagt in diesem Gespräch jemand (meistens die Kundin/der Kunde), dass er oder sie selbst ein "
              "bestimmtes Wertpapier kaufen, verkaufen oder handeln lassen möchte? Zählt auch, wenn die Beratung "
              "ablehnt oder der Auftrag nie erteilt wird.",
    },
    ("trade", "inside_info"): {
        "en": "Does that person base the wish to trade on knowledge they got from inside or confidential sources "
              "(their employer, the finance department, a family member, documents or figures seen early, "
              "something said \"off the record\") that has not been announced to the public yet, such as results, "
              "a takeover or a major order?",
        "de": "Stützt sich diese Person beim Handelswunsch auf Wissen aus internen oder vertraulichen Quellen "
              "(Arbeitgeber, Finanzabteilung, ein Familienmitglied, früh gesehene Unterlagen oder Zahlen, etwas "
              "\"inoffiziell\" Gesagtes), das der Öffentlichkeit noch nicht mitgeteilt wurde, etwa Ergebnisse, "
              "eine Übernahme oder ein Grossauftrag?",
    },
    ("trade", "public"): {
        "en": "In this call, is the information behind the trading wish said to be public already, for instance "
              "announced in a press release, contained in a published report, or available to everyone?",
        "de": "Wird in diesem Gespräch gesagt, dass die Information hinter dem Handelswunsch schon öffentlich ist, "
              "etwa in einer Medienmitteilung angekündigt, in einem veröffentlichten Bericht enthalten oder für "
              "alle zugänglich?",
    },
    ("access", "spoken"): {
        "en": "In this call, does someone (most often the customer) speak out the digits or characters of a value "
              "that might be a PIN, a TAN, a password, or a code used to log in, confirm or release something? "
              "Count it even if nobody knows whether the value still works and even if the advisor cuts them off. "
              "(Just the last four digits, a reference number or an amount of money does not count.)",
        "de": "Spricht in diesem Gespräch jemand (meistens die Kundin/der Kunde) die Ziffern oder Zeichen eines "
              "Werts aus, der eine PIN, eine TAN, ein Passwort oder ein Code zum Anmelden, Bestätigen oder "
              "Freigeben sein könnte? Zählt auch, wenn niemand weiss, ob der Wert noch funktioniert, und auch, "
              "wenn die Beratung die Person unterbricht. (Nur die letzten vier Ziffern, eine Referenznummer oder "
              "ein Geldbetrag zählen nicht.)",
    },
    ("access", "current"): {
        "en": "Is the value that was spoken tied to a login or release process that is still running and still "
              "valid? If the call leaves open which process it is for or whether it is still valid, answer "
              "\"unknown\".",
        "de": "Gehört der ausgesprochene Wert zu einem Anmelde- oder Freigabevorgang, der noch läuft und noch "
              "gültig ist? Wenn das Gespräch offen lässt, zu welchem Vorgang er gehört oder ob er noch gilt, "
              "antworte \"unknown\".",
    },
    ("access", "validity_open"): {
        "en": "In this call, does anyone express that they do not know, or that it is uncertain, whether the "
              "value that was read out still works or which process it is for?",
        "de": "Äussert in diesem Gespräch jemand, dass er nicht weiss oder dass ungewiss ist, ob der vorgelesene "
              "Wert noch funktioniert oder zu welchem Vorgang er gehört?",
    },
    ("access", "expired_or_sample"): {
        "en": "In this call, is the spoken value called expired, no longer valid or unusable, or is it presented "
              "as a dummy or example value (for instance taken from a guide or a help page)?",
        "de": "Wird der ausgesprochene Wert in diesem Gespräch als abgelaufen, nicht mehr gültig oder unbrauchbar "
              "bezeichnet, oder als Platzhalter oder Beispielwert dargestellt (etwa aus einer Anleitung oder "
              "einer Hilfeseite)?",
    },
    ("access", "asked_by_advisor"): {
        "en": "In this call, does the advisor request a PIN, TAN, password or code from the customer, asking them "
              "to say it or read it out?",
        "de": "Verlangt die Beraterin/der Berater in diesem Gespräch von der Kundin/dem Kunden eine PIN, eine TAN, "
              "ein Passwort oder einen Code, d.h. bittet sie oder ihn, ihn zu sagen oder vorzulesen?",
    },
    ("disclosure", "data_given"): {
        "en": "In this call, does the advisor reveal to the caller specific numbers or facts from an account, a "
              "loan or a client file of a person other than the caller (for instance a balance, the amount of a "
              "loan, an interest due date, or payments)?",
        "de": "Gibt die Beraterin/der Berater in diesem Gespräch der anrufenden Person bestimmte Zahlen oder "
              "Fakten aus einem Konto, einem Darlehen oder einem Kundendossier einer anderen Person als der "
              "anrufenden preis (etwa einen Saldo, die Höhe eines Darlehens, einen Zinstermin oder Zahlungen)?",
    },
    ("disclosure", "third_party_request"): {
        "en": "In this call, does the caller ask to be told what the bank knows about the accounts, loans or "
              "banking business of some other person, not about their own?",
        "de": "Will die anrufende Person in diesem Gespräch erfahren, was die Bank über die Konten, Darlehen oder "
              "Bankgeschäfte einer anderen Person weiss, also nicht über die eigenen?",
    },
    ("disclosure", "authorized"): {
        "en": "In this call, does the advisor confirm that a power of attorney or an information right for the "
              "caller is on file and that it covers precisely the information asked for?",
        "de": "Bestätigt die Beratung in diesem Gespräch, dass für die anrufende Person eine Vollmacht oder ein "
              "Auskunftsrecht hinterlegt ist und dass es genau die verlangte Auskunft abdeckt?",
    },
    ("disclosure", "not_authorized"): {
        "en": "In this call, does the advisor state that the caller does not have a power of attorney, an "
              "information right or permission to receive this information?",
        "de": "Stellt die Beratung in diesem Gespräch fest, dass die anrufende Person weder eine Vollmacht noch "
              "ein Auskunftsrecht noch eine Erlaubnis für diese Auskunft hat?",
    },
    ("disclosure", "beyond_scope"): {
        "en": "Does what was disclosed reach further than the confirmed extent of a power of attorney allows?",
        "de": "Reicht das, was herausgegeben wurde, weiter, als es der bestätigte Umfang einer Vollmacht erlaubt?",
    },
    ("documentation", "omit_request"): {
        "en": "In this call, does someone want a fact to stay out of the records or the notes, or to be kept "
              "from an internal department (for instance the credit check or the financing unit), and ask or "
              "insist on that?",
        "de": "Will in diesem Gespräch jemand, dass eine Tatsache nicht in die Akten oder die Notiz kommt oder "
              "einer internen Stelle (etwa der Kreditprüfung oder der Finanzierungsstelle) vorenthalten wird, und "
              "bittet darum oder besteht darauf?",
    },
    ("documentation", "relevant"): {
        "en": "Is the fact that is to be kept out of the records or withheld important for the matter at hand, "
              "for instance an outstanding debt or obligation that must be repaid, during a credit check?",
        "de": "Ist die Tatsache, die nicht in die Akten soll oder vorenthalten werden soll, für die Sache wichtig, "
              "etwa eine offene Schuld oder Verpflichtung, die zurückgezahlt werden muss, bei einer Kreditprüfung?",
    },
    ("documentation", "correction_or_private"): {
        "en": "Is the request only about fixing or deleting an old entry that is wrong or does not belong there, "
              "or about not writing down personal details that do not matter for the matter at hand, while "
              "everything that does matter stays on record?",
        "de": "Geht es bei der Bitte nur darum, einen alten Eintrag zu berichtigen oder zu löschen, der falsch ist "
              "oder nicht dazugehört, oder persönliche Details nicht aufzuschreiben, die für die Sache keine Rolle "
              "spielen, während alles Wichtige festgehalten bleibt?",
    },
    ("splitting", "split_request"): {
        "en": "In this call, does someone ask for a payment or an invoice to be paid as several smaller partial "
              "amounts instead of one?",
        "de": "Bittet in diesem Gespräch jemand darum, eine Zahlung oder Rechnung in mehreren kleineren "
              "Teilbeträgen statt auf einmal zu bezahlen?",
    },
    ("splitting", "avoid_control"): {
        "en": "Is the reason for splitting, either said explicitly or obvious from the call, to avoid an internal "
              "check, a required sign-off, a limit or who is responsible for approving it?",
        "de": "Ist der Grund für das Aufteilen, ausdrücklich gesagt oder aus dem Gespräch offensichtlich, eine "
              "interne Prüfung, eine nötige Freigabe, eine Limite oder die Zuständigkeit für die Bewilligung zu "
              "vermeiden?",
    },
    ("splitting", "single_invoice"): {
        "en": "Do the smaller amounts together make up one and the same invoice or payment?",
        "de": "Ergeben die kleineren Beträge zusammen ein und dieselbe Rechnung oder Zahlung?",
    },
    ("splitting", "harmless"): {
        "en": "Are these really several separate, genuine invoices, each paid when it falls due, or is avoiding "
              "a control merely rejected or mentioned as an example from training?",
        "de": "Sind es wirklich mehrere getrennte, echte Rechnungen, die jeweils bei Fälligkeit bezahlt werden, "
              "oder wird das Umgehen einer Kontrolle nur zurückgewiesen oder als Beispiel aus einer Schulung "
              "erwähnt?",
    },
}


def main() -> None:
    raw = yaml.safe_load(SRC.read_text())
    seen = set()
    for fid, fam in raw["families"].items():
        for fact in fam["facts"]:
            key = (fid, fact["id"])
            p = PARA2[key]  # KeyError = a fact without paraphrase: fail loudly
            fact["en"], fact["de"] = p["en"], p["de"]
            seen.add(key)
    missing = set(PARA2) - seen
    assert not missing, f"paraphrases for unknown facts: {sorted(missing)}"
    header = ("# R6 paraphrase ensemble (research): config/policy_table.yaml with every fact question (en and de)\n"
              "# reworded a SECOND time, independently of config/policy_table_para.yaml and in a different style,\n"
              "# written without reading transcripts or results. Ids, labels, roles and rules are identical.\n"
              "# Generated by scripts/research/make_para2_table.py.\n")
    DST.write_text(header + yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=120))
    print(f"wrote {DST} ({len(seen)} facts)")


if __name__ == "__main__":
    main()
