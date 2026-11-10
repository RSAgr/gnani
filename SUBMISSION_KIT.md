# Haq: submission kit
Deadline: **Tue 10 Nov 2026, 11:59 PM IST.** The post must be **live before** you submit the form.
Shortlisting is based on verified engagement, so post **in the morning** and share it with your college groups and anyone who works on labour issues.

---

## 0. Before recording (15 min)
1. Run `python app.py` with your key, then go to Settings → **Load demo data** (gives a week of synthetic history).
2. Say one live sentence and check that the transcript and the spoken reply both work. If anything errors, send me the red message.
3. For the "noisy site" moment, play construction-site noise from YouTube on a second device at low volume while you speak.

---

## 1. 60-second demo video (shot list)

| Time | Screen | Audio |
|---|---|---|
| 0–8 s | Black slide with white text: "87% of India's construction workers are paid below minimum wage." Then: "When the contractor doesn't pay, it's his register against the worker's memory." | Quiet site noise |
| 8–12 s | Haq home screen | You: "So I built **Haq**, a voice wage ledger. Workers just speak." |
| 12–24 s | Press the button with site noise playing and say: **"आज शर्मा जी की साइट पे काम किया, सात सौ तय हुआ था, चार सौ मिले"** | Haq replies in Hindi, including the line about the minimum wage. Let it play. |
| 24–32 s | Zoom on the yellow board: dues go up, and the red rate shows "न्यूनतम से ₹140 कम" | You: "It checks every rate against the legal minimum wage." |
| 32–44 s | Say **"शर्मा जी का हिसाब सुनाओ"** and the statement opens | Haq reads the full account aloud |
| 44–52 s | Scroll the हिसाब पत्र and click Print | You: "A dated statement, in his own words, that he can show the contractor or the labour office." |
| 52–60 s | Record log: point at "Chain verified" | You: "Every entry is sealed. Nothing can be quietly changed. Built on Gnani Prisma and Timbre. #GnaniAI" |

Keep it to 60 seconds or less (eligible for **Demo Day Drop**). Add burned-in English subtitles (CapCut auto-captions work) because many people watch on mute.

---

## 2. LinkedIn post
(Fill in the [brackets]. Tag Gnani AI by typing "@Gnani" and choosing the company page.)

The workers who built your hostel were probably paid less than the law allows.

87% of construction workers in India earn below the minimum wage, and unpaid wages are the most common complaint labour helplines receive. When a contractor says "you only worked 4 days, not 6", it's his register against the worker's memory. Most workers can't write their own record.

So for the Great Indian AI Internship Challenge I built **Haq (हक़)**, a voice wage ledger for daily-wage workers.

At the end of the day the worker just speaks:
🗣️ "आज शर्मा जी की साइट पे काम किया, सात सौ तय हुआ था, चार सौ मिले"

Haq then:
✅ logs the day, the agreed rate and the payment against that contractor
⚖️ checks the rate against the minimum wage and shows the shortfall in ₹
🔊 replies in Hindi, so nothing needs reading
📄 creates a printable हिसाब पत्र (statement of wages due) with the worker's own words for each day
🔒 seals every voice note in a SHA-256 chain, so no entry can be quietly changed

Built on Indian AI:
• @Gnani AI Prisma v3 speech-to-text, given the worker's contractor names as hints so it holds up on noisy building sites
• Gnani Timbre text-to-speech for every reply and statement

60-second demo below 👇
If you work with labour unions or NGOs, I'd love your feedback on what would make this usable on a real site.

#GnaniAI #GreatIndianAIInternshipChallenge #AIForGood #VoiceAI #IndianLanguages #LabourRights

---

## 3. X (Twitter) post
87% of India's construction workers are paid below minimum wage. Most can't write their own record.

I built Haq (हक़): they speak, it keeps a sealed wage ledger, flags underpayment, and reads the dues back in Hindi.

Built on @GnaniAI Prisma + Timbre 👇
#GnaniAI #GreatIndianAIInternshipChallenge

(Check that @GnaniAI is their real handle on X before posting.)

---

## 4. Submission form answers

**Project name:** Haq (हक़): a voice wage ledger for daily-wage workers

**Project explanation:**
Haq lets daily-wage construction workers, many of whom can't read or write, keep their own proof of work and pay just by speaking. At the end of each day the worker says something like "aaj Sharma ji ki site pe kaam kiya, 700 tay hua tha, 400 mile". Gnani Prisma v3 transcribes it. We send the worker's own contractor names and site vocabulary as keyterms, plus a topic description, so it stays accurate on noisy sites. A custom Hinglish engine that works on both Devanagari and Roman script then pulls out the contractor, days (including half days and "kal" for yesterday), the agreed daily rate, payments, advances, overtime, and refusals to pay. It keeps a running account for each contractor and checks every agreed rate against the minimum wage: the central-sphere construction rates from 1 Oct 2026 are built in, or the worker can enter their state's rate. The shortfall is shown in rupees. Every reply, balance and full statement is spoken back in Hindi with Gnani Timbre, so the app works without reading. For each contractor Haq produces a printable हिसाब पत्र (statement of wages due) listing every day with the worker's own words. The worker can show it to the contractor, a union or the labour department, have it read aloud, or share it on WhatsApp. Each voice clip is SHA-256 hashed and each record is chained to the previous one, so any later edit is detected; corrections are added, never deleted. The problem is large: Projecthero found that 87% of construction workers are paid below the minimum wage, and wage disputes are the most common complaint labour helplines receive. The app runs locally using only the Python standard library.

**Gnani AI models / APIs used:**
- Gnani Prisma v3.0 speech-to-text (REST `/stt/v3`; `transcribe` format; `keyterms` + `topic` context), with automatic fallback to Prisma v2.5
- Gnani Timbre v2.5 text-to-speech (REST `/api/v1/tts/inference`, voice Nalini, hi-IN), with fallback to Timbre v3.0

**Each member's contribution:** *(edit to what's true)*
- [Name]: problem research, Gnani STT/TTS integration with context biasing, Hinglish wage parser, ledger and hash chain, UI and statement, demo and posts

**Nominated post links:** [LinkedIn URL] · [X URL]
**Demo video:** [link]

**Award fit:** Real Deal (real-world problem), Noise Canceller (site audio + keyterm biasing), Mixed Vibes (Hinglish), Demo Day Drop (60-second demo), and Solo Ninja / Two-Person Army.

---

## 5. Interview prep (likely questions)
- **Why rules instead of an LLM for parsing?** It's predictable and auditable for money records, it runs offline at no cost, and each extraction can be explained. An LLM such as Gnani's Evon would be the next step for messy sentences, with the rule engine as a check.
- **Why the hash chain?** A worker's record is only useful in a dispute if it's credible. The chain shows nothing was edited after the fact, and the original voice clip is kept for every entry.
- **How would it reach workers without smartphones?** The same engine behind an IVR number or a WhatsApp voice-note bot. Gnani already runs telephony voice agents, and Prisma v3 is trained on phone audio.
- **Limits:** Hindi and Hinglish only for now; minimum wage depends on state, skill and area; the statement is evidence, not a legal finding.
