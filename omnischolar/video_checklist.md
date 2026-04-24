# OmniScholar — 3-Minute Demo Video Script

## Pre-flight Checklist (Before Recording)

- [ ] Ollama running: `ollama serve`
- [ ] Model loaded: `ollama run gemma4:e4b` (warm it up once)
- [ ] Streamlit running: `cd omnischolar && .\.venv\Scripts\python.exe -m streamlit run app.py`
- [ ] Screen at 1080p, font size 14 in browser (Ctrl+Shift+-)
- [ ] No notifications on (Do Not Disturb mode)
- [ ] Good lighting on face (ring light or window)
- [ ] Quiet room, no echo
- [ ] OBS or Loom set up for recording

---

## Scene-by-Scene Script

### 0:00 – 0:20 | On-camera intro (Kowshi face-on)

**Setting:** Laptop, OmniScholar logo visible on screen behind.

**Script:**
> "Hi, I'm Kowshi. In Sri Lanka, 1 in 3 A/L students fails their exam. They can't afford private tutors. They don't have reliable internet. I built OmniScholar — a fully offline AI tutor powered by Gemma 4 that speaks to students in English, Sinhala, or Tamil."

---

### 0:20 – 0:40 | Problem + Stats (Screen: browser open on DoE data or splash screen)

**Script:**
> "Only 4.19% of Physics students get an A. The gap is not intelligence — it's access. OmniScholar runs on a ₹25,000 laptop with no internet. One USB drive. Zero cloud."

**Show:** OmniScholar home screen loading. Point to "Offline Mode" badge.

---

### 0:40 – 1:10 | Virtual Teacher Dr. Omni (Screen: Virtual Teacher tab)

**Script:**
> "Meet Dr. Omni. I'll ask about binary search trees — in Sinhala."

**Action:** Type "binary search trees" in Sinhala script (or select Sinhala in language picker). Show lesson loading.

> "One Gemma 4 call returns: lesson, a Mermaid diagram, AND a check question. No serial calls. 4 seconds flat."

**Show:** Mermaid diagram renders. Mid-question appears. Type wrong answer. Show Socratic follow-up (no answer leak, just a probe).

---

### 1:10 – 1:40 | Test Me + Confidence Badge (Screen: Test Me tab)

**Script:**
> "The tutor never just gives answers. It uses Bloom's taxonomy and Vygotsky's ZPD — so questions adapt to where you actually are."

**Show:** Take a quick quiz. Show 🟢 grounding badge. Show 🔴 when switching to a topic with no uploaded materials.

> "Every response is graded: grounded in your uploaded syllabus, curriculum-based, or uncertain. No hallucination hiding."

---

### 1:40 – 2:10 | 3A Readiness Dashboard (Screen: My Progress / 3A tab)

**Script:**
> "And here's what makes this research-grade. Instead of a fake progress bar, OmniScholar uses Elo IRT — the same algorithm used in chess ratings and peer-reviewed digital education research."

**Show:** 3A dashboard for Physics. Point to: "72% A/L Physics ready (±9%, based on 18 attempts). Calibrated against DoE 2022/2023 grade distribution."

> "Grade prediction: B. Weakest topic: Optics. That's actionable. Not vibes."

---

### 2:10 – 2:30 | Technical Flex (Screen: VS Code or terminal briefly)

**Script:**
> "Under the hood: Gemma 4 via Ollama, hybrid BM25 + dense RAG, tutor safety eval — zero latency, rule-based, no LLM. And a Unsloth fine-tune pipeline targeting Sri Lanka curriculum terminology."

**Show:** Terminal showing `ollama list` with model. Quick flash of `finetune_omnischolar.py`.

---

### 2:30 – 2:50 | Impact Statement (Back to on-camera)

**Script:**
> "300,000 Sri Lankan A/L students sit exams each year. OmniScholar is free, offline, multilingual, and calibrated against real exam data. The technology is ready. The students need it now."

---

### 2:50 – 3:00 | GitHub URL + Call to action

**Show:** GitHub repo URL on screen. README visible.

**Script:**
> "The full code — including fine-tuning pipeline, Elo engine, and Modelfile — is on GitHub. Link in the description. Thank you."

---

## Post-Recording Checklist

- [ ] Trim silence at start/end
- [ ] Add captions (auto + verify Sinhala/Tamil script)
- [ ] Add OmniScholar logo overlay at 0:00 and 2:50
- [ ] Export 1080p 30fps MP4
- [ ] Upload to YouTube as Unlisted
- [ ] Paste YouTube URL in Kaggle submission form
