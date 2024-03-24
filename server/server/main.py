from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from psycopg.rows import dict_row
from vespa.application import Vespa

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/topic")
async def read_topic(topic_id: str):
    try:
        with psycopg.connect(INTERNAL_DB_CONNECTION_STR, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT * FROM topic WHERE id = '{topic_id}';
                    """.format(
                        topic_id
                    ),
                )

                response = cur.fetchall()

                return response[0]

    except Exception as e:
        print(e)
        return {"error": str(e)}


INTERNAL_DB_CONNECTION_STR = "dbname='mydb' user='myuser' host='localhost' password='mysecretpassword' port='5432'"


@app.get("/search")
async def search_topic(query: str):

    vespa_url = "http://localhost:8080"

    # Create a Vespa client
    app = Vespa(url=vespa_url)

    try:
        res = app.query(
            body={"yql": f"select * from codex where default contains '{query}';"}
        )

        return [hit["fields"] for hit in res.hits]

    except Exception as e:
        print(e)
        return {"error": str(e)}
