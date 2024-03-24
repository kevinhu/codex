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
                    SELECT * FROM resolved_topic WHERE id = '{topic_id}';
                    """
                )

                response = cur.fetchall()

                topic = response[0]

                cur.execute(
                    f"""
                    SELECT f.*, p.id as paper_id, p.title, p.authors, p.update_date, p.abstract
                    FROM finding f
                    JOIN topic_finding tf ON f.id = tf.finding_id
                    JOIN paper p ON f.paper_id = p.id
                    WHERE tf.resolved_topic_id = '{topic_id}';
                    """
                )

                findings = cur.fetchall()

                depth = 3

                #                     f"""
                # WITH RECURSIVE related_data AS (
                #     -- Initial selection from resolved_topic
                #     SELECT 'resolved_topic' as type, rt.id, 1 AS depth
                #     FROM resolved_topic rt
                #     WHERE rt.id = '{topic_id}'

                #     UNION ALL

                #     -- Recursive part: Findings related to resolved_topics, then resolved_topics related to findings
                #     SELECT
                #         CASE
                #             WHEN rd.type = 'resolved_topic' THEN 'finding'
                #             ELSE 'resolved_topic'
                #         END as type,
                #         CASE
                #             WHEN rd.type = 'resolved_topic' THEN tf.finding_id
                #             ELSE tf.resolved_topic_id
                #         END as id,
                #         rd.depth + 1 AS depth
                #     FROM related_data rd
                #     JOIN topic_finding tf ON
                #         (rd.type = 'resolved_topic' AND tf.resolved_topic_id = rd.id) OR
                #         (rd.type = 'finding' AND tf.finding_id = rd.id)
                #     WHERE rd.depth < {depth}
                # )
                # SELECT * FROM related_data
                # WHERE depth <= {depth}
                # ORDER BY depth, type, id;
                #                     """

                cur.execute(
                    f"""
WITH RECURSIVE related_data AS (
    -- Initial selection from resolved_topic
-- Initial selection from resolved_topic
    SELECT 'resolved_topic' as type, rt.id, 1 AS depth, NULL::text as edge
    FROM resolved_topic rt
    WHERE rt.id = '{topic_id}'

    UNION ALL

    -- Recursive part: Findings related to resolved_topics, then resolved_topics related to findings
    SELECT 
        CASE 
            WHEN rd.type = 'resolved_topic' THEN 'finding'
            ELSE 'resolved_topic'
        END as type,
        CASE 
            WHEN rd.type = 'resolved_topic' THEN tf.finding_id
            ELSE tf.resolved_topic_id
        END as id,
        rd.depth + 1 AS depth,
        CASE
            WHEN rd.type = 'resolved_topic' THEN rd.id || ',' || tf.finding_id
            ELSE tf.resolved_topic_id || ',' || rd.id
        END as edge
    FROM related_data rd
    JOIN topic_finding tf ON 
        (rd.type = 'resolved_topic' AND tf.resolved_topic_id = rd.id) OR 
        (rd.type = 'finding' AND tf.finding_id = rd.id)
    WHERE rd.depth < {depth}
)
SELECT type, id, edge FROM related_data
WHERE depth <= {depth}
ORDER BY depth, type, id;
                    """
                )

                n_deep_data = cur.fetchall()

                # Get all topics and findings N nested levels deep

                return {**topic, "findings": findings, "n_deep_data": n_deep_data}

    except Exception as e:
        print(e)
        return {"error": str(e)}


INTERNAL_DB_CONNECTION_STR = "dbname='mydb' user='myuser' host='localhost' password='mysecretpassword' port='5432'"


@app.get("/search")
async def search_topic(query: str, type_list_str: str):

    type_list = type_list_str.split(",") if type_list_str else []

    vespa_url = "http://localhost:8080"

    # Create a Vespa client
    app = Vespa(url=vespa_url)

    try:
        type_condition = ""
        if type_list:  # Check if type_list is not empty
            type_str = ", ".join(f"'{t}'" for t in type_list)
            type_condition = (
                f" and type in ({type_str})"  # Correctly format the IN clause
            )
        res = app.query(
            body={
                "yql": f"select * from codex where default contains '{query}'{type_condition};"
            }
        )

        return [hit["fields"] for hit in res.hits]

    except Exception as e:
        print(e)
        return {"error": str(e)}
