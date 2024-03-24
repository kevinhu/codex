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
topics = [topic for line in lines for topic in line.response.all_topics()]


# %%
INTERNAL_DB_CONNECTION_STR = "dbname='mydb' user='myuser' host='localhost' password='mysecretpassword' port='5432'"


# This is not great but it's just to get some data into the db
def insert_pg():
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
for topic in topics:
    topic_dict = topic.model_dump()
    # Using slugs until we have ids
    response = app.feed_data_point(
        schema="codex",
        data_id=topic_dict["slug"],
        fields={
            "name": topic_dict["name"],
            "slug": topic_dict["slug"],
            "description": topic_dict["description"],
        },
    )

# %%
