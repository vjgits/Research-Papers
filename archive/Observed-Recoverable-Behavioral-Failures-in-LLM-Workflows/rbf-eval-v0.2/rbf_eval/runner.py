import json, click
from pathlib import Path
from .schemas import Task
from .scorer import score_file
from .analysis import summarize_csv

def load_tasks(path):
    with open(path, encoding='utf-8') as f:
        return [Task.model_validate_json(line) for line in f if line.strip()]

def mock_response(task: Task, condition: str):
    # Deterministic mock used for smoke tests. Real provider adapters can be added here.
    return f"Mock response for {task.id} under {condition}. Verification performed."

@click.group()
def cli(): pass

@cli.command('run')
@click.option('--tasks', required=True)
@click.option('--models', multiple=True, required=True)
@click.option('--conditions', multiple=True, default=['first_pass'])
@click.option('--out', required=True)
def run_cmd(tasks, models, conditions, out):
    ts=load_tasks(tasks)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out,'w',encoding='utf-8') as f:
        for model in models:
            for t in ts:
                for cond in conditions:
                    output=mock_response(t, cond)
                    rec={'task_id':t.id,'model':model,'condition':cond,'output':output}
                    f.write(json.dumps(rec, ensure_ascii=False)+'
')
    click.echo(f'Wrote {out}')

@cli.command('score')
@click.option('--tasks', required=True)
@click.option('--raw', required=True)
@click.option('--out', required=True)
def score_cmd(tasks, raw, out):
    score_file(tasks, raw, out); click.echo(f'Wrote {out}')

@cli.command('summarize')
@click.option('--scores', required=True)
@click.option('--out', required=True)
def summarize_cmd(scores, out):
    summarize_csv(scores, out); click.echo(f'Wrote {out}')

if __name__ == '__main__': cli()
