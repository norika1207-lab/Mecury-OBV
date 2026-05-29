#!/usr/bin/env bash
set -euo pipefail

ssh -n lucky@100.73.113.61 'rm -f /Users/lucky/hf_models/gemma-2-2b-it/model-00001-of-00002.safetensors /Users/lucky/hf_models/gemma-2-2b-it/model-00002-of-00002.safetensors; mkdir -p /Users/lucky/hf_models/gemma-2-2b-it'
ssh -n ai@100.94.130.85 'cd /home/ai/hf_models/gemma-2-2b-it && tar -cf - config.json generation_config.json model-00001-of-00002.safetensors model-00002-of-00002.safetensors model.safetensors.index.json special_tokens_map.json tokenizer.json tokenizer.model tokenizer_config.json' |
  ssh lucky@100.73.113.61 'cd /Users/lucky/hf_models/gemma-2-2b-it && tar -xf - && du -sh . && ls -lh'
