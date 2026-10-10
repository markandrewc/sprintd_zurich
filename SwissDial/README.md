# SwissDial TTS

Schweizerdeutscher Text → Audio mit [swordi/SwissDial-TTS](https://huggingface.co/swordi/SwissDial-TTS)
(ESPnet VITS, Zeichen-Input, 22.05 kHz, 8 Dialekte über x-Vektoren).

## Setup

Läuft im Projekt-`.venv` (Python 3.11, torch 2.11 cu128):

```
pip install "torchaudio==2.11.*" --index-url https://download.pytorch.org/whl/cu128
pip install espnet==202511 soundfile kaldiio
```

Das Modell (~370 MB) lädt beim ersten Start automatisch in den HF-Cache.

## Nutzung

```
python SwissDial/tts.py "Grüezi mitenand, wie gaht's?"            # -> outputs/swissdial/zh_....wav
python SwissDial/tts.py "Grüessech mitenand" -d be -o bern.wav
python SwissDial/tts.py -f text.txt -d bs -s 1.1                  # Tempo 1.1
python SwissDial/tts.py "Hoi zäme" --all                          # alle 8 Dialekte
python SwissDial/app.py                                           # Web-UI auf http://localhost:7861
```

Im Code:

```python
from tts import SwissDialTTS          # aus SwissDial/ heraus
tts = SwissDialTTS()
wav = tts.synthesize("Grüezi mitenand", dialect="zh")   # np.float32, tts.fs Hz
tts.to_file("Grüezi mitenand", "out.wav", dialect="be")
```

Dialekte: `ag` Aargau, `be` Bern, `bs` Basel, `gr` Graubünden, `lu` Luzern, `sg` St. Gallen, `vs` Wallis, `zh` Zürich.

## Hinweise

- Trainiert auf Text in Dialekt-Schreibweise. Hochdeutsch funktioniert, klingt aber weniger natürlich.
- Längere Texte werden an Satzenden (`. ! ? …`) getrennt, einzeln synthetisiert und mit 0.25 s Pause zusammengefügt.
- Auf GPU dauert ein Satz ca. 0.1 s. CPU geht auch (`SWISSDIAL_DEVICE=cpu`).
- Die Warnung „weight norm is not applied in the pretrained model …“ beim Laden ist harmlos (Kompatibilitäts-Shim von ESPnet).
