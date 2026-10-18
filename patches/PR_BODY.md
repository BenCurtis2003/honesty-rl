## Problem

Training `Qwen/Qwen3.5-4B` (and other small Qwen3.5 checkpoints with `tie_word_embeddings: true`) learns nothing: from step 1 the trainer logs **entropy = 12.4225 = ln(vocab_size)**, **grad norm 0.0000**, and **mismatch KL ≈ 11**, every step.

Those checkpoints ship no `lm_head.weight`. `load_dcp` pops `lm_head.weight` from the state dict when `tie_word_embeddings` is set, on the assumption that the model ties it. `Qwen3_5ForCausalLM` builds a separate `VanillaOutputLinear` and never ties it, so the head stays at its meta-device init (zeros). The result is uniform logits and zero gradients through the head.

## Fix

When `config.tie_word_embeddings` is set, share the input embedding's weight with `lm_head` at construction. `inject_prime_lm_head` already carries `old_lm_head.weight` over to the injected head, so the tie survives injection, and `shard_norm_and_lm_head` already skips separate sharding for tied models.

## Verification

- New unit test `test_tied_word_embeddings_share_lm_head` (text and VLM configs, meta device): passes with the fix, fails on `main`.
- In a LoRA RL run on Qwen3.5-4B, 2× A6000: before, entropy 12.42, mismatch KL 11.3, grad norm 0. After, entropy 0.08, mismatch KL 0.0001, grad norm 0.007, and the run trains normally.
