# Development improvements — October 2026

Two rounds: **round 1** fixed broken core features; **round 2** (below the first section) redesigned the UI, sped up the model and made the app fully offline, guided by a research pass on learning science, local RAG, Ollama and Streamlit best practice.

A full audit of the OmniScholar app (`omnischolar/`), followed by fixes verified
with pytest, Streamlit `AppTest` and Playwright against the running app.

## Critical problems found and fixed

| Problem | Effect | Fix |
|---|---|---|
| Sidebar upload passed Streamlit's `UploadedFile` straight to `fitz.open`, and stored it as Chroma metadata | **Every PDF upload failed**, so RAG never had data | `rag.ingest_pdf` accepts paths, bytes or file objects |
| Chunk IDs were `{subject}_{page}_{i}` | A second PDF of the same subject was dropped | Content-hashed IDs + `upsert` (re-upload is idempotent) |
| `ALTER TABLE weak_concepts ADD COLUMN last_seen ... DEFAULT CURRENT_TIMESTAMP` (SQLite rejects non-constant defaults; error swallowed) | `get_weak_concepts` always returned `[]` | Add column without a default, backfill, set on insert |
| `Database.get_quiz_history` didn't exist (only a module function) | Quiz count always 0: the 3A engine never unlocked | Method added |
| Nothing called `save_quiz_result`; nothing wrote `study_sessions` | Streak, readiness and charts only ever showed seed data | Test Me scores answers locally and records the result and study day |
| `study_plan.build_schedule` was redefined later in the file with another signature | Study Plan crashed once quiz data existed | Shadowed duplicates removed (also in `weakness.py`) |
| `db.resolve_concept` missing | "Mark as Resolved" crashed | Method added |
| `OllamaClient._resolve_model` always preferred `gemma4:e4b` | The configured fine-tune was never used; heavier model on 8 GB laptops | Configured model first, resolved once |
| `SYSTEM_PROMPT` expects a profile JSON and `[MODE:]` tag; neither was sent | Language choice (Sinhala/Tamil), name, exam date and weak areas never reached the model | Profile and mode appended in `_build_system_prompt` |

## Other fixes

- **Data safety:** `save_student` used `INSERT OR REPLACE`, which wiped `pdf_files` on every save or language toggle → real upsert. Indexed PDFs are restored after a restart.
- **Retrieval quality:** BM25 index rebuilt lazily after restart (it was lost), filtered by subject, `rank-bm25` actually installed; sources now match the fused chunks; grounding score compares the answer with chunk text, not file names; A/L subject filter fixed.
- **Robustness:** the app no longer stops when Ollama is down; non-AI views still work. Tracebacks show only with `APP_DEBUG=True`. The Ollama timeout now works (the old thread-pool timeout blocked on shutdown). Lowercase `'english'` from the DB crashed the language selector.
- **Test Me:** handles both the fine-tune's JSON quiz schema and plain text, and no longer shows the answer key to the student.
- **Paths:** database and vector-store paths resolve against the app folder, so the cwd no longer decides which database is used; real env vars now override `.env`.

## Security

- User and model text interpolated into `unsafe_allow_html` cards is escaped.
- LLM-generated Mermaid code is embedded as a JSON literal with `</` escaped (a `</script>` in model output could inject HTML).
- `enableXsrfProtection` turned on; the server binds to `localhost` because there is no authentication (anyone on the LAN could otherwise use "Reset Demo Data").
- No SQL injection found (all queries are parameterised; the only f-string SQL uses constant column lists).

## Performance (measured)

| Metric | Before | After |
|---|---|---|
| Ollama request via `localhost` vs `127.0.0.1` (Windows IPv6 fallback) | 2.7 s | 0.7 s |
| New browser session, first script run (warm server) | ~5.5 s | 0.75 s |
| Cold server first run (includes ~5.6 s chromadb import) | 15.3 s | 7.1 s |
| PDF embedding | one request per chunk | one batched `embed` call |
| Ollama health check | every rerun | cached 15 s |

Also added `student_id` indexes on `quiz_history`, `weak_concepts` and `study_sessions`.

## UI / UX

Kept the existing dark design system and Streamlit (no framework rewrite). Changes:
the sidebar collapses on phones; a fixed seal no longer covers content on small
screens; 44 px touch targets; visible focus rings; `prefers-reduced-motion` support;
banner chips wrap. The live model name replaces the hardcoded `gemma4:e4b` / 9.6 GB labels.
Deprecated `use_container_width` replaced with `width="stretch"`.

Responsive check (Playwright): no horizontal overflow at 320, 375, 390, 768, 1024, 1440 and 1920 px.

## Testing

- `omnischolar/tests/`: 50 pytest tests. The 29 existing navigation tests were moved in; new tests cover the database (migrations, upsert, streak, analytics), RAG (two PDFs per subject, idempotent re-upload, subject filtering, BM25 rebuild), quiz scoring, and every one of the 12 modes rendering with Ollama unreachable.
- Tests run on a temporary DB and vector store. Previously `test_navigation.py` wrote to the real `omnischolar.db`.
- CI moved to `.github/workflows/ci.yml` (the old workflow lived under `omnischolar/.github`, which GitHub never runs).
- Manual Playwright E2E against the real app with a copied database: two-PDF upload, Learn answer grounded in an uploaded PDF, Test Me generate → answer → score saved to SQLite, Study Plan and Weakness modes, no app console errors.

## Removed

`achievement.py` (never called), unused duplicate functions in `_new_avatar.py`,
`study_plan.py`, `weakness.py`, and unused imports.

## Remaining limitations

- **No authentication**: this is a single-user local app. A new browser session loads the most recently saved profile.
- **Lighthouse not measured**: no Lighthouse tool was available. Streamlit pages are a client-rendered SPA, so SEO scores aren't meaningful for this app.
- **Cold model load**: the first request after Ollama starts can take longer than `OLLAMA_TIMEOUT=120`. Use 300 on slow machines.
- **Upstream Streamlit console error**: `Recording error: Container not found` (wavesurfer, inside Streamlit's `ChatInput`) appears on some page reloads. It comes from Streamlit's bundle, not app code.
- **Not exercised end-to-end with a live model**: Virtual Teacher lessons, Battle Game, Teacher paper generation and the 3A prediction flows. They render without errors (`AppTest`), but their LLM paths were not driven in the browser.
- `venv/` in the workspace is broken (no pip); recreate it as described in the README.

---

# Round 2 — UI/UX redesign, speed, offline

## Speed (measured on the 8 GB dev laptop, omnischolar-e2b-v2)

| Change | Before | After |
|---|---|---|
| Gemma 4 hidden "thinking" turned off by default (`think=False`) | 6.0 s, 410 tokens per answer | 2.5 s, 62 tokens |
| Learn page, first words of an answer (in the browser) | not measured | ≤3 s (full answer ~6 s) |
| Test Me "Check answers" | second full LLM call | instant (explanations generated with the quiz) |
| Model kept in RAM (`keep_alive`) + warm-up at start-up | cold start after 5 min idle | stays loaded |
| Dashboard data | ~10 SQLite round-trips per rerun | one cached bundle (cleared on writes) |
| Schema migrations | every rerun | once per server process |

Quizzes, battle questions and tutor follow-ups use Ollama JSON-schema structured output instead of regex/fence stripping.

## UI/UX

- **Real pages** (`st.navigation`): Study / Practice / You sections with icons, a URL per page and working browser back. This replaced sidebar buttons, `st.rerun()` and a 12-branch `if/elif`.
- **Slim sidebar**: logo, nav, a profile card with an edit dialog (onboarding on first visit), an answer-language switch that now persists, and an honest model status.
  - The old header language toggle was silently reset by the sidebar selectbox.
  - Demo reset moved to Settings.
- **Home** page holds the dashboard, so Learn, Revise and Test Me no longer stack it above themselves. Hardcoded marketing badges were removed.
- **Test Me** asks one radio question per item inside a form and gives per-question explanations. Wrong answers become weak areas.
- **Learn / Revise** stream answers with `st.write_stream`, keep separate chat histories, and offer "New chat". Retrieved passages are labelled `[file page N]` so answers can cite pages.
- **Accessibility**:
  - Dim text raised from 2.35:1 to 5.9:1 contrast (WCAG AA).
  - A global `header {visibility:hidden}` rule had hidden the nav section titles and the **mobile sidebar toggle**. On phones the navigation was unreachable.
  - 44 px touch targets on mobile.
- **Responsive**: no horizontal overflow at 320, 375, 390, 768, 1024 and 1920 px (Playwright).

## Fully offline

- Fonts (DM Sans, JetBrains Mono, Fraunces, Noto Sans Sinhala and Noto Sans Tamil; OFL) are vendored in `static/fonts` and registered with `[[theme.fontFaces]]`.
- Mermaid 11.17.2 (MIT) ships as a local Streamlit component (`components/mermaid`). Streamlit's static folder serves `.js` as `text/plain`, so it can't host scripts.
  - Model-written diagrams that fail to parse are retried with labels auto-quoted. Checked in the browser: the model's real binary-search diagram and pipe-label cases render after the fix.
- Playwright saw **no requests to any non-local host**.

## Retrieval

- The default embedding model is now `embeddinggemma`, which covers 100+ languages including Sinhala and Tamil and uses its documented task prompts. `nomic-embed-text` is English-only.
- Each embedding model gets its own collection. Chunks in an existing nomic index are re-embedded automatically from stored text, so no re-upload is needed.

## Bugs fixed in round 2

- Virtual Teacher lessons never came from the model: a `num_predict` argument raised a TypeError that was swallowed, so every lesson used the fallback.
- CS Battle asked for a JSON *array* but parsed an object, so it almost always fell back to the built-in question bank.
- `str.lstrip("```json")` strips a *character set*, so it could eat the first letters of valid JSON.
- The language selection didn't stick (see UI above).

## Research recommendations not implemented (yet)

These come from the research pass, ranked by expected value:
1. **FSRS spaced-repetition review queue** (`fsrs` on PyPI, MIT) for missed questions: the strongest evidence-backed learning feature.
2. **Hint ladder enforced in code** for the Virtual Teacher. A PNAS 2025 study found an answer-giving GPT tutor lowered exam scores by 17%.
3. **Per-topic Elo mastery** used to pick question difficulty. Today it is only used for display.
4. Heading-aware chunking, and offline OCR (Tesseract) for scanned PDFs.
5. Translated UI strings and Sinhala/Tamil text-to-speech voices. Currently only the model's answers change language.

## Still not verified

- Retrieval quality in Sinhala/Tamil: there are no public benchmarks for these languages, so it should be checked with real notes.
- Battle Game, Teacher paper generation and 3A predictions with a live model in the browser. They render without errors under `AppTest`.
