from pathlib import Path

from tqdm import tqdm
from crawler.types import PaperAnalysisRun, ProcessedPaper, process_response
from crawler.serializers import NdjsonReader
from huggingface_hub import HfApi
from loguru import logger
import os
from pydantic import BaseModel

HF_API = HfApi()
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"


class PaperModel(BaseModel):
    paper_id: str
    authors: str
    title: str
    update_date: str
    abstract: str


class FindingModel(BaseModel):
    finding_id: str
    name: str
    slug: str
    description: str
    paper_id: str


class TopicModel(BaseModel):
    topic_id: str
    name: str
    type: str
    slug: str
    description: str


class TopicFindingModel(BaseModel):
    topic_id: str
    finding_id: str


paper_models: list[PaperModel] = []
finding_models: list[FindingModel] = []
topic_models: list[TopicModel] = []
topic_finding_models: list[TopicFindingModel] = []


with NdjsonReader(
    Path(
        HF_API.hf_hub_download(
            repo_id="vllg/parsed_papers",
            filename="merged.jsonl",
            repo_type="dataset",
        )
    ),
    PaperAnalysisRun,
    validate=True,
) as f:
    with (
        open("data/processed/paper_models.jsonl", "w") as paper_w,
        open("data/processed/finding_models.jsonl", "w") as finding_w,
        open("data/processed/topic_models.jsonl", "w") as topic_w,
        open("data/processed/topic_finding_models.jsonl", "w") as topic_finding_w,
    ):
        for p in tqdm(f):
            paper = p.prompt.paper

            processed = process_response(p.response)

            paper_w.write(
                PaperModel(
                    paper_id=paper.paper_id,
                    authors=paper.metadata.authors,
                    title=paper.metadata.title,
                    update_date=paper.metadata.update_date,
                    abstract=paper.metadata.abstract,
                ).model_dump_json()
            )
            paper_w.write("\n")

            for finding in processed[0]:
                finding_w.write(
                    FindingModel(
                        finding_id=finding.finding_id,
                        name=finding.name,
                        slug=finding.slug,
                        description=finding.description,
                        paper_id=paper.paper_id,
                    ).model_dump_json()
                )
                finding_w.write("\n")

            for topic in processed[1]:
                topic_w.write(
                    TopicModel(
                        topic_id=topic.topic_id,
                        name=topic.name,
                        type=topic.type,
                        slug=topic.slug,
                        description=topic.description,
                    ).model_dump_json()
                )
                topic_w.write("\n")
                for finding_id in topic.linked_finding_ids:
                    topic_finding_w.write(
                        TopicFindingModel(
                            topic_id=topic.topic_id,
                            finding_id=finding_id,
                        ).model_dump_json()
                    )
                    topic_finding_w.write("\n")
