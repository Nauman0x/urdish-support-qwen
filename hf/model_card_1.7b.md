---
license: apache-2.0
base_model: Qwen/Qwen3-1.7B
language: [ur, en]
tags: [qwen3, gguf, customer-support, urdu, roman-urdu, qlora, unsloth, llama.cpp]
---

# Urdish Support Agent: Qwen3-1.7B

Qwen3-1.7B fine-tuned (QLoRA, Unsloth) to answer customers of any small Pakistani business in the script they wrote in (Roman Urdu, Urdu or English), using only the business's policy card, and to hand off to a person when the policy does not cover the question. Runs on a CPU.

Team Pixie, Qwen Local Hackathon 2026. Code, data, evaluation and full write-up: https://github.com/Nauman0x/urdish-support-qwen

Files: `urdish-v2-1.7b-q4_k_m.gguf` (recommended, 1.1 GB), `urdish-v2-1.7b-q8_0.gguf`, `merged/` (16-bit weights). The full model card with results follows.
