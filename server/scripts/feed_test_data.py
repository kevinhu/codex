# %%
from vespa.application import Vespa
import psycopg
from psycopg.rows import dict_row

# %%
url = "http://localhost:8080/"

# Create a Vespa client
app = Vespa(url=url)

# %%
test_data = [{"name": "Testing", "slug": "test_slug", "description": "This is a test"}]

# %%
INTERNAL_DB_CONNECTION_STR = "dbname='mydb' user='myuser' host='localhost' password='mysecretpassword' port='5432'"


def insert_pg():
    try:
        with psycopg.connect(INTERNAL_DB_CONNECTION_STR, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""""")

                response = cur.fetchall()

                return response

    except Exception as e:
        print(e)
        return {"error": str(e)}


# %%
for data in test_data:
    response = app.feed_data_point(schema="codex", data_id=data["slug"], fields=data)
    print(response)
