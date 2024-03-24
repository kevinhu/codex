import polars as pl
from pathlib import Path

from crawler.serializers import NdjsonReader
from crawler.types import PaperAnalysisRun

with NdjsonReader(
    Path("data/raw/finetune_responses.jsonl"), PaperAnalysisRun, validate=True
) as f:
    responses = list(f)

examples = []

for r in responses:
    examples.append(
        (
            r.prompt.paper.paper_id,
            r.prompt.user_text,
            r.response.to_response(),
        )
    )

dataset = pl.DataFrame(examples, schema=["paper_id", "user_text", "response"]).sort(
    by="paper_id"
)

dataset.write_parquet("data/processed/finetune_responses.parquet")
