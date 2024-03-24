# %%
from multiprocessing.pool import ThreadPool
import os
import traceback
import click
from crawler.types import (
    PaperAnalysisPrompt,
    PaperAnalysisResponse,
    PaperAnalysisRun,
    ProcessedPaper,
    process_response,
)
from loguru import logger
import httpx
import dotenv
from crawler.serializers import NdjsonReader
from pathlib import Path
import random
from tqdm import tqdm

dotenv.load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


def get_completion(prompt):
    res = httpx.post(
        "https://api.mistral.ai/v1/chat/completions",
        json={
            "model": "mistral-large-latest",
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.1,
            "top_p": 1,
            "max_tokens": 8192,
            "stream": False,
            "safe_prompt": False,
            "random_seed": 1337,
        },
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )
    
    if res.status_code != 200:
        logger.error(f"Failed to get completion: {res.text}")
        return None

    json = res.json()

    return json["choices"][0]["message"]["content"]


@click.group()
def cli():
    pass


@cli.command()
def prepare():
    sample_rate = 0.02

    prompts: list[PaperAnalysisPrompt] = []

    with NdjsonReader(
        Path("data/processed/cs_inlined_papers.jsonl"), ProcessedPaper, validate=True
    ) as f:
        for p in tqdm(f):
            if random.random() < sample_rate:
                prompt = PaperAnalysisPrompt(paper=p)
                prompts.append(prompt)

    with open("data/raw/finetune_prompts.jsonl", "w") as f:
        for prompt in prompts:
            f.write(prompt.model_dump_json())
            f.write("\n")


def run_prompt(prompt: PaperAnalysisPrompt):
    prompt_str = prompt.compile_prompt()
    try:
        completion = get_completion(prompt_str)
        response = PaperAnalysisResponse.from_response(completion)
        process_response(response)
    except Exception:
        print(traceback.format_exc())
        return None

    return PaperAnalysisRun(prompt=prompt, response=response)


@cli.command()
def execute():
    prompts: list[PaperAnalysisPrompt] = []
    with NdjsonReader(
        Path("data/raw/finetune_prompts.jsonl"), PaperAnalysisPrompt, validate=True
    ) as f:
        for prompt in f:
            prompts.append(prompt)

    num_failed = 0

    with open("data/raw/finetune_responses.jsonl", "w") as f:
        with ThreadPool(32) as pool:
            for response in tqdm(pool.imap_unordered(run_prompt, prompts)):
                if response is None:
                    num_failed += 1
                    logger.warning("Error processing prompt")
                    continue
                f.write(response.model_dump_json())
                f.write("\n")

    logger.info(f"Failed to process {num_failed} prompts")


if __name__ == "__main__":
    cli()
