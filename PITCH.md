# Haq (हक़): Solution Pitch

**Haq lets a daily-wage worker keep their own proof of work and pay just by speaking, built on Gnani Prisma and Timbre.** ([PDF version](Haq_Solution_Pitch.pdf))

## The problem
India's construction workers are paid in cash, by contractors, with no payslip. 87% are paid below the government minimum wage (Projecthero survey), and unpaid wages are the most common complaint labour helplines handle. In a dispute it is the contractor's register against the worker's memory, and many workers cannot read or write to keep a record.

## The solution
At the end of each day the worker speaks in Hindi or Hinglish: *"आज शर्मा जी की साइट पे काम किया, सात सौ तय हुआ था, चार सौ मिले"* (worked at Sharma ji's site today, agreed ₹700, got ₹400). Haq then:

- **Keeps an account per contractor:** days and half days, agreed rate, payments, advances, overtime at double rate, and days pay was refused.
- **Checks every rate against the minimum wage** (central construction rates from 1 Oct 2026, or the worker's state rate) and shows the shortfall in rupees.
- **Speaks every reply and balance back in Hindi,** so the worker never has to read.
- **Produces a printable हिसाब पत्र** (statement of wages due) with the worker's own words for each day, to show a contractor, union or labour office.
- **Seals each record in a SHA-256 hash chain,** so any later edit is detected. Corrections are added, never deleted.

## How Gnani AI powers it
| Model | How Haq uses it |
|---|---|
| **Gnani Prisma v3.0** (speech-to-text) | Transcribes each voice note with spoken amounts as digits. Haq sends the worker's own contractor names and site words as `keyterms`, plus a `topic`, so names and numbers hold up on noisy building sites. Falls back to Prisma v2.5. |
| **Gnani Timbre v2.5** (text-to-speech) | Speaks every confirmation, balance and full statement in Hindi, including reading the statement aloud to the contractor. Falls back to Timbre v3.0. |

## Why it matters
Existing apps help workers find jobs or track spending. Haq gives them evidence: a dated, sealed record in their own voice, and a clear figure for what the law says they are owed. For workers who can't read, voice is the only way in.

## What's next
IVR and WhatsApp voice notes for workers without smartphones; Bengali, Marathi, Telugu and Tamil; a dashboard for unions and NGOs to act on disputes.
