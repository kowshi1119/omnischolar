from huggingface_hub import hf_hub_download
import os
os.makedirs("C:/Users/kowsh/Desktop/hackathon/models", exist_ok=True)
path = hf_hub_download(
    repo_id="kowshikan/omnischolar-gemma4-edu",
    filename="gemma-3-1b-it.Q4_K_M.gguf",
    local_dir="C:/Users/kowsh/Desktop/hackathon/models",
    token=os.getenv("HF_TOKEN")
)
print("Downloaded to:", path)