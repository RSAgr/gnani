"""
Haq - a voice wage ledger for India's daily-wage workers.
Built on Gnani AI: Prisma (speech-to-text) + Timbre (text-to-speech).

Pure Python standard library. Run:
    python app.py           then open http://localhost:8000
"""

import datetime as dt
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import engine as E

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
AUDIO = DATA / "audio"
LEDGER_FILE = DATA / "ledger.json"
PORT = int(os.environ.get("PORT", "8000"))

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
STT_LANG = os.environ.get("GNANI_STT_LANG", "hi-IN")
TTS_PRIMARY = {"model": "timbre-v2.5", "voice": os.environ.get("GNANI_TTS_VOICE", "Nalini")}
TTS_FALLBACK = {"model": "timbre-v3.0", "voice": "Shivani"}
STT_TOPIC = ("A daily-wage construction worker in India records a short voice note about the "
             "work done today: the contractor's name, number of days, the agreed daily wage, "
             "money received or advance taken, overtime hours. Hindi and Hinglish, often noisy "
             "site audio.")

API_KEY = os.environ.get("GNANI_API_KEY", "").strip()

# --------------------------------------------------------------------------- Gnani


class GnaniError(Exception):
    pass


def _multipart(fields, file_bytes):
    boundary = "----haq" + uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n'
                   .encode() + str(v).encode("utf-8") + b"\r\n")
    out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="audio_file"; '
               f'filename="note.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
               + file_bytes + b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def _post(url, body, ctype, timeout=45):
    if not API_KEY:
        raise GnaniError("GNANI_API_KEY is not set. Restart app.py and paste your key.")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"X-API-Key-ID": API_KEY, "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raise GnaniError(f"Gnani API {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None
    except urllib.error.URLError as e:
        raise GnaniError(f"Could not reach Gnani API: {e.reason}") from None


def gnani_stt(wav, keyterms):
    """Prisma v3.0 with context (contractor names + site vocabulary). Falls back to v2.5."""
    attempts = [
        {"model": "prisma-v3.0", "language_code": STT_LANG, "format": "transcribe",
         "keyterms": json.dumps(keyterms, ensure_ascii=False), "topic": STT_TOPIC},
        {"model": "prisma-v3.0", "language_code": STT_LANG, "format": "transcribe"},
        {"language_code": STT_LANG, "format": "transcribe"},          # Prisma v2.5
    ]
    last, t0 = None, time.time()
    for fields in attempts:
        try:
            body, ctype = _multipart(fields, wav)
            raw, _ = _post(STT_URL, body, ctype)
            data = json.loads(raw.decode("utf-8"))
            if data.get("success") is False:
                raise GnaniError(json.dumps(data.get("error", data), ensure_ascii=False)[:300])
            text = data.get("transcript")
            if not text and isinstance(data.get("output"), dict):
                text = data["output"].get("literal", "")
            return (text or "").strip(), {
                "model": data.get("model") or fields.get("model", "prisma-v2.5"),
                "language": data.get("detected_language_code"),
                "latency": data.get("end_to_end_latency") or round(time.time() - t0, 2),
                "context": "keyterms" in fields,
            }
        except GnaniError as e:
            last = e
            if "401" in str(e) or "403" in str(e) or "not reach" in str(e):
                break
    raise last


def gnani_tts(text):
    last = None
    for cfg in (TTS_PRIMARY, TTS_FALLBACK):
        payload = {"text": text, "voice": cfg["voice"], "model": cfg["model"],
                   "language": "hi-IN", "speed": 0.95,
                   "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                                    "encoding": "linear_pcm", "container": "wav"}}
        try:
            raw, ctype = _post(TTS_URL, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                               "application/json")
            if "json" in ctype:
                raise GnaniError("TTS returned JSON: " + raw.decode("utf-8", "replace")[:200])
            return raw
        except GnaniError as e:
            last = e
            if "not reach" in str(e) or "401" in str(e):
                break
    raise last


# --------------------------------------------------------------------------- storage

_lock = threading.Lock()


def load():
    if LEDGER_FILE.exists():
        try:
            return json.loads(LEDGER_FILE.read_text("utf-8"))
        except json.JSONDecodeError:
            pass
    return E.new_ledger()


def save(ledger):
    DATA.mkdir(exist_ok=True)
    tmp = LEDGER_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(LEDGER_FILE)


def state(ledger):
    acc = E.accounts(ledger)
    mw = E.min_wage(ledger["settings"])
    accounts = sorted((a for a in acc.values() if a["days"] or a["paid"] or a["lines"]),
                      key=lambda a: -(a["due"]))
    for a in accounts:
        a.pop("lines", None)
    return {
        "settings": ledger["settings"],
        "min_wage": mw,
        "min_wage_table": E.MIN_WAGE_CENTRAL_OCT_2026,
        "min_wage_source": E.MIN_WAGE_SOURCE,
        "accounts": accounts,
        "totals": {
            "due": sum(max(0, a["due"]) for a in accounts),
            "days": sum(a["days"] for a in accounts),
            "earned": sum(a["earned"] + a["ot_pay"] for a in accounts),
            "paid": sum(a["paid"] for a in accounts),
            "shortfall": sum(a["shortfall"] for a in accounts),
        },
        "records": list(reversed(ledger["records"][-40:])),
        "employers": ledger["employers"],
        "chain": E.verify_chain(ledger),
        "key_set": bool(API_KEY),
    }


def statement(ledger, key):
    acc = E.accounts(ledger).get(key)
    if not acc:
        return None
    return {
        "account": acc,
        "settings": ledger["settings"],
        "min_wage": E.min_wage(ledger["settings"]),
        "min_wage_source": E.MIN_WAGE_SOURCE if ledger["settings"].get("area") != "custom"
        else "Worker-entered state minimum wage",
        "chain": E.verify_chain(ledger),
        "spoken": E.statement_text(ledger, key),
        "generated": dt.datetime.now().isoformat(timespec="minutes"),
    }


# --------------------------------------------------------------------------- demo data

def seed_demo():
    """Synthetic data only (contest rule: no real personal data)."""
    L = E.new_ledger()
    L["settings"].update(worker_name="Ramesh Kumar (demo)", skill="unskilled", area="A")
    today = dt.date.today()
    script = [
        (7, "सोमवार को शर्मा जी की साइट पे काम किया, सात सौ रोज़ तय हुआ"),
        (6, "आज भी शर्मा जी के यहाँ काम किया, पांच सौ मिले"),
        (5, "शर्मा जी की साइट पे काम किया"),
        (4, "आज शर्मा जी के यहाँ काम किया, 2 घंटे ओवरटाइम भी किया"),
        (4, "शर्मा जी ने पैसे नहीं दिए"),
        (3, "वर्मा ठेकेदार के यहाँ काम किया, 850 रोज़ की बात हुई, 850 मिले"),
        (2, "शर्मा जी की साइट पे काम किया, 1000 मिले"),
        (1, "शर्मा जी के यहाँ काम किया"),
    ]
    for back, text in script:
        day = today - dt.timedelta(days=back)
        E.handle(L, text, source="demo", today=day,
                 now=dt.datetime.combine(day, dt.time(19, 5 + back)))
    return L


# --------------------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_video(self, path):
        data = path.read_bytes()
        size, rng = len(data), self.headers.get("Range")
        m = re.match(r"bytes=(\d*)-(\d*)", rng or "")
        if m and (m.group(1) or m.group(2)):
            start = int(m.group(1)) if m.group(1) else size - int(m.group(2))
            end = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
            end = min(end, size - 1)
            chunk = data[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            chunk = data
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk)

    def _json(self):
        n = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            return self._send(200, (BASE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if u.path == "/statement":
            return self._send(200, (BASE / "statement.html").read_bytes(),
                              "text/html; charset=utf-8")
        if u.path == "/studio":
            return self._send(200, (BASE / "studio.html").read_bytes(), "text/html; charset=utf-8")
        if u.path == "/demo.mp4" and (BASE / "demo.mp4").exists():
            return self._send_video(BASE / "demo.mp4")
        if u.path == "/api/state":
            with _lock:
                return self._send(200, state(load()))
        if u.path == "/api/statement":
            with _lock:
                st = statement(load(), (q.get("emp") or [""])[0])
            return self._send(200 if st else 404, st or {"error": "No such contractor"})
        m = re.fullmatch(r"/audio/([\w\-]+\.wav)", u.path)
        if m and (AUDIO / m.group(1)).exists():
            return self._send(200, (AUDIO / m.group(1)).read_bytes(), "audio/wav")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/voice":
                n = int(self.headers.get("Content-Length", "0"))
                wav = self.rfile.read(n)
                AUDIO.mkdir(parents=True, exist_ok=True)
                sha = hashlib.sha256(wav).hexdigest()
                fname = dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + sha[:8] + ".wav"
                (AUDIO / fname).write_bytes(wav)
                with _lock:
                    terms = E.keyterms(load())
                transcript, meta = gnani_stt(wav, terms)
                return self._process(transcript, "voice", fname, sha, meta)
            if path == "/api/text":
                return self._process(self._json().get("text", ""), "typed", None, None,
                                     {"model": "typed"})
            if path == "/api/tts":
                return self._send(200, gnani_tts(self._json().get("text", "")[:900]), "audio/wav")
            if path == "/api/settings":
                body = self._json()
                with _lock:
                    L = load()
                    for k in ("worker_name", "skill", "area", "custom_rate"):
                        if k in body:
                            L["settings"][k] = body[k]
                    save(L)
                    return self._send(200, state(L))
            if path == "/api/demo":
                with _lock:
                    L = seed_demo()
                    save(L)
                    return self._send(200, state(L))
            if path == "/api/reset":
                with _lock:
                    L = load()
                    fresh = E.new_ledger()
                    fresh["settings"] = L["settings"]
                    save(fresh)
                    return self._send(200, state(fresh))
            self._send(404, {"error": "not found"})
        except GnaniError as e:
            self._send(502, {"error": str(e)})
        except Exception as e:  # keep the demo alive
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def _process(self, text, source, audio_file, sha, meta):
        with _lock:
            L = load()
            result = E.handle(L, text, source=source, audio_file=audio_file, audio_sha256=sha)
            save(L)
            payload = state(L)
        result.pop("record", None)
        payload.update(transcript=text, stt=meta, result=result)
        self._send(200, payload)


def main():
    global API_KEY
    if not API_KEY:
        print("Paste your Gnani API key (create one at app.gnani.ai/voice), or set GNANI_API_KEY.")
        try:
            API_KEY = input("GNANI_API_KEY> ").strip()
        except EOFError:
            API_KEY = ""
    DATA.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"\n  Haq is running  ->  http://localhost:{PORT}\n  Voice-over studio ->  http://localhost:{PORT}/studio\n  (Ctrl+C to stop)\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
