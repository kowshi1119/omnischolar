# OmniScholar

Offline AI study companion for Sri Lankan university and A/L students: Learn, Revise,
Test Me, a Virtual Teacher, past-paper practice, study plans and weakness tracking,
grounded in your own PDF notes. Runs entirely on your machine with Streamlit, Ollama
(Gemma 4 or the OmniScholar fine-tune), ChromaDB and SQLite.

| Folder | Contents |
|---|---|
| [`omnischolar/`](omnischolar/) | The application. **Start with [omnischolar/README.md](omnischolar/README.md)** for setup, configuration, running and testing |
| [`train/`](train/) | Fine-tuning and dataset scripts for the OmniScholar Gemma 4 model |
| `data/` | Training data |
| [`docs/DEVELOPMENT_IMPROVEMENTS.md`](docs/DEVELOPMENT_IMPROVEMENTS.md) | Audit findings, fixes and known limitations |

Quick start (Windows, from the repository root):

```bash
cd omnischolar
pip install -r requirements.txt
copy .env.example .env
python -m streamlit run app.py
```
