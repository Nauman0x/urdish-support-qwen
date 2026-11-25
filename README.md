# Urdish Support Agent

A small Qwen3 model, fine-tuned to answer customers of any small Pakistani business in the script they wrote in (Roman Urdu, Urdu or English), using only the business's own policy card, and to hand off to a person when the policy does not cover the question. Runs on a CPU.

Team Pixie, Qwen Local Hackathon 2026. Work in progress: the full write-up (results, how to run it, model links) is coming.

## First held-out results (60 chats, 3 business types never seen in training, CPU only)

| Model (Q4_K_M) | Fully correct | Reply in customer's script | Speed (8 threads) |
|---|---|---|---|
| Qwen3-1.7B base | 15.0% | 51.7% | 40 tok/s |
| Qwen3-1.7B tuned (v1) | 58.3% | 91.7% | 34 tok/s |
| Qwen3-4B base | 16.7% | 61.7% | 19 tok/s |
| Qwen3-4B tuned (v1) | 60.0% | 95.0% | 16 tok/s |

Code and data: MIT. Base models: Qwen3 (Apache-2.0). Training script adapted from [finetune-anywhere](https://github.com/junaiddshaukat/finetune-anywhere) (MIT).
