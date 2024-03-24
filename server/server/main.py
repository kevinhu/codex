from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from psycopg.rows import dict_row
from vespa.application import Vespa
import ssl
import os

app = FastAPI()

# if os.environ["FASTAPI_ENV"] == "production":
#     ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
#     ssl_context.load_cert_chain('/code/server/cert.pem', keyfile='/code/server/key.pem')

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
                    """
                )

                response = cur.fetchall()

                topic = response[0]

                cur.execute(
                    f"""
                    SELECT f.*
                    FROM finding f
                    JOIN topic_finding tf ON f.id = tf.finding_id
                    WHERE tf.topic_id = '{topic_id}';
                    """
                )

                findings = cur.fetchall()

                return {**topic, "findings": findings}

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
