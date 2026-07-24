from __future__ import annotations

import argparse
import json
import os
import random
import statistics
from pathlib import Path


def load_rows(path: Path, limit: int | None) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    random.Random(42).shuffle(rows)
    return rows[:limit] if limit else rows


def main() -> None:
    parser = argparse.ArgumentParser(description="LoRA SFT для Qwen3-0.6B")
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--data", type=Path, default=Path("training/data/train.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/adapter"))
    parser.add_argument("--profile", choices=("cpu-mvp", "gpu"), default="cpu-mvp")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--offline", action="store_true", help="Использовать только локальный кеш Hugging Face")
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer

    use_cuda = args.profile == "gpu" and torch.cuda.is_available()
    if args.profile == "gpu" and not use_cuda:
        raise SystemExit("GPU-профиль выбран, но CUDA недоступна. В Colab включите среду выполнения с GPU.")
    device = torch.device("cuda" if use_cuda else "cpu")
    dtype = (
        torch.bfloat16
        if use_cuda and torch.cuda.is_bf16_supported()
        else torch.float16
        if use_cuda
        else torch.float32
    )
    default_limit = None if use_cuda else 32
    rows = load_rows(args.data, args.max_samples if args.max_samples is not None else default_limit)
    if not rows:
        raise SystemExit("Датасет пуст. Сначала запустите training/build_dataset.py")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if use_cuda:
        torch.cuda.manual_seed_all(args.seed)

    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        local_files_only=args.offline,
        trust_remote_code=False,
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=dtype,
        low_cpu_mem_usage=True,
        local_files_only=args.offline,
        trust_remote_code=False,
    )
    model.config.use_cache = False
    if use_cuda:
        model.gradient_checkpointing_enable()
    config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, config).to(device)
    model.print_trainable_parameters()
    trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)

    class ChatDataset(Dataset):
        def __len__(self): return len(rows)
        def __getitem__(self, index):
            messages = rows[index]["messages"]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False, enable_thinking=False
            )
            prompt = tokenizer.apply_chat_template(
                messages[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
            # CPU training uses batch_size=1, so padding every example to the
            # global maximum only wastes compute. Keep each batch at its real
            # token length while retaining max_length as a truncation guard.
            encoded = tokenizer(text, truncation=True, max_length=args.max_length, return_tensors="pt")
            prompt_ids = tokenizer(
                prompt,
                truncation=True,
                max_length=args.max_length,
                return_tensors="pt",
            )["input_ids"].squeeze(0)
            input_ids = encoded["input_ids"].squeeze(0)
            mask = encoded["attention_mask"].squeeze(0)
            labels = input_ids.clone()
            labels[: min(len(prompt_ids), len(labels))] = -100
            labels[mask == 0] = -100
            if torch.all(labels == -100):
                raise ValueError(f"Ответ не помещается в max_length={args.max_length}; увеличьте лимит.")
            return {"input_ids": input_ids, "attention_mask": mask, "labels": labels}

    generator = torch.Generator().manual_seed(args.seed)
    loader = DataLoader(ChatDataset(), batch_size=1, shuffle=True, generator=generator)
    grad_accum = 8 if use_cuda else 4
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=2e-4)
    model.train(); optimizer.zero_grad(set_to_none=True)
    step = 0
    losses: list[float] = []
    for epoch in range(args.epochs):
        for batch_idx, batch in enumerate(loader, 1):
            batch = {key: value.to(device) for key, value in batch.items()}
            loss = model(**batch).loss / grad_accum
            loss.backward()
            losses.append(loss.item() * grad_accum)
            if batch_idx % grad_accum == 0 or batch_idx == len(loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step(); optimizer.zero_grad(set_to_none=True); step += 1
                print(f"epoch={epoch + 1} step={step} loss={losses[-1]:.4f}", flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output, safe_serialization=True)
    tokenizer.save_pretrained(args.output)
    (args.output / "training_metadata.json").write_text(
        json.dumps(
            {
                "base_model": args.model,
                "profile": args.profile,
                "samples": len(rows),
                "epochs": args.epochs,
                "optimizer_steps": step,
                "max_length": args.max_length,
                "seed": args.seed,
                "dtype": str(dtype),
                "trainable_parameters": trainable_parameters,
                "mean_training_loss": round(statistics.fmean(losses), 6),
                "final_training_loss": round(losses[-1], 6),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"LoRA-адаптер сохранён: {args.output.resolve()}")


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
