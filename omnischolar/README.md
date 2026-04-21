# 📚 OmniScholar

**Offline AI Study Companion for University Students — Powered by Gemma 4 (via Ollama)**

OmniScholar is a fully offline, privacy-first exam preparation assistant built for Sri Lankan university students. It supports personalized learning, adaptive quizzes, weak-area diagnosis, and day-by-day study plans — all running locally on your machine with no internet required after setup.

---

## Features

- **LEARN** — Structured explanations with memory tips and citations from your own notes
- **REVISE** — Examiner-ready summaries with common mistakes highlighted
- **TEST ME** — Adaptive MCQ quizzes auto-generated from your subject and weak areas
- **FIND WEAK AREAS** — Readiness report with percentage scores per topic
- **STUDY PLAN** — Day-by-day schedule from today to your exam date
- **PDF Upload** — Index your own lecture notes for RAG-powered answers
- **Multilingual** — Supports English, Sinhala, and Tamil

---

## Setup

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running

### 1. Pull required models

```bash
ollama pull gemma4:e4b
ollama pull nomic-embed-text
```

### 2. Clone the repo

```bash
git clone https://github.com/kowshi1119/omnischolar.git
cd omnischolar
```

### 3. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
OLLAMA_HOST=http://localhost:11434
HUGGINGFACE_TOKEN=your_token_here   # optional, not required for core features
```

### 6. Run the app

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

---

## Project Structure

```
omnischolar/
├── app.py           # Main Streamlit UI and orchestration
├── database.py      # SQLite persistence (student profiles, quiz history)
├── rag.py           # PDF ingestion and ChromaDB vector retrieval
├── prompt.py        # System prompt and mode definitions
├── requirements.txt # Python dependencies
├── .env.example     # Environment variable template
├── .gitignore       # Excludes secrets and generated files
└── study_db/        # ChromaDB vector store (auto-created on first PDF upload)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Gemma 4 via Ollama (fully local) |
| Embeddings | `nomic-embed-text` via Ollama |
| Vector Store | ChromaDB |
| Database | SQLite |
| PDF Parsing | PyMuPDF (fitz) |
| Env Config | python-dotenv |

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
