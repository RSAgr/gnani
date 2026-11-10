# Haq (हक़): every day of work, on record

**A voice wage ledger for India's daily-wage workers, built on Gnani AI.**

Construction workers in India are mostly paid in cash, by contractors, with no payslip. 87% are paid below the minimum wage ([Projecthero](https://www.rprealtyplus.com/interviews/mp-has-highest-percentage-of-jobs-paying-less-than-min-wage-110593.html)), and unpaid wages are the most common complaint labour helplines handle ([Scroll](https://scroll.in/article/1029692/rs-2-crore-in-9-months-a-helpline-is-assisting-workers-in-recovering-wages)). In a dispute, the contractor has a register and the worker has only memory, and many workers can't read or write to keep their own.

With Haq, the worker keeps that record by speaking for a few seconds at the end of each day:

> **"आज शर्मा जी की साइट पे काम किया, सात सौ तय हुआ था, चार सौ मिले"**
> *Worked at Sharma ji's site today, agreed ₹700, got ₹400.*

Haq logs it and replies in Hindi: *"…शर्मा जी पर कुल 300 रुपये बाकी हैं। ध्यान दें, 700 रुपये रोज़ न्यूनतम मज़दूरी 840 रुपये से कम है।"* (Sharma ji owes ₹300 in total. Note: ₹700 a day is below the minimum wage of ₹840.)

## What it does

| The worker says | Haq does |
|---|---|
| "aaj Sharma ji ki site pe kaam kiya, 700 tay, 400 mile" | Logs 1 day at ₹700/day and ₹400 received |
| "कल भी शर्मा जी के यहाँ काम किया" | Logs yesterday's work at the agreed rate |
| "वर्मा ठेकेदार के यहाँ आधा दिन काम किया" | Logs half a day with a new contractor |
| "2 घंटे ओवरटाइम भी किया" | Logs overtime at double the hourly rate |
| "Gupta ji se 1500 advance liya" | Records an advance |
| "शर्मा जी ने पैसे नहीं दिए" | Records that pay was refused that day |
| "शर्मा जी पर कितना बाकी है?" | Speaks the balance due |
| "शर्मा जी का हिसाब सुनाओ" | Reads the full statement aloud and opens the printable copy |
| "galti ho gayi, hata do" | Adds a correction (nothing is ever deleted) |

- **Minimum wage check.** Each agreed rate is compared with the minimum wage, and the shortfall is shown in rupees. Built in: the central construction rates from 1 Oct 2026 (unskilled: Area A ₹840, B ₹704, C ₹565/day; all four skill levels). The worker can enter their state's rate instead.
- **हिसाब पत्र (statement of wages due).** One page per contractor, ready to print or save as PDF. It lists each day with the worker's own words, plus totals, overtime, the minimum wage gap and signature lines. It can be read aloud in Hindi or copied to WhatsApp.
- **Tamper-evident records.** Each voice clip is SHA-256 hashed, and each record is chained to the one before it. If a past entry is edited, Haq shows which record broke.
- **Accounts per contractor.** Days worked, rate, earned, paid, and the balance due or advance taken. "Sharma ji" and "शर्मा जी" are matched as the same person.

## How Gnani AI is used

| Model | Role |
|---|---|
| **Prisma v3.0** (speech-to-text) | `format=transcribe`, so spoken amounts come back as digits. Haq sends the worker's contractor names and site words (ठेकेदार, दिहाड़ी, एडवांस…) as **`keyterms`**, plus a **`topic`**, for accuracy on noisy sites. Falls back to Prisma v2.5. |
| **Timbre v2.5** (text-to-speech) | Speaks every confirmation, balance and statement in Hindi (voice Nalini), so the app works without reading. Falls back to Timbre v3.0. |

## Run it

Python 3.8+. **No pip install**: Haq uses only the standard library.

```bash
export GNANI_API_KEY="your-key"     # Windows PowerShell: $env:GNANI_API_KEY="your-key"
python app.py                       # or run it without the variable and paste the key when asked
```

Open **http://localhost:8000** in Chrome, allow the microphone, and press the yellow button (or Space). To see it with sample data, go to **Settings → Load demo data**, which adds a week of synthetic records.

Run the tests with `python test_engine.py`.

## How it works

```
mic ─WAV─▶ app.py ─▶ Gnani Prisma v3 (+ contractor names as keyterms) ─▶ transcript
              │                                                          │
              │ clip saved + SHA-256                                     ▼
              │                    engine.py: Hinglish parsing (Devanagari + Roman,
              │                    "700" or "सात सौ"), contractor, days, rate, payment,
              │                    overtime, yesterday; query / statement / undo
              ▼                                                          │
       data/ledger.json ◀── hash-chained record ◀───────────────────────┘
              └─▶ Hindi reply ─▶ Gnani Timbre ─▶ spoken to the worker
```

| File | Purpose |
|---|---|
| `engine.py` | Parser, ledger, minimum wage, hash chain (pure logic) |
| `app.py` | Local server and Gnani API calls |
| `index.html` | Worker screen: voice, dues, contractor accounts, record log |
| `statement.html` | Printable हिसाब पत्र |
| `test_engine.py` | Engine tests, including tamper detection |
| `data/` | Ledger and voice clips, created on first run; stays on the device |

## Current limitations

- **Parsing is rule-based.** It handles Hindi and Hinglish with common phrasings. Unusual sentences or other languages fall through to "समझ नहीं आया" (didn't understand). A contractor is only recognised when the name comes with a marker such as *ji*, *ठेकेदार* or *की साइट*.
- **Name matching is phonetic.** Similar names (Verma and Varma) merge into one account. Very short names are only recognised with a marker.
- **One minimum wage for all dates.** Every past entry is checked against today's rate, even work done before the last revision. Only the central construction rates are built in; state rates have to be typed in.
- **The chain proves the order of records, not when they were made.** Timestamps come from the device clock. Someone with the file could rebuild the whole chain from scratch.
- **Single device, no backup.** If the phone or laptop is lost, the record is lost too.
- **It needs a smartphone or computer and internet** for Gnani. Each voice note is limited to about 28 seconds.
- **Fixed assumptions:** an 8-hour working day, and overtime at double the hourly rate.
- **Not yet tested with real workers** on real site audio.
- **The statement is the worker's own record, not a legal finding.**

## Roadmap

| Area | What it adds | Why it matters |
|---|---|---|
| **IVR and WhatsApp voice notes** | The same engine behind a phone number and a WhatsApp bot, using Prisma's telephony models | Reaches workers with basic phones and no app |
| **Dated wage tables** | A rates file with an effective date per state, skill and zone, updated every April and October | Each day is checked against the rate in force that day |
| **LLM fallback with rule checks** | Gnani's Evon reads sentences the rules miss. The rule engine then checks every number, and Haq asks back if anything is unclear (*"कितने दिन?"*, how many days?) | Handles natural speech without letting a model invent amounts |
| **Rights assistant (RAG)** | Spoken answers to "can he pay me less?" or "where do I complain?", drawn from the Code on Wages, the BOCW Act and state notifications, with the source named | Explains rights accurately. Money figures still come from the structured table, never from generated text |
| **Welfare board eligibility** | Uses the logged days of work to show when the worker qualifies to register with the state construction workers' welfare board | Registration opens access to welfare schemes for building workers |
| **Contractor acknowledgement** | The contractor confirms the day's entry with one tap on a WhatsApp link | Turns a one-sided record into an agreed one |
| **Agentic follow-up (worker approves each step)** | Reminders when dues pass a set age, a drafted complaint letter in the right format, and handover to a union or NGO caseworker | Takes the worker from "I'm owed money" to "someone is acting on it". Nothing is sent without the worker's approval |
| **External time-stamping** | The daily chain fingerprint (a hash, never personal data) is sent to a trusted party (a union, NGO or the worker's family) or to a public time-stamping service such as OpenTimestamps | Proves each record existed on that date, which the local chain alone can't. A full blockchain isn't needed |
| **Encrypted backup** | Ledger encrypted with a PIN, backed up to the worker's own cloud account | Survives a lost phone; the worker keeps control |
| **Union and NGO dashboard** | Shows disputes across workers who opt in, and contractors with repeated underpayment | Turns individual records into collective bargaining power |
| **More languages** | Parser vocabulary for Bengali, Marathi, Telugu and Tamil; Prisma and Timbre already support them | Many migrant workers don't speak Hindi |

---

All names and data in the demo are synthetic.
