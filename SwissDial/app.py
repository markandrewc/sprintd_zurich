"""
Web-UI für SwissDial-TTS: Text eingeben, Dialekt wählen, Audio anhören/herunterladen.

  python SwissDial/app.py     # http://localhost:7861

Umgebungsvariablen:
  SWISSDIAL_HOST  Default 0.0.0.0
  SWISSDIAL_PORT  Default 7861 (7860 belegt kev_app.py)
"""

import os

import gradio as gr

from tts import DIALECTS, SwissDialTTS

EXAMPLES = [
    ["Grüezi mitenand, wie gaht's eu hüt?", "zh"],
    ["Mir göh hüt z'Abe no chli ga loufe.", "be"],
    ["Hesch du scho gässe?", "bs"],
]

tts = SwissDialTTS()


def speak(text, dialect, speed):
    if not text or not text.strip():
        raise gr.Error("Bitte Text eingeben")
    return tts.fs, tts.synthesize(text, dialect, speed)


with gr.Blocks(title="SwissDial TTS") as demo:
    gr.Markdown("## SwissDial TTS\nSchweizerdeutscher Text in Dialekt-Schreibweise → Sprache (swordi/SwissDial-TTS, VITS)")
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(label="Text", lines=4, placeholder="Grüezi mitenand ...")
            dialect = gr.Dropdown([(f"{name} ({k})", k) for k, name in DIALECTS.items()], value="zh", label="Dialekt")
            speed = gr.Slider(0.5, 1.5, value=1.0, step=0.05, label="Tempo")
            btn = gr.Button("Sprechen", variant="primary")
        audio = gr.Audio(label="Audio", type="numpy", autoplay=True)
    gr.Examples(EXAMPLES, [text, dialect])
    btn.click(speak, [text, dialect, speed], audio)
    text.submit(speak, [text, dialect, speed], audio)

if __name__ == "__main__":
    demo.launch(server_name=os.environ.get("SWISSDIAL_HOST", "0.0.0.0"),
                server_port=int(os.environ.get("SWISSDIAL_PORT", "7861")))
