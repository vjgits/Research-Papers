# Recoverable Behavioral Failure (RBF) Multi-Model Experiment Pack

This pack provides a small pilot benchmark and runner scaffold for measuring recoverable behavioral failure proxies across multiple LLM APIs.

## Important
This pack does not contain completed multi-model results. You must run it with your own API keys. Do not report results in a paper until the scripts have actually been run and the raw outputs are archived.

## Models supported by scaffold
- OpenAI Responses API
- Anthropic Messages API
- Google Gemini Generate Content API

## Environment variables
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY

## Example
```bash
pip install -r requirements.txt
python run_eval.py --models openai:gpt-5.5 anthropic:claude-sonnet-4-5 google:gemini-2.5-pro --tasks tasks/evaluation_tasks.jsonl --out results/raw_outputs.jsonl
python score_results.py --raw results/raw_outputs.jsonl --out results/scored_results.csv
```

Model names are placeholders and may need adjustment to currently enabled models in your accounts.
