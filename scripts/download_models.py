from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import snapshot_download
from safetensors import safe_open
from sentence_transformers import SentenceTransformer
from transformers import AutoConfig, AutoTokenizer


def main() -> None:
    print("Загрузка multilingual MiniLM…")
    embedding_path = snapshot_download(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", max_workers=1
    )
    SentenceTransformer(embedding_path, local_files_only=True)
    print("Загрузка Qwen3-0.6B…")
    qwen_path = snapshot_download("Qwen/Qwen3-0.6B", max_workers=1)
    AutoTokenizer.from_pretrained(qwen_path, local_files_only=True, trust_remote_code=False)
    config = AutoConfig.from_pretrained(qwen_path, local_files_only=True, trust_remote_code=False)
    with safe_open(f"{qwen_path}/model.safetensors", framework="pt", device="cpu") as weights:
        tensor_count = len(list(weights.keys()))
    print(f"Проверено: {config.model_type}, тензоров: {tensor_count}")
    print("Модели готовы к офлайн-работе.")


if __name__ == "__main__":
    main()
