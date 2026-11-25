"""QLoRA fine-tune (Unsloth) on the reply tokens only, then save adapter + merged 16-bit weights.

Adapted from finetune-anywhere's paths/nvidia-gpu/train_unsloth.py (MIT). Changes: loss on assistant
tokens only (train_on_responses_only), Qwen3 ids from this repo's config, per-epoch adapter snapshots.

python scripts/train_qlora.py --model unsloth/Qwen3-1.7B --epochs 2 --output ~/qwen-hackathon/runs/tuned-1.7b
"""

import argparse
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NON_THINKING_PREFIX = "{% set enable_thinking = false %}\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=ROOT / "recipe/config.yaml")
    p.add_argument("--model", required=True, help="HF id, e.g. unsloth/Qwen3-1.7B")
    p.add_argument("--epochs", type=float)
    p.add_argument("--lr", type=float)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    cfg = yaml.safe_load(a.config.read_text())
    if a.epochs:
        cfg["epochs"] = a.epochs
    if a.lr:
        cfg["learning_rate"] = a.lr
    data = ROOT / "recipe/data"

    from unsloth import FastLanguageModel, is_bfloat16_supported  # must precede TRL
    from unsloth.chat_templates import train_on_responses_only
    from datasets import load_dataset
    from trl import SFTConfig, SFTTrainer

    started = time.monotonic()
    model, tok = FastLanguageModel.from_pretrained(
        model_name=a.model, max_seq_length=cfg["max_seq_length"], dtype=None, load_in_4bit=True
    )
    if not tok.chat_template.startswith(NON_THINKING_PREFIX):
        tok.chat_template = NON_THINKING_PREFIX + tok.chat_template
    model = FastLanguageModel.get_peft_model(
        model, r=cfg["rank"], lora_alpha=cfg["alpha"], lora_dropout=0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=cfg["seed"],
    )
    ds = load_dataset("json", data_files={s: str(data / f"{s}.jsonl") for s in ["train", "valid"]})
    ds = ds.map(
        lambda b: {"text": [tok.apply_chat_template(m, tokenize=False, enable_thinking=False) for m in b["messages"]]},
        batched=True, remove_columns=["messages"],
    )
    trainer = SFTTrainer(
        model=model, processing_class=tok, train_dataset=ds["train"], eval_dataset=ds["valid"],
        args=SFTConfig(
            output_dir=str(a.output / "checkpoints"), dataset_text_field="text", max_length=cfg["max_seq_length"],
            per_device_train_batch_size=cfg["batch_size"], gradient_accumulation_steps=cfg["gradient_accumulation_steps"],
            learning_rate=cfg["learning_rate"], num_train_epochs=cfg["epochs"], lr_scheduler_type="cosine",
            warmup_ratio=0.05, bf16=is_bfloat16_supported(), fp16=not is_bfloat16_supported(), logging_steps=5,
            save_strategy="epoch", eval_strategy="epoch", per_device_eval_batch_size=4, seed=cfg["seed"],
            report_to="none", packing=False,
        ),
    )
    trainer = train_on_responses_only(
        trainer, instruction_part="<|im_start|>user\n", response_part="<|im_start|>assistant\n"
    )
    t0 = time.monotonic()
    result = trainer.train()
    train_s = time.monotonic() - t0
    model.save_pretrained(str(a.output / "adapter"))
    tok.save_pretrained(str(a.output / "adapter"))
    import torch

    manifest = {
        "base_model": a.model,
        "base_revision": getattr(model.config, "_commit_hash", None),
        "config": cfg,
        "loss_on": "assistant tokens only",
        "training_seconds": round(train_s, 1),
        "preparation_seconds": round(t0 - started, 1),
        "metrics": result.metrics,
        "eval_history": [h for h in trainer.state.log_history if "eval_loss" in h],
        "gpu": torch.cuda.get_device_name(0),
        "peak_vram_gb": round(torch.cuda.max_memory_reserved() / 1e9, 2),
        "versions": {n: importlib.metadata.version(n) for n in ["unsloth", "torch", "transformers", "trl", "peft"]},
        "data_sha256": {s: hashlib.sha256((data / f"{s}.jsonl").read_bytes()).hexdigest() for s in ["train", "valid"]},
    }
    (a.output / "run.json").write_text(json.dumps(manifest, indent=2) + "\n")
    model.save_pretrained_merged(str(a.output / "merged"), tok, save_method="merged_16bit")
    print("saved", a.output)


if __name__ == "__main__":
    main()
