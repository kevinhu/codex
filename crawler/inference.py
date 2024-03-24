import multiprocessing
from pathlib import Path
from tqdm import tqdm
import random
import os
from huggingface_hub import HfApi
from transformers import AutoTokenizer

from crawler.types import (
    PaperAnalysisPrompt,
    PaperAnalysisResponse,
    PaperAnalysisRun,
    ProcessedPaper,
    process_response,
)
from crawler.serializers import NdjsonReader
from loguru import logger

HF_API = HfApi()
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"


CHUNK_SIZE = 250


def process_chunk(worker_idx: int, prompts: list[PaperAnalysisPrompt]):
    from vllm import LLM, SamplingParams

    os.environ["CUDA_VISIBLE_DEVICES"] = str(worker_idx)

    tokenizer = AutoTokenizer.from_pretrained("khu/paper_analyzer")

    llm = LLM(
        model="khu/paper_analyzer",
        gpu_memory_utilization=0.95,
        max_num_batched_tokens=8192 * 4,
        block_size=16,
        max_num_seqs=CHUNK_SIZE,
        seed=random.randint(0, 2**32 - 1),
    )

    sampling_params = SamplingParams(
        temperature=0.1,
        top_p=0.95,
        max_tokens=4096,
    )

    chunks = [prompts[i : i + CHUNK_SIZE] for i in range(0, len(prompts), CHUNK_SIZE)]

    with open(Path("data/processed/parsed_papers") / f"{worker_idx}.jsonl", "w") as f:
        for chunk in chunks:
            chunk = sorted(chunk, key=lambda x: len(x.compile_prompt()))
            instructions = [input.compile_prompt() for input in chunk]

            templated_instructions: list[str] = [  # type: ignore
                tokenizer.apply_chat_template(
                    [
                        {
                            "role": "user",
                            "content": instruction,
                        },
                    ],
                    tokenize=False,
                    add_generation_prompt=True,
                )
                for instruction in instructions
            ]

            outputs = llm.generate(templated_instructions, sampling_params)

            for input, output in zip(chunk, outputs):
                try:
                    parsed_response = PaperAnalysisResponse.model_validate_json(
                        output.outputs[0].text
                    )
                    process_response(parsed_response)

                    run = PaperAnalysisRun(prompt=input, response=parsed_response)

                    f.write(run.model_dump_json())
                    f.write("\n")

                except Exception as e:
                    logger.error(e)
                    continue


if __name__ == "__main__":
    import torch

    prompts = []

    with NdjsonReader(
        Path(
            HF_API.hf_hub_download(
                repo_id="khu/arxiv_markdown",
                filename="cs_inlined_papers.jsonl",
                repo_type="dataset",
            )
        ),
        ProcessedPaper,
        validate=True,
    ) as f:
        for p in tqdm(f):
            prompt = PaperAnalysisPrompt(paper=p)

            prompts.append(prompt)

    ctx = multiprocessing.get_context("spawn")

    num_workers = torch.cuda.device_count()

    worker_chunks = [
        prompts[i : i + len(prompts) // num_workers]
        for i in range(0, len(prompts), len(prompts) // num_workers)
    ]

    with ctx.Pool(num_workers) as pool:
        pool.starmap(process_chunk, enumerate(worker_chunks))
