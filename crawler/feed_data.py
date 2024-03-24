# %%
from vespa.application import Vespa
import psycopg
from psycopg.rows import dict_row
from pathlib import Path
from generate_data import PaperAnalysisRun
from tqdm import tqdm
from crawler.types import process_response
from vespa.io import VespaResponse

# %%
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
# %%
# RESPONSES = PROCESSED_DATA_DIR / "finetune_responses.jsonl"
RESPONSES = PROCESSED_DATA_DIR / "merged.jsonl"

# %%
# with open(RESPONSES, "r") as f:
#     total_lines = sum(1 for line in f)

total_lines = 53389

# %%

with open(RESPONSES, "r") as f:
    lines = []
    for line in tqdm(f, total=total_lines, desc="Processing"):
        processed_line = PaperAnalysisRun.model_validate_json(line)
        lines.append(processed_line)

# %%
INTERNAL_DB_CONNECTION_STR = "dbname='mydb' user='myuser' host='localhost' password='mysecretpassword' port='5432'"


def insert_pg():
    try:
        with psycopg.connect(INTERNAL_DB_CONNECTION_STR, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                processed_topics = []

                for line in tqdm(lines, desc="Inserting Records"):
                    processed = process_response(line.response)

                    paper = line.prompt.paper

                    db_paper = {
                        "paper_id": paper.paper_id,
                        "authors": paper.metadata.authors,
                        "title": paper.metadata.title,
                        "update_date": paper.metadata.update_date,
                        "abstract": paper.metadata.abstract,
                    }

                    cur.execute(
                        "INSERT INTO paper (id, authors, title, update_date, abstract) VALUES (%(paper_id)s, %(authors)s, %(title)s, %(update_date)s, %(abstract)s)",
                        db_paper,
                    )

                    for finding in processed[0]:
                        cur.execute(
                            "INSERT INTO finding (id, name, slug, description, paper_id) VALUES (%(finding_id)s, %(name)s, %(slug)s, %(description)s, %(paper_id)s)",
                            {**finding.model_dump(), "paper_id": paper.paper_id},
                        )

                    for topic in processed[1]:
                        topic_dict = topic.model_dump()
                        cur.execute(
                            "INSERT INTO topic (id, name, type, slug, description) VALUES (%(topic_id)s, %(name)s, %(type)s, %(slug)s, %(description)s)",
                            topic_dict,
                        )

                        for finding_id in topic_dict["linked_finding_ids"]:
                            topic_finding_dict = {
                                "topic_id": topic.topic_id,
                                "finding_id": finding_id,
                            }
                            cur.execute(
                                "INSERT INTO topic_finding (topic_id, finding_id) VALUES (%(topic_id)s, %(finding_id)s)",
                                topic_finding_dict,
                            )

                    processed_topics.extend(processed[1])

                return processed_topics

    except Exception as e:
        print(e)
        return []


# %%
processed_topics = insert_pg()


# %%
vespa_url = "http://localhost:8080/"

# Create a Vespa client
app = Vespa(url=vespa_url)


# %%
def map_fn(topic):
    topic_dict = topic.model_dump()
    return {
        "id": topic_dict["topic_id"],
        "fields": {
            "id": topic_dict["topic_id"],
            "name": topic_dict["name"],
            "type": topic_dict["type"],
            "slug": topic_dict["slug"],
            "description": topic_dict["description"],
        },
    }


pyvespa_feed_format = [map_fn(topic) for topic in processed_topics]


# %%


def callback(response: VespaResponse, id: str):
    if not response.is_successful():
        print(
            f"Failed to feed document {id} with status code {response.status_code}: Reason {response.get_json()}"
        )


# Wrap the iterable with tqdm for progress tracking
tqdm_iterable = tqdm(pyvespa_feed_format, desc="Feeding Data to Vespa")

# %%

app.feed_iterable(
    iter=tqdm_iterable,
    schema="codex",
    callback=callback,
    max_queue_size=4000,
    max_workers=16,
    max_connections=16,
)
# %%
