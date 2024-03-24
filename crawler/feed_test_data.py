# %%
from vespa.application import Vespa
import psycopg
from psycopg.rows import dict_row
from pathlib import Path
from generate_data import PaperAnalysisRun

# %%
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
# %%
with open(PROCESSED_DATA_DIR / "finetune_responses.jsonl", "r") as f:
    # read first N lines
    lines = [PaperAnalysisRun.model_validate_json(next(f)) for _ in range(5)]
    print(lines)

# %%
INTERNAL_DB_CONNECTION_STR = "dbname='mydb' user='myuser' host='localhost' password='mysecretpassword' port='5432'"


def insert_pg():
    topics = [topic for line in lines for topic in line.response.all_topics()]
    try:
        with psycopg.connect(INTERNAL_DB_CONNECTION_STR, row_factory=dict_row) as conn:
            with conn.cursor() as cur:

                for topic in topics:
                    cur.execute(
                        "INSERT INTO topic (name, slug, description) VALUES (%(name)s, %(slug)s, %(description)s)",
                        topic.model_dump(),
                    )

    except Exception as e:
        print(e)
        return {"error": str(e)}


# %%
insert_pg()


# %%
vespa_url = "http://localhost:8080/"

# Create a Vespa client
app = Vespa(url=vespa_url)

# %%
for data in lines:
    response = app.feed_data_point(schema="codex", data_id=data["slug"], fields=data)
    print(response)
