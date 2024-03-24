# %%
from multiprocessing.pool import ThreadPool
import os
import re
import traceback
from typing import Self
import click
from crawler.types import ProcessedPaper
from loguru import logger
from pydantic import BaseModel
import httpx
import dotenv
import polars as pl
from crawler.serializers import NdjsonReader
from pathlib import Path
import random
from tqdm import tqdm

dotenv.load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


class PaperAnalysisPrompt(BaseModel):
    paper: ProcessedPaper

    def compile_prompt(self):
        system_text = """\
Your task is to index machine learning research papers for a knowledge base. Given Markdown text of a research paper, your goal is to extract all relevant information and return it in a structured format.

Read the following instructions and return your response as a JSON object of type `Response` inside a Markdown code block.

```ts
type Response = {
    // Extract all findings, results, and insights from the paper. Remember, assume a relatively basic level of background knowledge, so be thorough in picking up information. Required.
    findings: Finding[];
    // List all tasks discussed in the paper. Required.
    tasks: Task[];
    // List all benchmarks discussed in the paper. Required.
    benchmarks: Benchmark[];
    // List all architectures discussed in the paper. Required.
    architectures: Architecture[];
    // List all models discussed in the paper. Required.
    models: Model[];
    // List all methods discussed in the paper. Required.
    methods: Method[];
    // List all datasets discussed in the paper. Required.
    datasets: Dataset[];
};

// List all informative findings from the paper because the original will be discarded later. Required.
// Every finding must be named to at least one topic later. Make sure you mention these topics by name so the connections are apparent.
type Finding = {
    // Unique identifier for the Finding. Use only lowercase alphanumeric characters and underscores. Required.
    slug: string;
    // Short name for the finding that could be used to retrieve it in a search engine. Required.
    name: string;
    // A clear, accessible, and impartial summary of the finding. Use at most five sentences. The description should make sense when read alone. Required.
    description: string;
};

// A topic is a concept or idea that is discussed in the paper and linked to findings. Do not merge similar topics into one.
type BaseTopic = {
    // Unique identifier for the Topic. Use only lowercase alphanumeric characters and underscores. Required.
    slug: string;
    // Short name for the topic that could be used to retrieve it in a search engine. Required.
    name: string;
    // A clear, accessible, and impartial summary of the topic. Use at most five sentences. The description should make sense when read out of context. Required.
    description: string;
    // Findings related to the topic. Reference these by their slugs. Must not be empty. Required.
    linked_findings: string[];
};

// A task is a specific problem class. For example, "sentiment analysis" is a task. Other tasks may include "named entity recognition" or "GPU utilization". Do not merge similar tasks into one.
// Each task must be linked to at least one finding.
type Task = BaseTopic & {
    type: "task";
};

// A benchmark is a standardized evaluation suite that evaluates the performance of a model on a specific task. Only create benchmarks if the name and description are clear. Do not count metrics such as BLEU as benchmarks. Do not merge similar benchmarks into one.
// Each benchmark must be linked to at least one finding.
type Benchmark = BaseTopic & {
    type: "benchmark";
};

// An architecture is a specific type of model. For example, "LSTM" is an architecture. Do not merge similar architectures into one.
// Each architecture must be linked to at least one finding.
type Architecture = BaseTopic & {
    type: "architecture";
};

// A specific instance of a model listed in the paper. For example, "BERT" is a model. General architectures like "transformer" should not be listed as models. Do not merge similar models into one.
// Each model must be linked to at least one finding.
type Model = BaseTopic & {
    type: "model";
};

// A method is a technique or algorithm. Metrics should be counted as Methods instead of Benchmarks. For example, a "convolutional neural network" is a type of method. Do not merge similar methods into one.
// Each method must be linked to at least one finding.
type Method = BaseTopic & {
    type: "method";
};

// A dataset is a collection of data used to train or evaluate a model. For example, "MNIST" is a dataset.
// Each dataset must be linked to at least one finding. Only create datasets if the name and description are clear. Do not merge similar datasets into one.
type Dataset = BaseTopic & {
    type: "dataset";
};
```
"""

        return system_text + self.user_text

    @property
    def user_text(self):
        paper_text = ""

        current_section = None

        for paragraph in self.paper.inlined_texts:
            # paper_text += paragraph.text + "\n"
            if paragraph.section and paragraph.section.strip() != current_section:
                paper_text += f"## {paragraph.section.strip()}\n"
                current_section = paragraph.section.strip()

            paper_text += paragraph.text.strip() + "\n"

        user_text = f"""\
```markdown
# {self.paper.metadata.title.strip()}

## Abstract
{self.paper.abstract.text.strip()}

{paper_text}
```

When extracting information, assume a relatively basic level of background knowledge. Your response should be concise and informative, focusing on the key aspects of the paper. Keep your JSON concise by omitting missing properties instead of explicitly setting them to `null`, `undefined`, or an empty string/array. Do not indent your JSON response.
"""
        return user_text


class Finding(BaseModel):
    slug: str
    name: str
    description: str


class Topic(BaseModel):
    slug: str
    name: str
    description: str
    linked_findings: list[str]


class Task(Topic):
    type: str = "task"


class Benchmark(Topic):
    type: str = "benchmark"


class Architecture(Topic):
    type: str = "architecture"


class Model(Topic):
    type: str = "model"


class Method(Topic):
    type: str = "method"


class Dataset(Topic):
    type: str = "dataset"


class PaperAnalysisResponse(BaseModel):
    findings: list[Finding]

    tasks: list[Task]
    benchmarks: list[Benchmark]
    architectures: list[Architecture]
    models: list[Model]
    methods: list[Method]
    datasets: list[Dataset]

    @classmethod
    def from_response(cls, text: str) -> Self:
        parsed_text: str

        match = re.search(r"```[^\n]*\n(.*?)```", text, flags=re.DOTALL)
        if match:
            parsed_text = match.group(1).strip()
        else:
            parsed_text = text.strip()

        structured = cls.model_validate_json(parsed_text)
        return structured

    def to_response(self) -> str:
        return self.model_dump_json(exclude_none=True, by_alias=False)


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


class PaperAnalysisRun(BaseModel):
    prompt: PaperAnalysisPrompt
    response: PaperAnalysisResponse


def run_prompt(prompt: PaperAnalysisPrompt):
    prompt_str = prompt.compile_prompt()
    try:
        completion = get_completion(prompt_str)
        response = PaperAnalysisResponse.from_response(completion)
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
