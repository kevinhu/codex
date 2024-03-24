# %%
from vespa.application import Vespa
import psycopg
from psycopg.rows import dict_row
from pathlib import Path
from generate_data import PaperAnalysisRun
from crawler.types import process_response

# %%
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
# %%
with open(PROCESSED_DATA_DIR / "finetune_responses.jsonl", "r") as f:
    # read first N lines
    lines = [PaperAnalysisRun.model_validate_json(next(f)) for _ in range(5)]

# %%
INTERNAL_DB_CONNECTION_STR = "dbname='mydb' user='myuser' host='localhost' password='mysecretpassword' port='5432'"


def insert_pg():
    topics = []

    try:
        with psycopg.connect(INTERNAL_DB_CONNECTION_STR, row_factory=dict_row) as conn:
            with conn.cursor() as cur:

                for line in lines:
                    processed = process_response(line.response)

                    for finding in processed[0]:
                        cur.execute(
                            "INSERT INTO finding (id, name, slug, description) VALUES (%(finding_id)s, %(name)s, %(slug)s, %(description)s)",
                            finding.model_dump(),
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

                    topics.extend(processed[1])

                return topics

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
for topic in processed_topics:
    topic_dict = topic.model_dump()
    response = app.feed_data_point(
        schema="codex",
        data_id=topic_dict["slug"],
        fields={
            "id": topic_dict["topic_id"],
            "name": topic_dict["name"],
            "slug": topic_dict["slug"],
            "description": topic_dict["description"],
        },
    )

# %%
