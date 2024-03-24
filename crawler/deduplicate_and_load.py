# %%
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import click
from tqdm import tqdm
from crawler.types import PaperAnalysisRun, process_response
from crawler.serializers import NdjsonReader
from huggingface_hub import HfApi
import os
from pydantic import BaseModel
from vespa.application import Vespa
from vespa.io import VespaResponse
from psycopg.rows import dict_row
import psycopg
import datetime

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


class ProcessedTopicModel(TopicModel):
    resolved_topic_id: str


class ResolvedTopicModel(BaseModel):
    topic_id: str
    name: str
    type: str
    slug: str
    description: str


class TopicFindingModel(BaseModel):
    topic_id: str
    finding_id: str


class ProcessedTopicFindingModel(BaseModel):
    topic_id: str
    finding_id: str
    resolved_topic_id: str


@click.group()
def cli():
    pass


@cli.command()
def prepare():
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


@cli.command()
def resolve():
    topic_models: list[TopicModel] = []

    with NdjsonReader(
        Path("data/processed/topic_models.jsonl"), TopicModel, validate=True
    ) as f:
        for p in tqdm(f):
            topic_models.append(p)

    topics_by_id: dict[str, TopicModel] = {
        topic.topic_id: topic for topic in topic_models
    }

    def union_equivalence_classes(
        a: dict[tuple[str, ...], set[str]], b: dict[str, set[str]], max_merge_count: int
    ):
        """
        Given two dictionaries of equivalence classes, merge them together such that
        two keys are in the same equivalence class if they are in the same class in
        either dictionary. Assumes that the items of a are a superset of the items
        of b.
        """

        if len(b) == 0:
            return a

        item_to_class_a: dict[str, tuple[str, ...]] = dict()
        class_to_item_a: dict[tuple[str, ...], set[str]] = dict()

        for key in sorted(a.keys()):
            equivalence_class = a[key]
            class_to_item_a[key] = equivalence_class
            for item in sorted(equivalence_class):
                item_to_class_a[item] = key

        def merge_equivalence_classes(
            class_key_a: tuple[str, ...],
            class_key_b: tuple[str, ...],
            class_to_items: dict[tuple[str, ...], set[str]],
            item_to_class: dict[str, tuple[str, ...]],
        ):
            class_a = class_to_items[class_key_a]
            class_b = class_to_items[class_key_b]

            new_key = tuple(sorted(class_key_a + class_key_b))

            # assign all items in the merged class to the new key
            for item in sorted(class_a):
                item_to_class[item] = new_key
            for item in sorted(class_b):
                item_to_class[item] = new_key

            # merge the two classes
            class_to_items[new_key] = class_a.union(class_b)

            # delete the old classes
            del class_to_items[class_key_a]
            del class_to_items[class_key_b]

            return new_key

        for key in sorted(b.keys()):
            equivalence_class = b[key]
            if len(equivalence_class) < 2:
                continue

            # get the set of classes in the first relation that contain any of the
            # items in the equivalence class from the second relation
            a_classes = sorted(
                set([item_to_class_a[item] for item in equivalence_class])
            )

            if len(a_classes) > 1:
                first_class = a_classes.pop()

                for other_class in a_classes:
                    # prevent gigantic equivalence classes from forming with false positives
                    if len(first_class) + len(other_class) > max_merge_count:
                        continue

                    else:
                        first_class = merge_equivalence_classes(
                            first_class, other_class, class_to_item_a, item_to_class_a
                        )

        return class_to_item_a

    topic_ids_by_slug: defaultdict[tuple[str], set[str]] = defaultdict(set)
    topic_ids_by_name: defaultdict[str, set[str]] = defaultdict(set)

    for topic in topic_models:
        topic_ids_by_slug[(topic.slug,)].add(topic.topic_id)
        topic_ids_by_name[topic.name].add(topic.topic_id)

    merged_topic_ids = union_equivalence_classes(
        topic_ids_by_slug, topic_ids_by_name, max_merge_count=256
    )

    raw_to_resolved_topic_id: dict[str, str] = dict()

    with open(
        "data/processed/processed_topic_models.jsonl", "w"
    ) as processed_topic_w, open(
        "data/processed/resolved_topic_models.jsonl", "w"
    ) as resolved_topic_w:
        for value in tqdm(merged_topic_ids.values()):
            topics = [topics_by_id[topic_id] for topic_id in value]

            resolved_topic = ResolvedTopicModel(
                topic_id=f"resolved_topic:{uuid4()}",
                name=topics[0].name,
                type=topics[0].type,
                slug=topics[0].slug,
                description=topics[0].description,
            )

            resolved_topic_w.write(resolved_topic.model_dump_json())
            resolved_topic_w.write("\n")

            for topic in topics:
                processed_topic = ProcessedTopicModel(
                    topic_id=topic.topic_id,
                    name=topic.name,
                    type=topic.type,
                    slug=topic.slug,
                    description=topic.description,
                    resolved_topic_id=resolved_topic.topic_id,
                )
                raw_to_resolved_topic_id[topic.topic_id] = resolved_topic.topic_id
                processed_topic_w.write(processed_topic.model_dump_json())
                processed_topic_w.write("\n")

    with NdjsonReader(
        Path("data/processed/topic_finding_models.jsonl"), TopicFindingModel
    ) as topic_finding_r, open(
        "data/processed/processed_topic_finding_models.jsonl", "w"
    ) as processed_topic_finding_w:
        for topic_finding in tqdm(topic_finding_r):
            resolved_topic_id = raw_to_resolved_topic_id[topic_finding.topic_id]

            processed_topic_finding = ProcessedTopicFindingModel(
                topic_id=topic_finding.topic_id,
                finding_id=topic_finding.finding_id,
                resolved_topic_id=resolved_topic_id,
            )
            processed_topic_finding_w.write(processed_topic_finding.model_dump_json())
            processed_topic_finding_w.write("\n")


@cli.command()
def load_postgres():
    INTERNAL_DB_CONNECTION_STR = "dbname='mydb' user='myuser' host='localhost' password='mysecretpassword' port='5432'"
    with psycopg.connect(INTERNAL_DB_CONNECTION_STR, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            with cur.copy(
                "COPY paper (id, authors, title, update_date, abstract, created_at) FROM STDIN"
            ) as paper_copy:
                with NdjsonReader(
                    Path("data/processed/paper_models.jsonl"), PaperModel
                ) as f:
                    for line in tqdm(f):
                        paper_copy.write_row(
                            (
                                line.paper_id,
                                line.authors,
                                line.title,
                                line.update_date,
                                line.abstract.strip(),
                                datetime.datetime.now(),
                            )
                        )

            with cur.copy(
                "COPY finding (id, name, slug, description, paper_id, created_at) FROM STDIN"
            ) as finding_copy:
                with NdjsonReader(
                    Path("data/processed/finding_models.jsonl"), FindingModel
                ) as f:
                    for line in tqdm(f):
                        finding_copy.write_row(
                            (
                                line.finding_id,
                                line.name,
                                line.slug,
                                line.description,
                                line.paper_id,
                                datetime.datetime.now(),
                            )
                        )

            with cur.copy(
                "COPY resolved_topic (id, name, type, slug, description, created_at) FROM STDIN"
            ) as resolved_topic_copy:
                with NdjsonReader(
                    Path("data/processed/resolved_topic_models.jsonl"),
                    ResolvedTopicModel,
                ) as f:
                    for line in tqdm(f):
                        resolved_topic_copy.write_row(
                            (
                                line.topic_id,
                                line.name,
                                line.type,
                                line.slug,
                                line.description,
                                datetime.datetime.now(),
                            )
                        )

            with cur.copy(
                "COPY topic (id, name, type, slug, description, created_at, resolved_topic_id) FROM STDIN"
            ) as topic_copy:
                with NdjsonReader(
                    Path("data/processed/processed_topic_models.jsonl"),
                    ProcessedTopicModel,
                ) as f:
                    for line in tqdm(f):
                        topic_copy.write_row(
                            (
                                line.topic_id,
                                line.name,
                                line.type,
                                line.slug,
                                line.description,
                                datetime.datetime.now(),
                                line.resolved_topic_id,
                            )
                        )

            with cur.copy(
                "COPY topic_finding (topic_id, finding_id, resolved_topic_id) FROM STDIN"
            ) as topic_finding_copy:
                with NdjsonReader(
                    Path("data/processed/processed_topic_finding_models.jsonl"),
                    ProcessedTopicFindingModel,
                ) as f:
                    for line in tqdm(f):
                        topic_finding_copy.write_row(
                            (
                                line.topic_id,
                                line.finding_id,
                                line.resolved_topic_id,
                            )
                        )


@cli.command()
def load_vespa():
    vespa_url = "http://localhost:8080/"

    # Create a Vespa client
    app = Vespa(url=vespa_url)

    def map_fn(topic: ResolvedTopicModel):
        return {
            "id": topic.topic_id,
            "fields": {
                "id": topic.topic_id,
                "name": topic.name,
                "type": topic.type,
                "slug": topic.slug,
                "description": topic.description,
            },
        }

    def feed_iter():
        with NdjsonReader(
            Path("data/processed/resolved_topic_models.jsonl"),
            ResolvedTopicModel,
        ) as f:
            # resolved_topics = list(f)
            for topic in tqdm(f):
                yield map_fn(topic)

    def callback(response: VespaResponse, id: str):
        if not response.is_successful():
            print(
                f"Failed to feed document {id} with status code {response.status_code}: Reason {response.get_json()}"
            )

    app.feed_iterable(
        iter=feed_iter(),
        schema="codex",
        callback=callback,
        max_queue_size=8000,
        max_workers=32,
        max_connections=32,
    )


if __name__ == "__main__":
    cli()
