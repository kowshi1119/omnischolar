# 📚 OmniScholar

**Offline AI Study Companion for University Students — Powered by Gemma 4 (via Ollama)**

OmniScholar is a fully offline, privacy-first exam preparation assistant built for Sri Lankan university students. It supports personalized learning, adaptive quizzes, weak-area diagnosis, and day-by-day study plans — all running locally on your machine with no internet required after setup.

---

## Features

Each feature is its own page (sidebar sections **Study**, **Practice**, **You**), with a URL you can bookmark.

- **Home**: readiness, exam countdown, streak, today's focus topic and shortcuts
- **Learn / Revise**: streamed explanations or exam-focused summaries that cite the page of your notes they used
- **Test Me**: multiple-choice quizzes with instant per-question explanations. Results feed your streak, readiness and weak areas
- **Virtual Teacher**: step-by-step lessons with diagrams, mid-lesson checks and voice narration
- **Past Papers, CS Battle, Study Plan, Weak Areas, Teacher Mode**: practice and planning tools
- **3A Achievement / My Progress**: Elo readiness for A/L students
- **My Notes**: upload PDFs to ground answers in your own material
- **Answer language**: English, Sinhala or Tamil, switchable from the sidebar
- **Fully offline**: the model, fonts and diagram renderer all run on your machine

---

## Setup

### Prerequisites

- Python 3.10+ (tested on 3.12, Windows 11)
- [Ollama](https://ollama.com) installed and running
- ~8 GB RAM is enough for `gemma4:e2b` or the OmniScholar fine-tune

### 1. Pull models

```bash
ollama pull gemma4:e2b
ollama pull embeddinggemma   # multilingual embeddings (English, Sinhala, Tamil)
ollama pull gemma4:e4b   # optional: only for the image explainer (vision)
```

To use the fine-tuned model instead, create it from a Modelfile
(`ollama create omnischolar-e2b-v2 -f Modelfile`) and set `OLLAMA_MODEL` in `.env`.

### 2. Install

```bash
git clone https://github.com/kowshi1119/omnischolar.git
cd omnischolar/omnischolar
python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama server (`localhost` is rewritten to `127.0.0.1` to avoid a ~2s IPv6 fallback on Windows) |
| `OLLAMA_MODEL` | `gemma4:e2b` | Chat model; falls back to an installed gemma4 model |
| `OLLAMA_VISION_MODEL` | `gemma4:e4b` | Image explainer |
| `OLLAMA_TIMEOUT` | `120` | Request timeout in seconds; raise it (e.g. 300) if the first answer times out while the model loads |
| `SQLITE_DB_PATH`, `CHROMA_DB_PATH` | `./omnischolar.db`, `./study_db` | Data location, relative to this folder |
| `APP_DEBUG` | `False` | Show full tracebacks in the UI |

Real environment variables take precedence over `.env`.

**Ollama server settings (8 GB laptops).** These are read by the Ollama server, not by
the app, so set them as Windows user environment variables and restart Ollama:
`OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0` (about half the context
memory), `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=2` (chat model + embedder).
The app itself keeps the model loaded (`OLLAMA_KEEP_ALIVE`, default 30 minutes), warms it
up at start-up, and turns off Gemma 4's hidden "thinking" for regular answers.

### 4. Run

```bash
python -m streamlit run app.py
```

Open http://localhost:8501. The server binds to `localhost` only (there is no login);
set `address` in `.streamlit/config.toml` to share it on a LAN.

If Ollama is not running, the app still opens: progress, history and study plans
work, and AI features show a clear message until `ollama serve` is started.

### 5. Test

```bash
pip install pytest ruff
ruff check . --select E9,F63,F7,F82
pytest tests -q
```

Tests use a temporary database and vector store and do not need Ollama.
They render every mode with Streamlit's `AppTest`, and cover the database,
the PDF ingestion and retrieval pipeline, and quiz scoring.
CI runs the same commands on every push and pull request (`.github/workflows/ci.yml`).

---

## Project Structure

```
omnischolar/
├── app.py             # Entry point: st.navigation pages, sidebar, Home, Learn/Revise, Test Me
├── nav.py             # Page registry so modules can switch pages (nav.go("TEST_ME"))
├── config.py          # Settings from environment / .env
├── database.py        # SQLite persistence and idempotent migrations
├── rag.py             # PDF ingestion, hybrid (dense + BM25) retrieval
├── ollama_client.py   # Chat / stream / embed wrapper around Ollama
├── prompt.py          # System prompt and mode definitions
├── ui_components.py   # Design system CSS and shared UI components
├── virtual_teacher.py, teacher.py, past_paper.py, battle_game.py,
│   study_plan.py, weakness.py, achievement_3a.py   # one module per mode
├── components/mermaid/ # Offline Mermaid diagram component (vendored mermaid.min.js)
├── static/            # Vendored fonts and logo (served at /app/static)
├── tests/             # pytest suite
└── study_db/          # ChromaDB store (created on first PDF upload)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Gemma 4 / OmniScholar fine-tune via Ollama (fully local) |
| Embeddings | `embeddinggemma` via Ollama (multilingual; older `nomic-embed-text` indexes are migrated automatically) |
| Retrieval | ChromaDB (dense) + rank-bm25, fused with Reciprocal Rank Fusion |
| Database | SQLite |
| PDF Parsing | PyMuPDF |
| Testing | pytest, Streamlit AppTest, Playwright (manual E2E) |

---

## Notes for Judges

- No API keys are required to run the core app — everything runs locally via Ollama.
- The `.env` file is excluded from this repo. Copy `.env.example` to `.env` to get started.
- The `study_db/` folder is auto-created when you first upload a PDF.
- Tested on Windows 11 with Python 3.12.

---

## 🏆 3A Achievement Module

> *"Kavindi is a Biological Science A/L student in Galle. She has eight weeks until the August 2026 A/L examination and wants to secure three A passes in Biology, Physics, and Chemistry."*

The **3A Achievement Module** is a dedicated preparation pathway for Advanced Level students targeting top grades. It is only visible in the mode selector after setting your profile to **A/L Student** in the sidebar.

### How Kavindi uses it

1. **Profile Setup** — Kavindi opens the sidebar, selects *A/L Student*, chooses *Biological Science Stream*, and multi-selects Biology, Physics, and Chemistry. She saves her profile with exam date `2026-08-15`.

2. **3A Achievement → Paper Library** — She browses the 2015–2024 past paper catalog filtered to her three subjects. She uploads her 2023 Biology Part I PDF (obtained from her school). The metadata table shows that Cell Biology, Genetics, and Plant Biology appeared across 9–10 of the last 10 papers.

3. **3A Achievement → Summarizer** — She uploads the 2022 Biology Part II paper PDF and clicks "Generate Summary." Gemma 4 returns:
   ```
   YEAR: 2022 | SUBJECT: Biology | PAPER: Part II (Structured/Essay)
   TOTAL QUESTIONS: 10 structured | TOTAL MARKS: 100
   MOST TESTED CHAPTER: Plant Biology — 22 marks across 3 questions
   DIFFICULTY: Easy 20% / Medium 55% / Hard 25%
   NIE ALIGNMENT: BIO-06 (Plant Biology) — 22 marks, BIO-07 (Animal Physiology) — 18 marks ...
   ```

4. **3A Achievement → 2027 Prediction** — She clicks "Generate 2027 Prediction" for Biology. Gemma 4's reasoning chain notes: *"Unit BIO-03 (Molecular Biology & Genetics) has appeared in 10 of 10 years, consistently as a 15-mark structured question. Confidence: 95% it appears in 2027."* A full mock 2027 paper with 50 predicted MCQs and 10 structured questions is generated, each tagged with a confidence percentage.

5. **3A Achievement → Curriculum Alignment** — Kavindi pastes the topics she just studied into the alignment tool. Each is mapped to its NIE unit, e.g. *"Osmosis → NIE BIO-06 Unit 6.3 — Transport in Plants (appeared in 7/10 papers)"*.

6. **3A Achievement → 3A Dashboard** — The dashboard shows her predicted grade per subject (e.g. Biology: B, Physics: C, Chemistry: C), a countdown to August 15, and a "What to fix before August" list ranked by NIE weight × past-paper frequency × readiness gap. Top action: *"#1 · Biology · BIO-03 — Molecular Biology (score: 55%, 10/10 papers)"*.

7. **Weakness Tracker** — In the Weakness Analysis mode, Kavindi's weak concept "Osmosis" now shows `NIE BIO-06 — Transport in Plants (appeared in 7/10 A/L papers)` beneath the concept card — not just a generic tag.

8. **Study Plan** — Her day-by-day plan is weighted by NIE syllabus percentage and past-paper frequency, so Organic Chemistry (10/10 papers, 22% NIE weight) gets more slots than a lower-frequency unit.

### Running the 3A demo

```bash
# Seed both demo students (Kowshi + Kavindi)
python seed_demo_data.py

# Launch the app
python -m streamlit run app.py --server.port 8501
```

In the demo, click **Demo Controls → Reset Demo Data** in the sidebar at any time to restore both students.
To see the A/L path: in the sidebar, type `Kavindi` as the name, set Student Type to *A/L Student*, select *Biological Science Stream*, pick Biology/Physics/Chemistry, and save. Then select **🏆 3A Achievement** from the mode list.

### Data files

| Path | Description |
|---|---|
| `data/al_syllabus/biological_science/biology.json` | NIE Biology syllabus: 9 units, weightings, past-paper frequencies |
| `data/al_syllabus/biological_science/physics.json` | NIE Physics — 7 units |
| `data/al_syllabus/biological_science/chemistry.json` | NIE Chemistry — 8 units |
| `data/al_syllabus/physical_science/combined_mathematics.json` | NIE Combined Maths — 6 units |
| `data/al_papers/catalog.json` | Past paper metadata 2015–2024 (no PDF content) |
| `al_config.py` | All 6 A/L streams with their official subject lists |
