from collections import Counter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from psycopg.rows import dict_row
from vespa.application import Vespa
import ssl
import os
import json

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

                all_topics = set()
                all_edges = set()
                all_findings = set()

                topic = response[0]

                all_topics.add(tuple(sorted(topic.items())))

                # Edges between topics and findings
                cur.execute(
                    f"""
                    SELECT tf.topic_id, tf.finding_id, tf.resolved_topic_id
                    FROM topic_finding tf
                    WHERE tf.resolved_topic_id = '{topic_id}';
                    """
                )

                edges = cur.fetchall()

                all_edges.update([tuple(sorted(edge.items())) for edge in edges])

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

                all_findings.update(
                    [tuple(sorted(finding.items())) for finding in findings]
                )

                # Edges between findings and topics
                cur.execute(
                    f"""
                    SELECT tf.topic_id, tf.finding_id, tf.resolved_topic_id
                    FROM topic_finding tf
                    WHERE tf.finding_id IN ({", ".join("'" + str(f["id"] + "'") for f in findings)}); 
                    """
                )

                edges = cur.fetchall()

                all_edges.update([tuple(sorted(edge.items())) for edge in edges])

                # Find all topics related to the findings
                cur.execute(
                    f"""
                    SELECT rt.*
                    FROM resolved_topic rt
                    JOIN topic_finding tf ON rt.id = tf.resolved_topic_id
                    WHERE tf.finding_id IN ({", ".join("'" + str(f["id"] + "'") for f in findings)});
                    """
                )

                topics = cur.fetchall()

                all_topics.update([tuple(sorted(topic.items())) for topic in topics])

                data = {
                    "topics": [dict(topic) for topic in all_topics],
                    "edges": [dict(edge) for edge in all_edges],
                    "findings": [dict(finding) for finding in all_findings],
                }

                return {
                    **topic,
                    "findings": findings,
                    "data": data,
                }

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


"""
CREATE MATERIALIZED VIEW topic_degree_count AS
SELECT
    resolved_topic_id,
    COUNT(*) AS degree
FROM
    topic_finding
GROUP BY
    resolved_topic_id;
    
CREATE INDEX topic_degree_count_degree_idx ON topic_degree_count(degree int8_ops);
"""


@app.get("/graph")
async def get_graph():
    try:
        with psycopg.connect(INTERNAL_DB_CONNECTION_STR, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT resolved_topic_id FROM topic_degree_count WHERE degree<500 ORDER BY degree DESC LIMIT 50;
                    """
                )

                response = cur.fetchall()

                topic_ids = [r["resolved_topic_id"] for r in response]

                # get just topics
                cur.execute(
                    """
                    SELECT t.id, t.name, t.id, tdc.degree
                    FROM resolved_topic t
                    JOIN topic_degree_count tdc ON t.id = tdc.resolved_topic_id
                    WHERE t.id = ANY(%(topic_ids)s)
                    """,
                    {"topic_ids": topic_ids},
                )
                topics = cur.fetchall()

                # get just findings
                cur.execute(
                    """
                    SELECT f.id as finding_id, f.paper_id, f.name
                    FROM finding f
                    JOIN topic_finding tf ON f.id = tf.finding_id
                    WHERE tf.resolved_topic_id = ANY(%(topic_ids)s)
                    """,
                    {"topic_ids": topic_ids},
                )
                findings = cur.fetchall()

                # get links
                cur.execute(
                    """
                    SELECT tf.topic_id, tf.finding_id, tf.resolved_topic_id
                    FROM topic_finding tf
                    WHERE tf.resolved_topic_id = ANY(%(topic_ids)s)
                    """,
                    {"topic_ids": topic_ids},
                )
                links = cur.fetchall()

                finding_degrees = Counter()
                for link in links:
                    finding_degrees[link["finding_id"]] += 1

                # filter out single-degree findings
                links = [
                    link for link in links if finding_degrees[link["finding_id"]] > 1
                ]

                linked_topics = set(link["resolved_topic_id"] for link in links)
                linked_findings = set(link["finding_id"] for link in links)

                # filter out unlinked
                topics = [topic for topic in topics if topic["id"] in linked_topics]
                findings = [
                    finding
                    for finding in findings
                    if finding["finding_id"] in linked_findings
                ]

                return {
                    "topics": topics,
                    "findings": findings,
                    "links": links,
                }

    except Exception as e:
        print(e)
        return {"error": str(e)}
