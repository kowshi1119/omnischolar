#!/usr/bin/env python3
"""
train/download_model.py
───────────────────────
Download a fine-tuned OmniScholar model from HuggingFace Hub.

Usage
─────
  # CLI
  python train/download_model.py --repo kowshikan/omnischolar-gemma4-edu

  # Kaggle exec() pattern (Cell 1: set token, Cell 2: run)
  import sys, os
  os.environ["HF_TOKEN"] = "hf_..."   # or use Kaggle Secrets → HF_TOKEN
  sys.argv = [
      'download_model.py',
      '--repo', 'kowshikan/omnischolar-gemma4-edu',
      '--local_dir', '/kaggle/working/omnischolar-model',
  ]
  exec(open('/kaggle/working/download_model.py').read())

Arguments
─────────
  --repo       HuggingFace repo id  (default: kowshikan/omnischolar-gemma4-edu)
  --local_dir  Destination folder   (default: ./omnischolar-model)
  --revision   Branch/tag/commit    (default: main)
  --token      HF token (overrides HF_TOKEN / HUGGINGFACE_TOKEN env vars)
  --ignore     Space-separated glob patterns to skip (e.g. "*.bin *.pt")
"""

import argparse
import os
import sys
from pathlib import Path


def _get_token(cli_token: str) -> str:
    return (
        cli_token
        or os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACE_TOKEN")
        or ""
    )


def _login(token: str) -> None:
    if not token:
        print("[download] WARNING: No HF token found. Private repos will fail.")
        return
    try:
        from huggingface_hub import login as hf_login
        hf_login(token=token, add_to_git_credential=False)
        print("[download] Logged in to HuggingFace Hub.")
    except Exception as exc:
        print(f"[download] HF login warning: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a HuggingFace model/repo to a local directory."
    )
    parser.add_argument(
        "--repo",
        default="kowshikan/omnischolar-gemma4-edu",
        help="HuggingFace repo id (default: kowshikan/omnischolar-gemma4-edu)",
    )
    parser.add_argument(
        "--local_dir",
        default="./omnischolar-model",
        help="Local destination folder (default: ./omnischolar-model)",
    )
    parser.add_argument(
        "--revision",
        default="main",
        help="Branch, tag, or commit hash (default: main)",
    )
    parser.add_argument(
        "--token",
        default="",
        help="HF token (overrides HF_TOKEN / HUGGINGFACE_TOKEN env vars)",
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        help="Glob patterns to ignore (e.g. --ignore '*.bin' '*.pt')",
    )

    args = parser.parse_args()

    token = _get_token(args.token)
    _login(token)

    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"[download] Repo     : {args.repo}")
    print(f"[download] Revision : {args.revision}")
    print(f"[download] Local dir: {local_dir.resolve()}")
    if args.ignore:
        print(f"[download] Ignoring : {args.ignore}")

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("[download] huggingface_hub not installed. Running: pip install huggingface_hub")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub", "--quiet"])
        from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=args.repo,
        local_dir=str(local_dir),
        revision=args.revision,
        token=token or None,
        ignore_patterns=args.ignore or None,
    )

    print(f"[download] Done. Model saved to: {local_dir.resolve()}")


main()
