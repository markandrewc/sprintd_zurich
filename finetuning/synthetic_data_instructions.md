# Auftrag: Synthetische Bank-Telefongespräche mit Compliance-Labels

Du erzeugst realistische, fiktive Telefongespräche zwischen einer Bank in der Schweiz und ihren Kundinnen und Kunden,
jeweils mit exakten Labels. Die Daten trainieren ein Entscheidungsmodell, das in echten Anrufen Compliance-Verstösse
erkennt und die Stelle findet, an der sie passieren. Später werden die Gespräche vertont (Text-to-Speech) und
durchlaufen dieselbe Pipeline wie echte Anrufe.

Diese Anweisung gilt für jede Anfrage, die du dazu bekommst. Eine Anfrage nennt die Anzahl Gespräche (Standard 20), die
Batch-Nummer und optional Prüfpunkte, die in diesem Durchgang häufiger vorkommen sollen.

---

## 1. Worauf es ankommt

Das Modell soll **Regeln** lernen, nicht **Muster eines Datensatzes**. Ein Datensatz aus wenigen Vorlagen mit
ausgetauschten Namen und Beträgen ist wertlos: Das Modell lernt dann die Vorlagen auswendig und versagt bei echten
Anrufen. Deshalb gilt:

- Jedes Gespräch hat eine **eigene Geschichte**: eigener Anlass, eigene Personen, eigener Verlauf, eigene Formulierungen.
- Ob ein Verstoss vorliegt, darf sich **nicht an Oberflächenmerkmalen** ablesen lassen (Reizwörter, Länge, Tonfall,
  Position im Gespräch, wer spricht). Es muss sich aus dem **Inhalt und Zusammenhang** ergeben.
- Die Labels müssen **stimmen**. Ein falsches Label schadet mehr als ein fehlendes Gespräch.

---

## 2. Die Prüfpunkte

Zu jedem Gespräch gehören alle 9 Labels, je `true` oder `false`. **Das Label ist die wahre Antwort auf die Frage für
dieses Gespräch.** Die Fragen sind genau die, die das Modell später gestellt bekommt.

**Wer zählt als „someone“**: jede Person, die im Gespräch spricht, und jede Person, deren Handlung im Gespräch
geschildert wird, **sofern die Handlung zum Anliegen gehört, das im Gespräch verfolgt wird**. Erzählt jemand, woher er
eine Information hat, und will darauf handeln, zählt die Weitergabe. Meldet jemand der Bank einen Vorfall als **Opfer
oder Zeuge** (zum Beispiel einen abgewehrten Betrugsversuch), sind die Labels für die Handlungen des Täters `false`;
`true` bleibt nur, was im Gespräch selbst geschieht oder was die anrufende Person selbst vorhat.

Mehrere Labels können gleichzeitig `true` sein, auch in derselben Gesprächsstelle.

Die Klarstellungen unter jeder Frage legen fest, wie zu labeln ist. Sie beschreiben Regeln, keine Szenarien: Erfinde
die Situationen selbst und übernimm keine Formulierungen aus dieser Anweisung ins Gespräch.

### Gesetzlich

**`insider_trading`** (Insiderhandel)
> Does someone want to trade because of non-public, price-relevant information, or pass such information on?
- `true`: Ein Kauf- oder Verkaufswunsch wird mit einer Information begründet, die noch nicht öffentlich ist und den Kurs
  beeinflussen kann; oder jemand gibt eine solche Information weiter oder empfiehlt einen Handel auf dieser Grundlage
  (siehe „someone“). Ausführung ist nicht nötig; ein späterer Rückzieher macht den geäusserten Wunsch nicht ungeschehen.
- `false`: Die Information ist öffentlich; allgemeine Markteinschätzung; kein Handelswunsch und keine Weitergabe;
  jemand weigert sich, etwas zu verraten.

**`market_manipulation`** (Marktmanipulation)
> Does someone try to influence a market price through orders or information?
- `true`: Aufträge oder Informationen mit dem **Zweck**, einen Kurs zu bewegen, festzulegen oder Handel vorzutäuschen.
  Der Versuch genügt.
- `false`: Aufträge aus Anlagegründen, auch grosse; Fragen zur Ausführung oder Marktlage.

**`money_laundering`** (Geldwäscherei)
> Does someone hide where money comes from or who it belongs to, or try to avoid a legal reporting obligation?
- `true`: Zur Herkunft von Vermögen wird ausgewichen, die Antwort verweigert oder bewusst verschleiert; oder die Person,
  der Vermögen wirklich gehört oder zugutekommt, soll gegenüber der Bank verborgen bleiben; oder Transaktionen werden so
  gestaltet, **damit** eine gesetzliche Melde- oder Identifikationspflicht nicht greift. Der Versuch genügt. Konkrete
  Schwellenwerte nicht nennen oder erfinden.
- `false`: Herkunft wird plausibel erklärt (auch wenn Belege erst nachgereicht werden); Vertretung oder Begünstigung wird
  offen angegeben; Gestaltung aus echten, genannten Gründen. Interne Limiten der Bank gehören zu `control_circumvention`.

**`confidential_information`** (Vertrauliche Informationen)
> Does someone reveal confidential information to a person who is not entitled to it, or try to obtain such information without being entitled to it?
- `true`: Vertrauliche Informationen (über Kunden, über die Bank, Geschäftsgeheimnisse, Insiderinformationen) gehen an
  jemanden ohne Berechtigung; oder jemand versucht, an solche Informationen zu kommen, ohne berechtigt zu sein. Der
  Versuch genügt, auch wenn die Bank ablehnt. Gibt jemand eine Insiderinformation weiter, ist in der Regel auch dieses
  Label `true`.
- `false`: Auskunft an oder Anfrage von einer berechtigten Person; öffentliche Informationen; die Auskunft wird verweigert
  und es wurde auch nicht danach gefragt.

**`false_records`** (Falsche Dokumentation)
> Does someone want false information recorded, or relevant information withheld from the people who need it for a decision?
- `true`: Jemand will, dass wissentlich Falsches festgehalten wird, oder dass eine für einen Entscheid wesentliche
  Tatsache der zuständigen Stelle vorenthalten wird, auch um eine Prüfung zu bestehen. Der Versuch genügt.
- `false`: Ein Fehler wird korrigiert; Unklares wird als offen festgehalten; für den Entscheid unwesentliche Details
  werden weggelassen.

**`bribery`** (Bestechung)
> Does someone offer or request an undue advantage in exchange for an action?
- `true`: Ein persönlicher Vorteil wird für eine Handlung angeboten oder verlangt. Ein deutlich verstandenes Angebot
  genügt, auch wenn es indirekt formuliert ist.
- `false`: Normale Gebühren und Angebote der Bank; ein Dank ohne Gegenleistung.

### Intern (Policy der Bank)

**`control_circumvention`** (Kontrollumgehung)
> Does someone try to get around an internal approval, limit or control?
- `true`: Jemand versucht, eine interne Freigabe, Limite oder Kontrolle **auszulassen oder auszuschalten**, sodass sie
  gar nicht angewendet wird. Der Versuch genügt.
- `false`: Wer eine Kontrolle durchlaufen lässt, sie aber mit falschen oder verschwiegenen Angaben täuscht, fällt unter
  `false_records`, nicht hierunter. Ebenfalls `false`: offizielle Anträge, Fragen zum Ablauf.

**`access_credentials`** (Zugangsdaten)
> Is a valid access credential revealed, or does someone ask for another person's access credentials?
- `true`: Ein **gültiges** Geheimnis, das Zugang gewährt oder eine Transaktion bestätigt, wird tatsächlich ausgesprochen
  (auch gegenüber der Bank); oder jemand fragt eine andere Person nach deren Zugangsgeheimnis (siehe „someone“).
- `false`: Angaben, die allein keinen Zugang gewähren; Geheimnisse, die nicht mehr gültig sind; jemand will eines sagen
  und wird vorher gestoppt; übliche Identifikationsfragen; Aufforderung, etwas selbst in einer App einzugeben; Warnungen.

**`manipulated_customer`** (Kunde als Betrugsopfer)
> Does someone appear to act under pressure or deception from a third party?
- `true`: Deutliche Anzeichen, dass jemand im Gespräch auf Druck oder Täuschung einer Drittperson hin handelt oder
  handeln will. Erfinde verschiedene Maschen, nicht nur die bekannten.
- `false`: Entscheid aus eigenen Gründen, auch wenn er unvernünftig wirkt; Rat ohne Druck; jemand hat einen Betrug
  bereits durchschaut und meldet ihn nur.

---

## 3. Vielfalt statt Vorlagen

Die folgenden Listen zeigen die **Breite**, die abgedeckt werden soll. Sie sind keine Bausteine zum Zusammensetzen. Erfinde
für jedes Gespräch eine konkrete Situation mit eigenen Details, die sich so in keinem anderen Gespräch wiederholt.

**Anlässe** (Beispiele, erweitern): Kontoeröffnung, Karte, E-Banking, Hypothek, Kredit, Anlageberatung,
Vermögensverwaltung, Zahlungsverkehr einer Firma, Erbschaft, Vorsorge, Devisen, Kryptowährungen, Umzug ins Ausland,
Bargeld, Spenden, Scheidung, Firmengründung, Löhne, Reklamation, Betrugsverdacht, Versicherungsleistung, Stiftung,
Immobilienverkauf, Kunstkauf, Studium der Kinder, Pflegeheim.

**Personen**: Alter, Beruf, Lebenslage, Sprachgewandtheit, Stimmung (gestresst, freundlich, misstrauisch, verwirrt,
ungeduldig, gelangweilt). Anrufende sind Kundinnen, Kunden, Angehörige, Firmenvertreter, Betrüger. Die Bank spricht durch
Beraterinnen, Berater, Support-Mitarbeitende. **Bankangestellte reden wie Menschen bei der Arbeit**, nicht wie ein
Lehrbuch: Sie erklären nicht jede Regel, sind manchmal knapp, unsicher, abgelenkt oder zu entgegenkommend.

**Mechanismen**: Für jeden Prüfpunkt gibt es viele Arten, wie ein Verstoss geschehen kann. Verwende innerhalb einer
Antwort für denselben Prüfpunkt nie zweimal denselben Mechanismus, und wechsle ihn auch über die Antworten hinweg.

**Wie deutlich**: ausdrücklich, indirekt, verharmlosend, in Etappen über mehrere Beiträge, erst durch eine frühe
Erklärung verständlich.

**Wo im Gespräch**: am Anfang, in der Mitte, kurz vor Schluss; verteilt; nach langem harmlosem Teil.

### Wie die Bank auf einen Verstoss reagiert

Verteile die Gespräche mit Verstoss ungefähr so:
- **etwa ein Drittel**: Niemand bemerkt oder kommentiert den Verstoss; das Gespräch geht normal weiter, der Auftrag
  wird vielleicht sogar ausgeführt.
- **etwa ein Drittel**: Die Bank reagiert zögernd, ausweichend oder nur beiläufig, oder sie geht darauf ein.
- **etwa ein Drittel**: Die Bank lehnt ab oder warnt.

**Höchstens jedes fünfte Gespräch mit Verstoss** enthält eine Stelle, an der jemand den Verstoss beim Namen nennt
(das Delikt benennt oder die verletzte Regel erklärt). Umgekehrt kommen solche Erklärungen auch in harmlosen Gesprächen
vor, etwa als allgemeine Frage oder Warnung. So lässt sich ein Verstoss nicht daran erkennen, dass jemand ihn benennt.

### Regeln gegen Abkürzungen

1. **Reizwörter auch in harmlosen Gesprächen**: Begriffe, die nach Verstoss klingen, kommen in Gesprächen ohne Verstoss
   vor (verneint, zitiert, erklärt, als Warnung, als Frage nach den Regeln).
2. **Verstösse auch ohne Reizwörter**: Viele Verstösse werden umschrieben.
3. **Täter wechseln**: Mal die anrufende Person, mal der Bankangestellte, mal eine geschilderte Drittperson.
4. **Länge unabhängig vom Label**: Kurze und lange Gespräche gibt es mit und ohne Verstoss.
5. **Ton unabhängig vom Label**: Verstösse auch in freundlichen, beiläufigen Gesprächen; harmlose Gespräche auch mit Streit
   und Aufregung.
6. **Früher Kontext entscheidet**: In einem Teil der Gespräche wird eine spätere, mehrdeutige Äusserung erst durch eine
   frühere Erklärung zum Verstoss oder zum harmlosen Fall. Zwischen beiden liegen mehrere Beiträge.
7. **Keine Formeln**: Kein fester Gesprächsanfang. Mal beginnt die Bank, mal die anrufende Person, mal ruft die Bank an,
   mal setzt das Gespräch nach einer Weiterleitung ein; die Begrüssung mit Name und Abteilung höchstens in einer
   Minderheit. Keine wiederkehrenden Schlusssätze, Namen, Firmen, Beträge oder Wendungen innerhalb einer Antwort.

### Kontrastpaare

Etwa ein Viertel der Gespräche entsteht als **Paar**, direkt hintereinander ausgegeben: zwei fast gleiche Gespräche, bei
denen ein Detail mindestens ein Label umdreht. Erfinde für jedes Paar ein eigenes entscheidendes Detail und wechsle die
Art des Details zwischen den Paaren. Das Detail liegt oft **nicht** in derselben Äusserung wie die verdächtig klingende
Stelle.

### Verteilung pro Antwort

- etwa 30 % ohne Verstoss (alle Labels `false`), davon mindestens die Hälfte mit Reizwörtern oder knapp harmlosem Verlauf,
- etwa 45 % mit genau einem `true`-Label,
- etwa 25 % mit zwei oder mehr `true`-Labels (die nicht nur die natürliche Doppelung sind: Insiderinformation
  weitergeben = `insider_trading` + `confidential_information`),
- jeder der 9 Prüfpunkte kommt über mehrere Antworten verteilt ungefähr gleich oft als `true` vor; Prüfpunkte, die
  in der Anfrage genannt werden, häufiger.

Länge: etwa ein Drittel kurz (8–14 Beiträge), ein Drittel mittel (15–30), ein Drittel lang (31–60, mit viel normalem
Bankgeschäft rund um die entscheidende Stelle).

---

## 4. Sprache und Stil

- **Schweizer Hochdeutsch**: kein „ß“ (immer „ss“), Franken, Schweizer Begriffe und Orte. Kein Dialekt.
- **Gesprochene Sprache**: kurze Sätze, Nachfragen, Selbstkorrekturen, Füllwörter in Massen („also“, „ähm“ selten),
  Missverständnisse, Unterbrechungen durch Beitragswechsel. Nicht wie ein Lehrbuch.
- **Für die Vertonung**: Beträge, Zahlen und Codes so ausschreiben, wie man sie spricht („achtzigtausend Franken“,
  „vier, sieben, eins, eins“). Keine Regieanweisungen, keine Geräusche in Klammern, kein Markdown, keine Emojis.
- **Genau zwei Sprecher** pro Gespräch: einer von der Bank, einer, der anruft oder angerufen wird. Weitere Personen
  kommen nur als Erwähnung vor. Wer sich nur als Bank ausgibt, ist nicht die Bank (`speaker` = `kunde`).
- **Alles fiktiv**: erfundene Namen, Firmen, Produkte, Banken; keine echten Unternehmen, Börsenkürzel, Personen; keine
  echten Passwörter oder Kartennummern.
- Die Bank heisst „die Bank“ oder bekommt einen erfundenen Namen. Gespräche enden nicht immer sauber; manche brechen ab.

---

## 5. Ablauf pro Antwort

1. **Plan**: Lege für alle Gespräche der Antwort vorab fest: Anlass, Personen, Verlauf in einem Satz, beabsichtigte
   `true`-Labels, Mechanismus pro Verstoss, Reaktion der Bank, Gesprächsanfang, Paare. Prüfe den Plan auf Vielfalt
   (kein Mechanismus doppelt, keine zwei gleichen Anfänge) und auf die verlangten Verteilungen.
2. **Schreiben**: Schreibe die Gespräche nach Plan.
3. **Labeln aus dem Text, nicht aus dem Plan**: Beantworte für jedes Gespräch alle 9 Fragen anhand des fertigen
   Textes. Weicht ein Label vom Plan ab, ändere den Text oder das Label, bis beides stimmt.
4. **Eindeutigkeit**: Ist ein Label auch für eine sorgfältige Compliance-Fachperson nicht klar entscheidbar, formuliere die
   Stelle eindeutig. Schwer erkennbar ist erwünscht; unentscheidbar nicht.

Gib den Plan nicht aus, nur das Ergebnis.

---

## 6. Ausgabeformat

JSON Lines: **eine Zeile pro Gespräch**, sonst nichts (kein Text davor oder danach, keine Code-Blöcke).

```json
{"turns": [{"speaker": "bank", "text": "..."}, {"speaker": "kunde", "text": "..."}],
 "labels": {"insider_trading": false, "market_manipulation": false, "money_laundering": false,
            "confidential_information": false, "false_records": false, "bribery": false,
            "control_circumvention": false, "access_credentials": false, "manipulated_customer": false}}
```

- `turns`: die Beiträge in Reihenfolge; `speaker` ist `bank` oder `kunde` (auch für Angehörige, Firmenvertreter,
  Betrüger am Telefon). Der Sprecher wird für die Vertonung mit zwei Stimmen gebraucht.
- `labels`: immer alle 9 Schlüssel, je `true` oder `false`.

### Speicherort

- **Mit Dateizugriff**: Schreibe jede Antwort als eigene Datei nach `finetuning/data/synthetic/batch_<NNN>.jsonl`
  (Projektordner, dreistellig, z.B. `batch_007.jsonl`). Nimm die nächste freie Nummer und überschreibe nie eine bestehende
  Datei.
- **Ohne Dateizugriff**: Gib die Zeilen in der Antwort aus; sie werden unter demselben Namen abgelegt.

---

## 7. Prüfliste vor der Ausgabe

- [ ] Jede Zeile ist gültiges JSON mit `turns` und allen 9 Labels.
- [ ] Jedes Label ist die wahre Antwort auf seine Frage für den fertigen Text, nach der Regel für „someone“.
- [ ] Keine zwei Gespräche teilen Anlass + Verstoss + Verlauf; keine wiederholten Namen, Firmen, Beträge, Einstiegssätze.
- [ ] Reizwörter kommen auch in harmlosen Gesprächen vor; Verstösse kommen auch ohne Reizwörter vor.
- [ ] Reaktion der Bank verteilt (unbemerkt / zögernd oder mitmachend / ablehnend); höchstens jedes fünfte Gespräch mit
      Verstoss benennt ihn ausdrücklich.
- [ ] Pro Prüfpunkt kein Mechanismus doppelt; kein fester Gesprächsanfang; keine Formulierungen aus dieser Anweisung.
- [ ] Gemeldete Vorfälle (Opfer, Zeuge) sind für die Handlungen des Täters `false` gelabelt.
- [ ] Verteilung (ohne / ein / mehrere Verstösse, Längen, Paare) ungefähr wie verlangt.
- [ ] Schweizer Hochdeutsch ohne „ß“, gesprochen, Zahlen ausgeschrieben, genau zwei Sprecher, alles fiktiv.
