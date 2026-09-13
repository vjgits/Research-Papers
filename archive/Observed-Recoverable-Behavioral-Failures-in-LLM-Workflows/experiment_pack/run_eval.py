#!/usr/bin/env python3
"""Run RBF pilot tasks against OpenAI, Anthropic, and Gemini APIs.

Usage:
  python run_eval.py --models openai:gpt-5.5 anthropic:claude-sonnet-4-5 google:gemini-2.5-pro \
    --tasks tasks/evaluation_tasks.jsonl --out results/raw_outputs.jsonl
"""
import argparse, json, os, time, traceback
from pathlib import Path


def load_tasks(path):
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line:
                yield json.loads(line)


def call_openai(model, prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    resp = client.responses.create(model=model, input=prompt, temperature=0)
    return getattr(resp, 'output_text', str(resp))


def call_anthropic(model, prompt):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    msg = client.messages.create(
        model=model,
        max_tokens=800,
        temperature=0,
        messages=[{"role":"user","content":prompt}],
    )
    return "\n".join(block.text for block in msg.content if getattr(block, 'type', None) == 'text')


def call_google(model, prompt):
    from google import genai
    client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
    resp = client.models.generate_content(model=model, contents=prompt)
    return getattr(resp, 'text', str(resp))


def call_model(model_spec, prompt):
    provider, model = model_spec.split(':', 1)
    if provider == 'openai':
        return call_openai(model, prompt)
    if provider == 'anthropic':
        return call_anthropic(model, prompt)
    if provider in ('google', 'gemini'):
        return call_google(model, prompt)
    raise ValueError(f'Unknown provider in {model_spec}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', nargs='+', required=True, help='provider:model specs, e.g. openai:gpt-5.5')
    ap.add_argument('--tasks', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sleep', type=float, default=0.25)
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    tasks = list(load_tasks(args.tasks))
    with open(args.out, 'a', encoding='utf-8') as out:
        for model_spec in args.models:
            for task in tasks:
                rec = {"model_spec": model_spec, "task_id": task['id'], "category": task['category'], "prompt": task['prompt']}
                start = time.time()
                try:
                    rec['output'] = call_model(model_spec, task['prompt'])
                    rec['ok'] = True
                except Exception as e:
                    rec['ok'] = False
                    rec['error'] = repr(e)
                    rec['traceback'] = traceback.format_exc()[-2000:]
                rec['latency_sec'] = round(time.time() - start, 3)
                out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                out.flush()
                time.sleep(args.sleep)

if __name__ == '__main__':
    main()
