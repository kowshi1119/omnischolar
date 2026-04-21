# OmniScholar — Development Progress

**Project:** Offline AI Study Companion for University Students
**Model:** Gemma 4 via Ollama (local, fully offline)
**Repo:** https://github.com/kowshi1119/omnischolar
**Last Updated:** April 21, 2026

---

## Project Overview

OmniScholar is a privacy-first, fully offline exam preparation assistant built for Sri Lankan university students. It runs entirely on local hardware using Ollama + Gemma 4, with ChromaDB for RAG-powered PDF ingestion and SQLite for student progress tracking.

---

## Completed Milestones

### Phase 1 — Foundation
- [x] Project scaffolding: repo, `.gitignore`, `.env` / `config.py` pattern
- [x] Ollama integration (`ollama_client.py`) — streaming, embeddings, timeout handling, multi-model support
- [x] ChromaDB RAG pipeline (`rag.py`) — PDF ingestion, chunking, semantic search
- [x] SQLite database layer (`database.py`, 696 lines) — students, quiz history, weak concepts, study streaks
- [x] Core prompt library (`prompt.py`, 413 lines) — LEARN, REVISE, TEST ME, STUDY PLAN, BATTLE GAME, WEAK AREAS
- [x] GitHub Actions CI workflow added (`.github/`)

### Phase 2 — Core Features
- [x] **LEARN mode** — Structured explanations with memory tips, RAG citations from uploaded PDFs
- [x] **REVISE mode** — Examiner-ready summaries with common mistake callouts
- [x] **TEST ME mode** — Adaptive MCQ quizzes, auto-graded, weak-area biased
- [x] **FIND WEAK AREAS** — Per-topic readiness %, highlighted problem concepts
- [x] **STUDY PLAN** — Day-by-day schedule from today to exam date (`study_plan.py`, 459 lines)
- [x] **BATTLE GAME** — Head-to-head quiz game mode (`battle_game.py`, 367 lines)
- [x] **PDF Upload** — Multi-PDF ingestion, RAG-powered Q&A
- [x] **Multilingual** — English, Sinhala, Tamil support
- [x] **Past Papers** — Past exam paper parsing and practice (`past_paper.py`, 635 lines)
- [x] **Virtual Teacher** — Extended AI tutor session (`virtual_teacher.py`, 1442 lines)
- [x] **Achievement System** — Badges, streaks, milestones (`achievement.py`, 645 lines)
- [x] **Weakness Tracker** — Resolved vs unresolved weak concept tracking (`weakness.py`, 394 lines)

### Phase 3 — UI/UX Design System (Dark Academic Arcade)
- [x] Full design system established: `#060A14` navy background, `#00D4FF` cyan, `#FFB800` amber
- [x] Typography: Space Grotesk (sans) + JetBrains Mono (mono)
- [x] `ui_components.py` — complete UI primitive library (783 lines)
- [x] `omnischolar_ui_design.html` — reference design mockup

### Phase 4 — UI/UX Enhancements v2 (Latest — commit `aec1707`)
- [x] **Mode card CSS classes** — `.omni-mode-card`, `.omni-tag`, `.omni-stat` added to `inject_premium_css()`
- [x] **`render_impact_counter()`** — animated streak / questions / concepts-fixed counter; wired into dashboard via live DB queries
- [x] **`render_gemma_badges()`** — Gemma 4 · Offline · RAG badges replacing inline HTML in `app.py`
- [x] **`render_system_status()`** — Ollama + model health indicator card
- [x] **`render_grounding_indicator()`** — improved 3-band natural language display (None / Partial / Strong)
- [x] **`render_thinking_state()`** — improved 3-dot pulsing animation
- [x] **`render_welcome_banner()`** — improved styling and layout
- [x] **Unified `COLORS` dict** — added `bg`, `sans`, `mono`, `card`, `section`, `border`, `muted` keys; removed duplicate definition
- [x] `app.py` wiring — all new components imported and called; removed ~60 lines of inline HTML duplication
- [x] `ui_components.py` deduplication — removed triple-copy bug (1676 → 783 lines, clean single copy)

### Phase 5 — Demo & Seeding
- [x] `seed_demo_data.py` — seeds demo student, quiz history, weak areas, study streaks for hackathon judges
- [x] `_new_avatar.py` — 3D avatar component integration

### Phase 6 — Training Pipeline (separate `train/` folder)
- [x] `train/download_model.py` — pulls base model weights
- [x] `train/finetune_omnischolar.py` — fine-tuning script (Gemma 4 edu adapter)
- [x] `train/upload_model.py` — pushes fine-tuned model to HuggingFace Hub
- [x] HuggingFace repo: `kowshikan/omnischolar-gemma4-edu`

---

## Current State

| File | Lines | Status |
|---|---|---|
| `app.py` | 485 | ✅ Clean, all components wired |
| `ui_components.py` | 783 | ✅ Clean, single copy, all v2 enhancements |
| `database.py` | 696 | ✅ Complete |
| `virtual_teacher.py` | 1442 | ✅ Complete |
| `achievement.py` | 645 | ✅ Complete |
| `verify.py` | 797 | ✅ Complete |
| `past_paper.py` | 635 | ✅ Complete |
| `study_plan.py` | 459 | ✅ Complete |
| `prompt.py` | 413 | ✅ Complete |
| `teacher.py` | 391 | ✅ Complete |
| `weakness.py` | 394 | ✅ Complete |
| `battle_game.py` | 367 | ✅ Complete |
| `ollama_client.py` | 178 | ✅ Complete |
| `rag.py` | 79 | ✅ Complete |
| `config.py` | 46 | ✅ Complete |

---

## Security Notes

- `.env` is gitignored — `HUGGINGFACE_TOKEN`, `WANDB_API_KEY`, `API_SECRET_KEY` never committed
- `.env.example` committed with placeholder values only
- All source files scanned — zero secrets found in tracked files
- `*.db`, `*.sqlite3`, `study_db/` gitignored (contain student data)
- `*.gguf`, `gguf/`, `models/` gitignored (large binary model weights)

---

## Git History

| Commit | Description |
|---|---|
| `aec1707` | feat: UI/UX v2 enhancements — 8 new components, clean ui_components, app.py wiring |
| `0033666` | Fix: rewrite app.py 12 modes dark theme, restore Database class |
| `86132a8` | Final: add all Claude session work to main branch |
| `a465bba` | Add ui_components.py with full Dark Academic Arcade design system |
| `9c0e994` | Add achievement, battle_game, config, study_plan, verify, weakness modules |
| `a0f008a` | Apply master patch set: PDF extraction, timeouts, multi-PDF, 3D avatar |
| `4757024` | Add GitHub Actions workflow |
| `aa22cdc` | Add README with setup instructions for judges |
| `c9cc6de` | Add gitignore and env config |

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Ollama and pull models
ollama pull gemma4:e4b
ollama pull nomic-embed-text

# 3. Copy and fill environment variables
cp .env.example .env

# 4. Seed demo data (optional)
python seed_demo_data.py

# 5. Launch the app
python -m streamlit run app.py --server.port 8501
```
