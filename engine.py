"""
Haq - core engine.

Turns a daily-wage worker's spoken Hindi / Hinglish note into ledger entries:

    "aaj Sharma ji ki site pe kaam kiya, 700 tay hua tha, 400 mile"
        -> work 1 day for Sharma ji @ Rs 700/day, payment Rs 400 received

and keeps a per-employer account (days, earned, paid, due), checks the agreed
rate against the minimum wage, and stores every record in a SHA-256 hash chain
so the history cannot be silently edited. Corrections are appended, never
deleted.

Pure Python, no dependencies. Works on Devanagari and Roman transcripts.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import uuid

# ---------------------------------------------------------------------------
# Minimum wages
# Central-sphere minimum wages for construction / building operations,
# Rs per day, effective 1 October 2026 (Labour Bureau VDA order of
# 30 Sep 2026). Many private sites fall under STATE rates instead, so the
# worker can always enter their own state's rate as "custom".
# ---------------------------------------------------------------------------

MIN_WAGE_CENTRAL_OCT_2026 = {
    "unskilled": {"A": 840, "B": 704, "C": 565},
    "semi_skilled": {"A": 933, "B": 794, "C": 661},
    "skilled": {"A": 1024, "B": 933, "C": 794},
    "highly_skilled": {"A": 1111, "B": 1024, "C": 933},
}
MIN_WAGE_SOURCE = ("Central-sphere minimum wage, construction, w.e.f. 1 Oct 2026 "
                   "(Labour Bureau VDA order, 30 Sep 2026)")

DEFAULT_SETTINGS = {
    "worker_name": "",
    "skill": "unskilled",
    "area": "A",            # A / B / C / custom
    "custom_rate": None,     # state rate entered by the worker
    "hours_per_day": 8,
}


def min_wage(settings):
    if settings.get("area") == "custom" and settings.get("custom_rate"):
        return float(settings["custom_rate"])
    skill = settings.get("skill", "unskilled")
    area = settings.get("area", "A")
    return float(MIN_WAGE_CENTRAL_OCT_2026.get(skill, {}).get(area, 0) or 0)


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

NUKTA = "़"
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def norm(s: str) -> str:
    return s.replace(NUKTA, "").replace("ँ", "ं").lower()


def _set(words: str) -> set:
    return {norm(w) for w in words.split()}


CURRENCY = _set("rupaye rupay rupaiye rupees rupee rs rs. inr रुपये रुपए रुपया रूपये रु ₹ paise पैसे")
WORK = _set("kaam काम dihadi dihaadi दिहाड़ी दिहाडी majdoori mazdoori मजदूरी मज़दूरी shift शिफ्ट "
            "duty ड्यूटी hazri haziri हाजिरी हाज़िरी chinai चिनाई palstar plaster प्लास्टर")
WORK_VERBS = _set("kiya kiye kari kara किया किए किये करी lagaya lagayi लगाया लगाई gaya gayi gaye गया गई गए "
                  "hua hui हुआ हुई kar kiya. raha रहा")
NEG = _set("nahi nahin nhi नहीं नही na mat")
RATE_KW = _set("tay tai तय roz rozana रोज़ रोज रोजाना rate रेट per baat बात "
               "fix फिक्स pakka पक्का")
PAY_KW = _set("mile mila mili मिले मिला मिली diye diya di दिए दिये दिया दी payment पेमेंट advance "
              "एडवांस udhaar paid pay received chukaya चुकाया")
OT_KW = _set("overtime ओवरटाइम extra एक्स्ट्रा zyada jyada ज्यादा ज़्यादा")
HOURS = _set("ghante ghanta घंटे घंटा hour hours")
DAY_WORDS = _set("din दिन day days")
HALF = _set("aadha adha आधा half")
QUERY_KW = _set("kitna kitne kitni कितना कितने कितनी baaki baki बाकी बाक़ी bakaya बकाया hisaab hisab "
                "हिसाब total टोटल batao बताओ bataiye बताइए")
STATEMENT_KW = _set("sunao सुनाओ patra पत्र statement parchi पर्ची report रिपोर्ट")
UNDO_KW = _set("galti गलती undo cancel कैंसल hatao हटाओ hata हटा mitao मिटाओ")
YESTERDAY = _set("kal कल yesterday")
DAY_BEFORE = _set("parso parson परसों")
CONNECTORS = _set("aur और lekin लेकिन magar मगर but and phir फिर")
HONORIFICS = _set("ji जी thekedar thekedaar ठेकेदार contractor कॉन्ट्रैक्टर seth सेठ sahab saheb saab "
                  "साहब sir सर babu बाबू malik मालिक munshi मुंशी bhaiya भैया madam मैडम")
POSSESSIVE = _set("ki ke ka की के का")
PLACE_AFTER_POSS = _set("site साइट yahan yaha यहां यहाँ ghar घर makan मकान")
STOP = _set("aaj आज kal कल maine मैंने main मैं mera मेरा meri मेरी hum हम humne हमने pe पे par पर "
            "se से ko को ne ने me में mein tha था thi थी the थे hai है hain हैं ho हो to तो bhi भी "
            "site साइट wala वाला wale वाले is इस us उस yeh ये woh वो sirf सिर्फ bas बस abhi अभी "
            "kuch कुछ sab सब total poora पूरा")

NUM_WORDS = {
    "ek": 1, "एक": 1, "do": 2, "दो": 2, "teen": 3, "तीन": 3, "char": 4, "chaar": 4, "चार": 4,
    "paanch": 5, "panch": 5, "पांच": 5, "पाँच": 5, "chhe": 6, "chhah": 6, "छह": 6, "छः": 6,
    "saat": 7, "सात": 7, "aath": 8, "आठ": 8, "nau": 9, "नौ": 9, "das": 10, "दस": 10,
    "gyarah": 11, "ग्यारह": 11, "barah": 12, "बारह": 12, "pandrah": 15, "पंद्रह": 15,
    "bees": 20, "बीस": 20, "pachchees": 25, "पच्चीस": 25, "tees": 30, "तीस": 30,
    "chalis": 40, "chaalis": 40, "चालीस": 40, "pachas": 50, "pachaas": 50, "पचास": 50,
    "saath": 60, "साठ": 60, "sattar": 70, "सत्तर": 70, "assi": 80, "अस्सी": 80,
    "nabbe": 90, "नब्बे": 90, "dedh": 1.5, "डेढ़": 1.5, "डेढ": 1.5, "dhai": 2.5, "ढाई": 2.5,
    "sava": 1.25, "सवा": 1.25, "saadhe": None, "साढ़े": None,
}
MULT_WORDS = {"sau": 100, "सौ": 100, "hazaar": 1000, "hazar": 1000, "हजार": 1000, "हज़ार": 1000}
NUM_WORDS = {norm(k): v for k, v in NUM_WORDS.items()}
MULT_WORDS = {norm(k): v for k, v in MULT_WORDS.items()}


def tokenize(text: str):
    t = text.translate(DEV_DIGITS)
    t = re.sub(r"(?<=\d),(?=\d)", "", t)                 # 1,200 -> 1200
    t = t.replace("₹", " ₹ ")
    t = re.sub(r"(\d)([^\d\s.,])", r"\1 \2", t)          # 700rs -> 700 rs
    t = re.sub(r"([^\d\s.,₹])(\d)", r"\1 \2", t)
    t = re.sub(r"[।|,;!?\"'()\[\]:]", " , ", t)
    out = []
    for raw in t.split():
        tok = norm(raw.strip("."))
        if tok:
            out.append(tok)
    return out


def is_digit_tok(t):
    return re.fullmatch(r"\d+(\.\d+)?", t) is not None


def number_spans(tokens):
    """Return [(value, start, end_exclusive)] for digit tokens and number-word runs."""
    spans, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if is_digit_tok(t):
            spans.append((float(t), i, i + 1))
            i += 1
            continue
        if t in NUM_WORDS or t in MULT_WORDS:
            j, total, cur, saadhe = i, 0.0, 0.0, False
            while j < len(tokens) and (tokens[j] in NUM_WORDS or tokens[j] in MULT_WORDS):
                w = tokens[j]
                if w in NUM_WORDS:
                    if NUM_WORDS[w] is None:
                        saadhe = True
                    else:
                        cur += NUM_WORDS[w] + (0.5 if saadhe else 0)
                        saadhe = False
                else:
                    cur = (cur or 1) * MULT_WORDS[w]
                    if MULT_WORDS[w] >= 1000:
                        total += cur
                        cur = 0
                j += 1
            val = total + cur
            # a lone "do"/"ek" is too ambiguous (also means "give"/"one") unless next to din/sau etc.
            lone_ambiguous = (j - i == 1 and t in {"do", "ek", "na", "nau", "sava"}
                              and not (j < len(tokens) and tokens[j] in DAY_WORDS | HOURS | CURRENCY))
            if val > 0 and not lone_ambiguous:
                spans.append((val, i, j))
            i = j
            continue
        i += 1
    return spans


# ---------------------------------------------------------------------------
# Employer detection
# ---------------------------------------------------------------------------

_DEV2LAT = {
    "क": "k", "ख": "k", "ग": "g", "घ": "g", "ङ": "n", "च": "c", "छ": "c", "ज": "j", "झ": "j",
    "ञ": "n", "ट": "t", "ठ": "t", "ड": "d", "ढ": "d", "ण": "n", "त": "t", "थ": "t", "द": "d",
    "ध": "d", "न": "n", "प": "p", "फ": "f", "ब": "b", "भ": "b", "म": "m", "य": "y", "र": "r",
    "ल": "l", "व": "v", "श": "s", "ष": "s", "स": "s", "ह": "", "ं": "n", "ः": "",
}


def phon_key(word: str) -> str:
    """Script-independent phonetic skeleton: 'Sharma' and 'शर्मा' -> 'srm'."""
    w = norm(word)
    if any("\u0900" <= ch <= "\u097f" for ch in w):
        w = "".join(_DEV2LAT.get(ch, "") for ch in w)
    else:
        w = (w.replace("ch", "c").replace("sh", "s").replace("ph", "f").replace("w", "v")
               .replace("z", "j").replace("q", "k").replace("x", "ks").replace("h", ""))
        w = re.sub(r"[aeiou]", "", w)
        w = re.sub(r"[^a-z]", "", w)
    return re.sub(r"(.)\1+", r"\1", w)


def _name_ok(tok):
    return (tok and not is_digit_tok(tok) and tok not in STOP and tok not in HONORIFICS
            and tok not in WORK and tok not in WORK_VERBS and tok not in CURRENCY
            and tok not in PAY_KW and tok not in RATE_KW and tok not in NUM_WORDS
            and tok not in MULT_WORDS and tok not in POSSESSIVE and tok not in QUERY_KW
            and tok not in CONNECTORS and tok != "," and len(tok) >= 2)


def find_employer(tokens, raw_tokens, known: dict):
    """Return (key, display) or (None, None). `known` maps key -> display."""
    for i, t in enumerate(tokens):
        if t in HONORIFICS and i > 0 and _name_ok(tokens[i - 1]):
            key = phon_key(tokens[i - 1]) or tokens[i - 1]
            disp = known.get(key) or f"{_pretty(raw_tokens[i - 1])} {raw_tokens[i]}"
            return key, disp
        if (t in POSSESSIVE and i > 0 and i + 1 < len(tokens)
                and tokens[i + 1] in PLACE_AFTER_POSS and _name_ok(tokens[i - 1])):
            key = phon_key(tokens[i - 1]) or tokens[i - 1]
            return key, known.get(key) or _pretty(raw_tokens[i - 1])
    for t in tokens:
        k = phon_key(t)
        if len(k) >= 3 and k in known and _name_ok(t):
            return k, known[k]
    return None, None


def _pretty(s):
    return s[:1].upper() + s[1:] if s and s[0].isascii() else s


# ---------------------------------------------------------------------------
# Understanding one utterance
# ---------------------------------------------------------------------------

def _window_type(tokens, start, end):
    """Classify a money number by nearby keywords: rate / pay / None."""
    after = tokens[end:end + 4]
    before = tokens[max(0, start - 3):start]

    def kind(toks):
        for k in toks:
            if k in PAY_KW:
                return "pay"
            if k in RATE_KW:
                return "rate"
            if k in DAY_WORDS and toks is after:
                # "700 din ka" / "700 roz"
                return "rate"
        return None

    joined_after = " ".join(after)
    if re.search(r"\b(din|दिन) (ka|ke|की|का|के)\b", joined_after) or "per" in after:
        return "rate"
    k = kind(after)
    if k:
        return k
    # "din ke 700" / "rate 700" / "advance 2000"
    if len(before) >= 2 and before[-2] in DAY_WORDS and before[-1] in POSSESSIVE:
        return "rate"
    return kind(list(reversed(before)))


def parse(text: str, known_employers: dict, last_employer=None, today=None):
    """Parse an utterance. Returns an intent dict (does not touch the ledger)."""
    today = today or dt.date.today()
    raw_tokens = [r for r in re.sub(r"[।|,;!?\"'()\[\]:]", " , ",
                                    text.translate(DEV_DIGITS).replace("₹", " ₹ ")).split()]
    tokens = tokenize(text)
    # keep raw tokens aligned with normalised ones for pretty names
    raw_aligned = _align_raw(text, tokens)
    tset = set(tokens)

    date = today
    if tset & YESTERDAY:
        date = today - dt.timedelta(days=1)
    elif tset & DAY_BEFORE:
        date = today - dt.timedelta(days=2)

    emp_key, emp_disp = find_employer(tokens, raw_aligned, known_employers)
    explicit_employer = emp_key is not None

    if not tokens:
        return {"intent": "empty"}

    spans = number_spans(tokens)
    money_spans = []
    days = None
    ot_hours = None
    for val, s, e in spans:
        nxt = tokens[e] if e < len(tokens) else ""
        nxt2 = tokens[e + 1] if e + 1 < len(tokens) else ""
        if nxt in DAY_WORDS and nxt2 not in POSSESSIVE and val <= 31:
            days = (days or 0) + val
        elif nxt in HOURS:
            if tset & OT_KW:
                ot_hours = (ot_hours or 0) + val
        else:
            money_spans.append((val, s, e))

    # half day
    for i, t in enumerate(tokens):
        if t in HALF and (i + 1 < len(tokens) and tokens[i + 1] in DAY_WORDS):
            days = 0.5

    if tset & UNDO_KW and not money_spans:
        return {"intent": "undo"}

    has_query = bool(tset & QUERY_KW)
    if has_query and not money_spans:
        intent = "statement" if tset & STATEMENT_KW else "query"
        return {"intent": intent, "employer": emp_key if explicit_employer else None,
                "employer_display": emp_disp if explicit_employer else None}
    if tset & STATEMENT_KW and not money_spans:
        return {"intent": "statement", "employer": emp_key if explicit_employer else None,
                "employer_display": emp_disp if explicit_employer else None}

    # work?
    worked = False
    for i, t in enumerate(tokens):
        if t in WORK:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            if nxt in POSSESSIVE:          # "kaam ke paise" is not a work day
                continue
            window = tokens[i + 1:i + 4]
            if any(w in NEG for w in window):
                continue
            if any(w in WORK_VERBS for w in tokens) or days is not None:
                worked = True
    if days is not None and not worked and any(t in WORK for t in tokens):
        worked = True
    if worked and days is None:
        days = 1.0
    if not worked:
        days = None

    rates, pays, unknown = [], [], []
    for val, s, e in money_spans:
        kind = _window_type(tokens, s, e)
        (rates if kind == "rate" else pays if kind == "pay" else unknown).append(val)
    for val in unknown:
        if worked and not rates:
            rates.append(val)
        else:
            pays.append(val)

    no_pay_said = bool(tset & NEG) and bool(tset & PAY_KW) and not pays

    if not worked and not rates and not pays and ot_hours is None:
        if tset & NEG and tset & (PAY_KW | CURRENCY):
            return {"intent": "note", "note": "not_paid", "date": date.isoformat(),
                    "employer": emp_key if explicit_employer else last_employer,
                    "employer_display": emp_disp if explicit_employer else
                    known_employers.get(last_employer)}
        if tset & NEG and tset & WORK:
            return {"intent": "note", "note": "no_work", "date": date.isoformat(),
                    "employer": None, "employer_display": None}
        return {"intent": "unknown"}

    if not explicit_employer:
        emp_key = last_employer
        emp_disp = known_employers.get(last_employer) if last_employer else None

    return {
        "intent": "log",
        "date": date.isoformat(),
        "employer": emp_key,
        "employer_display": emp_disp,
        "employer_explicit": explicit_employer,
        "days": days,
        "rate": rates[-1] if rates else None,
        "payments": pays,
        "ot_hours": ot_hours,
        "no_pay_said": no_pay_said,
    }


def _align_raw(text, tokens):
    """Best-effort original-case tokens aligned with tokenize() output."""
    t = text.translate(DEV_DIGITS)
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    t = t.replace("₹", " ₹ ")
    t = re.sub(r"(\d)([^\d\s.,])", r"\1 \2", t)
    t = re.sub(r"([^\d\s.,₹])(\d)", r"\1 \2", t)
    t = re.sub(r"[।|,;!?\"'()\[\]:]", " , ", t)
    raw = [r.strip(".") for r in t.split() if r.strip(".")]
    return raw if len(raw) == len(tokens) else tokens


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

def new_ledger():
    return {"settings": dict(DEFAULT_SETTINGS), "employers": {}, "records": [],
            "last_employer": None}


def _canonical(rec):
    body = {k: rec[k] for k in sorted(rec) if k not in ("hash",)}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _seal(ledger, rec):
    prev = ledger["records"][-1]["hash"] if ledger["records"] else "0" * 64
    rec["seq"] = len(ledger["records"]) + 1
    rec["prev_hash"] = prev
    rec["hash"] = hashlib.sha256(_canonical(rec).encode("utf-8")).hexdigest()
    ledger["records"].append(rec)
    return rec


def verify_chain(ledger):
    prev = "0" * 64
    for i, rec in enumerate(ledger["records"]):
        if rec.get("prev_hash") != prev or rec.get("seq") != i + 1:
            return {"ok": False, "broken_at": i + 1}
        if hashlib.sha256(_canonical(rec).encode("utf-8")).hexdigest() != rec.get("hash"):
            return {"ok": False, "broken_at": i + 1}
        prev = rec["hash"]
    return {"ok": True, "records": len(ledger["records"]),
            "fingerprint": prev[:12] if ledger["records"] else None}


def _voided_ids(ledger):
    return {e["target"] for r in ledger["records"] for e in r["entries"] if e["type"] == "void"}


def add_record(ledger, *, transcript, entries, source, audio_file=None, audio_sha256=None,
               now=None):
    now = now or dt.datetime.now()
    rec = {
        "id": uuid.uuid4().hex[:10],
        "created": now.isoformat(timespec="seconds"),
        "transcript": transcript,
        "source": source,
        "audio_file": audio_file,
        "audio_sha256": audio_sha256,
        "entries": entries,
    }
    return _seal(ledger, rec)


def accounts(ledger):
    """Compute per-employer accounts from the record chain."""
    settings = ledger["settings"]
    mw = min_wage(settings)
    hpd = settings.get("hours_per_day") or 8
    voided = _voided_ids(ledger)
    acc = {}
    for key, disp in ledger["employers"].items():
        acc[key] = {"key": key, "name": disp, "days": 0.0, "earned": 0.0, "ot_hours": 0.0,
                    "ot_pay": 0.0, "paid": 0.0, "rate": None, "first": None, "last": None,
                    "lines": [], "shortfall": 0.0, "unpriced_days": 0.0}
    # latest rate per employer (applies to work logged before a rate was known)
    latest_rate = {}
    for rec in ledger["records"]:
        for e in rec["entries"]:
            if e["id"] in voided:
                continue
            if e["type"] == "rate":
                latest_rate[e["employer"]] = e["amount"]
            if e["type"] == "work" and e.get("rate"):
                latest_rate.setdefault(e["employer"], e["rate"])

    for rec in ledger["records"]:
        for e in rec["entries"]:
            if e["id"] in voided or e["type"] == "void":
                continue
            a = acc.get(e.get("employer"))
            if a is None:
                continue
            d = e.get("date")
            a["first"] = min(a["first"], d) if a["first"] else d
            a["last"] = max(a["last"], d) if a["last"] else d
            line = {"date": d, "type": e["type"], "record": rec["id"], "said": rec["transcript"],
                    "source": rec["source"], "audio": rec.get("audio_file")}
            if e["type"] == "work":
                rate = e.get("rate") or latest_rate.get(e["employer"])
                earned = (rate or 0) * e["days"]
                ot = e.get("ot_hours") or 0
                ot_pay = (rate or 0) / hpd * 2 * ot
                a["days"] += e["days"]
                a["earned"] += earned
                a["ot_hours"] += ot
                a["ot_pay"] += ot_pay
                if not rate:
                    a["unpriced_days"] += e["days"]
                if rate and mw and rate < mw:
                    a["shortfall"] += (mw - rate) * e["days"]
                line.update(days=e["days"], rate=rate, earned=earned, ot_hours=ot, ot_pay=ot_pay)
            elif e["type"] == "payment":
                a["paid"] += e["amount"]
                line.update(amount=e["amount"])
            elif e["type"] == "rate":
                line.update(rate=e["amount"])
            a["lines"].append(line)
    for key, a in acc.items():
        a["rate"] = latest_rate.get(key)
        a["due"] = a["earned"] + a["ot_pay"] - a["paid"]
        a["below_min"] = bool(a["rate"] and mw and a["rate"] < mw)
        a["lines"].sort(key=lambda l: l["date"])
    return acc


# ---------------------------------------------------------------------------
# Applying an utterance + building the spoken Hindi reply
# ---------------------------------------------------------------------------

HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर",
             "अक्टूबर", "नवंबर", "दिसंबर"]


def hi_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {HI_MONTHS[d.month - 1]}"


def rs(x):
    x = round(float(x), 2)
    return str(int(x)) if x == int(x) else f"{x:.2f}"


def days_hi(d):
    if d == 0.5:
        return "आधा दिन"
    return f"{rs(d)} दिन"


def handle(ledger, text, *, source="voice", audio_file=None, audio_sha256=None, today=None,
           now=None):
    """Parse + apply an utterance. Returns {intent, reply, record?, employer?}."""
    today = today or dt.date.today()
    p = parse(text, ledger["employers"], ledger.get("last_employer"), today)
    intent = p["intent"]

    if intent == "empty":
        return {"intent": intent, "reply": "कुछ सुनाई नहीं दिया। कृपया फिर से बोलिए।"}

    if intent == "unknown":
        return {"intent": intent,
                "reply": "माफ़ कीजिए, समझ नहीं आया। ऐसे बोलिए: आज शर्मा जी की साइट पे काम किया, "
                         "सात सौ तय हुआ, चार सौ मिले।"}

    if intent == "undo":
        voided = _voided_ids(ledger)
        for rec in reversed(ledger["records"]):
            live = [e for e in rec["entries"] if e["type"] != "void" and e["id"] not in voided]
            if live:
                entries = [{"id": uuid.uuid4().hex[:10], "type": "void", "target": e["id"],
                            "date": today.isoformat()} for e in live]
                r = add_record(ledger, transcript=text, entries=entries, source=source,
                               audio_file=audio_file, audio_sha256=audio_sha256, now=now)
                return {"intent": "undo", "record": r,
                        "reply": "ठीक है, पिछली एंट्री रद्द कर दी। रिकॉर्ड में सुधार दर्ज हो गया है।"}
        return {"intent": "undo", "reply": "रद्द करने के लिए कोई एंट्री नहीं है।"}

    acc = accounts(ledger)
    if intent == "note":
        key = p.get("employer")
        entry = {"id": uuid.uuid4().hex[:10], "type": "note", "note": p["note"],
                 "employer": key, "date": p["date"]}
        r = add_record(ledger, transcript=text, entries=[entry], source=source,
                       audio_file=audio_file, audio_sha256=audio_sha256, now=now)
        if p["note"] == "no_work":
            return {"intent": "note", "record": r,
                    "reply": "ठीक है, दर्ज कर लिया कि आज काम नहीं मिला।"}
        a = accounts(ledger).get(key)
        reply = "ठीक है, दर्ज कर लिया कि पैसे नहीं मिले।"
        if a:
            reply += " " + _due_phrase(a)
        return {"intent": "note", "record": r, "employer": key, "reply": reply}

    if intent in ("query", "statement"):
        key = p.get("employer")
        if key and key in acc:
            a = acc[key]
            reply = _account_sentence(a, ledger)
            return {"intent": intent, "employer": key, "reply": reply}
        live = [a for a in acc.values() if a["days"] or a["paid"]]
        if not live:
            return {"intent": intent, "reply": "अभी तक कोई काम दर्ज नहीं है।"}
        if intent == "statement" and len(live) == 1:
            return {"intent": intent, "employer": live[0]["key"],
                    "reply": _account_sentence(live[0], ledger)}
        total_due = sum(max(0, a["due"]) for a in live)
        parts = [f"{a['name']} पर {rs(a['due'])} रुपये" for a in live if a["due"] > 0]
        adv = [f"{a['name']} से {rs(-a['due'])} रुपये एडवांस" for a in live if a["due"] < 0]
        reply = f"कुल बकाया {rs(total_due)} रुपये है।"
        if parts:
            reply += " " + ", ".join(parts) + "।"
        if adv:
            reply += " " + ", ".join(adv) + " लिया हुआ है।"
        return {"intent": intent, "reply": reply}

    # ---- log ----
    key, disp = p["employer"], p["employer_display"]
    if not key:
        key, disp = "_unnamed", "बिना नाम का ठेकेदार"
    if key not in ledger["employers"]:
        ledger["employers"][key] = disp
    disp = ledger["employers"][key]
    ledger["last_employer"] = key

    entries = []
    rate = p["rate"]
    current_rate = acc.get(key, {}).get("rate")
    if rate:
        entries.append({"id": uuid.uuid4().hex[:10], "type": "rate", "employer": key,
                        "amount": rate, "date": p["date"]})
    if p["days"]:
        entries.append({"id": uuid.uuid4().hex[:10], "type": "work", "employer": key,
                        "days": p["days"], "rate": rate or current_rate,
                        "ot_hours": p["ot_hours"] or 0, "date": p["date"]})
    elif p["ot_hours"]:
        entries.append({"id": uuid.uuid4().hex[:10], "type": "work", "employer": key,
                        "days": 0, "rate": rate or current_rate, "ot_hours": p["ot_hours"],
                        "date": p["date"]})
    for amt in p["payments"]:
        entries.append({"id": uuid.uuid4().hex[:10], "type": "payment", "employer": key,
                        "amount": amt, "date": p["date"]})

    rec = add_record(ledger, transcript=text, entries=entries, source=source,
                     audio_file=audio_file, audio_sha256=audio_sha256, now=now)
    a = accounts(ledger)[key]

    bits = []
    when = "आज" if p["date"] == today.isoformat() else hi_date(p["date"])
    if p["days"]:
        bits.append(f"{disp} के यहाँ {when} का {days_hi(p['days'])} काम लिख लिया")
    if p["ot_hours"]:
        bits.append(f"{rs(p['ot_hours'])} घंटे ओवरटाइम दर्ज किया")
    if rate:
        bits.append(f"{rs(rate)} रुपये रोज़ तय")
    if p["payments"]:
        bits.append(f"{rs(sum(p['payments']))} रुपये मिले")
    reply = "ठीक है। " + ", ".join(bits) + "।"
    if a["unpriced_days"]:
        reply += f" {disp} के साथ रोज़ का रेट अभी दर्ज नहीं है, कृपया रेट भी बोलिए।"
    else:
        reply += " " + _due_phrase(a)
    mw = min_wage(ledger["settings"])
    eff_rate = rate or current_rate
    if eff_rate and mw and eff_rate < mw:
        reply += (f" ध्यान दें, {rs(eff_rate)} रुपये रोज़ न्यूनतम मज़दूरी {rs(mw)} रुपये से कम है।")
    if not p["employer_explicit"] and key != "_unnamed":
        reply += f" यह {disp} के खाते में जोड़ा है।"
    if key == "_unnamed":
        reply += " अगली बार ठेकेदार का नाम भी बोलिए।"
    return {"intent": "log", "record": rec, "employer": key, "reply": reply}


def _due_phrase(a, short=False):
    who = "" if short else f"{a['name']} पर "
    if a["due"] > 0:
        return f"{who}कुल {rs(a['due'])} रुपये बाकी हैं।"
    if a["due"] < 0:
        return f"{a['name']} से {rs(-a['due'])} रुपये एडवांस लिया हुआ है।"
    return f"{a['name']} का पूरा हिसाब बराबर है।"


def _account_sentence(a, ledger):
    if not a["days"] and not a["paid"]:
        return f"{a['name']} के साथ अभी कोई काम दर्ज नहीं है।"
    s = f"{a['name']}: "
    if a["first"] and a["last"] and a["first"] != a["last"]:
        s += f"{hi_date(a['first'])} से {hi_date(a['last'])} तक "
    s += f"{days_hi(a['days'])} काम हुआ।"
    if a["rate"]:
        s += f" {rs(a['rate'])} रुपये रोज़ के हिसाब से {rs(a['earned'])} रुपये बनते हैं।"
    if a["ot_pay"]:
        s += f" ओवरटाइम के {rs(a['ot_pay'])} रुपये अलग से।"
    s += f" {rs(a['paid'])} रुपये मिले हैं। " + _due_phrase(a, short=True)
    mw = min_wage(ledger["settings"])
    if a["below_min"]:
        s += (f" तय रेट न्यूनतम मज़दूरी {rs(mw)} रुपये से कम है; इस हिसाब से "
              f"{rs(a['shortfall'])} रुपये और बनते हैं।")
    return s


def statement_text(ledger, key):
    acc = accounts(ledger)
    return _account_sentence(acc[key], ledger) if key in acc else ""


def keyterms(ledger):
    """Names and site words to bias Gnani Prisma v3 towards (max 200)."""
    terms = []
    for key, disp in ledger["employers"].items():
        if key != "_unnamed":
            terms.append(disp)
    terms += ["ठेकेदार", "दिहाड़ी", "मज़दूरी", "एडवांस", "ओवरटाइम", "साइट", "मिस्त्री", "हाज़िरी",
              "थेकेदार", "रेट", "पेमेंट"]
    seen, out = set(), []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:200]
