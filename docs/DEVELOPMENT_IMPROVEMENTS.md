# Development improvements — October 2026

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
- **Not fully offline yet**: Google Fonts and the Mermaid library still load from CDNs. They degrade gracefully without internet but should be vendored for true offline use.
- **Weak concepts aren't recorded by Test Me**: wrong answers aren't written to `weak_concepts` yet; that data comes from other modes and the seed data.
- **Cold model load**: the first request after Ollama starts can take longer than `OLLAMA_TIMEOUT=120`. Use 300 on slow machines.
- **Upstream Streamlit console error**: `Recording error: Container not found` (wavesurfer, inside Streamlit's `ChatInput`) appears on some page reloads. It comes from Streamlit's bundle, not app code.
- **Not exercised end-to-end with a live model**: Virtual Teacher lessons, Battle Game, Teacher paper generation and the 3A prediction flows. They render without errors (`AppTest`), but their LLM paths were not driven in the browser.
- `venv/` in the workspace is broken (no pip); recreate it as described in the README.
