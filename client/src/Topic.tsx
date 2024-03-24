import { useEffect, useState } from "react";
import { Toaster } from "sonner";
import MistralClient from "@mistralai/mistralai";
import { useLocalStorage } from "usehooks-ts";
import { Link, useLoaderData } from "react-router-dom";
import { ArrowUUpLeft } from "@phosphor-icons/react";
import { TopicWithFindings } from "./App";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import { ForceGraph3D } from "react-force-graph";
// import SpriteText from "three-spritetext";
import Markdown from "marked-react";

export const Topic = () => {
  const { entity } = useLoaderData() as { entity: TopicWithFindings | null };
  const [apiKey, setApiKey] = useLocalStorage<string>("api_key", "");
  const [introResponse, setIntroResponse] = useState("");
  const [timelineResponse, setTimelineResponse] = useState("");
  const [testResponse, setTestResponse] = useState<string>("");

  const [loading, setLoading] = useState<boolean>(false);
  const [graphData, setGraphData] = useState<{
    nodes: { id: string; color: string; type: string }[];
    links: { source: string; target: string }[];
  } | null>(null);

  useEffect(() => {
    const n_deep_data = entity?.n_deep_data;

    const uniqueMap = new Map<string, object>();
    if (n_deep_data) {
      for (const obj of n_deep_data) {
        if (!uniqueMap.has(obj.id)) {
          uniqueMap.set(obj.id, obj);
        }
      }
    }
    const nodes = Array.from(uniqueMap.values()) as {
      id: string;
      type: string;
      edge: string | null;
    }[];

    const formattedNodes = nodes.map((node) => ({
      id: node.id,
      color: node.type === "finding" ? "red" : "blue",
      type: node.type,
    }));

    // Split edge by ,
    const edges = [];

    for (const node of nodes) {
      if (node.edge) {
        const edge = node.edge.split(",");
        const formattedEdge = {
          source: edge[0],
          target: edge[1],
        };
        edges.push(formattedEdge);
      }
    }

    const newGraphData = {
      nodes: formattedNodes,
      links: edges,
    };

    setGraphData(newGraphData);
  }, [entity?.n_deep_data]);

  const testMistralEndpoint = async () => {
    setLoading(true);
    const client = new MistralClient(apiKey);

    try {
      const streamResponse = await client.chatStream({
        model: "mistral-large-latest",
        messages: [
          { role: "user", content: "What is the best French cheese?" },
        ],
      });

      setTestResponse("");

      for await (const chatResponse of streamResponse) {
        setTestResponse(
          (response) => response + chatResponse.choices[0].delta.content
        );
      }

      console.log(testResponse);
    } catch (error) {
      console.error(error);
    }

    setLoading(false);
  };

  const generateIntro = async (findingsStr: string) => {
    const client = new MistralClient(apiKey);

    try {
      const content = `Your task is to write a readable markdown intro in the style of a Wikipedia page intro using findings from research papers. Include citations when necessary using markdown links to the paper IDs.
This should be no longer than 5 sentences. Focus on what the topic is and why it is important & major conclusions.

Here are the findings for the topic "${entity?.name}":
"""
${findingsStr}
"""
      // `;

      const streamResponse = await client.chatStream({
        model: "mistral-large-latest",
        messages: [{ role: "user", content }],
      });

      setIntroResponse("");

      for await (const chatResponse of streamResponse) {
        setIntroResponse(
          (response) => response + chatResponse.choices[0].delta.content
        );
      }
    } catch (error) {
      console.error(error);
    }
  };
  const generateTimeline = async (findingsStr: string) => {
    const client = new MistralClient(apiKey);

    try {
      const content = `Your task is to write a readable markdown timeline article in the style of a Wikipedia page using findings from research papers. Include citations when necessary using markdown links to the paper IDs

Here are the findings for the topic "${entity?.name}", given in chronological order:
"""
${findingsStr}
"""
      // `;

      const streamResponse = await client.chatStream({
        model: "mistral-large-latest",
        messages: [{ role: "user", content }],
      });

      setTimelineResponse("");

      for await (const chatResponse of streamResponse) {
        setTimelineResponse(
          (response) => response + chatResponse.choices[0].delta.content
        );
      }
    } catch (error) {
      console.error(error);
    }
  };

  const generateArticle = async () => {
    setLoading(true);
    try {
      const chronologicallyOrderedFindings =
        entity?.findings?.sort(
          (a, b) =>
            new Date(a.update_date).getTime() -
            new Date(b.update_date).getTime()
        ) || [];

      const findingsStr = chronologicallyOrderedFindings
        .map((finding) => JSON.stringify(finding))
        .slice(0, 30)
        .join("\n");

      await Promise.all([
        generateIntro(findingsStr),
        generateTimeline(findingsStr),
      ]);
    } catch (error) {
      console.error(error);
    }

    setLoading(false);
  };

  return (
    <div className="flex flex-col items-center px-2">
      <Toaster />
      <div className="flex flex-col w-full max-w-screen-md space-y-6 py-12">
        <Link to="/">
          <ArrowUUpLeft size={24} />
        </Link>
        <div className="h-16">
          {entity ? (
            <>
              <h2>{entity.type}</h2>
              <h1 className="text-3xl">{entity.name}</h1>
            </>
          ) : (
            <Skeleton height={30} width={240} />
          )}
        </div>
        <div>
          {entity ? <p>{entity.description}</p> : <Skeleton count={3} />}
        </div>
        <div className="flex flex-col space-y-2 p-4 rounded-md bg-gray-50 border-gray-200 border">
          <p className="text-xl text-gray-700">
            Generate an article for this topic
          </p>

          <label htmlFor="api_key" className="text-gray-500">
            API Key
          </label>
          <input
            id="api_key"
            type="text"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1"
          />
          <button
            onClick={generateArticle}
            disabled={loading}
            className="bg-blue-500 text-white rounded px-3 py-1 disabled:opacity-50"
          >
            Generate
          </button>
          <button
            onClick={testMistralEndpoint}
            disabled={loading}
            className="bg-white text-blue-500 border border-blue-500 rounded px-3 py-1 disabled:opacity-50"
          >
            Test endpoint
          </button>

          <div className="border border-gray-300 rounded px-2 py-1 bg-gray-50 whitespace-pre-wrap text-gray-600">
            {testResponse || "What is the best French cheese?"}
          </div>
        </div>
        <div className="markdown">
          <h1>Introduction</h1>
          {introResponse && <Markdown>{introResponse}</Markdown>}
        </div>
        <div className="markdown">
          <h1>Timeline</h1>
          {timelineResponse && <Markdown>{timelineResponse}</Markdown>}
        </div>
        {graphData && (
          <div className="border border-gray-200 rounded w-fit overflow-hidden self-center">
            <ForceGraph3D
              width={512}
              height={512}
              backgroundColor={"#f9f9f9"}
              linkColor={() => "rgba(0,0,0,0.2)"}
              graphData={graphData}
              // nodeThreeObject={(node: {
              //   id: string;
              //   name: string;
              //   color: string;
              //   type: string;
              // }) => {
              //   const sprite = new SpriteText(node.name);
              //   sprite.color = node.color;
              //   sprite.textHeight = 8;
              //   return sprite;
              // }}
            />
          </div>
        )}
        {entity && (
          <div className="flex flex-col space-y-2">
            <h2 className="text-lg">Findings</h2>
            <div className="flex flex-col space-y-2">
              {entity.findings?.length > 0 ? (
                entity.findings.map((finding) => (
                  <div key={finding.id} className="flex flex-col space-y-1">
                    <a
                      href={`https://arxiv.org/abs/${finding.paper_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="underline text-blue-500 text-sm"
                    >
                      {finding.paper_id}: {finding.title}
                    </a>
                    <h3 className="font-bold">{finding.name}</h3>
                    <p>{finding.description}</p>
                    <hr />
                  </div>
                ))
              ) : (
                <>No findings</>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
