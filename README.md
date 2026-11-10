# Haq (हक़): every day of work, on record

**A voice wage ledger for India's daily-wage workers, built on Gnani AI.**

Most construction workers in India are paid in cash, by a contractor, with no payslip. According to Projecthero's survey, 87% are paid below the minimum wage, and the most common complaint labour helplines receive is unpaid wages. When a dispute comes up, the contractor has a register and the worker has nothing, and many workers can't read or write to keep their own.

Haq lets the worker keep their own record just by speaking at the end of each day:

> **"आज शर्मा जी की साइट पे काम किया, सात सौ तय हुआ था, चार सौ मिले"**
> *"Worked at Sharma ji's site today, agreed 700, got 400"*

Haq writes it down and answers in Hindi: *"ठीक है। शर्मा जी के यहाँ आज का 1 दिन काम लिख लिया… शर्मा जी पर कुल 300 रुपये बाकी हैं। ध्यान दें, 700 रुपये रोज़ न्यूनतम मज़दूरी 840 रुपये से कम है।"*

## What it does

| The worker says | Haq does |
|---|---|
| "aaj Sharma ji ki site pe kaam kiya, 700 tay, 400 mile" | Logs 1 day at ₹700/day and ₹400 received, and updates Sharma ji's account |
| "कल भी शर्मा जी के यहाँ काम किया" | Logs yesterday's work at the rate already agreed |
| "वर्मा ठेकेदार के यहाँ आधा दिन काम किया" | Logs half a day |
| "2 घंटे ओवरटाइम भी किया" | Logs overtime, paid at double the hourly rate |
| "Gupta ji se 1500 advance liya" | Records the advance against that contractor |
| "शर्मा जी ने पैसे नहीं दिए" | Records that pay was refused that day |
| "शर्मा जी पर कितना बाकी है?" | Speaks the balance due |
| "शर्मा जी का हिसाब सुनाओ" | Reads the full statement aloud and opens the printable copy |
| "galti ho gayi, hata do" | Records a correction; nothing is deleted |

- **A minimum wage check on every entry.** Compares the agreed rate with the minimum wage and shows the shortfall in rupees. Built in: the central-sphere construction rates from 1 Oct 2026 (Area A ₹840, B ₹704, C ₹565 for unskilled work; all four skill levels included). The worker can enter their state's rate instead, because many private sites follow state rates.
- **हिसाब पत्र (statement of wages due).** One page per contractor that can be printed or saved as a PDF. It lists every day with the worker's own words, totals, overtime, the minimum wage gap, and signature lines. It can be read aloud to the contractor in Hindi (Gnani Timbre) or copied for WhatsApp.
- **Records that can't be quietly changed.** Every voice clip is kept and SHA-256 hashed, and every record is chained to the one before it. If any past entry is edited, Haq shows exactly which record broke. Corrections are added as new records, never deleted.
- **Accounts per contractor.** Days worked, rate, amount earned, amount paid and balance due (or advance taken) for each contractor. "Sharma ji" and "शर्मा जी" are recognised as the same person through a phonetic key that works across scripts.

## How Gnani AI is used

| | |
|---|---|
| **Gnani Prisma v3.0** (speech-to-text) | `POST /stt/v3`, `language_code=hi-IN`, `format=transcribe` (spoken numbers come back as digits). Haq sends **`keyterms`**: the worker's own contractor names plus site words (ठेकेदार, दिहाड़ी, एडवांस…), and a **`topic`** describing the recording. This context helps accuracy on noisy building-site audio and on names. Falls back to Prisma v2.5 automatically. |
| **Gnani Timbre v2.5** (text-to-speech) | Voice `Nalini`, `hi-IN`. Every confirmation, balance and full statement is spoken back, so a worker who can't read can still use everything. Falls back to Timbre v3.0 (`Shivani`). |

## Run it

Needs only Python 3.8+. **No pip install** is needed; it uses only the standard library.

```bash
# macOS / Linux
export GNANI_API_KEY="your-key"        # create one at app.gnani.ai/voice
python3 app.py

# Windows (PowerShell)
$env:GNANI_API_KEY="your-key"
python app.py
```
Or just run `python app.py` and paste the key when it asks. Then open **http://localhost:8000** in Chrome, allow the microphone, press the yellow button (or Space), speak, and press it again.

**Settings → Load demo data** fills in a week of synthetic records for "Ramesh Kumar (demo)", so you can explore it straight away.

## How it works

```
mic ─16 kHz WAV─▶ app.py ─▶ Gnani Prisma v3 (+ contractor names as keyterms) ─▶ transcript
                    │                                                         │
                    │ clip saved + SHA-256                                    ▼
                    │                         engine.py: Hinglish understanding
                    │                         (Devanagari + Roman, digits + "सात सौ"),
                    │                         contractor detection, rate / payment / days /
                    │                         overtime / yesterday, query / statement / undo
                    ▼                                                         │
          data/ledger.json  ◀── hash-chained record ◀──────────────────────────┘
                    │
                    └─▶ Hindi reply ─▶ Gnani Timbre ─▶ spoken to the worker
```

| File | |
|---|---|
| `engine.py` | Parser, ledger, minimum wage, hash chain (pure logic, testable) |
| `app.py` | Local web server and Gnani API calls |
| `index.html` | Worker screen: voice capture, dues, contractor accounts, sealed record log |
| `statement.html` | Printable हिसाब पत्र |
| `data/` | Created on first run: the ledger and the voice clips. Stays on the device. |

## Limits and next steps
- Understands Hindi and Hinglish today. Prisma and Timbre already support 10 Indian languages, so the next step is adding parser vocabulary for Bengali, Marathi, Telugu and Tamil, and for the regional Hindi spoken by many migrant workers.
- Runs as a local web app. The natural next form is a WhatsApp voice-note bot or an IVR number, so workers without smartphones can use it, and a dashboard where unions and NGOs can see disputes across many workers.
- The statement is the worker's own record, not a legal finding. It's meant to support conversations with contractors, unions and the labour department.

All demo names and data are synthetic.
