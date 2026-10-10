#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_calls.py – build the 50 held-out test calls with the FHNW STT4SG TTS API.

Standard library only (no installs, no local AI models). The FHNW API does all
translation (Standard German -> Swiss German) and all speech synthesis; this script
only sends requests, caches results, checks texts with string rules and mixes audio.

  python3 make_calls.py                         full run (resumable, sequential)
  python3 make_calls.py --only T50-trade-01-A   one call (repeat --only for more)
  python3 make_calls.py --voice-check           one sample per dialect into voice_check/
  python3 make_calls.py --offline               no API calls: assemble what the cache allows
  python3 make_calls.py --validate              final validation report only
  python3 make_calls.py --mock --root DIR       test mode with a fake API (never touches the real cache)

Etiquette (hard rules): one request at a time, 2 s pause between API calls, every result
cached by sha1(endpoint + dialect + text), resume after interruption, stop after 5
consecutive failures. Usage terms: non-commercial hackathon test data only, never used
to train a model, all dialogue content fictional.
"""
import argparse
import array
import csv
import datetime
import hashlib
import json
import math
import os
import random
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave

BASE = "https://stt4sg.fhnw.ch/tts"
EP_TRANSLATE = "translate_interface"
EP_SPEECH = "speech_interface"
DIALECTS = ["Aargau", "Bern", "Basel", "Graubünden", "Luzern", "St. Gallen", "Valais", "Zürich"]
PAUSE_S = 2.0
MAX_CONSEC_FAIL = 5
SR = 16000
CPS_MIN, CPS_MAX = 8.0, 26.0   # on the untrimmed audio; brief said 8-22, see README (Luzern voice runs at 21-24)
CPS_NOTE = 22.0                 # above this the sentence is logged as fast, without splitting
VOICE_SENTENCE = "Guten Tag, hier ist die Kundenberatung. Wie kann ich Ihnen heute helfen?"
SNR_RANGE = (16.0, 24.0)       # target, measured result must lie in 15-25 dB
EVENT_REL_DB = (-12.0, -6.0)   # bell or knock relative to the speech of the act turn
TARGET_RMS_DB = -20.0
PEAK_LIMIT_DB = -1.0
SILENCE_DB = -40.0
NOISY_SCALE = 0.89             # fixed -1 dB headroom for every noisy file (a fixed factor keeps pairs bit-identical)
NOISY_LIMIT = 0.98             # sample-wise limit after scaling; clipped samples are counted in <id>.json
CAL_NOISE_S = 10               # length of the calibration noise that sets the noise level
VERSION = "v6"

ROOT = os.path.dirname(os.path.abspath(__file__))


class StopRun(Exception):
    pass


class ApiError(Exception):
    pass


# --------------------------------------------------------------------------- utils

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Log:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def __call__(self, msg):
        line = "[%s] %s" % (now(), msg)
        print(line, flush=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def sha1(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def cache_key(endpoint, dialect, text):
    return sha1(endpoint + dialect + text)


def atomic_write_bytes(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".tmp_")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def atomic_write_text(path, text):
    atomic_write_bytes(path, text.encode("utf-8"))


def write_json(path, obj):
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def fmt_ts(sec):
    m = int(sec // 60)
    return "%02d:%04.1f" % (m, sec - 60 * m)


def safe_name(dialect):
    return dialect.replace(". ", "_").replace(" ", "_").replace("ü", "ue")


# ------------------------------------------------------------------------- the API

class Api:
    """Sequential Gradio client: POST /call/<ep> -> event_id, GET /call/<ep>/<id> -> SSE."""

    def __init__(self, log):
        self.log = log
        self.last = 0.0
        self.consec_fail = 0
        self.use_curl = False
        self.calls = 0

    def _http(self, method, url, body=None, timeout=300):
        if not self.use_curl:
            req = urllib.request.Request(url, data=body, method=method,
                                         headers={"Content-Type": "application/json",
                                                  "User-Agent": "sprintd-test50/1.0 (non-commercial hackathon test set)"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.read()
            except urllib.error.URLError as e:
                reason = getattr(e, "reason", None)
                if isinstance(reason, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in str(e):
                    self.log("TLS certificates of this Python are not set up, switching to /usr/bin/curl")
                    self.use_curl = True
                else:
                    raise
        cmd = ["curl", "-sS", "--fail", "-m", str(timeout), "-X", method,
               "-H", "Content-Type: application/json", "-A", "sprintd-test50/1.0"]
        if body is not None:
            cmd += ["--data-binary", "@-"]
        cmd.append(url)
        p = subprocess.run(cmd, input=body, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout + 10)
        if p.returncode != 0:
            raise ApiError("curl %d: %s" % (p.returncode, p.stderr.decode("utf-8", "replace")[:200]))
        return p.stdout

    @staticmethod
    def parse_sse(text):
        event, data = None, []
        result = None
        for line in text.splitlines() + [""]:
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
            elif line == "":
                if event in ("complete", "error"):
                    result = (event, "\n".join(data))
                    break
                event, data = None, []
        return result

    def call(self, endpoint, data):
        attempt = 0
        while True:
            wait = PAUSE_S - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            t0 = time.time()
            try:
                body = json.dumps({"data": data}).encode("utf-8")
                post = json.loads(self._http("POST", "%s/call/%s" % (BASE, endpoint), body, timeout=60).decode("utf-8"))
                eid = post["event_id"]
                sse = self._http("GET", "%s/call/%s/%s" % (BASE, endpoint, eid)).decode("utf-8", "replace")
                self.last = time.time()
                res = self.parse_sse(sse)
                if res is None:
                    raise ApiError("no complete event: %r" % sse[:200])
                ev, payload = res
                if ev != "complete":
                    raise ApiError("event %s: %s" % (ev, payload[:200]))
                self.consec_fail = 0
                self.calls += 1
                return json.loads(payload), time.time() - t0
            except (ApiError, urllib.error.URLError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
                self.last = time.time()
                self.consec_fail += 1
                self.log("API %s failed (%d in a row): %s" % (endpoint, self.consec_fail, str(e)[:200]))
                if self.consec_fail >= MAX_CONSEC_FAIL:
                    raise StopRun("stopped after %d consecutive failures" % self.consec_fail)
                backoff = min(120, 4 * (2 ** attempt))
                attempt += 1
                time.sleep(backoff)

    def download(self, info):
        url = info.get("url") if isinstance(info, dict) else None
        if not url:
            url = "%s/file=%s" % (BASE, info["path"])
        return self._http("GET", url, None, timeout=120)


class MockApi:
    """Offline stand-in for tests: identity translation (with an occasional dropped negation)
    and synthetic 'speech' (tone bursts) whose length follows the text. Never used for real data."""

    def __init__(self, log):
        self.log = log
        self.calls = 0

    def call(self, endpoint, data):
        self.calls += 1
        text, dialect = data
        if endpoint == EP_TRANSLATE:
            rep = {"nicht": "nöd", "kein": "kei", "keine": "kei", "keinen": "kei", "keinem": "keim",
                   "nichts": "nüt", "niemand": "niemer", "niemanden": "niemer", "ich": "i", "ist": "isch",
                   "Guten": "Guete", "habe": "ha", "haben": "händ", "Sie": "Si", "nicht.": "nöd."}
            out = " ".join(rep.get(w, w) for w in text.split(" "))
            if out == text:
                out = out[0].lower() + out[1:]
            if int(sha1(text)[:4], 16) % 23 == 0:
                out = re.sub(r"\b(nöd|kei|nüt)\b ?", "", out, count=1)
            return [out], 0.0
        return [{"mock_text": text, "dialect": dialect}, None], 0.0

    def download(self, info):
        text, dialect = info["mock_text"], info["dialect"]
        rng = random.Random(sha1(dialect + text))
        f0 = 110 + 15 * DIALECTS.index(dialect)
        dur = max(0.6, len(text) / 16.0)
        n = int(dur * SR)
        lead, tail = int(0.15 * SR), int(0.25 * SR)
        x = [0.0] * (lead + n + tail)
        syl = int(0.18 * SR)
        for s0 in range(0, n, syl):
            f = f0 * (1 + 0.15 * rng.random())
            amp = 0.15 + 0.1 * rng.random()
            for i in range(min(syl, n - s0)):
                env = math.sin(math.pi * i / syl)
                t = i / SR
                x[lead + s0 + i] = amp * env * (math.sin(2 * math.pi * f * t) + 0.4 * math.sin(4 * math.pi * f * t))
        return wav_bytes(x)


# --------------------------------------------------------------------- audio basics

def wav_bytes(samples):
    import io
    a = array.array("h", (max(-32768, min(32767, int(round(v * 32767)))) for v in samples))
    if sys.byteorder == "big":
        a.byteswap()
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(a.tobytes())
    w.close()
    return buf.getvalue()


def write_wav(path, samples):
    atomic_write_bytes(path, wav_bytes(samples))


def _convert_external(path):
    """Convert to 16 kHz mono PCM16 with afconvert (macOS) or ffmpeg. Returns new path or None."""
    out = path + ".16k.wav"
    if shutil.which("afconvert"):
        p = subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", path, out],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0 and os.path.exists(out):
            return out
    if shutil.which("ffmpeg"):
        p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR),
                            "-acodec", "pcm_s16le", out], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0 and os.path.exists(out):
            return out
    return None


def read_wav(path):
    """Return mono float samples at 16 kHz. Converts other formats if needed."""
    try:
        w = wave.open(path, "rb")
    except (wave.Error, EOFError):
        conv = _convert_external(path)
        if not conv:
            raise
        return read_wav(conv)
    ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    raw = w.readframes(n)
    w.close()
    if (ch, sw, sr) != (1, 2, SR):
        conv = _convert_external(path)
        if conv:
            return read_wav(conv)
    if sw == 2:
        a = array.array("h")
        a.frombytes(raw[: len(raw) // 2 * 2])
        if sys.byteorder == "big":
            a.byteswap()
        vals = [v / 32768.0 for v in a]
    else:
        vals = []
        for i in range(0, len(raw) - sw + 1, sw):
            b = raw[i:i + sw]
            if sw == 1:
                vals.append((b[0] - 128) / 128.0)
            else:
                vals.append(int.from_bytes(b, "little", signed=True) / float(2 ** (8 * sw - 1)))
    if ch > 1:
        vals = [sum(vals[i:i + ch]) / ch for i in range(0, len(vals) - ch + 1, ch)]
    if sr != SR:  # built-in linear resampler
        ratio = sr / float(SR)
        m = int(len(vals) / ratio)
        out = []
        for j in range(m):
            pos = j * ratio
            i = int(pos)
            frac = pos - i
            a0 = vals[i]
            a1 = vals[i + 1] if i + 1 < len(vals) else a0
            out.append(a0 + (a1 - a0) * frac)
        vals = out
    return vals


def db(x):
    return 20 * math.log10(max(x, 1e-12))


def rms(x):
    return math.sqrt(sum(v * v for v in x) / len(x)) if x else 0.0


def frame_rms(x, frame):
    return [rms(x[i:i + frame]) for i in range(0, len(x), frame)]


def trim_silence(x):
    frame = int(0.01 * SR)
    fr = frame_rms(x, frame)
    thr = 10 ** (SILENCE_DB / 20)
    idx = [i for i, v in enumerate(fr) if v >= thr]
    if not idx:
        return []
    a = max(0, (idx[0] - 2) * frame)
    b = min(len(x), (idx[-1] + 4) * frame)
    return x[a:b]


def active_rms(x):
    frame = int(0.02 * SR)
    thr = 10 ** (SILENCE_DB / 20)
    act = [v for v in frame_rms(x, frame) if v >= thr]
    if not act:
        return 0.0
    return math.sqrt(sum(v * v for v in act) / len(act))


def normalise(x):
    r = active_rms(x)
    if r <= 0:
        return x, 0.0
    g = (10 ** (TARGET_RMS_DB / 20)) / r
    peak = max(abs(v) for v in x)
    lim = 10 ** (PEAK_LIMIT_DB / 20)
    if peak * g > lim:
        g = lim / peak
    return [v * g for v in x], db(g)


def biquad_coeffs(kind, f0, q=0.7071):
    w0 = 2 * math.pi * f0 / SR
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2 * q)
    if kind == "lp":
        b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2
    else:
        b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2
    a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def biquad(x, c):
    b0, b1, b2, a1, a2 = c
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, xi in enumerate(x):
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        if -1e-30 < yi < 1e-30:
            yi = 0.0
        x2, x1, y2, y1 = x1, xi, y1, yi
        y[i] = yi
    return y


HP300 = biquad_coeffs("hp", 300.0)
LP3400 = biquad_coeffs("lp", 3400.0)


def phone_band(x):
    return biquad(biquad(x, HP300), LP3400)


def pink_noise(n, rng):
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    out = [0.0] * n
    g = rng.gauss
    for i in range(n):
        w = g(0.0, 1.0)
        b0 = 0.99886 * b0 + w * 0.0555179
        b1 = 0.99332 * b1 + w * 0.0750759
        b2 = 0.96900 * b2 + w * 0.1538520
        b3 = 0.86650 * b3 + w * 0.3104856
        b4 = 0.55000 * b4 + w * 0.5329522
        b5 = -0.7616 * b5 - w * 0.0168980
        out[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11
        b6 = w * 0.115926
    return out


def bell(rng):
    n = int(0.6 * SR)
    k = math.log(1000.0) / 0.6
    ph = rng.random() * 2 * math.pi
    x = []
    for i in range(n):
        t = i / SR
        env = math.exp(-k * t) * min(1.0, t / 0.004)
        x.append(env * (math.sin(2 * math.pi * 880 * t + ph) + 0.6 * math.sin(2 * math.pi * 1320 * t + ph)))
    return x


def knock(rng):
    hits = rng.choice([3, 4])
    gap = int(0.08 * SR)
    blen = int(0.03 * SR)
    x = [0.0] * (gap * (hits - 1) + blen)
    for h in range(hits):
        lp = 0.0
        amp = 1.0 - 0.12 * h
        for i in range(blen):
            t = i / SR
            lp = 0.6 * lp + 0.4 * rng.uniform(-1, 1)
            env = math.exp(-t / 0.006)
            thump = math.sin(2 * math.pi * 160 * t) * math.exp(-t / 0.012)
            x[h * gap + i] += amp * env * (0.7 * lp + 0.8 * thump)
    return x


def loud_rms(x):
    """RMS over the loud part of an event (envelope within 20 dB of its peak)."""
    frame = int(0.01 * SR)
    fr = frame_rms(x, frame)
    pk = max(fr) if fr else 0.0
    sel = [v for v in fr if v >= pk * 0.1]
    return math.sqrt(sum(v * v for v in sel) / len(sel)) if sel else 0.0


def median_f0(x):
    """Rough median pitch by autocorrelation on 8 kHz decimated audio (voice check only)."""
    y = [(x[i] + x[i + 1]) / 2 for i in range(0, len(x) - 1, 2)]
    sr = SR // 2
    fr, hop = int(0.03 * sr), int(0.02 * sr)
    lo, hi = sr // 400, sr // 70
    energies = [sum(v * v for v in y[s:s + fr]) for s in range(0, len(y) - fr, hop)]
    if not energies:
        return None
    emax = max(energies)
    f0s = []
    for k, s in enumerate(range(0, len(y) - fr, hop)):
        if energies[k] < 0.1 * emax:
            continue
        seg = y[s:s + fr + hi]
        best, best_lag = 0.0, 0
        rs = []
        for lag in range(lo, hi + 1):
            c = e0 = e1 = 0.0
            for i in range(fr):
                a, b = seg[i], seg[i + lag] if i + lag < len(seg) else 0.0
                c += a * b
                e0 += a * a
                e1 += b * b
            rs.append(c / math.sqrt(e0 * e1 + 1e-12))
        mx = max(rs)
        if mx < 0.5:
            continue
        first = next(i for i, r in enumerate(rs) if r >= 0.9 * mx)
        f0s.append(sr / float(lo + first))
    if not f0s:
        return None
    f0s.sort()
    return round(f0s[len(f0s) // 2])


# ------------------------------------------------------------ translation checks

DE_NEG = {"nicht", "kein", "keine", "keinen", "keinem", "keiner", "keines", "nie", "niemals", "niemand",
          "niemanden", "niemandem", "nichts", "nirgends", "nirgendwo"}
CH_NEG = {"ke", "kä", "keis", "niema", "niemu", "nieneds", "nienet", "nümm", "nonig", "nanig", "noni", "nonid", "nanid", "nonöd", "nonit", "nanit", "nonie", "nonöt", "nonig", "nonid",
          "nüme", "nümme", "nimmi", "nüt", "niemerem", "niemertem", "niemandem", "niemanden", "niemerä", "niemertä", "niemerum", "niemertum",
          "nöd", "nid", "ned", "ni", "nit", "nöt", "net", "nüd", "nod", "nüt", "nüüt", "nünt", "nix", "nyt", "nüd",
          "kei", "keis", "keini", "keine", "kein", "keim", "keiner", "keinä", "keis", "käi", "käis", "kai", "kais",
          "kaini", "käini", "keini", "keinem", "keinen", "nie", "nia", "niä", "niemer", "niemert", "niemand",
          "niemmer", "niemu", "niemr", "niemerem", "nümme", "nüme", "nümm", "nüm", "nimme", "nimmi", "nüt",
          "niene", "nienet", "nirgends", "nirgendwo", "nienets", "nichts", "nicht", "nie", "nüüt", "nünt",
          "nichtt", "nöüt", "nöt"}

ARTICLES = {"ein", "eine", "einen", "einem", "einer", "eines", "e", "es", "en", "em", "ä", "a", "i", "ne", "nen",
            "ei", "äi", "ai", "eini", "einä", "u", "und", "ond", "un"}


def _collapse(s):
    return re.sub(r"(.)\1+", r"\1", s)


def _forms(*xs):
    return sorted({x for x in xs} | {_collapse(x) for x in xs})


_MORPH = {}


def _add(forms, kind, val):
    for f in forms:
        _MORPH.setdefault(f, []).append((kind, val))


_UNIT = {
    0: _forms("null", "nul", "nulä", "nulle"),
    1: _forms("eins", "eis", "ais", "äis", "ains", "ein", "ei", "äi", "ai"),
    2: _forms("zwei", "zwai", "zwoi", "zwöi", "zwee", "zwo", "zwö", "zwäi", "zwou", "zwöu", "zwe"),
    3: _forms("drei", "drü", "drüü", "drey", "drej", "dri", "drüi"),
    4: _forms("vier", "vieri", "viär", "fier", "viere"),
    5: _forms("fünf", "füf", "füüf", "föif", "foif", "fif", "feif", "fünfi", "füfi", "föifi", "füfe"),
    6: _forms("sechs", "sächs", "säx", "sex", "sechsi", "sächsi", "säks", "seks", "sächse"),
    7: _forms("sieben", "sibe", "sibä", "sübe", "siebe", "sibni", "sibi", "sibne", "sübä", "siibe", "sieb", "sebe",
              "sebä", "sebni", "sibu"),
    8: _forms("acht", "achti"),
    9: _forms("neun", "nün", "nüün", "nüni", "nyn", "nüne", "nüüni", "nüü", "nini"),
}
_TEEN_STEM = {3: ["drei", "dri", "drü", "drei"], 4: ["vier", "viär"], 5: ["fünf", "füf", "föif", "fuf", "fünf"],
              6: ["sech", "säch", "sechs", "sächs"], 7: ["sieb", "sibe", "sib", "sübe", "sibä"], 8: ["acht", "ach"],
              9: ["neun", "nün", "nüün"]}
_TEN = ["zehn", "zä", "zäh", "ze", "zee", "zeh", "zehni", "zäni", "zächni", "zäne"]
_TENS = {20: ["zwanzig", "zwanzg", "zwänzg", "zwänzig", "zwänzgi", "zwänzge", "zwänzk", "zwanzk"],
         30: ["dreissig", "drissg", "drisig", "drissig", "drüssg", "dreissg", "dreisg", "drisk", "drissk"],
         40: ["vierzig", "vierzg", "vierzgi", "viärzg", "vierzk"],
         50: ["fünfzig", "füfzg", "föifzg", "fufzg", "füfzig", "fünfzg", "feifzg", "füfzk", "föifzk"],
         60: ["sechzig", "sächzg", "sechzg", "sächzig", "sechzgi", "sächzk"],
         70: ["siebzig", "sibezg", "sibzg", "sübezg", "siebzg", "sibezig", "sibezk"],
         80: ["achtzig", "achzg", "achtzg", "achzig", "achzk"],
         90: ["neunzig", "nünzg", "nünzig", "neunzg", "nünzk"]}
for v, fs in _UNIT.items():
    _add(fs, "unit", v)
_add(_forms("zehn", "zä", "zäh", "zee", "zeh", "zehni", "zäni", "zächni"), "unit", 10)
_add(_forms("elf", "ölf", "elfi", "ölfi", "euf", "öuf"), "unit", 11)
_add(_forms("zwölf", "zwölfi", "zwöuf", "zwölfe"), "unit", 12)
for v, stems in _TEEN_STEM.items():
    _add(_forms(*[s + t for s in stems for t in _TEN]), "unit", 10 + v)
for v, fs in _TENS.items():
    _add(_forms(*fs), "tens", v)
_add(_forms("hundert", "hundärt", "hunderd", "hundrt", "hondert", "hondärt", "hunnert", "hundertt", "hundart",
            "hunert", "hunder", "hondert"),
     "hundred", 100)
_add(_forms("tausend", "tusig", "tuusig", "tausig", "tusend", "tused", "tuused", "tuusend", "tausnd", "tuusit",
            "dausig", "dausend", "dusig", "duusig", "tüüsig", "tüsig", "tuusik", "toosig"),
     "thousand", 1000)
_add(_forms("und", "e", "ä", "a", "i", "u", "ond", "un", "en", "än", "an", "end", "e n"), "conn", 0)
_MAXLEN = max(len(k) for k in _MORPH)


def _segment(s):
    """All morpheme segmentations of s (small strings), as lists of (kind, val)."""
    out = []

    def rec(pos, acc):
        if len(out) > 20:
            return
        if pos == len(s):
            out.append(list(acc))
            return
        for L in range(min(_MAXLEN, len(s) - pos), 0, -1):
            piece = s[pos:pos + L]
            for m in _MORPH.get(piece, []):
                acc.append(m)
                rec(pos + L, acc)
                acc.pop()

    rec(0, [])
    return out


def _evaluate(seq):
    total, cur = 0, 0
    kinds = [k for k, _ in seq]
    for i, (k, v) in enumerate(seq):
        if k == "conn":
            if i == 0 or i == len(seq) - 1 or kinds[i - 1] != "unit" or kinds[i + 1] != "tens":
                return None
        elif k == "unit":
            if i > 0 and kinds[i - 1] in ("unit", "tens"):
                return None
            cur += v
        elif k == "tens":
            if i > 0 and kinds[i - 1] == "tens":
                return None
            if i > 0 and kinds[i - 1] == "unit":
                return None  # unit+tens needs a connector ("einundzwanzig")
            cur += v
        elif k == "hundred":
            cur = (cur or 1) * 100
        elif k == "thousand":
            total += (cur or 1) * 1000
            cur = 0
    return total + cur


def _parse_cardinal(w):
    best = None
    for seq in _segment(w):
        v = _evaluate(seq)
        if v is not None and (best is None or len(seq) < best[0]):
            best = (len(seq), v)
    return None if best is None else best[1]


_ORD_STEMS = {"erst": 1, "ers": 1, "ersch": 1, "zweit": 2, "drit": 3, "dritt": 3, "sieb": 7, "siebt": 7,
              "sibet": 7, "acht": 8}
_ORD_SUFFIX = ["igschte", "ischte", "ischti", "igste", "igsten", "schte", "schti", "sten", "ster", "stes", "stem",
               "ste", "ten", "ter", "tes", "tem", "te", "ti", "tä", "ta", "ts"]


def number_value(word):
    """Integer value of one token, or None. Articles and 'einmal' are not numbers."""
    w = word.lower().strip("'’.,:;!?«»\"")
    if not w:
        return None
    if re.fullmatch(r"\d[\d'’.]*", w):
        return int(re.sub(r"\D", "", w))
    if w in ARTICLES or w in ("erst", "erscht", "zerscht", "zuerst", "ersch", "einmal", "eimol", "eimal",
                              "einisch", "nomal", "nomol", "achtung", "achten", "achtet", "achte", "achtest",
                              "beachten", "erstens", "zweitens"):
        return None
    w = re.sub(r"stell?ig\w*$", "", w)
    m = re.match(r"^(.+?)(mal|mol)$", w)
    if m and m.group(1) not in ("ein", "ei", "äi", "ai", "eis", "eins", "no", "noch"):
        w = m.group(1)
    for c in (w, _collapse(w)):
        if c in ARTICLES:
            return None
        v = _parse_cardinal(c)
        if v is not None and not (v in (1,) and c in ("ein", "ei", "äi", "ai")):
            return v
    for c in (w, _collapse(w)):
        for suf in _ORD_SUFFIX:
            if c.endswith(suf) and len(c) > len(suf):
                stem = c[: len(c) - len(suf)]
                if stem in _ORD_STEMS:
                    return _ORD_STEMS[stem]
                v = _parse_cardinal(stem)
                if v is not None and stem not in ("ein", "ei", "äi", "ai", "a", "e", "i", "u"):
                    return v
    return None


def numbers_in(text):
    vals = []
    for tok in re.findall(r"[0-9][0-9'’.]*|[A-Za-zÄÖÜäöüàéèâêîôûçß]+", text):
        v = number_value(tok)
        if v is not None:
            vals.append(v)
    return vals


def tokens(text):
    return [t.lower() for t in re.findall(r"[A-Za-zÄÖÜäöüàéèâêîôûçß]+", text)]


# DE pattern -> acceptable CH pattern (checked in decisive and evidence turns)
KEY_TERMS = [
    (r"abgelaufen", r"abgl|ablauf|abgloff|ungültig|gültig|abgelauf"),
    (r"\bgültig|\bgilt\b", r"gült|gilt|gält|güelt"),
    (r"Webseite", r"web|internet|site"),
    (r"Vollmacht", r"vollm|volm"),
    (r"Kredit(stelle|abteilung|prüfung)", r"kredit"),
    (r"Rechnung", r"r[äe]chn"),
    (r"Freigabe|freigeben", r"freig"),
    (r"Zeile", r"z[ei]i?l|zeil"),
    (r"Bürgschaft", r"bürg|burg"),
    (r"Leasing|geleast", r"lea?s|lis"),
    (r"Darlehen", r"darl"),
    (r"\bCode", r"cod|kod|kot"),
    (r"Muster|Beispiel", r"must|musch|bisp|beisp|bispil"),
    (r"Aktivierungscode", r"aktivier"),
    (r"Unterschrift", r"und[ae]rschr|unterschr"),
    (r"\bohne\b", r"\bohn|\bohni"),
    (r"Erbbescheinigung", r"erb"),
    (r"Handelsregister", r"regi"),
    (r"Einzelunterschrift", r"einzel|einzu|eizel"),
    (r"gelöscht", r"lösch|losch|gstriche|glösch"),
    (r"Medienkonferenz", r"medie|konfer"),
    (r"Buchhaltung", r"buech|buch"),
    (r"bekanntgegeben", r"bekannt|bekant|kommuniz|mitteilt|gmäldet|veröffentl"),
    (r"Öffentlichkeit|öffentlich", r"öffentl|offentl|publik"),
    (r"Radio", r"radio"),
    (r"Zeitung", r"zi?itig|zeitig|zeitung"),
    (r"Nachrichten", r"nach?richt|nochricht|news|nochrichte"),
    (r"Sitzung", r"sitzig|sitzung|sitzi"),
    (r"Schwager", r"schwag|schwog"),
    (r"Finanzabteilung", r"finanz"),
    (r"Verwaltungsrat", r"verwalt"),
    (r"umgehen", r"umg"),
    (r"Kontrolle", r"kontroll"),
    (r"Prüfung", r"prüe?f|pruef"),
    (r"Monatsraten|\bRaten\b", r"rat"),
    (r"Vertrag", r"vertr"),
    (r"Anzahlung", r"a+n?zahl"),
    (r"Generalunternehmer", r"general"),
    (r"Handwerkern", r"handw"),
    (r"\beinzige\b", r"einzig|eizig|einzg|eis"),
    (r"verschiedene", r"verschi"),
    (r"Reservationsnummer", r"reserv"),
    (r"Datum", r"datum"),
    (r"Kreditkarte", r"kredit"),
    (r"Rechnungsnummer", r"r[äe]chn|nummer"),
    (r"Debitkarte", r"debit"),
    (r"Kundennummer", r"kund|chund|nummer"),
    (r"Elektrizitätswerk", r"elektr|strom"),
    (r"\bTAN\b", r"\btan\b"),
    (r"\bPIN\b", r"\bpin\b"),
    (r"Zettel", r"z[äe]d?t?t?el|zädel|zettel|zedel"),
    (r"Rechts(dienst|abteilung)", r"recht"),
    (r"\bPunkt\b", r"punkt|pünkt"),
    (r"Notiz", r"notiz"),
    (r"Schwester", r"schw[öe]s?c?h?t?er|schwöschter|schwester"),
    (r"zerstritten", r"stritt|krach|verkracht"),
    (r"Onkel", r"onk|ungg?l|unkel|ongg?el"),
    (r"aufgelöst", r"glöst|gelöst|aufglöst|ufglöst"),
    (r"veraltet", r"veralt|alt"),
    (r"aktuell", r"aktu"),
    (r"falsch", r"falsch"),
    (r"bar bezahlt", r"\bbar\b"),
    (r"Versprecher", r"versprech|versprächer"),
    (r"protokollieren", r"protokoll"),
    (r"verbergen", r"verberg|versteck"),
    (r"Fehlernummer", r"fehler|fähler"),
    (r"Fitnesscenter", r"fitness"),
]


def check_translation(de, ch, names, decisive):
    probs = []
    ch_l = ch.lower()
    if not ch.strip():
        return ["leer"]
    if re.search(r"\d", ch):
        probs.append("Ziffern im CH-Text (für TTS ausschreiben)")
    if ch.strip() == de.strip():
        probs.append("identisch mit DE")
    n_de = sum(1 for t in tokens(de) if t in DE_NEG)
    n_ch = sum(1 for t in tokens(ch) if t in CH_NEG)
    if n_de != n_ch:
        probs.append("Negation %d→%d" % (n_de, n_ch))
    nd, nc = numbers_in(de), numbers_in(ch)
    if nd != nc:
        probs.append("Zahlen %s→%s" % (nd, nc))
    for n in names:
        if re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", de) and not re.search(r"(?<!\w)" + re.escape(n.lower()), ch_l):
            probs.append("Name %s fehlt" % n)
    if decisive:
        for dp, cp in KEY_TERMS:
            if re.search(dp, de, re.IGNORECASE) and not re.search(cp, ch_l):
                probs.append("Schlüsselwort %s fehlt" % re.sub(r"\\b|[()?|]", " ", dp).split()[0])
    clitics = {"d", "s", "z", "dr", "mr", "sch", "st", "ds", "zs?"}
    garbled = [t for t in re.findall(r"[A-Za-zÄÖÜäöüß]+", ch)
               if len(t) >= 2 and not re.search(r"[aeiouyäöüàéèâêîôû]", t.lower()) and t.lower() not in clitics]
    if garbled:
        probs.append("Wort ohne Vokal: %s" % ", ".join(garbled))
    ratio = len(ch) / max(1, len(de))
    if ratio < 0.5 or ratio > 1.6:
        probs.append("Länge %.2f" % ratio)
    return probs


# --------------------------------------------------------------------- the build

class Builder:
    def __init__(self, root, api, log, offline=False):
        self.root = root
        self.api = api
        self.log = log
        self.offline = offline
        self.cache = os.path.join(root, "cache")
        self.texts_path = os.path.join(root, "texts_test50.jsonl")
        self.review_path = os.path.join(root, "needs_review.csv")
        self.calls = [json.loads(l) for l in open(self.texts_path, encoding="utf-8") if l.strip()]
        self.decisions = self._read_review()
        self.review_rows = {}
        self.sent_state = {}   # sentence key -> dict(ch_auto, ch_final, edited, problems, blocked)

    # ---- needs_review.csv
    def _read_review(self):
        dec = {}
        if os.path.exists(self.review_path):
            with open(self.review_path, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    dec[row["key"]] = row
        return dec

    def _write_review(self, current_keys=()):
        fields = ["key", "calls", "turn", "sentence", "speaker", "dialect", "de", "ch_auto", "problems",
                  "decision", "ch_final", "note"]
        # keep rows of sentences outside this run (e.g. after --only), drop rows of sentences that no longer exist
        all_keys = {sha1(t["dialect"] + "\n" + s["de"])[:16] for c in self.calls for t in c["turns"] for s in t["sentences"]}
        merged = {k: dict(r) for k, r in self.decisions.items() if k in all_keys and k not in current_keys}
        merged.update(self.review_rows)
        rows = sorted(merged.values(), key=lambda r: (r["calls"].split(";")[0], r["turn"], int(r["sentence"])))
        buf = [fields]
        for r in rows:
            buf.append([r.get(k, "") for k in fields])
        import io
        s = io.StringIO()
        w = csv.writer(s)
        for b in buf:
            w.writerow(b)
        atomic_write_text(self.review_path, s.getvalue())

    # ---- API wrappers with cache
    def _cached(self, endpoint, dialect, text):
        key = cache_key(endpoint, dialect, text)
        sub = "translate" if endpoint == EP_TRANSLATE else "speech"
        return key, os.path.join(self.cache, sub, key)

    def translate(self, de, dialect):
        key, base = self._cached(EP_TRANSLATE, dialect, de)
        if os.path.exists(base + ".json"):
            return json.load(open(base + ".json", encoding="utf-8"))["result"]
        if self.offline:
            return None
        data, dt = self.api.call(EP_TRANSLATE, [de, dialect])
        out = str(data[0]).strip()
        write_json(base + ".json", {"endpoint": EP_TRANSLATE, "dialect": dialect, "text": de, "result": out,
                                    "time": now(), "seconds": round(dt, 2)})
        self.log("translate %-10s %4.1fs  %s" % (dialect, dt, de[:60]))
        return out

    def speech(self, ch, dialect):
        key, base = self._cached(EP_SPEECH, dialect, ch)
        if os.path.exists(base + ".wav"):
            return base + ".wav"
        if self.offline:
            return None
        data, dt = self.api.call(EP_SPEECH, [ch, dialect])
        raw = self.api.download(data[0])
        atomic_write_bytes(base + ".download", raw)
        x = read_wav(base + ".download")
        write_wav(base + ".wav", x)
        os.remove(base + ".download")
        write_json(base + ".json", {"endpoint": EP_SPEECH, "dialect": dialect, "text": ch, "time": now(),
                                    "seconds": round(dt, 2), "source": data[0] if isinstance(data[0], dict) else None,
                                    "n_samples": len(x)})
        self.log("speech    %-10s %4.1fs  %.1fs audio  %s" % (dialect, dt, len(x) / SR, ch[:50]))
        return base + ".wav"

    # ---- sentence pipeline
    def sentence_jobs(self, calls):
        """Unique sentences (dialect, de) with the calls/turns that use them."""
        jobs = {}
        for c in calls:
            names = c.get("names", [])
            for t in c["turns"]:
                for j, s in enumerate(t["sentences"]):
                    k = sha1(t["dialect"] + "\n" + s["de"])[:16]
                    jb = jobs.setdefault(k, {"key": k, "de": s["de"], "dialect": t["dialect"], "speaker": t["speaker"],
                                             "uses": [], "names": set(), "decisive": False})
                    jb["uses"].append((c["id"], t["id"], j))
                    jb["names"].update(names)
                    if t.get("decisive") or t["id"] in c["evidence"].values():
                        jb["decisive"] = True
        return jobs

    def run_translation(self, jobs):
        for k, jb in jobs.items():
            ch = self.translate(jb["de"], jb["dialect"])
            st = {"ch_auto": ch, "ch_final": None, "edited": False, "problems": [], "blocked": True}
            if ch is None:
                st["problems"] = ["noch nicht übersetzt"]
                self.sent_state[k] = st
                continue
            probs = check_translation(jb["de"], ch, sorted(jb["names"]), jb["decisive"])
            st["problems"] = probs
            dec = self.decisions.get(k, {})
            decision = (dec.get("decision") or "").strip().lower()
            proposal = (dec.get("ch_final") or "").strip()
            # An 'edit' decision always wins (also for sentences the string checks did not flag);
            # a filled ch_final without a decision is a pending proposal and holds the sentence back.
            if decision == "edit" and proposal:
                st.update(ch_final=proposal, edited=True, blocked=False)
            elif decision == "keep" and dec.get("ch_auto", ch) == ch:
                st.update(ch_final=ch, blocked=False)
            elif not probs and not proposal:
                st.update(ch_final=ch, blocked=False)
            if probs or decision in ("keep", "edit") or proposal:
                use = jb["uses"][0]
                self.review_rows[k] = {
                    "key": k, "calls": ";".join(sorted({u[0] for u in jb["uses"]})), "turn": use[1],
                    "sentence": use[2] + 1, "speaker": jb["speaker"], "dialect": jb["dialect"], "de": jb["de"],
                    "ch_auto": ch, "problems": "; ".join(probs) or ("Sichtprüfung" if proposal else "-"),
                    "decision": dec.get("decision", ""), "ch_final": dec.get("ch_final", ""), "note": dec.get("note", "")}
            self.sent_state[k] = st
        self._write_review(set(jobs))

    def _split_text(self, ch):
        mid = len(ch) / 2.0
        cands = [m.end() for m in re.finditer(r",\s+|\s+(und|aber|weil|dass|wenn|oder)\s+", ch)]
        cands = [c for c in cands if 8 < c < len(ch) - 8]
        if not cands:
            sp = [m.start() for m in re.finditer(r"\s", ch)]
            cands = [c for c in sp if 8 < c < len(ch) - 8]
        if not cands:
            return None
        cut = min(cands, key=lambda c: abs(c - mid))
        return ch[:cut].strip(), ch[cut:].strip()

    def snippet(self, ch, dialect):
        """Synthesised, trimmed audio for one CH sentence, split if speech rate is implausible.
        Returns (samples, info) or (None, info)."""
        path = self.speech(ch, dialect)
        if path is None:
            return None, {"status": "missing"}
        raw = read_wav(path)
        peak = max((abs(v) for v in raw), default=0.0)
        x = trim_silence(raw)
        info = {"raw_peak": round(peak, 4), "clipped": peak >= 0.999, "split": False}
        dur = len(x) / float(SR)
        raw_dur = len(raw) / float(SR)
        cps = len(ch) / raw_dur if raw_dur > 0 else 0.0
        info["cps"] = round(cps, 1)
        info["cps_trimmed"] = round(len(ch) / dur, 1) if dur > 0 else 0.0
        info["fast"] = cps > CPS_NOTE
        if dur < 0.2 or not (CPS_MIN <= cps <= CPS_MAX):
            parts = self._split_text(ch)
            if parts:
                ys = []
                ok = True
                for p in parts:
                    pp = self.speech(p, dialect)
                    if pp is None:
                        return None, {"status": "missing"}
                    yr = read_wav(pp)
                    y = trim_silence(yr)
                    d = len(y) / float(SR)
                    pc = len(p) / (len(yr) / float(SR)) if yr else 0.0
                    if d < 0.2 or not (CPS_MIN <= pc <= CPS_MAX):
                        ok = False
                    ys.append(y)
                x = ys[0] + [0.0] * int(0.12 * SR) + ys[1]
                dur = len(x) / float(SR)
                info.update(split=True, parts=list(parts), cps=round(len(ch) / dur, 1), cps_ok=ok)
            else:
                info["cps_ok"] = False
        else:
            info["cps_ok"] = True
        if not x:
            return None, dict(info, status="empty")
        y, gain = normalise(x)
        info["gain_db"] = round(gain, 1)
        info["status"] = "ok"
        return y, info

    # ---- assembly
    def assemble(self, c):
        seed_key = c["noise_plan"]["seed_key"]
        cdir = os.path.join(self.root, "calls", c["id"])
        os.makedirs(cdir, exist_ok=True)
        cust = c["customer_role"]
        restart_turn = c["noise_plan"]["restart_turn"]
        sents, edited = [], 0
        for t in c["turns"]:
            for j, s in enumerate(t["sentences"]):
                k = sha1(t["dialect"] + "\n" + s["de"])[:16]
                st = self.sent_state[k]
                y, info = self.snippet(st["ch_final"], t["dialect"])
                if y is None:
                    return None, "snippet %s %s: %s" % (t["id"], j + 1, info.get("status"))
                sents.append((t, j, s, st, y, info))
                edited += 1 if st["edited"] else 0
        lead = int(0.25 * SR)
        timeline = []
        pos = lead
        prev_turn = None
        for (t, j, s, st, y, info) in sents:
            if prev_turn is not None:
                if j == 0:
                    rng = random.Random("%s|gap|%s" % (seed_key, t["id"]))
                    gap = rng.uniform(0.30, 0.90)
                    if t["id"] == restart_turn:
                        first = (st["ch_final"].split() or [""])[0]
                        frag = 0.35 * len(y) / SR * len(first) / max(1, len(st["ch_final"]))
                        gap = max(gap, frag + 0.15 + 0.08)
                else:
                    rng = random.Random("%s|gap|%s|%d" % (seed_key, t["id"], j))
                    gap = rng.uniform(0.12, 0.30)
                pos += int(round(gap * SR))
            timeline.append((pos, t, j, s, st, y, info))
            pos += len(y)
            prev_turn = t["id"]
        total = pos + int(0.5 * SR)
        mix = [0.0] * total
        stem_b = [0.0] * total
        stem_k = [0.0] * total
        for (p, t, j, s, st, y, info) in timeline:
            stem = stem_b if t["speaker"] == "Beratung" else stem_k
            for i, v in enumerate(y):
                mix[p + i] += v
                stem[p + i] += v
        # timestamps
        turn_info = {}
        for (p, t, j, s, st, y, info) in timeline:
            ti = turn_info.setdefault(t["id"], {"start": p, "end": p + len(y), "sentences": []})
            ti["end"] = p + len(y)
            ti["sentences"].append({"de": s["de"], "ch_auto": st["ch_auto"], "ch_final": st["ch_final"],
                                    "edited": st["edited"], "key": s.get("key", False),
                                    "start": round(p / SR, 3), "end": round((p + len(y)) / SR, 3),
                                    "speech": {kk: info[kk] for kk in ("cps", "cps_trimmed", "fast", "split", "gain_db", "clipped") if kk in info},
                                    "_p": p, "_n": len(y)})
        # ---- noisy version (built from the clean mix)
        noisy_src = list(mix)
        events = []
        rng_ev = random.Random("%s|events" % seed_key)
        # word restart on the first sentence of the restart (context) turn
        rt = turn_info.get(restart_turn)
        if rt:
            s0 = rt["sentences"][0]
            first = (s0["ch_final"].split() or [""])[0]
            frag_n = int(0.35 * s0["_n"] * len(first) / max(1, len(s0["ch_final"])))
            frag_n = max(frag_n, int(0.06 * SR))
            start = s0["_p"] - int(0.15 * SR) - frag_n
            if start > 0:
                for i in range(frag_n):
                    fade = min(1.0, (frag_n - i) / (0.01 * SR))
                    noisy_src[start + i] += mix[s0["_p"] + i] * fade
                events.append({"type": "restart", "turn": restart_turn, "word": first,
                               "start": round(start / SR, 3), "end": round((start + frag_n) / SR, 3)})
        # bell or knock over the key sentence of the act turn (partial overlap)
        at = turn_info[c["noise_plan"]["event_turn"]]
        keys = [s for s in at["sentences"] if s["key"]] or at["sentences"]
        ks = keys[0]
        act_speech = []
        for s in at["sentences"]:
            act_speech.extend(mix[s["_p"]:s["_p"] + s["_n"]])
        act_ref = active_rms(phone_band(act_speech)) or 10 ** (TARGET_RMS_DB / 20)
        ev_type = c["noise_plan"]["event_type"]
        ev = bell(rng_ev) if ev_type == "bell" else knock(rng_ev)
        rel = rng_ev.uniform(*EVENT_REL_DB)
        g = act_ref * (10 ** (rel / 20)) / max(loud_rms(ev), 1e-9)
        ev = [v * g for v in ev]
        ks_len = ks["_n"]
        lo_off = int(0.15 * ks_len)
        hi_off = max(lo_off + 1, int(0.6 * ks_len) - len(ev))
        if hi_off <= lo_off:
            hi_off = lo_off + 1
        ev_start = ks["_p"] + rng_ev.randrange(lo_off, hi_off)
        for i, v in enumerate(ev):
            if ev_start + i < total:
                noisy_src[ev_start + i] += v
        events.append({"type": ev_type, "turn": c["noise_plan"]["event_turn"], "rel_db": round(rel, 1),
                       "start": round(ev_start / SR, 3), "end": round(min(total, ev_start + len(ev)) / SR, 3)})
        # telephone band + pink noise, noise generated per turn segment so pairs share it
        speech_f = phone_band(noisy_src)
        noise = [0.0] * total
        bounds = []
        turns_sorted = [turn_info[t["id"]] for t in c["turns"]]
        prev_end = 0
        for t, ti in zip(c["turns"], turns_sorted):
            bounds.append((t["id"], prev_end, ti["end"]))
            prev_end = ti["end"]
        bounds.append(("tail", prev_end, total))
        for tid, a, b in bounds:
            noise[a:b] = pink_noise(b - a, random.Random("%s|noise|%s" % (seed_key, tid)))
        noise_f = phone_band(noise)
        clean_f = phone_band(mix)
        snr_target = min(SNR_RANGE[1], max(SNR_RANGE[0], c["noise_plan"]["snr_db"]))
        # Noise level: speech reference = each sentence band-limited on its own (all turns except the changed
        # turn of a pair); noise reference = a fixed calibration noise per pair. Both are the same for A and B,
        # so the act turn gets bit-identical noise (v5 used the call's own noise, whose filter memory after the
        # changed turn moved the gain in the 5th digit).
        changed = c.get("changed_turn")
        ref_sp = []
        for t, ti in zip(c["turns"], turns_sorted):
            if t["id"] == changed:
                continue
            for s in ti["sentences"]:
                ref_sp.extend(phone_band(mix[s["_p"]:s["_p"] + s["_n"]]))
        cal = phone_band(pink_noise(CAL_NOISE_S * SR, random.Random("%s|noise|calibration" % seed_key)))[SR // 10:]
        gain_n = (active_rms(ref_sp) / (10 ** (snr_target / 20))) / max(rms(cal), 1e-12)
        gain_n = float("%.5g" % gain_n)
        noise_f = [v * gain_n for v in noise_f]
        noisy = [a + b for a, b in zip(speech_f, noise_f)]
        # measured SNR over all speech of the call
        sp_frames = []
        for s in [s for ti in turns_sorted for s in ti["sentences"]]:
            sp_frames.extend(clean_f[s["_p"]:s["_p"] + s["_n"]])
        snr_meas = db(active_rms(sp_frames)) - db(rms(noise_f))
        # fixed headroom plus a sample-wise limit (both local operations, so pairs stay identical)
        noisy_scale = NOISY_SCALE
        noisy = [v * noisy_scale for v in noisy]
        n_clip = sum(1 for v in noisy if abs(v) > NOISY_LIMIT)
        if n_clip:
            noisy = [max(-NOISY_LIMIT, min(NOISY_LIMIT, v)) for v in noisy]
        # ---- write audio
        write_wav(os.path.join(cdir, c["id"] + "_clean.wav"), mix)
        write_wav(os.path.join(cdir, c["id"] + "_noisy.wav"), noisy)
        write_wav(os.path.join(cdir, c["id"] + "_Beratung.wav"), stem_b)
        write_wav(os.path.join(cdir, c["id"] + "_Kunde.wav"), stem_k)
        # act audio fingerprint (clean), for the pair identity check
        act_id = c["belege"][-1]
        ati = turn_info[act_id]
        act_clean = mix[ati["start"]:ati["end"]]
        act_noisy = noisy[ati["start"]:ati["end"]]
        fp_clean = hashlib.sha1(wav_bytes(act_clean)).hexdigest()
        fp_noisy = hashlib.sha1(wav_bytes(act_noisy)).hexdigest()
        meta = {"duration_s": round(total / SR, 2), "events": events, "snr_target": snr_target,
                "snr_measured": round(snr_meas, 1), "noisy_scale": round(noisy_scale, 3), "noisy_clipped": n_clip,
                "act_fp_clean": fp_clean, "act_fp_noisy": fp_noisy, "edited_sentences": edited,
                "turn_info": turn_info}
        return meta, None

    # ---- outputs
    def write_outputs(self, c, meta):
        cdir = os.path.join(self.root, "calls", c["id"])
        ti = meta["turn_info"]
        cust = c["customer_role"]
        turns = []
        for t in c["turns"]:
            x = ti[t["id"]]
            ch_auto = " ".join(s["ch_auto"] for s in x["sentences"])
            ch_final = " ".join(s["ch_final"] for s in x["sentences"])
            turns.append({"id": t["id"], "speaker": t["speaker"], "dialect": t["dialect"], "de": t["de"],
                          "ch_auto": ch_auto, "ch_final": ch_final,
                          "edited": any(s["edited"] for s in x["sentences"]),
                          "decisive": t.get("decisive", False),
                          "start": round(x["start"] / SR, 3), "end": round(x["end"] / SR, 3),
                          "sentences": [{k: v for k, v in s.items() if not k.startswith("_")} for s in x["sentences"]]})
        tmap = {t["id"]: t for t in turns}
        belege = []
        for b in c["belege"]:
            ks = [s for s in tmap[b]["sentences"] if s.get("key")] or tmap[b]["sentences"]
            belege.append({"turn": b, "start": ks[0]["start"], "end": ks[0]["end"],
                           "turn_start": tmap[b]["start"], "turn_end": tmap[b]["end"]})
        kw = json.load(open(os.path.join(self.root, "Stichwortliste.json"), encoding="utf-8")) \
            if os.path.exists(os.path.join(self.root, "Stichwortliste.json")) else None
        hits = []
        for h in c["keyword_hits"]:
            h = dict(h)
            if kw:
                k = next(k for k in kw["keywords"] if k["id"] == h["id"])
                h["ch_hit"] = any(re.search(r"(?<!\w)" + re.escape(p.lower()) + r"(?!\w)", tmap[h["turn"]]["ch_final"].lower())
                                  for p in k["gsw"])
            hits.append(h)
        rec = {"id": c["id"], "family": c["family"], "type": c["type"], "pair_id": c["pair_id"], "variant": c["variant"],
               "families_involved": c["families_involved"], "title": c["title"], "beschreibung": c["beschreibung"],
               "dialects": c["dialects"], "duration_s": meta["duration_s"], "turns": turns,
               "facts": c["facts"], "evidence": c["evidence"], "zitate": c["zitate"], "expected": c["expected"],
               "family_verdicts": c["family_verdicts"], "belege": belege, "begruendung": c["begruendung"],
               "offen": c["offen"], "keyword_hits": hits, "noise_events": meta["events"],
               "snr_db": {"target": meta["snr_target"], "measured": meta["snr_measured"]},
               "noisy_scale": meta["noisy_scale"], "noisy_clipped_samples": meta["noisy_clipped"],
               "edited_sentences": meta["edited_sentences"],
               "act_audio_sha1": {"clean": meta["act_fp_clean"], "noisy": meta["act_fp_noisy"]},
               "audio": {"clean": c["id"] + "_clean.wav", "noisy": c["id"] + "_noisy.wav",
                         "stem_beratung": c["id"] + "_Beratung.wav", "stem_kunde": c["id"] + "_Kunde.wav",
                         "sample_rate": SR, "format": "PCM16 mono WAV"}}
        write_json(os.path.join(cdir, c["id"] + ".json"), rec)
        head = "Beratung: %s · %s: %s" % (c["dialects"]["Beratung"], cust, c["dialects"][cust])
        de_lines, ch_lines = [head, ""], [head, ""]
        for t in turns:
            hdr = "%s · %s (%s) [%s–%s]" % (t["id"], t["speaker"], t["dialect"], fmt_ts(t["start"]), fmt_ts(t["end"]))
            de_lines += [hdr, t["de"], ""]
            ch_lines += [hdr, t["ch_final"], ""]
        atomic_write_text(os.path.join(cdir, c["id"] + "_DE.txt"), "\n".join(de_lines))
        atomic_write_text(os.path.join(cdir, c["id"] + "_CH.txt"), "\n".join(ch_lines))
        atomic_write_text(os.path.join(cdir, c["id"] + "_outcept.txt"), self.outcept_txt(rec, c))
        return rec

    def outcept_txt(self, rec, c):
        n_words = c.get("n_words") or sum(len(t["de"].split()) for t in rec["turns"])
        ereignis = {"alarm": "present", "no_alert": "absent", "review": "undetermined"}[rec["expected"]]
        act = rec["belege"][-1]
        kws = ["%s '%s' %s (%s)" % (h["id"], h["phrase"], h["turn"], h["label"]) for h in rec["keyword_hits"]]
        ev = [e for e in rec["noise_events"] if e["type"] in ("bell", "knock")]
        rs = [e for e in rec["noise_events"] if e["type"] == "restart"]
        lines = [
            "%s · %s" % (rec["id"], rec["title"]),
            rec["beschreibung"],
            "Dauer: short, ungefähr %.1f min bei 120 Wörtern/min; %d Wörter. Audio: %.1f min." % (n_words / 120.0, n_words, rec["duration_s"] / 60.0),
            "Testziel: %s" % rec["family"],
            "Ereignis: %s" % ereignis,
            "Bearbeitung: %s" % rec["expected"],
            "Begründung: %s" % rec["begruendung"],
            "Offen: %s" % (rec["offen"] or "keine Voraussetzung für diese Sollbewertung"),
            "Prüfpräfix bis %s; Belege: %s" % (act["turn"], ", ".join(b["turn"] for b in rec["belege"])),
            "Frühere Regelausschlussstelle: nicht separat annotiert",
            "Keywordstellen: %s" % ("; ".join(kws) if kws else "keine registrierte Vollphrase; Kontexttest"),
            "Geplante Geräuschstellen: %s" % "; ".join("%s %s" % ({"bell": "Glocke", "knock": "Klopfen"}[e["type"]], e["turn"]) for e in ev),
            "Geplante Wortversuche: %s" % "; ".join("%s '%s' (35 Prozent, danach intakter Satz)" % (e["turn"], e["word"]) for e in rs),
            "Exakte hörbare Zeitmarke: %s Schlüsselsatz %s–%s (aus Audioproduktion)." % (act["turn"], fmt_ts(act["start"]), fmt_ts(act["end"])),
            "",
        ]
        for t in rec["turns"]:
            lines += ["%s · %s" % (t["id"], t["speaker"]), t["ch_final"], ""]
        return "\n".join(lines)

    def update_texts(self, recs):
        """Write CH texts back into texts_test50.jsonl (DE and labels unchanged)."""
        out = []
        for c in self.calls:
            c2 = json.loads(json.dumps(c))
            for t in c2["turns"]:
                parts_a, parts_f, ed = [], [], False
                for s in t["sentences"]:
                    k = sha1(t["dialect"] + "\n" + s["de"])[:16]
                    st = self.sent_state.get(k)
                    if st:
                        s["ch_auto"] = st["ch_auto"]
                        s["ch_final"] = st["ch_final"]
                        s["edited"] = st["edited"]
                        ed = ed or st["edited"]
                    parts_a.append(s.get("ch_auto") or "")
                    parts_f.append(s.get("ch_final") or "")
                t["ch_auto"] = " ".join(p for p in parts_a if p) or None
                t["ch_final"] = " ".join(p for p in parts_f if p) if all(parts_f) else None
                t["edited"] = ed
            r = recs.get(c["id"])
            if r:
                c2["duration_s"] = r["duration_s"]
            out.append(json.dumps(c2, ensure_ascii=False))
        atomic_write_text(self.texts_path, "\n".join(out) + "\n")


# ----------------------------------------------------------------- voice check

def voice_check(root, b, log):
    vdir = os.path.join(root, "voice_check")
    os.makedirs(vdir, exist_ok=True)
    rows = [["dialect", "file", "ch_text", "duration_s", "median_f0_hz"]]
    for d in DIALECTS:
        ch = b.translate(VOICE_SENTENCE, d)
        if ch is None:
            continue
        path = b.speech(ch, d)
        if path is None:
            continue
        x = trim_silence(read_wav(path))
        y, _ = normalise(x)
        fn = "%s.wav" % safe_name(d)
        write_wav(os.path.join(vdir, fn), y)
        rows.append([d, fn, ch, "%.2f" % (len(y) / SR), median_f0(y) or ""])
    import io
    s = io.StringIO()
    csv.writer(s).writerows(rows)
    atomic_write_text(os.path.join(vdir, "voices.csv"), s.getvalue())
    log("voice check: %d samples in voice_check/ (listen and report same-sounding voices)" % (len(rows) - 1))


# ------------------------------------------------------------------- validation

SEV = {"no_alert": 0, "review": 1, "alarm": 2}


def family_verdict(cfg, facts):
    if cfg.get("classify_only"):
        return "no_alert"
    if facts.get(cfg["gate"]) == "nein":
        return "no_alert"
    if any(facts.get(s) == "unklar" for s in cfg.get("review_if_unklar", [])):
        return "review"
    vals = [facts.get(s, "unklar") for s in cfg["alarm_if"]]
    if all(v == "ja" for v in vals):
        return "alarm"
    if any(v == "nein" for v in vals):
        return "no_alert"
    return "review"


def validate(root, log):
    rep = []
    errs = 0
    calls = [json.loads(l) for l in open(os.path.join(root, "texts_test50.jsonl"), encoding="utf-8") if l.strip()]
    fams = json.load(open(os.path.join(root, "families-test50.json"), encoding="utf-8"))["families"]
    # 1 verdicts
    dist = {}
    for c in calls:
        v = max((family_verdict(fams[f], s) for f, s in c["facts"].items()), key=SEV.get)
        if v != c["expected"]:
            rep.append("ERROR 1 %s: rules give %s, expected %s" % (c["id"], v, c["expected"]))
            errs += 1
        dist[(c["family"], c["type"], c["expected"])] = dist.get((c["family"], c["type"], c["expected"]), 0) + 1
    rep.append("1 verdicts: rule logic reproduces expected for %d calls" % len(calls))
    for k in sorted(dist):
        rep.append("    %-14s %-13s %-9s %2d" % (k + (dist[k],)))
    # 2 pairs (text level)
    pairs = {}
    for c in calls:
        if c.get("pair_id"):
            pairs.setdefault(c["pair_id"], {})[c["variant"]] = c
    for pid, pv in sorted(pairs.items()):
        a, b = pv.get("A"), pv.get("B")
        if not a or not b:
            continue
        diff = [x["id"] for x, y in zip(a["turns"], b["turns"]) if x["de"] != y["de"]]
        act = a["belege"][-1]
        ok = len(diff) == 1 and 3 <= int(diff[0][1:]) <= 6 and int(act[1:]) - int(diff[0][1:]) >= 5 \
            and abs(a["n_words"] - b["n_words"]) <= 5
        if not ok:
            rep.append("ERROR 2 %s: differing %s, act %s, words %d/%d" % (pid, diff, act, a["n_words"], b["n_words"]))
            errs += 1
    rep.append("2 pairs: %d pairs checked (one changed turn T003-T006, act >= 5 turns later, ±5 words)" % len(pairs))
    # 3-5 need the built calls
    built = {}
    for c in calls:
        p = os.path.join(root, "calls", c["id"], c["id"] + ".json")
        if os.path.exists(p):
            built[c["id"]] = json.load(open(p, encoding="utf-8"))
    rep.append("   built calls: %d of %d" % (len(built), len(calls)))
    n3 = 0
    for cid, r in built.items():
        tm = {t["id"]: t for t in r["turns"]}
        for slot, tid in r["evidence"].items():
            q = r["zitate"].get(slot)
            if tid not in tm or (q and q not in tm[tid]["de"]):
                rep.append("ERROR 3 %s: evidence %s %s" % (cid, slot, tid))
                errs += 1
        for b in r["belege"]:
            t = tm[b["turn"]]
            if not (t["start"] <= b["start"] < b["end"] <= t["end"]):
                rep.append("ERROR 3 %s: Beleg %s outside its turn" % (cid, b["turn"]))
                errs += 1
        n3 += 1
    rep.append("3 evidence and Belege times: %d calls checked" % n3)
    open_rows = 0
    if os.path.exists(os.path.join(root, "needs_review.csv")):
        for row in csv.DictReader(open(os.path.join(root, "needs_review.csv"), encoding="utf-8")):
            if not (row.get("decision") or "").strip():
                open_rows += 1
    rep.append("4 needs_review.csv: %d rows without decision" % open_rows)
    if open_rows:
        errs += 1
    bad_audio = 0
    snrs = []
    for cid, r in built.items():
        last = -1.0
        for t in r["turns"]:
            for s in t["sentences"]:
                sp = s.get("speech", {})
                if s["start"] < last or s["end"] <= s["start"]:
                    rep.append("ERROR 5 %s %s: timestamps not monotonic" % (cid, t["id"]))
                    bad_audio += 1
                last = s["end"]
                if sp.get("clipped"):
                    rep.append("ERROR 5 %s %s: clipped snippet" % (cid, t["id"]))
                    bad_audio += 1
                if sp.get("cps") is not None and not (CPS_MIN <= sp["cps"] <= CPS_MAX):
                    rep.append("WARN 5 %s %s: %.1f characters per second" % (cid, t["id"], sp["cps"]))
        snr = r["snr_db"]["measured"]
        snrs.append(snr)
        if not 15.0 <= snr <= 25.0:
            rep.append("ERROR 5 %s: noisy SNR %.1f dB" % (cid, snr))
            bad_audio += 1
    for pid, pv in sorted(pairs.items()):
        ra, rb = built.get(pv["A"]["id"]), built.get(pv["B"]["id"])
        if ra and rb:
            same_c = ra["act_audio_sha1"]["clean"] == rb["act_audio_sha1"]["clean"]
            same_n = ra["act_audio_sha1"]["noisy"] == rb["act_audio_sha1"]["noisy"]
            if not same_c:
                rep.append("ERROR 5 %s: act audio differs between A and B (clean)" % pid)
                bad_audio += 1
            if not same_n:
                rep.append("ERROR 5 %s: act audio differs between A and B (noisy)" % pid)
                bad_audio += 1
            rep.append("   %s act audio identical: clean %s, noisy %s" % (pid, same_c, same_n))
    errs += bad_audio
    if snrs:
        rep.append("5 audio: %d problems; noisy SNR %.1f–%.1f dB" % (bad_audio, min(snrs), max(snrs)))
    rep.append("validation errors: %d" % errs)
    atomic_write_text(os.path.join(root, "logs", "validation.txt"), "\n".join(rep) + "\n")
    for line in rep:
        log(line)
    return errs


def write_manifest(root, calls, recs):
    import io
    s = io.StringIO()
    w = csv.writer(s)
    w.writerow(["id", "family", "type", "expected", "duration_s", "dialects", "n_turns", "edited_sentences"])
    for c in calls:
        r = recs.get(c["id"])
        cust = c["customer_role"]
        w.writerow([c["id"], c["family"], c["type"], c["expected"], r["duration_s"] if r else "",
                    "Beratung=%s; %s=%s" % (c["dialects"]["Beratung"], cust, c["dialects"][cust]),
                    len(c["turns"]), r["edited_sentences"] if r else ""])
    atomic_write_text(os.path.join(root, "manifest.csv"), s.getvalue())


# ------------------------------------------------------------------------- main

def assemble_ready(b, calls, recs, log):
    """Build every call whose sentences are all decided and synthesised. Returns 0 or 3 (calls open)."""
    status = 0
    for c in calls:
        if c["id"] in recs:
            continue
        keys = [sha1(t["dialect"] + "\n" + s["de"])[:16] for t in c["turns"] for s in t["sentences"]]
        nblk = sum(1 for k in keys if b.sent_state[k]["blocked"])
        if nblk:
            log("skip %s: %d sentences wait for review" % (c["id"], nblk))
            status = 3
            continue
        t0 = time.time()
        meta, err = b.assemble(c)
        if err:
            log("skip %s: %s" % (c["id"], err))
            status = 3
            continue
        recs[c["id"]] = b.write_outputs(c, meta)
        log("built %s  %.1f s  SNR %.1f dB  (%.0f s)" % (c["id"], meta["duration_s"], meta["snr_measured"],
                                                         time.time() - t0))
    return status


def wait_for_review(b, jobs, calls, recs, log, max_hours=14):
    """Keep running: whenever needs_review.csv gets new decisions, synthesise the unblocked
    sentences and build the calls that are now complete (sequential, same etiquette)."""
    deadline = time.time() + max_hours * 3600
    status = 3
    first = True
    while time.time() < deadline:
        open_calls = [c["id"] for c in calls if c["id"] not in recs]
        if not open_calls:
            return 0
        if not first:  # first round: pick up decisions written while synthesis was still running
            log("waiting for decisions in needs_review.csv (%d calls open) – Ctrl+C stops, a rerun resumes"
                % len(open_calls))
            mt = os.path.getmtime(b.review_path) if os.path.exists(b.review_path) else 0
            while time.time() < deadline:
                time.sleep(30)
                if os.path.exists(b.review_path) and os.path.getmtime(b.review_path) != mt:
                    break
            time.sleep(5)
        first = False
        b.decisions = b._read_review()
        b.review_rows = {}
        b.run_translation(jobs)
        for k, jb in jobs.items():
            st = b.sent_state[k]
            if not st["blocked"]:
                b.snippet(st["ch_final"], jb["dialect"])
        status = assemble_ready(b, calls, recs, log)
        if status == 0:
            return 0
    return status


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", default=[], help="call id (repeatable)")
    ap.add_argument("--voice-check", action="store_true", help="only make voice_check/")
    ap.add_argument("--offline", action="store_true", help="no API calls, use the cache only")
    ap.add_argument("--validate", action="store_true", help="only run the final validation")
    ap.add_argument("--mock", action="store_true", help="fake API for testing (needs --root)")
    ap.add_argument("--wait-review", action="store_true",
                    help="after the pass, wait for decisions in needs_review.csv and finish the blocked calls")
    ap.add_argument("--root", default=ROOT, help="folder with texts_test50.jsonl (default: this script's folder)")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if args.mock and root == ROOT:
        sys.exit("--mock needs a separate --root folder so it never mixes with real data")
    log = Log(os.path.join(root, "logs", "progress.log"))
    if args.validate:
        sys.exit(1 if validate(root, log) else 0)
    api = MockApi(log) if args.mock else Api(log)
    b = Builder(root, api, log, offline=args.offline)
    calls = b.calls
    if args.only:
        missing = [x for x in args.only if x not in {c["id"] for c in calls}]
        if missing:
            sys.exit("unknown id: %s" % ", ".join(missing))
        calls = [c for c in calls if c["id"] in args.only]
    log("start: %d calls, root %s%s (make_calls %s%s)" % (len(calls), root, " (MOCK)" if args.mock else "",
                                                          VERSION, ", offline" if args.offline else ""))
    status = 0
    recs = {}
    try:
        vdone = os.path.exists(os.path.join(root, "voice_check", "voices.csv"))
        if args.voice_check or (not args.only and not vdone):
            voice_check(root, b, log)
            if args.voice_check:
                return
        jobs = b.sentence_jobs(calls)
        log("phase 1/3 translate: %d unique sentences" % len(jobs))
        b.run_translation(jobs)
        blocked = [k for k, st in b.sent_state.items() if st["blocked"]]
        log("translation checks: %d sentences need review (needs_review.csv)" % len(blocked))
        log("phase 2/3 synthesise unblocked sentences")
        for k, jb in jobs.items():
            st = b.sent_state[k]
            if not st["blocked"]:
                b.snippet(st["ch_final"], jb["dialect"])
        log("phase 3/3 assemble calls")
        status = assemble_ready(b, calls, recs, log)
        if args.wait_review and status == 3:
            status = wait_for_review(b, jobs, calls, recs, log)
    except StopRun as e:
        log("STOP: %s" % e)
        status = 2
    except KeyboardInterrupt:
        log("interrupted – rerun the same command to resume")
        status = 130
    finally:
        prev = {}
        for c in b.calls:
            p = os.path.join(root, "calls", c["id"], c["id"] + ".json")
            if c["id"] not in recs and os.path.exists(p):
                prev[c["id"]] = json.load(open(p, encoding="utf-8"))
        prev.update(recs)
        if b.sent_state:
            b.update_texts(prev)
        write_manifest(root, b.calls, prev)
        log("API calls this run: %d" % api.calls)
    if status == 0 and not args.only:
        if validate(root, log):
            status = 4
    log("done (exit %d)" % status)
    sys.exit(status)


if __name__ == "__main__":
    main()
