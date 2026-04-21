#!/usr/bin/env python3
"""
train/upload_model.py
─────────────────────
Upload a local model folder to HuggingFace Hub.
Python equivalent of: hf upload <repo> <local_dir>

Usage
─────
  # CLI
  python train/upload_model.py --local_dir ./omnischolar-model

  # Kaggle exec() pattern
  import sys, os
  os.environ["HF_TOKEN"] = "hf_..."   # or use Kaggle Secrets → HF_TOKEN
  sys.argv = [
      'upload_model.py',
      '--local_dir', '/kaggle/working/omnischolar-model',
      '--repo',      'kowshikan/omnischolar-gemma4-edu',
  ]
  exec(open('/kaggle/working/upload_model.py').read())

Arguments
─────────
  --local_dir   Folder to upload          (default: ./omnischolar-model)
  --repo        HuggingFace repo id       (default: kowshikan/omnischolar-gemma4-edu)
  --repo_type   model | dataset | space   (default: model)
  --path_in_repo  Subfolder inside repo   (default: repo root)
  --revision    Branch to push to         (default: main)
  --commit_msg  Commit message            (default: Upload OmniScholar model)
  --token       HF token (overrides env vars)
  --ignore      Space-separated glob patterns to skip (e.g. "*.tmp __pycache__")
  --private     Create repo as private if it does not exist yet
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
        print("[upload] ERROR: No HF token found. Set HF_TOKEN env var or pass --token.")
        sys.exit(1)
    try:
        from huggingface_hub import login as hf_login
        hf_login(token=token, add_to_git_credential=False)
        print("[upload] Logged in to HuggingFace Hub.")
    except Exception as exc:
        print(f"[upload] HF login error: {exc}")
        sys.exit(1)


def _ensure_repo(api, repo_id: str, repo_type: str, private: bool) -> None:
    from huggingface_hub.utils import RepositoryNotFoundError
    try:
        api.repo_info(repo_id=repo_id, repo_type=repo_type)
        print(f"[upload] Repo exists: {repo_id}")
    except RepositoryNotFoundError:
        print(f"[upload] Creating repo: {repo_id} (private={private})")
        api.create_repo(repo_id=repo_id, repo_type=repo_type, private=private, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload a local folder to HuggingFace Hub."
    )
    parser.add_argument(
        "--local_dir",
        default="./omnischolar-model",
        help="Local folder to upload (default: ./omnischolar-model)",
    )
    parser.add_argument(
        "--repo",
        default="kowshikan/omnischolar-gemma4-edu",
        help="HuggingFace repo id (default: kowshikan/omnischolar-gemma4-edu)",
    )
    parser.add_argument(
        "--repo_type",
        default="model",
        choices=["model", "dataset", "space"],
        help="Repo type (default: model)",
    )
    parser.add_argument(
        "--path_in_repo",
        default="",
        help="Subfolder inside the repo to upload to (default: repo root)",
    )
    parser.add_argument(
        "--revision",
        default="main",
        help="Branch to push to (default: main)",
    )
    parser.add_argument(
        "--commit_msg",
        default="Upload OmniScholar model",
        help="Commit message",
    )
    parser.add_argument(
        "--token",
        default="",
        help="HF token (overrides HF_TOKEN / HUGGINGFACE_TOKEN env vars)",
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=["*.tmp", "__pycache__", ".DS_Store"],
        help="Glob patterns to ignore",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create repo as private if it does not exist yet",
    )

    args = parser.parse_args()

    local_dir = Path(args.local_dir)
    if not local_dir.exists():
        print(f"[upload] ERROR: local_dir does not exist: {local_dir.resolve()}")
        sys.exit(1)

    token = _get_token(args.token)
    _login(token)

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[upload] huggingface_hub not installed. Running: pip install huggingface_hub")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub", "--quiet"])
        from huggingface_hub import HfApi

    api = HfApi()
    _ensure_repo(api, args.repo, args.repo_type, args.private)

    print(f"[upload] Local dir  : {local_dir.resolve()}")
    print(f"[upload] Repo       : {args.repo}")
    print(f"[upload] Repo type  : {args.repo_type}")
    print(f"[upload] Branch     : {args.revision}")
    print(f"[upload] Ignoring   : {args.ignore}")
    print("[upload] Uploading...")

    url = api.upload_folder(
        folder_path=str(local_dir),
        repo_id=args.repo,
        repo_type=args.repo_type,
        path_in_repo=args.path_in_repo or None,
        revision=args.revision,
        commit_message=args.commit_msg,
        ignore_patterns=args.ignore or None,
        token=token,
    )

    print(f"[upload] Done. View at: {url}")


main()
